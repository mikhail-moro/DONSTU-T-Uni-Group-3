import regex as re


import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("module://kivy_garden.matplotlib.backend_kivy")

from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivy

from kivymd.uix.datatables.datatables import MDDataTable, CellRow  # noqa
from kivymd.uix.button import MDFillRoundFlatButton, MDIconButton
from kivymd.uix.anchorlayout import MDAnchorLayout
from kivymd.uix.list import OneLineAvatarListItem, MDList
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.app import MDApp

from kivy.properties import OptionProperty, ObjectProperty
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp

from database import UserItems, Item, Database, DATETIME_FORMAT

import typing as T  # noqa

if T.TYPE_CHECKING:
    from database import AppDatabase
    from kivy.uix.widget import Widget
    from kivymd.uix.widget import MDWidget
    WidgetT = T.Union[MDWidget, Widget, T.Type[MDWidget], T.Type[Widget]]


MOBILE = {
    'ui': """
MDBoxLayout:
    id: main_layout
    orientation: 'vertical'
    MDAnchorLayout:
        id: table
        size_hint_y: 0.4
        padding_y: (None, 30)
        padding_x: (0.0, 0.0)
        anchor_x: 'center'
        anchor_y: 'top'
    MDAnchorLayout:
        id: controls
        size_hint_y: 0.6
        padding_y: (30, None)
        anchor_x: 'center'
        anchor_y: 'bottom'
""",
    'data_edit_font_size': 28,
    'buttons_font_size': 22,
    'columns_sizes': [36, 56, 36, 10],
    'plot_font_size': 14
}

DESKTOP = {
    'ui': """
MDBoxLayout:
    id: main_layout
    orientation: 'horizontal'
    MDAnchorLayout:
        id: table
        size_hint_x: 0.5
        size_hint_y: 1.0
        anchor_x: 'right'
        anchor_y: 'center'
    MDAnchorLayout:
        id: controls
        size_hint_x: 0.5
        size_hint_y: 1.0
        anchor_x: 'left'
        anchor_y: 'center'
""",
    'data_edit_font_size': 18,
    'buttons_font_size': 16,
    'columns_sizes': [16, 28, 14, 8],
    'plot_font_size': 14
}

CONFIG: dict


def _columns_size() -> T.List[float]:
    """
    All columns size in configs are set for 720p width,
    for another screen widths, columns will be linear resized.
    """
    k = Window.system_size[0] / 720
    return [dp(s*k) for s in CONFIG['columns_sizes']]


# Kivy and KivyMD haven't functional to create custom text validation,
# 'cause of it just override exist validation methods.
class MDTextFieldWithValidation(MDTextField):
    validator: str = OptionProperty(None, options=["date", "email", "time", "phone", "description", "price", "no null"])
    on_validation_change: T.Callable[[bool], None] = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_validation_change = kwargs['on_validation_change']

    def is_descripton_invalid(self, text: str) -> bool: # noqa
        """
        Description string must be non-empty and contain only letters and digits
        """
        if re.match(r"\A[A-Za-zА-Яа-я0-9]+\Z", text) is not None and len(text) > 0:
            return False
        return True

    def is_price_invalid(self, text: str) -> bool: # noqa
        """
        Price string should have one of these formats - d, d., .d, d.d (d - any digit [0-9]).
        Examples: 0, 10., .99, 149.99
        """
        if any([
            re.match(r"\A\d+\.\d+\Z", text) is not None,  # 0.99
            re.match(r"\A\d+\.\Z", text) is not None,  # 99.
            re.match(r"\A\.\d+\Z", text) is not None,  # .99
            re.match(r"\A\d+\Z", text) is not None  # 99
        ]):
            if len(text) > 0:
                return False
        return True

    def is_null(self, text: str) -> bool: # noqa
        return len(text.strip()) == 0

    def _get_has_error(self) -> bool:
        """
        Returns `False` or `True` depending on the state of the text field,
        for example when the allowed character limit has been exceeded or when
        the :attr:`~MDTextField.required` parameter is set to `True`.
        """
        if self.validator and self.validator != "phone":
            has_error = {
                "date": self.is_date_valid,
                "email": self.is_email_valid,
                "time": self.is_time_valid,
                "no null": self.is_null,
                "price": self.is_price_invalid,
                "description": self.is_descripton_invalid
            }[self.validator](self.text)
            self.on_validation_change.__call__(has_error) # noqa
            return has_error
        if self.max_text_length and len(self.text) > self.max_text_length:
            has_error = True
        else:
            if all((self.required, len(self.text) == 0)):
                has_error = True
            else:
                has_error = False
        return has_error


class Plot(FigureCanvasKivy):
    datatable: MDDataTable

    def __init__(self, datatable_instance: MDDataTable, **kwargs):
        fig, ax = plt.subplots()
        fig.figure.tight_layout()
        ax.pie([])
        super().__init__(fig, **kwargs)
        self.datatable = datatable_instance

    def redraw(self, sender: 'WidgetT'):
        desc = []
        price = []
        for row in self.datatable.row_data:
            desc.append(row[0])
            price.append(float(row[2]))

        self.figure.clear()
        _, labels = self.figure.gca().pie(x=price, labels=desc)
        for label in labels: label.set_fontsize(CONFIG['plot_font_size']) # noqa

        # 'Cause of kivy_garden.matplotlib bug, pie plot will be rendered without text if xticks not passed.
        # To hide xticks set it color to color of figure background
        self.figure.gca().set_xticks([1])
        self.figure.gca().tick_params(axis='x', colors=self.figure.get_facecolor())
        self.draw()

    def clear(self, sender: 'WidgetT'):
        self.figure.clear()
        self.figure.gca().pie(x=[])
        self.draw()


class NewUserDialog(MDDialog):
    on_username_passed = ObjectProperty(None)

    def __init__(
        self,
        on_username_passed: T.Callable[[str], None],
        **kwargs
    ):
        self.on_username_passed = on_username_passed

        self.back = MDIconButton(
            icon="arrow-left",
            on_press=self.on_back_press,
        )
        self.create = MDIconButton(
            icon="plus",
            on_press=self.on_create_press,
        )
        self.field = MDTextFieldWithValidation(
            text="Username",
            hint_text="",
            validator="no null",
            on_validation_change=self.on_text_invalid,
            font_size=CONFIG['data_edit_font_size']
        )
        super().__init__(
            title="New user",
            type="custom",
            content_cls=self.field,
            buttons=[self.back, self.create],
            **kwargs
        )

    def on_text_invalid(self, has_error: bool):
        self.create.disabled = has_error

    def on_back_press(self, sender: 'WidgetT'):
        self.dismiss(force=True)

    def on_create_press(self, sender: 'WidgetT'):
        self.on_username_passed(self.field.text)
        self.dismiss(force=True)


class UserSelectDialog(MDDialog):
    users_list: MDList
    current_pid: int = 0
    selected_user: str = None
    num_users_per_page: int

    def __init__(
        self,
        database_instance: 'AppDatabase',
        num_users_per_page: int,
        on_select: T.Callable[[str], None],
        **kwargs
    ):
        self.on_select = on_select
        self.new_dialog = NewUserDialog(on_username_passed=self.on_new_user)
        self.database_instance = database_instance
        self.num_users_per_page = num_users_per_page

        self.users_list = MDList(*self._get_users())

        super().__init__(
            title="Select user",
            type="custom",
            content_cls=self.users_list,
            buttons=[
                MDFillRoundFlatButton(
                    text="New",
                    on_press=self.on_new_press,
                    disabled=False
                ),
                MDIconButton(
                    icon="arrow-left",
                    on_press=self.on_left_press,
                    disabled=True
                ),
                MDIconButton(
                    icon="arrow-right",
                    on_press=self.on_right_press,
                    disabled=False
                ),
            ],
            **kwargs
        )

    def on_left_press(self, sender: 'WidgetT'):
        self.current_pid -= 1
        self.users_list.clear_widgets()

        for user in self._get_users():
            self.users_list.add_widget(user)
        self.buttons[1].disabled = self.current_pid == 0

    def on_right_press(self, sender: 'WidgetT'):
        self.current_pid += 1
        self.users_list.clear_widgets()

        for user in self._get_users():
            self.users_list.add_widget(user)
        self.buttons[2].disabled = len(self.users_list.children) == 0

    def on_new_press(self, sender: 'WidgetT'):
        self.new_dialog.open()

    def item_press(self, sender: 'WidgetT'):
        self.on_select(sender.text)
        self.dismiss(force=True)

    def on_new_user(self, user_id: str):
        self.database_instance.create_user(user_id=user_id)
        self.on_select(user_id)
        self.dismiss(force=True)

    def _get_users(self) -> list[str] | None:
        users = self.database_instance.iter_all_users(self.current_pid, self.num_users_per_page)
        return [OneLineAvatarListItem(text=user, on_press=self.item_press) for user in users]


class Controls(MDBoxLayout):
    def __init__(
        self,
        datatable_instance: 'Table',
        database_instance: 'AppDatabase',
        *args,
        **kwargs
    ):
        self.datatable_instance = datatable_instance
        self.database_instance = database_instance

        super().__init__(
            *args,
            orientation='vertical',
            padding=(10, 10, 10, 10),
            spacing=32,
            **kwargs
        )

        # Link table with it controls
        def on_row_data_press(desc: str, price: float):
            self.set(desc=desc, price=price)

        def on_row_delete_press(desc: str):
            self.database_instance.delete_data_by_id(self.user_id, [desc])
            self.datatable_instance.update()

        self.datatable_instance.on_row_data_press = on_row_data_press
        self.datatable_instance.on_row_delete = on_row_delete_press

        # Anchors
        self.top_anchor = MDAnchorLayout(anchor_x='center', anchor_y='top', size_hint=(1, 0.4))
        self.bottom_anchor = MDAnchorLayout(anchor_x='center', anchor_y='bottom', size_hint=(1, 0.6))

        # Cell values and add record button
        self.data_edit_wrapper = MDBoxLayout(orientation='vertical', padding=(dp(20), 0))
        self.desc = MDTextFieldWithValidation(
            text="",
            hint_text="Description",
            helper_text='Only letters and digits',
            validator='description',
            on_validation_change=self.on_text_invalid,
            font_size=CONFIG['data_edit_font_size']
        )
        self.price = MDTextFieldWithValidation(
            text="0.0",
            hint_text="Price",
            helper_text="Only digits",
            validator='price',
            on_validation_change=self.on_text_invalid,
            font_size=CONFIG['data_edit_font_size']
        )
        self.add = MDFillRoundFlatButton(
            text='Apply',
            size_hint=(0.27, None),
            pos_hint={'center_x': 0.5},
            font_size=CONFIG['buttons_font_size'],
            on_press=self.on_add_press
        )
        self.data_edit_wrapper.add_widget(self.desc)
        self.data_edit_wrapper.add_widget(self.price)
        self.data_edit_wrapper.add_widget(self.add)

        # Plot and it controls
        self.plot_wrapper = MDBoxLayout(orientation='vertical')
        self.plot = Plot(self.datatable_instance, size_hint=(0.92, 3), pos_hint={'center_x': .5})

        self.plot_controls_wrapper = MDAnchorLayout(anchor_x='center', anchor_y='center')
        self.plot_controls = MDBoxLayout(size_hint=(0.4, 0.5))

        self.plot_draw = MDAnchorLayout(
            MDFillRoundFlatButton(
                text='Plot',
                on_press=self.plot.redraw,
                font_size=CONFIG['buttons_font_size'],
                size_hint=(0.27, None)
            ),
            anchor_x='left'
        )
        self.plot_clear = MDAnchorLayout(
            MDFillRoundFlatButton(
                text='Clear',
                on_press=self.plot.clear,
                font_size=CONFIG['buttons_font_size'],
                size_hint=(0.27, None)
            ),
            anchor_x='right'
        )
        self.plot_controls.add_widget(self.plot_draw)
        self.plot_controls.add_widget(self.plot_clear)

        self.plot_controls_wrapper.add_widget(self.plot_controls)
        self.plot_wrapper.add_widget(self.plot)
        self.plot_wrapper.add_widget(self.plot_controls_wrapper)

        self.top_anchor.add_widget(self.data_edit_wrapper)
        self.bottom_anchor.add_widget(self.plot_wrapper)
        self.add_widget(self.top_anchor)
        self.add_widget(self.bottom_anchor)

    def set(self, desc: str, price: float):
        self.desc.text = desc
        self.price.text = str(price)

    def set_user(self, user_id: str):
        self.user_id = user_id

    def on_text_invalid(self, has_error: bool):
        self.add.disabled = has_error

    def on_add_press(self, sender: 'WidgetT'):
        data = Item(
            description=self.desc.text,
            price=float(self.price.text)
        )
        self.database_instance.add_data_by_id(self.user_id, UserItems(data))
        self.datatable_instance.update()

        self.desc.text = ""
        self.price.text = ""


class Table(MDDataTable):
    on_row_delete: T.Callable[[str, float], None] = ObjectProperty(None)
    on_row_data_press: T.Callable[[str, float], None] = ObjectProperty(None)

    def __init__(
        self,
        database_instance: 'AppDatabase',
        **kwargs
    ):
        self.database_instance = database_instance
        columns_size = _columns_size()

        super().__init__(
            column_data=[
                ("Description", columns_size[0]),
                ("Time", columns_size[1], self.sort_time),
                ("Price", columns_size[2], self.sort_price),
                ("", columns_size[3])
            ],
            use_pagination=True,
            **kwargs
        )

    def set_user(self, user_id: str):
        self.user_id = user_id

    def update(self):
        data = self.database_instance.get_data_by_id(self.user_id)

        self.row_data = [
            (
                item.description,
                item.time.strftime(DATETIME_FORMAT),
                item.price,
                ("delete", [0.1, 0.1, 0.1, 1], "",)
            )
            for item in data.items
        ]

    def sort_time(self, row: CellRow):  # noqa
        return zip(*sorted(enumerate(row), key=lambda d: d[1][1]))

    def sort_price(self, row: CellRow):  # noqa
        return zip(*sorted(enumerate(row), key=lambda d: d[1][2]))

    def on_row_press(self, instance_cell_row: CellRow):
        row_data = self.row_data[int(instance_cell_row.index / len(self.column_data))]

        if instance_cell_row.index % (len(self.column_data)-1) == 0:
            self.on_row_delete(row_data[0]) # noqa
        else:
            self.on_row_data_press(row_data[0], float(row_data[2])) # noqa


class Main(MDApp):
    user_select: UserSelectDialog
    database_instance: 'AppDatabase'

    def __init__(self, database_instance: 'AppDatabase', **kwargs):
        self.database_instance = database_instance
        super().__init__(**kwargs)

    def on_start(self):
        self.user_select.open()

    def build(self):
        root = Builder.load_string(CONFIG['ui'])

        table = Table(database_instance=self.database_instance)
        controls = Controls(
            datatable_instance=table,
            database_instance=self.database_instance,
        )

        def on_select(user_id: str):
            controls.set_user(user_id)
            table.set_user(user_id)
            table.update()

        self.user_select = UserSelectDialog(
            self.database_instance,
            num_users_per_page=5,
            on_select=on_select
        )

        root.ids.table.add_widget(table)
        root.ids.controls.add_widget(controls)
        return root


def run(dotenv_path: str = None, config: T.Literal['mobile', 'desktop'] = 'mobile'):
    global CONFIG, DESKTOP, MOBILE

    if config == 'desktop':
        CONFIG = DESKTOP
    elif config == 'mobile':
        CONFIG = MOBILE
    else:
        raise ValueError("config param must be one of ['mobile', 'desktop']")

    import const
    if dotenv_path:
        const.load_dotenv(dotenv_path)

    database = Database()
    Main(database_instance=database).run()
