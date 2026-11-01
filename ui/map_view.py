import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt, QPoint, QPointF, QRectF
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QBrush, QImage,
    QPixmap, QFont, QFontMetricsF, QRegion
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem

from navigation import ROOT, FLOORS
from ui.label_layout import SCALE, shop_regions, fit_label, pixel_box
from ui.styles import ACCENT


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
        self.network_item = None
        self.player_item = None
        self.buffer_item = None
        self.svg = None
        self.load_floor('ground')

    # =========================================================================
    # Floor Rendering and Label Layout
    # =========================================================================

    def load_floor(self, floor: str) -> None:
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

            image = QImage(4200, 3000, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter, QRectF(0, 0, 4200, 3000))
            painter.end()

            item = QGraphicsPixmapItem(QPixmap.fromImage(image))
            item.setScale(0.1)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            self.scene().addItem(item)
            self.floor_items[floor] = item

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
                tag_name = element.tag.rsplit('}', 1)[-1]
                if tag_name in ('path', 'rect', 'polygon', 'polyline', 'circle', 'ellipse', 'text', 'image', 'use', 'line'):
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
            outline.setScale(0.1)
            outline.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            outline.setZValue(0.1)
            self.scene().addItem(outline)
            self.structure_items[floor] = outline

        self.svg = self.floor_items[floor]
        self.svg.setVisible(self.window.map_picture.isChecked())
        self.structure_items[floor].setVisible(self.window.network.isChecked())
        for item in self.shop_labels[floor]:
            item.setVisible(self.window.network.isChecked())

        self.network_item = None
        self.player_item = self.scene().addEllipse(
            -2.2, -2.2, 4.4, 4.4,
            QPen(QColor('white'), 0.6),
            QBrush(QColor(ACCENT))
        )
        self.player_item.setToolTip('You are here (simulated)')
        self.player_item.setZValue(10)

        brush = QColor(ACCENT)
        brush.setAlpha(18)
        self.buffer_item = self.scene().addEllipse(QRectF(), QPen(QColor(ACCENT), 0.35), QBrush(brush))
        self.buffer_item.setZValue(1)

        self.setSceneRect(QRectF(0, 0, 420, 300))
        self.reset_view()

    def make_shop_labels(self, floor: str, regions: list) -> list:
        artwork = self.floor_items[floor].pixmap().toImage()
        font = QFont('Segoe UI', 24, QFont.Weight.DemiBold)
        metrics = QFontMetricsF(font)
        groups = {}

        for place in self.window.model.places:
            if place.floor != floor or place.category not in ('Stores', 'Dining'):
                continue
            point = QPoint(round(place.xy[0] * SCALE), round(place.xy[1] * SCALE))
            candidates = [i for i, region in enumerate(regions) if region.contains(point)]
            key = min(candidates, key=lambda i: regions[i].boundingRect().width() * regions[i].boundingRect().height()) if candidates else place.id
            groups.setdefault(key, []).append(place)

        labels = []
        for key, places in groups.items():
            region = regions[key] if isinstance(key, int) else QRegion(pixel_box(QPointF(*places[0].xy), 12, 6))
            title = ' / '.join(p.title for p in places)
            path, scale, center = fit_label(title, region, font, metrics, places[0].xy)
            text = self.scene().addPath(path)
            size = text.boundingRect()
            text.setScale(scale)
            box = QRectF(0, 0, size.width() * scale + 0.6, size.height() * scale + 0.4)
            label = self.scene().addRect(box, QPen(Qt.PenStyle.NoPen), QBrush(Qt.BrushStyle.NoBrush))
            label.setPos(center - box.center())
            label.setZValue(5)
            units = ', '.join(p.unit for p in places if p.unit)
            label.setToolTip(title + (f'\nUnit {units}' if units else '') + '\nPosition inferred from the source map and directory')
            samples = [
                artwork.pixelColor(
                    max(0, min(artwork.width() - 1, int((center.x() + dx) * 10))),
                    max(0, min(artwork.height() - 1, int((center.y() + dy) * 10)))
                ).lightnessF()
                for dx, dy in ((0, 0), (-1, -1), (1, 1), (-1, 1), (1, -1))
            ]
            label.setData(0, sorted(samples)[2] < 0.55)
            label.setData(1, region)
            label.setData(2, isinstance(key, int))
            text.setParentItem(label)
            text.setPos(0.3 - size.left() * scale, 0.2 - size.top() * scale)
            labels.append(label)
        return labels

    # =========================================================================
    # Navigation Viewport Controls & Keyboard / Mouse Events
    # =========================================================================

    def reset_view(self) -> None:
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom(self, factor: float) -> None:
        current = self.transform().m11()
        if 0.5 <= current * factor <= 30:
            self.scale(factor, factor)

    def wheelEvent(self, event) -> None:
        self.zoom(1.2 if event.angleDelta().y() > 0 else 1 / 1.2)
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() in self.window.directions:
            self.keys.add(event.key())
            event.accept()
        elif event.key() == Qt.Key.Key_E:
            if not event.isAutoRepeat():
                self.window.transition()
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if not event.isAutoRepeat():
            self.keys.discard(event.key())
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event) -> None:
        self.keys.clear()
        super().focusOutEvent(event)

    # =========================================================================
    # Drawing Primitives & Overlay Redraw
    # =========================================================================

    def line(self, points: list, color: str, width: float, dashed: bool = False) -> None:
        path = QPainterPath(QPointF(*points[0]))
        for xy in points[1:]:
            path.lineTo(QPointF(*xy))
        pen = QPen(QColor(color), width)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        item = self.scene().addPath(path, pen)
        self.overlay.append(item)

    def marker(self, xy: tuple, color: str, size: float, tooltip: str) -> None:
        item = self.scene().addEllipse(
            xy[0] - size, xy[1] - size, size * 2, size * 2,
            QPen(QColor('white'), 0.6), QBrush(QColor(color))
        )
        item.setToolTip(tooltip)
        self.overlay.append(item)

    def redraw(self, path: list, results: list, radius: float) -> None:
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
            shop_points = QPainterPath()
            for node_id in set(w.model.data['entrances'].values()):
                node = w.model.nodes[node_id]
                if node['floor'] == floor:
                    shop_points.addEllipse(QPointF(*node['xy']), 0.9, 0.9)
            pen = QPen(QColor('#61736b'), 0.65)
            self.network_item = self.scene().addPath(network_path, pen)
            points_item = self.scene().addPath(shop_points, QPen(QColor('black'), 0.65), QBrush(QColor('black')))
            points_item.setParentItem(self.network_item)

        self.network_item.setVisible(w.network.isChecked())
        r = radius / w.model.scale
        self.buffer_item.setRect(-r, -r, 2 * r, 2 * r)

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

    def apply_visibility(self) -> None:
        visible = self.window.network.isChecked()
        self.svg.setVisible(self.window.map_picture.isChecked())
        self.structure_items[self.window.viewed_floor].setVisible(visible)
        for item in self.shop_labels[self.window.viewed_floor]:
            item.setVisible(visible)
            light_text = self.window.map_picture.isChecked() and item.data(0)
            text = item.childItems()[0]
            text.setBrush(QBrush(QColor('#ffffff' if light_text else '#20332c')))
            text.setPen(QPen(QColor('#20332c' if light_text else '#ffffff'), 0.35))
        if self.network_item is not None:
            self.network_item.setVisible(visible)
        for item in self.overlay:
            item.setVisible(visible)
        self.update_player()

    def update_player(self) -> None:
        player = self.window.player
        for item in (self.player_item, self.buffer_item):
            item.setVisible(self.window.network.isChecked() and player.floor == self.window.viewed_floor)
            item.setPos(QPointF(*player.xy))
