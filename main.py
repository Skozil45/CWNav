"""CWNav desktop entry point. Run with python main.py."""
import math
import sys
import time
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush, QImage, QPixmap, QFont, QFontMetricsF, QRegion
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QGraphicsView, QGraphicsScene, QSplitter, QCheckBox,
    QMessageBox, QScrollArea, QAbstractSpinBox, QGraphicsPixmapItem)

from navigation import ROOT, FLOORS, Model, Player
from label_layout import SCALE, shop_regions, fit_label, pixel_box

ACCENT = '#00695c'


class MapView(QGraphicsView):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Mall map. Arrow keys or WASD to move; drag to pan; wheel to zoom.')
        self.keys = set()
        self.overlay = []
        self.floor_items = {}
        self.structure_items = {}
        self.shop_labels = {}
        self.network_item = self.player_item = self.buffer_item = None
        self.svg = None
        self.load_floor('ground')

    def load_floor(self, floor):
        for item in (self.network_item, self.player_item, self.buffer_item):
            if item is not None:
                self.scene().removeItem(item)
        for item in self.overlay:
            self.scene().removeItem(item)
        self.overlay = []
        for item in self.floor_items.values():
            item.hide()
        for item in self.structure_items.values():
            item.hide()
        for labels in self.shop_labels.values():
            for item in labels:
                item.hide()
        if floor not in self.floor_items:
            filename = 'ground-floor.svg' if floor == 'ground' else '1st-floor.svg'
            display_filename = filename.replace('.svg', '-no-units.svg')
            renderer = QSvgRenderer(str(ROOT / 'extracted-maps' / display_filename))
            if not renderer.isValid():
                raise ValueError(f'Invalid SVG: {filename}')
            # Render once at explicit bounds; Qt SVG item caching distorts this artwork.
            image = QImage(4200, 3000, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter, QRectF(0, 0, 4200, 3000))
            painter.end()
            item = QGraphicsPixmapItem(QPixmap.fromImage(image))
            item.setScale(.1)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            self.scene().addItem(item)
            self.floor_items[floor] = item
            # Keep source shop/service shapes, without treating them as surveyed GIS areas.
            structure = ET.parse(ROOT / 'extracted-maps' / filename).getroot()
            shop_ids = []
            for index, element in enumerate(structure.iter()):
                if element.get('fill') == '#7c7e70':
                    element.set('id', f'shop-{index}')
                    shop_ids.append(f'shop-{index}')
            shop_renderer = QSvgRenderer(ET.tostring(structure))
            regions = shop_regions(shop_renderer, shop_ids)
            self.shop_labels[floor] = self.make_shop_labels(floor, regions)
            for element in structure.iter():
                if element.tag.rsplit('}', 1)[-1] in ('path', 'rect', 'polygon', 'polyline', 'circle', 'ellipse', 'text', 'image', 'use', 'line'):
                    if element.get('fill') in ('#7c7e70', '#697884'):
                        element.set('fill', 'none')
                        element.set('stroke', '#61736b')
                        element.set('stroke-width', '0.35')
                    else:
                        element.set('display', 'none')
            renderer = QSvgRenderer(ET.tostring(structure))
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            renderer.render(painter, QRectF(0, 0, 4200, 3000))
            painter.end()
            outline = QGraphicsPixmapItem(QPixmap.fromImage(image))
            outline.setScale(.1)
            outline.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            outline.setZValue(.1)
            self.scene().addItem(outline)
            self.structure_items[floor] = outline
        self.svg = self.floor_items[floor]
        self.svg.setVisible(self.window.map_picture.isChecked())
        self.structure_items[floor].setVisible(self.window.network.isChecked())
        for item in self.shop_labels[floor]:
            item.setVisible(self.window.network.isChecked())
        self.network_item = None
        self.player_item = self.scene().addEllipse(-2.2,-2.2,4.4,4.4,
            QPen(QColor('white'), .6), QBrush(QColor(ACCENT)))
        self.player_item.setToolTip('You are here (simulated)')
        self.player_item.setZValue(10)
        brush = QColor(ACCENT)
        brush.setAlpha(18)
        self.buffer_item = self.scene().addEllipse(QRectF(), QPen(QColor(ACCENT),.35), QBrush(brush))
        self.buffer_item.setZValue(1)
        # Raster coordinates map exactly back to the original 420x300 SVG viewBox.
        self.setSceneRect(QRectF(0, 0, 420, 300))
        self.reset_view()

    def make_shop_labels(self, floor, regions):
        artwork = self.floor_items[floor].pixmap().toImage()
        font = QFont('Segoe UI', 24, QFont.Weight.DemiBold)
        metrics = QFontMetricsF(font)
        groups = {}
        for place in self.window.model.places:
            if place.floor != floor or place.category not in ('Stores', 'Dining'):
                continue
            point = QPoint(round(place.xy[0]*SCALE), round(place.xy[1]*SCALE))
            candidates = [i for i, region in enumerate(regions) if region.contains(point)]
            # Source-marker matches remain inferred, even with silhouette containment.
            key = min(candidates, key=lambda i: regions[i].boundingRect().width()*regions[i].boundingRect().height()) if candidates else place.id
            groups.setdefault(key, []).append(place)
        labels = []
        for key, places in groups.items():
            region = regions[key] if isinstance(key, int) else QRegion(pixel_box(QPointF(*places[0].xy), 12, 6))
            title = ' / '.join(p.title for p in places)
            path, scale, center = fit_label(title, region, font, metrics, places[0].xy)
            text = self.scene().addPath(path)
            size = text.boundingRect()
            text.setScale(scale)
            box = QRectF(0, 0, size.width()*scale+.6, size.height()*scale+.4)
            label = self.scene().addRect(box, QPen(Qt.PenStyle.NoPen), QBrush(Qt.BrushStyle.NoBrush))
            label.setPos(center - box.center())
            label.setZValue(5)
            units = ', '.join(p.unit for p in places if p.unit)
            label.setToolTip(title + (f'\nUnit {units}' if units else '') + '\nPosition inferred from the source map and directory')
            samples = [artwork.pixelColor(max(0, min(artwork.width()-1, int((center.x()+dx)*10))),
                                          max(0, min(artwork.height()-1, int((center.y()+dy)*10)))).lightnessF()
                       for dx, dy in ((0,0),(-1,-1),(1,1),(-1,1),(1,-1))]
            label.setData(0, sorted(samples)[2] < .55)
            label.setData(1, region)
            label.setData(2, isinstance(key, int))
            text.setParentItem(label)
            text.setPos(.3-size.left()*scale, .2-size.top()*scale)
            labels.append(label)
        return labels

    def reset_view(self):
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom(self, factor):
        current = self.transform().m11()
        if .5 <= current * factor <= 30:
            self.scale(factor, factor)

    def wheelEvent(self, event):
        self.zoom(1.2 if event.angleDelta().y() > 0 else 1/1.2)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in self.window.directions:
            self.keys.add(event.key())
            event.accept()
        elif event.key() == Qt.Key.Key_E:
            if not event.isAutoRepeat():
                self.window.transition()
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat():
            self.keys.discard(event.key())
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event):
        self.keys.clear()
        super().focusOutEvent(event)

    def line(self, points, color, width, dashed=False):
        path = QPainterPath(QPointF(*points[0]))
        for xy in points[1:]:
            path.lineTo(QPointF(*xy))
        pen = QPen(QColor(color), width)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        item = self.scene().addPath(path, pen)
        self.overlay.append(item)

    def marker(self, xy, color, size, tooltip):
        item = self.scene().addEllipse(xy[0]-size, xy[1]-size, size*2, size*2,
                                      QPen(QColor('white'), .6), QBrush(QColor(color)))
        item.setToolTip(tooltip)
        self.overlay.append(item)

    def redraw(self, path, results, radius):
        for item in self.overlay:
            self.scene().removeItem(item)
        self.overlay.clear()
        w = self.window
        floor = w.viewed_floor
        if self.network_item is None:
            network_path = QPainterPath()
            for a, b, line in w.model.edges:
                if w.model.nodes[a]['floor'] == floor:
                    network_path.moveTo(QPointF(*w.model.nodes[a]['xy']))
                    network_path.lineTo(QPointF(*w.model.nodes[b]['xy']))
            for node_id in set(w.model.data['entrances'].values()):
                node = w.model.nodes[node_id]
                if node['floor'] == floor:
                    network_path.addEllipse(QPointF(*node['xy']), .9, .9)
            pen = QPen(QColor('#61736b'), .65)
            self.network_item = self.scene().addPath(network_path, pen)
        self.network_item.setVisible(w.network.isChecked())
        r = radius / w.model.scale
        self.buffer_item.setRect(-r,-r,2*r,2*r)
        for _, place in results:
            if place.floor == floor:
                self.marker(place.xy, '#52685b', 1, place.title)
        if path:
            if w.player.floor == floor:
                self.line([w.player.xy, w.model.nodes[path[0]]['xy']], ACCENT, 1.4)
            for a, b in zip(path, path[1:]):
                na, nb = w.model.nodes[a], w.model.nodes[b]
                if na['floor'] == nb['floor'] == floor:
                    self.line([na['xy'], nb['xy']], ACCENT, 1.4)
        if w.destination and w.destination.floor == floor:
            xy = w.model.nodes[w.destination.entrance]['xy'] if w.destination.entrance else w.destination.xy
            self.marker(xy, '#a34419', 2, 'Destination: ' + w.destination.title)
        for c in w.model.data['connectors']:
            for node in [c['a'], c['b']]:
                if w.model.nodes[node]['floor'] == floor:
                    self.marker(w.model.nodes[node]['xy'], '#584486', 1.5, c['name'])
        self.update_player()
        self.apply_visibility()

    def apply_visibility(self):
        visible = self.window.network.isChecked()
        self.svg.setVisible(self.window.map_picture.isChecked())
        self.structure_items[self.window.viewed_floor].setVisible(visible)
        for item in self.shop_labels[self.window.viewed_floor]:
            item.setVisible(visible)
            light_text = self.window.map_picture.isChecked() and item.data(0)
            text = item.childItems()[0]
            text.setBrush(QBrush(QColor('#ffffff' if light_text else '#20332c')))
            text.setPen(QPen(QColor('#20332c' if light_text else '#ffffff'), .35))
        if self.network_item is not None:
            self.network_item.setVisible(visible)
        for item in self.overlay:
            item.setVisible(visible)
        self.update_player()

    def update_player(self):
        player = self.window.player
        for item in (self.player_item, self.buffer_item):
            item.setVisible(self.window.network.isChecked() and player.floor == self.window.viewed_floor)
            item.setPos(QPointF(*player.xy))


class Window(QMainWindow):
    directions = {Qt.Key.Key_W:(0,-1), Qt.Key.Key_Up:(0,-1),
                  Qt.Key.Key_S:(0,1), Qt.Key.Key_Down:(0,1),
                  Qt.Key.Key_A:(-1,0), Qt.Key.Key_Left:(-1,0),
                  Qt.Key.Key_D:(1,0), Qt.Key.Key_Right:(1,0)}

    def __init__(self):
        super().__init__()
        self.setWindowTitle('CWNav | Ciputra World Surabaya')
        self.resize(1360, 880)
        self.setMinimumSize(760, 620)
        self.model = Model()
        self.player = Player(self.model)
        self.destination = None
        self.total_distance = None
        self.viewed_floor = 'ground'
        self.last_time = time.monotonic()
        self.last_results = None
        self.last_detail_refresh = 0.0
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 12)
        header = QHBoxLayout()
        title = QLabel('CWNav')
        title.setObjectName('title')
        header.addWidget(title)
        header.addWidget(QLabel('Ciputra World Surabaya  /  Indoor navigation'))
        header.addStretch()
        layout.addLayout(header)
        notice = QLabel('SIMULATION  ·  Approximate approaches, distances and floor connections')
        notice.setObjectName('notice')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        splitter = QSplitter()
        layout.addWidget(splitter, 1)
        panel = QWidget()
        side = QVBoxLayout(panel)
        side.setContentsMargins(6, 8, 18, 8)
        side.addWidget(self.label('Find a store or facility', True))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Name or unit number, e.g. Fore or 53')
        self.search.setAccessibleName('Search stores by name or unit number')
        side.addWidget(self.search)
        self.stores = QListWidget()
        self.stores.setAccessibleName('Search results; Enter selects a destination')
        self.stores.setMinimumHeight(100)
        self.stores.setMaximumHeight(230)
        side.addWidget(self.stores)
        side.addWidget(self.label('Your route', True))
        self.transport = QComboBox()
        self.transport.addItems(['Any floor connection','Lifts only','Escalators only'])
        self.transport.setAccessibleName('Route transport preference')
        side.addWidget(self.transport)
        self.route_label = self.label('Choose a destination to plan a route.')
        side.addWidget(self.route_label)
        clear = QPushButton('Clear destination')
        clear.clicked.connect(self.clear_destination)
        side.addWidget(clear)
        side.addWidget(self.label('Nearby on your floor', True))
        self.category = QComboBox()
        self.category.addItems(['All','Dining','Toilets','Lifts','Escalators','ATMs','Stores'])
        self.category.setAccessibleName('Facility category')
        self.category.setCurrentText('Dining')
        side.addWidget(self.category)
        radius_row = QHBoxLayout()
        radius_label = QLabel('Search radius')
        self.radius = QSpinBox()
        self.radius.setRange(5,60)
        self.radius.setValue(20)
        self.radius.setSuffix(' m (approx.)')
        self.radius.setAccessibleName('Search radius in approximate meters')
        radius_label.setBuddy(self.radius)
        radius_row.addWidget(radius_label)
        radius_row.addWidget(self.radius)
        side.addLayout(radius_row)
        self.near_status = self.label('')
        side.addWidget(self.near_status)
        self.nearby_list = QListWidget()
        self.nearby_list.setAccessibleName('Nearby facilities; Enter selects a destination')
        self.nearby_list.setMinimumHeight(90)
        self.nearby_list.setMaximumHeight(180)
        side.addWidget(self.nearby_list)
        side.addWidget(self.label('Nearby = straight-line distance. Routes follow corridors.\n20 m expands to 40 / 60 m when empty.'))
        side.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(280)
        splitter.addWidget(scroll)
        map_panel = QWidget()
        map_layout = QVBoxLayout(map_panel)
        map_layout.setContentsMargins(8,8,0,0)
        toolbar = QHBoxLayout()
        self.floor = QComboBox()
        self.floor.addItems(list(FLOORS.values()))
        self.floor.setAccessibleName('Viewed floor; does not move the player')
        toolbar.addWidget(self.floor)
        follow = QPushButton('Show player floor')
        follow.clicked.connect(self.show_player)
        toolbar.addWidget(follow)
        self.map_picture = QCheckBox('Map picture')
        self.map_picture.setChecked(True)
        toolbar.addWidget(self.map_picture)
        self.network = QCheckBox('Graph')
        self.network.setToolTip('Show shop outlines, shared rails, entry points, route, player and search buffer')
        self.network.setChecked(True)
        toolbar.addWidget(self.network)
        toolbar.addStretch()
        self.view = MapView(self)
        for text, action in [('Zoom in',lambda:self.view.zoom(1.25)),('Zoom out',lambda:self.view.zoom(.8)),('Reset view',self.view.reset_view)]:
            button = QPushButton(text)
            button.clicked.connect(action)
            toolbar.addWidget(button)
        map_layout.addLayout(toolbar)
        map_layout.addWidget(self.view, 1)
        self.position_label = self.label('')
        map_layout.addWidget(self.position_label)
        self.cross = QPushButton('Use floor connection (E)')
        self.cross.clicked.connect(self.transition)
        map_layout.addWidget(self.cross)
        speed_row = QHBoxLayout()
        speed_label = QLabel('Movement speed')
        self.speed = QDoubleSpinBox()
        self.speed.setRange(.5, 12)
        self.speed.setSingleStep(.5)
        self.speed.setDecimals(1)
        self.speed.setValue(12)
        self.speed.setSuffix(' m/s (approx.)')
        self.speed.setAccessibleName('Simulated movement speed in approximate meters per second')
        speed_label.setBuddy(self.speed)
        speed_row.addWidget(speed_label)
        speed_row.addWidget(self.speed)
        speed_row.addStretch()
        map_layout.addLayout(speed_row)
        map_layout.addWidget(self.label('WASD / arrows to walk. Drag to pan; scroll to zoom. E: change floor within ≈ 3 m along the walkway.\nTeal: player and route  ·  Rust: destination  ·  Purple: floor connector'))
        splitter.addWidget(map_panel)
        splitter.setSizes([330,1000])
        self.setCentralWidget(root)
        self.search.textChanged.connect(self.filter_stores)
        self.stores.itemClicked.connect(self.select_item)
        self.stores.itemActivated.connect(self.select_item)
        self.nearby_list.itemClicked.connect(self.select_item)
        self.nearby_list.itemActivated.connect(self.select_item)
        self.floor.currentIndexChanged.connect(self.change_floor)
        self.category.currentTextChanged.connect(self.refresh)
        self.radius.valueChanged.connect(self.refresh)
        self.network.toggled.connect(self.view.apply_visibility)
        self.map_picture.toggled.connect(self.view.apply_visibility)
        self.transport.currentIndexChanged.connect(self.change_transport)
        self.filter_stores()
        self.refresh()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        QTimer.singleShot(0,self.view.reset_view)

    def label(self, text, heading=False):
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        if heading:
            label.setObjectName('heading')
        return label

    def filter_stores(self):
        self.stores.clear()
        query = self.search.text().casefold().strip()
        for p in sorted(self.model.places, key=lambda p:(p.title,p.floor)):
            if query not in f'{p.title} {p.unit}'.casefold():
                continue
            item = QListWidgetItem(f'{p.title}\n{FLOORS[p.floor]}'+(f' · Unit {p.unit}' if p.unit else ''))
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            item.setToolTip('Approximate approach mapped' if p.entrance else 'Entrance not mapped: routing unavailable')
            self.stores.addItem(item)
        if not self.stores.count():
            item = QListWidgetItem('No matching stores or facilities')
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.stores.addItem(item)

    def select_item(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        if not key:
            return
        self.destination = self.model.by_id[key]
        self.total_distance = self.player.route(self.destination.entrance)[1] if self.destination.entrance else None
        self.refresh()

    def clear_destination(self):
        self.destination, self.total_distance = None, None
        self.refresh()

    def change_transport(self,index):
        self.player.transport = ('any','lift','escalator')[index]
        if self.destination and self.destination.entrance:
            self.total_distance = self.player.route(self.destination.entrance)[1]
        self.refresh()

    def change_floor(self, index):
        self.viewed_floor = list(FLOORS)[index]
        self.view.load_floor(self.viewed_floor)
        self.refresh()

    def show_player(self):
        self.floor.setCurrentIndex(list(FLOORS).index(self.player.floor))
        self.view.reset_view()

    def transition(self):
        if self.player.transition():
            self.view.keys.clear()
            self.show_player()
            self.refresh()

    def tick(self):
        now = time.monotonic()
        elapsed = now-self.last_time
        self.last_time = now
        if not self.isActiveWindow():
            self.view.keys.clear()
            return
        dx,dy = 0,0
        for key in self.view.keys:
            vx,vy = self.directions[key]
            dx,dy = dx+vx,dy+vy
        if isinstance(QApplication.focusWidget(), (QLineEdit, QAbstractSpinBox)):
            return
        if dx or dy:
            before = self.player.xy
            self.player.move(dx,dy,elapsed,self.speed.value())
            if self.player.xy != before:
                self.view.update_player()
                if now-self.last_detail_refresh >= .1 or self.player.target is None:
                    self.refresh()

    def refresh(self, *_):
        self.last_detail_refresh = time.monotonic()
        path = []
        p = self.destination
        if p:
            if not p.entrance:
                reason = self.model.data.get('unsupported',{}).get(p.id,'Entrance not mapped.')
                message = f'{p.title}\n{FLOORS[p.floor]} · Unit {p.unit or "not listed"}\nRouting unavailable: {reason}'
            else:
                path, remaining = self.player.route(p.entrance)
                if not path:
                    message = f'{p.title}\nNo connected route from your position.'
                elif remaining < .2:
                    message = f'{p.title}\nArrived at the approximate approach point.'
                else:
                    total = self.total_distance if self.total_distance is not None else remaining
                    message = f'{p.title}\nRemaining ≈ {remaining:.1f} m · Initial ≈ {total:.1f} m\nEntrance and distance are approximate.'
                    transitions = [c['name'] for c in self.model.data['connectors'] if any({a,b}=={c['a'],c['b']} for a,b in zip(path,path[1:]))]
                    if transitions:
                        message += '\nVia '+', '.join(transitions)+'. Press E within ≈ 3 m along the walkway.'
            self.route_label.setText(message)
        else:
            self.route_label.setText('Choose a destination to plan a route.\nRoutes reuse the shared corridor rails.')
        results, radius = self.model.nearby(self.player.xy,self.player.floor,self.category.currentText(),self.radius.value())
        rows = [(p.id,round(distance,1)) for distance,p in results]
        if rows != self.last_results:
            selected = self.nearby_list.currentItem()
            selected_id = selected.data(Qt.ItemDataRole.UserRole) if selected else None
            self.nearby_list.clear()
            for distance,place in results:
                item = QListWidgetItem(f'{place.title}\n≈ {distance:.1f} m straight-line'+(' · route unavailable' if not place.entrance else ''))
                item.setData(Qt.ItemDataRole.UserRole,place.id)
                self.nearby_list.addItem(item)
                if place.id == selected_id:
                    self.nearby_list.setCurrentItem(item)
            if not results:
                item = QListWidgetItem('No facilities found within this radius')
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.nearby_list.addItem(item)
            self.last_results = rows
        self.near_status.setText(f'{FLOORS[self.player.floor]} · {len(results)} results within ≈ {radius} m')
        connector = self.player.connector()
        self.cross.setEnabled(connector is not None)
        self.cross.setText(f"Use {connector.get('kind','escalator')} (E)" if connector else 'Use floor connection (E)')
        self.cross.setToolTip((connector['name']+'\n' if connector else '') + 'Available within approximately 3 m along the connected walkway. Press E or click to change floor.')
        x,y = self.player.xy
        self.position_label.setText(f'Player: {FLOORS[self.player.floor]} · ({x:.1f}, {y:.1f}) map units   |   Viewing: {FLOORS[self.viewed_floor]}')
        self.view.redraw(path,results,radius)


STYLE = '''
QWidget { font-family: "Segoe UI"; font-size: 13px; color: #24332e; background: #f7f6f2; }
QMainWindow { background: #f7f6f2; }
QLabel#title { font-size: 29px; font-weight: 700; color: #00695c; }
QLabel#heading { font-size: 15px; font-weight: 600; margin-top: 10px; }
QLabel#notice { background: #eee7d7; color: #604a19; padding: 8px; border-radius: 4px; }
QPushButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox { background: white; border: 1px solid #99a79f; border-radius: 4px; padding: 7px; min-height: 18px; }
QPushButton:hover { background: #e5eee9; }
QPushButton:pressed { background: #c9ded3; }
QPushButton:disabled { color: #727972; background: #eceeea; border-color: #b9c0ba; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QListWidget:focus { border: 2px solid #00695c; }
QListWidget { background: white; border: 1px solid #bdc6bf; border-radius: 4px; }
QListWidget::item { padding: 7px; border-bottom: 1px solid #eef0ed; }
QListWidget::item:selected { background: #d4e7de; color: #173b2c; }
QGraphicsView { background: white; border: 1px solid #bdc6bf; border-radius: 5px; }
QScrollArea { border: none; background: transparent; }
QToolTip { background: #ffffff; color: #24332e; border: 1px solid #99a79f; }
QCheckBox::indicator:checked { background: #00695c; border: 2px solid #00695c; }
QCheckBox::indicator:unchecked { background: white; border: 1px solid #62776b; }
'''


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    loading = QLabel('Loading CWNav maps and directory…')
    loading.setWindowTitle('CWNav')
    loading.setMargin(24)
    loading.show()
    app.processEvents()
    try:
        window = Window()
    except (OSError, ValueError, KeyError, TypeError) as error:
        loading.close()
        QMessageBox.critical(None, 'CWNav could not load', f'Check the bundled maps and navigation-data.json.\n\n{error}')
        return 1
    loading.close()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
