import os
import sys

import typing as T

import firebase_admin as fba
import firebase_admin.firestore as fs

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget
)
from PySide6.QtCharts import QChartView, QPieSeries, QChart


if T.TYPE_CHECKING:
    from google.cloud.firestore import CollectionReference, Client
    from google.cloud.firestore_v1.types.write import WriteResult


Scalar = T.Union[int, float]
CURRENT_DIR = os.path.dirname(__file__)


class FireBaseDatabase:
    _app: fba.App

    _fs_client: 'Client'
    _col: 'CollectionReference'

    def __init__(
        self,
        credentials: T.Union[str, os.PathLike, fba.credentials.Certificate],
        collection_name: str = 'default'
    ):
        if not isinstance(credentials, fba.credentials.Certificate):
            credentials = fba.credentials.Certificate(credentials)

        self._app = fba.initialize_app(credential=credentials)
        self._fs_client = fs.client(app=self._app)
        self._col = self._fs_client.collection(collection_name)

    def get_data_by_uid(self, uid: str = 'main') -> T.Dict[str, Scalar]:
        return self._col.document(uid).get().to_dict()

    def add_data_by_uid(
        self,
        field: T.Hashable,
        value: T.Union[str, Scalar],
        uid: str = 'main'
    ) -> 'WriteResult':
        return self._col.document(uid).set({field: value}, merge=True)


class Widget(QWidget):
    def __init__(self, database: FireBaseDatabase, user_id: str = 'main'):
        super().__init__()
        self.items = 0

        # Example data
        """
        self._data = {
            "Water": 24.5, "Electricity": 55.1, "Rent": 850.0, "Supermarket": 230.4, "Internet": 29.99,
            "Bars": 21.85, "Public transportation": 60.0, "Coffee": 22.45, "Restaurants": 120
        }
        """

        self._db = database
        self._uid = user_id
        self._data = database.get_data_by_uid(user_id)

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

        self._db.add_data_by_uid(
            field=des,
            value=price,
            uid=self._uid
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
    def check_disable(self, s):
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

    def fill_table(self, data=None):
        data = self._data if not data else data
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


class MainWindow(QMainWindow):
    def __init__(self, widget):
        super().__init__()
        self.setWindowTitle("Tutorial")

        # Menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        # Exit QAction
        exit_action = self.file_menu.addAction("Exit", self.close)
        exit_action.setShortcut("Ctrl+Q")

        self.setCentralWidget(widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    db = FireBaseDatabase(credentials=os.path.join(CURRENT_DIR, 'credentials', 'credentials/credentials.json'))

    widget = Widget(database=db)
    window = MainWindow(widget)
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec())
