import sys
import functools
import typing as T # noqa

from PySide6.QtCore import Qt, Slot, QModelIndex
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QTableWidgetItem,
    QApplication,
    QTableWidget,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QListWidget,
    QLineEdit,
    QDialog,
    QWidget
)
from PySide6.QtCharts import QChartView, QPieSeries, QChart


if T.TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from database import AppDatabase, Value

    # QWidget or it subclasses
    QType = T.Union[T.NewType('QSubType', QWidget), QWidget]


def add_on_destroy_callback(
        widget: 'QType',
        callback: T.Callable[['QType'], None],
        position: T.Literal['before', 'after'] = 'before'
) -> 'QType':
    if position == 'before':
        def new_destroy(self: 'QType'):
            callback(self)
            super(self.__class__, self).destroy()
    else:
        def new_destroy(self: 'QType'):
            super(self.__class__, self).destroy()
            callback(self)
    widget.destroy = functools.partial(new_destroy, widget)
    return widget


class Widget(QWidget):
    items: int = 0

    _db: 'AppDatabase'
    _data: T.Dict[str, 'Value']
    _doc_id: str

    def __init__(self, parent, database: 'AppDatabase', doc_id: str):
        super().__init__(parent)

        self._db = database
        self._data = database.get_data_by_id(doc_id)
        self._doc_id = doc_id

        # Left
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Description", "Price"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Chart
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.Antialiasing)

        # Right
        self.description = QLineEdit()
        self.description.setClearButtonEnabled(True)
        self.price = QLineEdit()
        self.price.setClearButtonEnabled(True)

        self.add = QPushButton("Add")
        self.clear = QPushButton("Clear")
        self.plot = QPushButton("Plot")

        # Disabling 'Add' button
        self.add.setEnabled(False)

        form_layout = QFormLayout()
        form_layout.addRow("Description", self.description)
        form_layout.addRow("Price", self.price)
        self.right = QVBoxLayout()
        self.right.addLayout(form_layout)
        self.right.addWidget(self.add)
        self.right.addWidget(self.plot)
        self.right.addWidget(self.chart_view)
        self.right.addWidget(self.clear)

        # QWidget Layout
        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.table)
        self.layout.addLayout(self.right)

        # Signals and Slots
        self.add.clicked.connect(self.add_element)
        self.plot.clicked.connect(self.plot_data)
        self.clear.clicked.connect(self.clear_table)
        self.description.textChanged.connect(self.check_disable)
        self.price.textChanged.connect(self.check_disable)

        # Fill example data
        self.fill_table()

    @Slot()
    def add_element(self):
        des = self.description.text()
        price = float(self.price.text())

        self._db.add_data_by_id(
            user_id=self._doc_id,
            **{des: price}
        )

        self.table.insertRow(self.items)
        description_item = QTableWidgetItem(des)
        price_item = QTableWidgetItem(f"{price:.2f}")
        price_item.setTextAlignment(Qt.AlignRight)

        self.table.setItem(self.items, 0, description_item)
        self.table.setItem(self.items, 1, price_item)

        self.description.clear()
        self.price.clear()

        self.items += 1

    @Slot()
    def check_disable(self):
        enabled = bool(self.description.text() and self.price.text())
        self.add.setEnabled(enabled)

    @Slot()
    def plot_data(self):
        # Get table information
        series = QPieSeries()
        for i in range(self.table.rowCount()):
            text = self.table.item(i, 0).text()
            number = float(self.table.item(i, 1).text())
            series.append(text, number)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().setAlignment(Qt.AlignLeft)
        self.chart_view.setChart(chart)

    def fill_table(self, data: T.Dict[str, T.Iterable[T.Any]] = None):
        if data is None:
            data = self._data

        for desc, price in data.items():
            description_item = QTableWidgetItem(desc)
            price_item = QTableWidgetItem(f"{price:.2f}")
            price_item.setTextAlignment(Qt.AlignRight)
            self.table.insertRow(self.items)
            self.table.setItem(self.items, 0, description_item)
            self.table.setItem(self.items, 1, price_item)
            self.items += 1

    @Slot()
    def clear_table(self):
        self.table.setRowCount(0)
        self.items = 0


class ChangeDialog(QDialog):
    _row_index2doc: T.Dict[int, T.Any] = {}
    current_row: int
    current_item: str

    def __init__(self, parent, database: 'AppDatabase'):
        super().__init__(parent)

        def newdoc_destroy_callback(newdoc: NewDocDialog) -> None:
            database.create_user(newdoc.text)
            self.current_item = newdoc.text
            self.destroy()

        self.setWindowTitle('Set data document')

        self.newdocDialog = NewDocDialog(self)
        self.newdocDialog = add_on_destroy_callback(self.newdocDialog, newdoc_destroy_callback) # noqa

        self.listView = QListWidget(self)
        self.listView.clicked.connect(self.list_widget_item_clicked)
        self.buttonBox = QDialogButtonBox(self)

        self.selectBtn = QPushButton('Select', self)
        self.cancelBtn = QPushButton('Cancel', self)
        self.newdocBtn = QPushButton('New', self)

        self.selectBtn.clicked.connect(self.select)
        self.cancelBtn.clicked.connect(self.cancel)
        self.newdocBtn.clicked.connect(self.newdoc)

        self.buttonBox.addButton(self.selectBtn, QDialogButtonBox.ButtonRole.NoRole)
        self.buttonBox.addButton(self.cancelBtn, QDialogButtonBox.ButtonRole.NoRole)
        self.buttonBox.addButton(self.newdocBtn, QDialogButtonBox.ButtonRole.NoRole)

        self.selectBtn.setEnabled(False)

        index = 0
        for batch in database.iter_all_users(n=10):
            for row, doc in enumerate(batch):
                self._row_index2doc[index+row] = doc
                self.listView.insertItem(index+row, doc)
            index += len(batch)

        layout = QVBoxLayout(self)
        layout.addWidget(self.listView)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def select(self) -> None:
        self.current_item = self._row_index2doc[self.current_row]
        self.destroy()

    def cancel(self) -> None:
        sys.exit(1)

    def newdoc(self) -> None:
        self.newdocDialog.show()

    def list_widget_item_clicked(self, item: QModelIndex):
        self.current_row = item.row()
        self.selectBtn.setEnabled(True)

    def get_selected_doc(self) -> T.Any:
        return self.current_item


class NewDocDialog(QDialog):
    text: str

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle('Add doc')

        self.textInput = QLineEdit(self)
        self.ok = QPushButton('Ok')
        self.ok.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.textInput)
        layout.addWidget(self.ok)
        self.setLayout(layout)

    def accept(self) -> None:
        self.text = self.textInput.text()
        self.destroy()


class MainWindow(QMainWindow):
    def __init__(self, database: 'AppDatabase'):
        super().__init__()

        def dialog_destroy_callback(dialog_instance: ChangeDialog):
            widget = Widget(
                self,
                database=database,
                doc_id=dialog_instance.get_selected_doc()
            )
            self.setCentralWidget(widget)
            widget.show()

        dialog = ChangeDialog(self, database=database)
        dialog = add_on_destroy_callback(dialog, dialog_destroy_callback, position='after')
        dialog.show()

        self.setWindowTitle("Tutorial")

        # Menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        # Exit QAction
        exit_action = self.file_menu.addAction("Exit", self.close)
        exit_action.setShortcut("Ctrl+Q")


def run(dotenv_path: str = None):

    if dotenv_path:
        import const
        const.load_dotenv(dotenv_path)

    import database
    db = database.Database()

    app = QApplication(sys.argv)
    window = MainWindow(database=db)
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    run('.env')
