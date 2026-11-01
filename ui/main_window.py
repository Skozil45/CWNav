"""Main application window for CWNav."""
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QSplitter, QCheckBox,
    QScrollArea, QAbstractSpinBox, QListWidgetItem, QApplication
)

from navigation import FLOORS, Model, Player
from ui.map_view import MapView
from ui.sidebar_panel import SidebarPanel


class Window(QMainWindow):
    directions = {
        Qt.Key.Key_W: (0, -1), Qt.Key.Key_Up: (0, -1),
        Qt.Key.Key_S: (0, 1), Qt.Key.Key_Down: (0, 1),
        Qt.Key.Key_A: (-1, 0), Qt.Key.Key_Left: (-1, 0),
        Qt.Key.Key_D: (1, 0), Qt.Key.Key_Right: (1, 0)
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle('CWNav | Ciputra World Surabaya')
        self.resize(1360, 880)
        self.setMinimumSize(760, 620)

        # Core navigation model and simulated player
        self.model = Model()
        self.player = Player(self.model)
        self.destination = None
        self.total_distance = None
        self.viewed_floor = 'ground'
        self.last_time = time.monotonic()
        self.last_results = None
        self.last_detail_refresh = 0.0

        # Build UI layout
        self._init_ui()

        # Connect initial state and loop timer
        self.filter_stores()
        self.refresh()

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        QTimer.singleShot(0, self.view.reset_view)

    # =========================================================================
    # UI Layout Construction
    # =========================================================================

    def _init_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 12)

        # Header bar
        header = QHBoxLayout()
        title = QLabel('CWNav')
        title.setObjectName('title')
        header.addWidget(title)
        header.addWidget(QLabel('Ciputra World Surabaya  /  Indoor navigation'))
        header.addStretch()
        layout.addLayout(header)

        notice = QLabel('SIMULATION | Approximate approaches, distances and floor connections')
        notice.setObjectName('notice')
        notice.setWordWrap(True)
        layout.addWidget(notice)

        splitter = QSplitter()
        layout.addWidget(splitter, 1)

        # Sidebar scroll area
        self.sidebar = SidebarPanel(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.sidebar)
        scroll.setMinimumWidth(280)
        splitter.addWidget(scroll)

        # Map display panel
        map_panel = QWidget()
        map_layout = QVBoxLayout(map_panel)
        map_layout.setContentsMargins(8, 8, 0, 0)

        toolbar = QHBoxLayout()
        self.floor = QComboBox()
        self.floor.addItems(list(FLOORS.values()))
        self.floor.setAccessibleName('Viewed floor; does not move the player')
        self.floor.currentIndexChanged.connect(self.change_floor)
        toolbar.addWidget(self.floor)

        follow = QPushButton('Show player floor')
        follow.clicked.connect(self.show_player)
        toolbar.addWidget(follow)

        self.map_picture = QCheckBox('Map picture')
        self.map_picture.setChecked(True)
        self.map_picture.toggled.connect(lambda: self.view.apply_visibility())
        toolbar.addWidget(self.map_picture)

        self.network = QCheckBox('Graph')
        self.network.setToolTip('Show shop outlines, shared rails, entry points, route, player and search buffer')
        self.network.setChecked(True)
        self.network.toggled.connect(lambda: self.view.apply_visibility())
        toolbar.addWidget(self.network)
        toolbar.addStretch()

        self.view = MapView(self)
        for text, action in [
            ('Zoom in', lambda: self.view.zoom(1.25)),
            ('Zoom out', lambda: self.view.zoom(0.8)),
            ('Reset view', self.view.reset_view)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(action)
            toolbar.addWidget(btn)

        map_layout.addLayout(toolbar)
        map_layout.addWidget(self.view, 1)

        self.position_label = self._label('')
        map_layout.addWidget(self.position_label)

        self.cross = QPushButton('Use floor connection (E)')
        self.cross.clicked.connect(self.transition)
        map_layout.addWidget(self.cross)

        speed_row = QHBoxLayout()
        speed_label = QLabel('Movement speed')
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.5, 12)
        self.speed.setSingleStep(0.5)
        self.speed.setDecimals(1)
        self.speed.setValue(12)
        self.speed.setSuffix(' m/s (approx.)')
        self.speed.setAccessibleName('Simulated movement speed in approximate meters per second')
        speed_label.setBuddy(self.speed)
        speed_row.addWidget(speed_label)
        speed_row.addWidget(self.speed)
        speed_row.addStretch()
        map_layout.addLayout(speed_row)

        map_layout.addWidget(self._label(
            'WASD / arrows to walk. Drag to pan; scroll to zoom. E: change floor within ~3 m along the walkway.\n'
            'Teal: player and route | Rust: destination | Purple: floor connector'
        ))

        splitter.addWidget(map_panel)
        splitter.setSizes([330, 1000])
        self.setCentralWidget(root)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setTextFormat(Qt.TextFormat.PlainText)
        lbl.setWordWrap(True)
        return lbl

    # =========================================================================
    # User Action Handlers & Routing Controls
    # =========================================================================

    def filter_stores(self) -> None:
        self.sidebar.stores.clear()
        query = self.sidebar.search.text().casefold().strip()
        for p in sorted(self.model.places, key=lambda p: (p.title, p.floor)):
            if query not in f'{p.title} {p.unit}'.casefold():
                continue
            item = QListWidgetItem(f'{p.title}\n{FLOORS[p.floor]}' + (f' - Unit {p.unit}' if p.unit else ''))
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            item.setToolTip('Approximate approach mapped' if p.entrance else 'Entrance not mapped: routing unavailable')
            self.sidebar.stores.addItem(item)

        if not self.sidebar.stores.count():
            item = QListWidgetItem('No matching stores or facilities')
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.sidebar.stores.addItem(item)

    def select_item(self, item) -> None:
        key = item.data(Qt.ItemDataRole.UserRole)
        if not key:
            return
        self.destination = self.model.by_id[key]
        self.total_distance = self.player.route(self.destination.entrance)[1] if self.destination.entrance else None
        self.refresh()

    def clear_destination(self) -> None:
        self.destination = None
        self.total_distance = None
        self.refresh()

    def change_transport(self, index: int) -> None:
        self.player.transport = ('any', 'lift', 'escalator')[index]
        if self.destination and self.destination.entrance:
            self.total_distance = self.player.route(self.destination.entrance)[1]
        self.refresh()

    def change_floor(self, index: int) -> None:
        self.viewed_floor = list(FLOORS)[index]
        self.view.load_floor(self.viewed_floor)
        self.refresh()

    def show_player(self) -> None:
        self.floor.setCurrentIndex(list(FLOORS).index(self.player.floor))
        self.view.reset_view()

    def transition(self) -> None:
        if self.player.transition():
            self.view.keys.clear()
            self.show_player()
            self.refresh()

    # =========================================================================
    # Simulation Game Loop & Real-Time GIS Updates
    # =========================================================================

    def tick(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_time
        self.last_time = now

        if not self.isActiveWindow():
            self.view.keys.clear()
            return

        dx, dy = 0, 0
        for key in self.view.keys:
            vx, vy = self.directions[key]
            dx, dy = dx + vx, dy + vy

        if isinstance(QApplication.focusWidget(), (QWidget,)) and QApplication.focusWidget() == self.sidebar.search:
            return

        if dx or dy:
            before = self.player.xy
            self.player.move(dx, dy, elapsed, self.speed.value())
            if self.player.xy != before:
                self.view.update_player()
                if now - self.last_detail_refresh >= 0.1 or self.player.target is None:
                    self.refresh()

    def refresh(self, *_) -> None:
        self.last_detail_refresh = time.monotonic()
        path = []
        p = self.destination

        if p:
            if not p.entrance:
                reason = self.model.data.get('unsupported', {}).get(p.id, 'Entrance not mapped.')
                message = f'{p.title}\n{FLOORS[p.floor]} | Unit {p.unit or "not listed"}\nRouting unavailable: {reason}'
            else:
                path, remaining = self.player.route(p.entrance)
                if not path:
                    message = f'{p.title}\nNo connected route from your position.'
                elif remaining < 0.2:
                    message = f'{p.title}\nArrived at the approximate approach point.'
                else:
                    total = self.total_distance if self.total_distance is not None else remaining
                    message = f'{p.title}\nRemaining ~ {remaining:.1f} m | Initial ~ {total:.1f} m\nEntrance and distance are approximate.'
                    transitions = [
                        c['name'] for c in self.model.data['connectors']
                        if any({a, b} == {c['a'], c['b']} for a, b in zip(path, path[1:]))
                    ]
                    if transitions:
                        message += '\nVia ' + ', '.join(transitions) + '. Press E within ~ 3 m along the walkway.'
            self.sidebar.route_label.setText(message)
        else:
            self.sidebar.route_label.setText('Choose a destination to plan a route.\nRoutes reuse the shared corridor rails.')

        results, radius = self.model.nearby(
            self.player.xy,
            self.player.floor,
            self.sidebar.category.currentText(),
            self.sidebar.radius.value()
        )
        rows = [(place.id, round(distance, 1)) for distance, place in results]

        if rows != self.last_results:
            selected = self.sidebar.nearby_list.currentItem()
            selected_id = selected.data(Qt.ItemDataRole.UserRole) if selected else None
            self.sidebar.nearby_list.clear()

            for distance, place in results:
                item = QListWidgetItem(
                    f'{place.title}\n~ {distance:.1f} m straight-line' +
                    (' | route unavailable' if not place.entrance else '')
                )
                item.setData(Qt.ItemDataRole.UserRole, place.id)
                self.sidebar.nearby_list.addItem(item)
                if place.id == selected_id:
                    self.sidebar.nearby_list.setCurrentItem(item)

            if not results:
                item = QListWidgetItem('No facilities found within this radius')
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.sidebar.nearby_list.addItem(item)
            self.last_results = rows

        self.sidebar.near_status.setText(f'{FLOORS[self.player.floor]} | {len(results)} results within ~ {radius} m')
        connector = self.player.connector()
        self.cross.setEnabled(connector is not None)
        self.cross.setText(f"Use {connector.get('kind', 'escalator')} (E)" if connector else 'Use floor connection (E)')
        self.cross.setToolTip(
            (connector['name'] + '\n' if connector else '') +
            'Available within approximately 3 m along the connected walkway. Press E or click to change floor.'
        )

        x, y = self.player.xy
        self.position_label.setText(f'Player: {FLOORS[self.player.floor]} | ({x:.1f}, {y:.1f}) map units   |   Viewing: {FLOORS[self.viewed_floor]}')
        self.view.redraw(path, results, radius)
