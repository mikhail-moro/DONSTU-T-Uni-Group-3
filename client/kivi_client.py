import sys
import typing as T
import matplotlib.pyplot as plt

from tools import add_on_destroy_callback
from database import Database, Value

if T.TYPE_CHECKING:
    from database import AppDatabase

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
#from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
#from kivy_matplotlib_widget.uix.graph_widget import FigureCanvasAgg

from kivymd.uix.datatables import MDDataTable


class Widget(App):
    items: int = 0

    _db: 'AppDatabase'
    _data: T.Dict[str, Value]
    _doc_id: str

    def __init__(self, database: 'AppDatabase', doc_id: str):
        self._db = database
        self._data = database.get_data_by_id(doc_id)
        self._doc_id = doc_id
        super().__init__()

    def build(self):
        # Left
        self.table = MDDataTable(cols=2)
        # Chart
        #self.chart_view = FigureCanvasAgg()

        # Right
        self.description = BoxLayout(orientation='horizontal')
        self.description.add_widget(Label(text='Description'))
        self.description.add_widget(TextInput())

        self.price = BoxLayout(orientation='horizontal')
        self.price.add_widget(Label(text='Price'))
        self.price.add_widget(TextInput())

        self.add = Button(text="Add")
        self.plot = Button(text="Plot")
        self.clear = Button(text="Clear")

        # Disabling 'Add' button
        self.add.set_disabled(True)

        form_layout = BoxLayout(orientation='vertical')
        form_layout.add_widget(self.description)
        form_layout.add_widget(self.price)

        self.right = BoxLayout(orientation='vertical')
        self.right.add_widget(form_layout)
        self.right.add_widget(self.add)
        self.right.add_widget(self.plot)
        #self.right.add_widget(self.chart_view)
        self.right.add_widget(self.clear)

        # QWidget Layout
        self.layout = BoxLayout(orientation='horizontal')
        self.layout.add_widget(self.table)
        self.layout.add_widget(self.right)

        # Signals and Slots
        self.add.on_press = self.add_element
        self.plot.on_press = self.plot_data
        self.clear.on_press = self.clear_table
        self.description.on_press = self.check_disable
        self.price.on_press = self.check_disable

        # Fill example data
        self.fill_table()

        return self.layout

    def add_element(self):
        des = self.description.text()
        price = float(self.price.text())

        self._db.add_data_by_id(
            user_id=self._doc_id,
            **{des: price}
        )
        self.table.add_row([des, str(price)])

        self.description.children[1].text = ''
        self.price.children[1].text = ''

    def check_disable(self):
        enabled = bool(
            self.description.children[1].text
            and
            self.price.children[1].text
        )
        self.add.setEnabled(enabled)

    def plot_data(self):
        """
        prices = []
        desc = []

        for i in range(1, len(self.table.children)):
            prices.append(float(self.table.children[i][1]))
            desc.append(self.table.children[i][0])

        plt.pie(prices, labels=desc)
        """
        return None

    def fill_table(self, data: T.Dict[str, T.Iterable[T.Any]] = None):
        if data is None:
            data = self._data

        for desc, price in data.items():
            self.table.add_row([desc, str(price)])

    def clear_table(self):
        for i in range(1, len(self.table.data)):
            del self.table.table_data[i]


def run():
    import tools
    tools.load_dotenv('.env')

    import database
    db = database.Database()

    app = Widget(database=db, doc_id='New')
    app.build()
    app.run()

    sys.exit(app.exec())


if __name__ == '__main__':
    run()
