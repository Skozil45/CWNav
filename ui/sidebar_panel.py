"""Sidebar controls and search panel for CWNav."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QComboBox, QSpinBox
)


class SidebarPanel(QWidget):
    """Encapsulates store search, route selection, and nearby facilities."""

    def __init__(self, window):
        super().__init__()
        self.window = window

        side = QVBoxLayout(self)
        side.setContentsMargins(6, 8, 18, 8)

        # Store search section
        side.addWidget(self._heading('Find a store or facility'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Name or unit number, e.g. Fore or 53')
        self.search.setAccessibleName('Search stores by name or unit number')
        side.addWidget(self.search)

        self.stores = QListWidget()
        self.stores.setAccessibleName('Search results; Enter selects a destination')
        self.stores.setMinimumHeight(100)
        self.stores.setMaximumHeight(230)
        side.addWidget(self.stores)

        # Route preference section
        side.addWidget(self._heading('Your route'))
        self.transport = QComboBox()
        self.transport.addItems(['Any floor connection', 'Lifts only', 'Escalators only'])
        self.transport.setAccessibleName('Route transport preference')
        side.addWidget(self.transport)

        self.route_label = self._label('Choose a destination to plan a route.')
        side.addWidget(self.route_label)

        clear_btn = QPushButton('Clear destination')
        clear_btn.clicked.connect(self.window.clear_destination)
        side.addWidget(clear_btn)

        # Nearby facilities section
        side.addWidget(self._heading('Nearby on your floor'))
        self.category = QComboBox()
        self.category.addItems(['All', 'Dining', 'Toilets', 'Lifts', 'Escalators', 'ATMs', 'Stores'])
        self.category.setAccessibleName('Facility category')
        self.category.setCurrentText('Dining')
        side.addWidget(self.category)

        radius_row = QHBoxLayout()
        radius_label = QLabel('Search radius')
        self.radius = QSpinBox()
        self.radius.setRange(5, 60)
        self.radius.setValue(20)
        self.radius.setSuffix(' m (approx.)')
        self.radius.setAccessibleName('Search radius in approximate meters')
        radius_label.setBuddy(self.radius)
        radius_row.addWidget(radius_label)
        radius_row.addWidget(self.radius)
        side.addLayout(radius_row)

        self.near_status = self._label('')
        side.addWidget(self.near_status)

        self.nearby_list = QListWidget()
        self.nearby_list.setAccessibleName('Nearby facilities; Enter selects a destination')
        self.nearby_list.setMinimumHeight(90)
        self.nearby_list.setMaximumHeight(180)
        side.addWidget(self.nearby_list)

        side.addWidget(self._label('Nearby = straight-line distance. Routes follow corridors.\n20 m expands to 40 / 60 m when empty.'))
        side.addStretch()

        self._wire_signals()

    def _wire_signals(self) -> None:
        self.search.textChanged.connect(self.window.filter_stores)
        self.stores.itemClicked.connect(self.window.select_item)
        self.stores.itemActivated.connect(self.window.select_item)
        self.nearby_list.itemClicked.connect(self.window.select_item)
        self.nearby_list.itemActivated.connect(self.window.select_item)
        self.category.currentTextChanged.connect(self.window.refresh)
        self.radius.valueChanged.connect(self.window.refresh)
        self.transport.currentIndexChanged.connect(self.window.change_transport)

    def _heading(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setTextFormat(Qt.TextFormat.PlainText)
        lbl.setWordWrap(True)
        lbl.setObjectName('heading')
        return lbl

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setTextFormat(Qt.TextFormat.PlainText)
        lbl.setWordWrap(True)
        return lbl
