"""线性图标：用 QPainter 直接绘制，避免外部图标字体依赖。"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

ICON_MUTED = "#8B93B3"
ICON_SOFT = "#A6ADC8"
ICON_LIGHT = "#FFFFFF"
ICON_ACCENT = "#D9A441"
ICON_ERR = "#D14B4B"
ICON_OK = "#1F9D6B"
ICON_PRIMARY = "#4F5BD5"


def _pen(painter: QPainter, color: str, width: float) -> None:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)


def _draw(name: str, p: QPainter, color: str) -> None:
    p.setRenderHint(QPainter.Antialiasing, True)
    pen_w = 1.7
    _pen(p, color, pen_w)

    if name == "camera":
        p.drawRoundedRect(QRectF(3, 6.5, 18, 13), 2.6, 2.6)
        p.drawPolyline(QPolygonF([QPointF(8, 6.5), QPointF(9.6, 4.2), QPointF(14.4, 4.2), QPointF(16, 6.5)]))
        p.drawEllipse(QRectF(8.8, 9.6, 6.4, 6.4))
    elif name == "restore":
        path = QPainterPath(QPointF(20.2, 12))
        path.arcTo(QRectF(4.2, 4.2, 15.6, 15.6), 0, 300)
        p.drawPath(path)
        p.drawPolyline(QPolygonF([QPointF(20.2, 4.2), QPointF(20.2, 9.4), QPointF(15.0, 9.4)]))
    elif name == "refresh":
        path = QPainterPath(QPointF(19.5, 12))
        path.arcTo(QRectF(4.5, 4.5, 15, 15), 20, 290)
        p.drawPath(path)
        p.drawPolyline(QPolygonF([QPointF(20.2, 3.8), QPointF(20.2, 8.6), QPointF(15.4, 8.6)]))
    elif name == "folder":
        p.drawPolyline(QPolygonF([
            QPointF(3, 7.5), QPointF(3, 18.8), QPointF(21, 18.8), QPointF(21, 8.2),
            QPointF(11.6, 8.2), QPointF(9.4, 5.6), QPointF(3, 5.6), QPointF(3, 7.5),
        ]))
    elif name == "folder_plus":
        p.drawPolyline(QPolygonF([
            QPointF(3, 7.5), QPointF(3, 18.8), QPointF(21, 18.8), QPointF(21, 8.2),
            QPointF(11.6, 8.2), QPointF(9.4, 5.6), QPointF(3, 5.6), QPointF(3, 7.5),
        ]))
        p.drawLine(QPointF(12, 11.2), QPointF(12, 15.8))
        p.drawLine(QPointF(9.7, 13.5), QPointF(14.3, 13.5))
    elif name == "sort":
        p.drawLine(QPointF(3, 6), QPointF(13, 6))
        p.drawLine(QPointF(3, 12), QPointF(16, 12))
        p.drawLine(QPointF(3, 18), QPointF(9, 18))
        p.drawLine(QPointF(19, 5), QPointF(19, 15))
        p.drawPolyline(QPolygonF([QPointF(16, 12), QPointF(19, 15.4), QPointF(22, 12)]))
    elif name == "undo":
        p.drawPolyline(QPolygonF([QPointF(9, 6.5), QPointF(4, 12), QPointF(9, 17.5)]))
        p.drawLine(QPointF(4, 12), QPointF(14, 12))
        p.drawArc(QRectF(9, 7, 11, 10), 0, -180)
    elif name == "moon":
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        path = QPainterPath()
        path.addEllipse(QRectF(4.5, 2.5, 16, 19))
        cut = QPainterPath()
        cut.addEllipse(QRectF(10.5, 0.2, 15.5, 17.5))
        p.drawPath(path.subtracted(cut))
        p.restore()
    elif name == "star":
        points = []
        for i in range(8):
            radius = 9.5 if i % 2 == 0 else 2.6
            angle = math.radians(-90 + i * 45)
            points.append(QPointF(12 + radius * math.cos(angle), 12.5 + radius * math.sin(angle)))
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawPolygon(QPolygonF(points))
        p.restore()
    elif name == "sparkle":
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        path = QPainterPath()
        path.moveTo(12, 2)
        path.quadTo(13.2, 10.8, 22, 12)
        path.quadTo(13.2, 13.2, 12, 22)
        path.quadTo(10.8, 13.2, 2, 12)
        path.quadTo(10.8, 10.8, 12, 2)
        p.drawPath(path)
        p.restore()
    elif name == "sliders":
        p.drawLine(QPointF(3, 6.5), QPointF(21, 6.5))
        p.drawLine(QPointF(3, 12), QPointF(21, 12))
        p.drawLine(QPointF(3, 17.5), QPointF(21, 17.5))
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(9, 6.5), 2.5, 2.5)
        p.drawEllipse(QPointF(15.5, 12), 2.5, 2.5)
        p.drawEllipse(QPointF(7, 17.5), 2.5, 2.5)
        p.restore()
    elif name == "trash":
        p.drawLine(QPointF(4, 7), QPointF(20, 7))
        p.drawPolyline(QPolygonF([QPointF(9, 7), QPointF(9, 4.5), QPointF(15, 4.5), QPointF(15, 7)]))
        p.drawPolyline(QPolygonF([QPointF(6, 7), QPointF(7, 20), QPointF(17, 20), QPointF(18, 7)]))
        p.drawLine(QPointF(10, 10.5), QPointF(10.4, 16.5))
        p.drawLine(QPointF(14, 10.5), QPointF(13.6, 16.5))
    elif name == "pencil":
        p.drawPolyline(QPolygonF([
            QPointF(4, 20), QPointF(5.4, 14.6), QPointF(16.4, 3.6),
            QPointF(20.4, 7.6), QPointF(9.4, 18.6), QPointF(4, 20),
        ]))
        p.drawLine(QPointF(14.6, 5.4), QPointF(18.6, 9.4))
    elif name == "copy":
        p.drawRoundedRect(QRectF(8, 8, 12, 12), 2, 2)
        p.drawPolyline(QPolygonF([
            QPointF(16, 5.5), QPointF(16, 4.5), QPointF(16, 4), QPointF(4, 4),
            QPointF(4, 16), QPointF(4.5, 16), QPointF(5.5, 16),
        ]))
    elif name == "download":
        p.drawLine(QPointF(12, 3.5), QPointF(12, 15))
        p.drawPolyline(QPolygonF([QPointF(7.5, 10.5), QPointF(12, 15.2), QPointF(16.5, 10.5)]))
        p.drawPolyline(QPolygonF([QPointF(4, 16.5), QPointF(4, 20), QPointF(20, 20), QPointF(20, 16.5)]))
    elif name == "upload":
        p.drawLine(QPointF(12, 15), QPointF(12, 3.5))
        p.drawPolyline(QPolygonF([QPointF(7.5, 8), QPointF(12, 3.3), QPointF(16.5, 8)]))
        p.drawPolyline(QPolygonF([QPointF(4, 16.5), QPointF(4, 20), QPointF(20, 20), QPointF(20, 16.5)]))
    elif name == "plus":
        p.drawLine(QPointF(12, 5), QPointF(12, 19))
        p.drawLine(QPointF(5, 12), QPointF(19, 12))
    elif name == "chevron_right":
        p.drawPolyline(QPolygonF([QPointF(9.5, 5.5), QPointF(16, 12), QPointF(9.5, 18.5)]))
    elif name == "chevron_down":
        p.drawPolyline(QPolygonF([QPointF(5.5, 9.5), QPointF(12, 16), QPointF(18.5, 9.5)]))
    elif name == "more":
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        for x in (6, 12, 18):
            p.drawEllipse(QPointF(x, 12), 1.7, 1.7)
        p.restore()
    elif name == "search":
        p.drawEllipse(QRectF(4, 4, 12.5, 12.5))
        p.drawLine(QPointF(15.5, 15.5), QPointF(20.5, 20.5))
    elif name == "info":
        p.drawEllipse(QRectF(3.5, 3.5, 17, 17))
        p.drawLine(QPointF(12, 11), QPointF(12, 16.5))
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(12, 7.8), 1.1, 1.1)
        p.restore()
    elif name == "shield":
        p.drawPolyline(QPolygonF([
            QPointF(12, 3), QPointF(19, 5.8), QPointF(19, 11.5),
            QPointF(18.3, 14.5), QPointF(12, 20.5), QPointF(5.7, 14.5),
            QPointF(5, 11.5), QPointF(5, 5.8), QPointF(12, 3),
        ]))
        p.drawPolyline(QPolygonF([QPointF(9, 11.6), QPointF(11.4, 14), QPointF(15.4, 9.6)]))
    elif name == "monitor":
        p.drawRoundedRect(QRectF(2.8, 4, 18.4, 12.6), 2, 2)
        p.drawLine(QPointF(9, 20.5), QPointF(15, 20.5))
        p.drawLine(QPointF(12, 16.6), QPointF(12, 20.5))
    elif name == "clock":
        p.drawEllipse(QRectF(3.5, 3.5, 17, 17))
        p.drawLine(QPointF(12, 7.5), QPointF(12, 12.3))
        p.drawLine(QPointF(12, 12.3), QPointF(15.5, 14.2))
    elif name == "grid":
        for rect in (QRectF(3.5, 3.5, 7, 7), QRectF(13.5, 3.5, 7, 7),
                     QRectF(3.5, 13.5, 7, 7), QRectF(13.5, 13.5, 7, 7)):
            p.drawRoundedRect(rect, 1.8, 1.8)
    elif name == "sun":
        p.drawEllipse(QRectF(8, 8, 8, 8))
        for i in range(8):
            angle = math.radians(i * 45)
            p.drawLine(
                QPointF(12 + 6.3 * math.cos(angle), 12 + 6.3 * math.sin(angle)),
                QPointF(12 + 9.2 * math.cos(angle), 12 + 9.2 * math.sin(angle)),
            )
    elif name == "play":
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawPolygon(QPolygonF([QPointF(8, 5), QPointF(19, 12), QPointF(8, 19)]))
        p.restore()
    elif name == "tray":
        p.drawPolyline(QPolygonF([
            QPointF(3.5, 14), QPointF(3.5, 19.5), QPointF(20.5, 19.5),
            QPointF(20.5, 14),
        ]))
        p.drawLine(QPointF(12, 3.5), QPointF(12, 14))
        p.drawPolyline(QPolygonF([QPointF(7.5, 9.8), QPointF(12, 14.3), QPointF(16.5, 9.8)]))
    elif name == "external":
        p.drawPolyline(QPolygonF([
            QPointF(14, 4), QPointF(20, 4), QPointF(20, 10),
        ]))
        p.drawLine(QPointF(20, 4), QPointF(11, 13))
        p.drawPolyline(QPolygonF([
            QPointF(17, 14), QPointF(17, 20), QPointF(4, 20), QPointF(4, 7), QPointF(10, 7),
        ]))
    elif name == "list":
        p.drawEllipse(QPointF(5, 6.5), 1.1, 1.1)
        p.drawEllipse(QPointF(5, 12), 1.1, 1.1)
        p.drawEllipse(QPointF(5, 17.5), 1.1, 1.1)
        p.drawLine(QPointF(9, 6.5), QPointF(20, 6.5))
        p.drawLine(QPointF(9, 12), QPointF(20, 12))
        p.drawLine(QPointF(9, 17.5), QPointF(20, 17.5))
    elif name == "box":
        p.drawPolyline(QPolygonF([
            QPointF(3.5, 7.5), QPointF(12, 3.2), QPointF(20.5, 7.5),
            QPointF(20.5, 16.5), QPointF(12, 20.8), QPointF(3.5, 16.5), QPointF(3.5, 7.5),
        ]))
        p.drawLine(QPointF(3.5, 7.5), QPointF(12, 11.8))
        p.drawLine(QPointF(20.5, 7.5), QPointF(12, 11.8))
        p.drawLine(QPointF(12, 11.8), QPointF(12, 20.8))
    else:
        p.drawEllipse(QRectF(8, 8, 8, 8))


def make_icon(name: str, color: str = ICON_MUTED, size: int = 20) -> QIcon:
    scale = 2
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.scale(scale * size / 24.0, scale * size / 24.0)
    try:
        _draw(name, painter, color)
    finally:
        painter.end()
    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)


def icon_pixmap(name: str, color: str = ICON_MUTED, size: int = 20) -> QPixmap:
    return make_icon(name, color, size).pixmap(size, size)
