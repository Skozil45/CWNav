from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QComboBox, QSpinBox, QToolButton, QSizePolicy
)
from navigation import CATEGORIES


class SidebarPanel(QWidget):
    """Encapsulates store search, route selection, and nearby facilities."""

    def __init__(self, window):
        super().__init__()
        self.window = window

        side = QVBoxLayout(self)
        side.setContentsMargins(6, 8, 18, 8)
        side.setSpacing(6)

        search_section = self._accordion(side, 'Find a store or facility', True)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Name or unit number, e.g. Fore or 53')
        self.search.setAccessibleName('Search stores by name or unit number')
        search_section.addWidget(self.search)

        self.stores = QListWidget()
        self.stores.setAccessibleName('Search results; Enter selects a destination')
        self.stores.setFixedHeight(230)
        search_section.addWidget(self.stores)

        side.addWidget(self._heading('Your route'))

        self.route_label = self._label('Choose a destination to plan a route.')
        side.addWidget(self.route_label)

        nearest_section = self._accordion(side, 'Nearest by walking route')
        self.route_category = QComboBox()
        self.route_category.addItems(CATEGORIES)
        self.route_category.setCurrentText('Dining')
        self.route_category.setAccessibleName('Category for shortest walking route')
        nearest_section.addWidget(self.route_category)
        self.find_nearest = QPushButton('Find nearest')
        self.find_nearest.clicked.connect(self.window.find_nearest_place)
        nearest_section.addWidget(self.find_nearest)
        self.nearest_status = self._label('Across both floors. Uses route preference, not nearby radius.')
        nearest_section.addWidget(self.nearest_status)

        nearby_section = self._accordion(side, 'Nearby on your floor')
        self.category = QComboBox()
        self.category.addItems(CATEGORIES)
        self.category.setAccessibleName('Facility category')
        self.category.setCurrentText('Dining')
        nearby_section.addWidget(self.category)

        radius_row = QHBoxLayout()
        radius_label = QLabel('Search radius')
        self.radius = QSpinBox()
        self.radius.setRange(5, 60)
        self.radius.setValue(20)
        self.radius.setSuffix(' m')
        self.radius.setAccessibleName('Search radius in meters')
        radius_label.setBuddy(self.radius)
        radius_row.addWidget(radius_label)
        radius_row.addWidget(self.radius)
        nearby_section.addLayout(radius_row)

        # Unified nearby card: header bar + list widget
        nearby_box = QVBoxLayout()
        nearby_box.setSpacing(0)

        self.near_status = QLabel('')
        self.near_status.setObjectName('near_header')
        self.near_status.setTextFormat(Qt.TextFormat.PlainText)
        nearby_box.addWidget(self.near_status)

        self.nearby_list = QListWidget()
        self.nearby_list.setObjectName('nearby_list')
        self.nearby_list.setAccessibleName('Nearby facilities; Enter selects a destination')
        self.nearby_list.setFixedHeight(180)
        nearby_box.addWidget(self.nearby_list)

        nearby_section.addLayout(nearby_box)
        side.addStretch()
        clear_btn = QPushButton('Clear destination')
        clear_btn.clicked.connect(self.window.clear_destination)
        side.addWidget(clear_btn)

        self._wire_signals()

    def _wire_signals(self) -> None:
        self.search.textChanged.connect(self.window.filter_stores)
        self.stores.itemClicked.connect(self.window.select_item)
        self.stores.itemActivated.connect(self.window.select_item)
        self.nearby_list.itemClicked.connect(self.window.select_item)
        self.nearby_list.itemActivated.connect(self.window.select_item)
        self.category.currentTextChanged.connect(self.window.refresh)
        self.radius.valueChanged.connect(self.window.refresh)

    def _accordion(self, side: QVBoxLayout, title: str, expanded: bool = False) -> QVBoxLayout:
        header = QToolButton()
        header.setObjectName('accordion')
        header.setText(title)
        header.setCheckable(True)
        header.setChecked(expanded)
        header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        header.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        header.setAccessibleName(title)
        header.setToolTip('Expand or collapse this section')
        body = QWidget()
        body.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        content = QVBoxLayout(body)
        content.setContentsMargins(6, 6, 6, 10)
        body.setVisible(expanded)
        header.toggled.connect(body.setVisible)
        header.toggled.connect(lambda checked: header.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow))
        side.addWidget(header)
        side.addWidget(body)
        return content

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
