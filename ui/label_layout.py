"""Fit fixed labels inside rasterized source shop silhouettes, in local map units."""
import math
import textwrap

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QBitmap, QImage, QPainter, QPainterPath, QRegion

SCALE = 4


def shop_regions(renderer, keys):
    regions = []
    for key in keys:
        bounds = renderer.boundsOnElement(key)
        image = QImage(math.ceil(bounds.width()*SCALE), math.ceil(bounds.height()*SCALE), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter, key, QRectF(0, 0, bounds.width()*SCALE, bounds.height()*SCALE))
        painter.end()
        region = QRegion(QBitmap.fromImage(image.createAlphaMask()))
        region.translate(round(bounds.x()*SCALE), round(bounds.y()*SCALE))
        regions.append(region)
    return regions


def pixel_box(center, width, height):
    left = math.floor((center.x()-width/2)*SCALE)
    top = math.floor((center.y()-height/2)*SCALE)
    return QRect(left, top, math.ceil((center.x()+width/2)*SCALE)-left+1,
                 math.ceil((center.y()+height/2)*SCALE)-top+1)


def fit_label(title, region, font, metrics, marker):
    bounds = region.boundingRect()
    center = QPointF(bounds.center())/SCALE
    candidates = [center, QPointF(*marker)]
    candidates += [QPointF(bounds.x()+bounds.width()*x/8, bounds.y()+bounds.height()*y/8)/SCALE
                   for x in range(1,8) for y in range(1,8)]
    candidates = [p for p in candidates if region.contains(QPoint(round(p.x()*SCALE), round(p.y()*SCALE)))]
    best = None
    for columns in sorted({8,12,16,20,28,len(title)}):
        lines = textwrap.wrap(title, columns, break_long_words=False)
        width = max(metrics.horizontalAdvance(line) for line in lines)
        path = QPainterPath()
        for row, line in enumerate(lines):
            path.addText((width-metrics.horizontalAdvance(line))/2, metrics.ascent()+row*metrics.lineSpacing(), font, line)
        text_bounds = path.boundingRect()
        for point in candidates:
            low, high = 0., .16
            for _ in range(9):
                scale = (low+high)/2
                box = pixel_box(point, text_bounds.width()*scale+1, text_bounds.height()*scale+1)
                if QRegion(box).subtracted(region).isEmpty():
                    low = scale
                else:
                    high = scale
            # Favor readable type, then keep the label near the shop's center.
            score = low - .00015*math.hypot(point.x()-center.x(), point.y()-center.y())
            if low > 0 and (best is None or score > best[0]):
                best = (score, path, low, point)
    if best is None:
        raise ValueError(f'No interior label area for {title}')
    return best[1:]
