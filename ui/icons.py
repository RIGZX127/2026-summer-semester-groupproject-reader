"""Small line icons drawn with Qt for consistent cross-platform rendering."""

from __future__ import annotations

from math import cos, pi, sin

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF

COMPACT_CONTROL_SIZE = 36
COMPACT_ICON_SIZE = 20


def _canvas(color: str) -> tuple[QPixmap, QPainter]:
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.65, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    return pixmap, painter


def stateful_icon(normal: QIcon, checked: QIcon) -> QIcon:
    """Combine normal and checked artwork so toggled buttons retain contrast."""
    size = QSize(20, 20)
    normal_pixmap = normal.pixmap(size)
    checked_pixmap = checked.pixmap(size)
    icon = QIcon()
    for mode in (QIcon.Mode.Normal, QIcon.Mode.Active, QIcon.Mode.Selected):
        icon.addPixmap(normal_pixmap, mode, QIcon.State.Off)
        icon.addPixmap(checked_pixmap, mode, QIcon.State.On)
    icon.addPixmap(normal_pixmap, QIcon.Mode.Disabled, QIcon.State.Off)
    icon.addPixmap(checked_pixmap, QIcon.Mode.Disabled, QIcon.State.On)
    return icon


def sidebar_icon(color: str = "#EAF0ED") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawRoundedRect(3, 4, 14, 12, 3, 3)
    painter.drawLine(8, 4, 8, 16)
    painter.end()
    return QIcon(pixmap)


def expand_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    for x1, y1, x2, y2 in (
        (4, 8, 4, 4),
        (4, 4, 8, 4),
        (12, 4, 16, 4),
        (16, 4, 16, 8),
        (4, 12, 4, 16),
        (4, 16, 8, 16),
        (12, 16, 16, 16),
        (16, 16, 16, 12),
    ):
        painter.drawLine(x1, y1, x2, y2)
    painter.end()
    return QIcon(pixmap)


def restore_icon(color: str = "#FFFFFF") -> QIcon:
    pixmap, painter = _canvas(color)
    for x1, y1, x2, y2 in (
        (8, 8, 4, 8),
        (8, 8, 8, 4),
        (12, 8, 16, 8),
        (12, 8, 12, 4),
        (8, 12, 4, 12),
        (8, 12, 8, 16),
        (12, 12, 16, 12),
        (12, 12, 12, 16),
    ):
        painter.drawLine(x1, y1, x2, y2)
    painter.end()
    return QIcon(pixmap)


def add_icon(color: str = "#EAF0ED") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawEllipse(QPointF(10, 10), 7, 7)
    painter.drawLine(10, 6, 10, 14)
    painter.drawLine(6, 10, 14, 10)
    painter.end()
    return QIcon(pixmap)


def sync_icon(color: str = "#EAF0ED") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawArc(QRectF(3.5, 3.5, 13, 13), 35 * 16, 145 * 16)
    painter.drawArc(QRectF(3.5, 3.5, 13, 13), 215 * 16, 145 * 16)
    painter.drawLine(QPointF(4.2, 6.2), QPointF(4.0, 3.3))
    painter.drawLine(QPointF(4.2, 6.2), QPointF(7.0, 5.7))
    painter.drawLine(QPointF(15.8, 13.8), QPointF(16.0, 16.7))
    painter.drawLine(QPointF(15.8, 13.8), QPointF(13.0, 14.3))
    painter.end()
    return QIcon(pixmap)


def settings_icon(color: str = "#EAF0ED") -> QIcon:
    pixmap, painter = _canvas(color)
    points: list[QPointF] = []
    for tooth in range(8):
        center_angle = -67.5 + tooth * 45
        for offset, radius in ((-22.5, 6.0), (-12, 7.6), (12, 7.6), (22.5, 6.0)):
            radians = (center_angle + offset) * pi / 180
            points.append(QPointF(10 + cos(radians) * radius, 10 + sin(radians) * radius))
    painter.drawPolygon(QPolygonF(points))
    painter.drawEllipse(QPointF(10, 10), 2.7, 2.7)
    painter.end()
    return QIcon(pixmap)


def agent_icon(color: str = "#EAF0ED") -> QIcon:
    """Draw a connected chat-agent mark distinct from the theme sun icon."""
    pixmap, painter = _canvas(color)
    painter.drawRoundedRect(3, 4, 14, 12, 4, 4)
    painter.drawLine(10, 4, 10, 2)
    painter.drawEllipse(QPointF(10, 2), 0.8, 0.8)
    painter.drawEllipse(QPointF(7.2, 9.5), 1, 1)
    painter.drawEllipse(QPointF(12.8, 9.5), 1, 1)
    painter.drawArc(QRectF(7, 9, 6, 4), 205 * 16, 130 * 16)
    painter.end()
    return QIcon(pixmap)


def feed_icon(color: str = "#7D9188") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawEllipse(QPointF(5, 15), 1.25, 1.25)
    painter.drawArc(QRectF(4, 8, 8, 8), 0, 90 * 16)
    painter.drawArc(QRectF(4, 4, 12, 12), 0, 90 * 16)
    painter.end()
    return QIcon(pixmap)


def import_icon(color: str = "#EAF0ED") -> QIcon:
    """Draw a downward arrow entering a shared file tray."""
    pixmap, painter = _canvas(color)
    painter.drawLine(10, 3, 10, 12)
    painter.drawLine(6.8, 9, 10, 12.2)
    painter.drawLine(13.2, 9, 10, 12.2)
    painter.drawRoundedRect(3, 12, 14, 5, 2, 2)
    painter.drawLine(3, 12, 3, 16)
    painter.drawLine(17, 12, 17, 16)
    painter.drawLine(3, 14.5, 7, 14.5)
    painter.drawLine(13, 14.5, 17, 14.5)
    painter.end()
    return QIcon(pixmap)


def export_icon(color: str = "#EAF0ED") -> QIcon:
    """Draw an upward arrow leaving a shared file tray."""
    pixmap, painter = _canvas(color)
    painter.drawLine(10, 12, 10, 3)
    painter.drawLine(6.8, 6.2, 10, 3)
    painter.drawLine(13.2, 6.2, 10, 3)
    painter.drawRoundedRect(3, 12, 14, 5, 2, 2)
    painter.drawLine(3, 12, 3, 16)
    painter.drawLine(17, 12, 17, 16)
    painter.drawLine(3, 14.5, 7, 14.5)
    painter.drawLine(13, 14.5, 17, 14.5)
    painter.end()
    return QIcon(pixmap)


def reader_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawLine(10, 5, 10, 16)
    painter.drawArc(QRectF(3, 4, 7, 12), 90 * 16, 180 * 16)
    painter.drawArc(QRectF(10, 4, 7, 12), 270 * 16, 180 * 16)
    painter.drawLine(4, 4, 8, 4)
    painter.drawLine(12, 4, 16, 4)
    painter.end()
    return QIcon(pixmap)


def web_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawEllipse(QRectF(3, 3, 14, 14))
    painter.drawEllipse(QRectF(7, 3, 6, 14))
    painter.drawLine(4, 7, 16, 7)
    painter.drawLine(4, 13, 16, 13)
    painter.drawLine(3, 10, 17, 10)
    painter.end()
    return QIcon(pixmap)


def split_view_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawRoundedRect(3, 4, 14, 12, 2, 2)
    painter.drawLine(10, 4, 10, 16)
    painter.drawLine(6, 7, 8, 7)
    painter.drawLine(12, 7, 14, 7)
    painter.end()
    return QIcon(pixmap)


def font_size_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    font = QFont()
    font.setPixelSize(14)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRectF(1, 1, 13, 18), Qt.AlignmentFlag.AlignCenter, "A")
    font.setPixelSize(9)
    painter.setFont(font)
    painter.drawText(QRectF(11, 7, 8, 10), Qt.AlignmentFlag.AlignCenter, "a")
    painter.end()
    return QIcon(pixmap)


def theme_icon(color: str = "#68766F", mode: str = "system") -> QIcon:
    pixmap, painter = _canvas(color)
    if mode == "light":
        painter.drawEllipse(QPointF(10, 10), 3.2, 3.2)
        for angle in range(0, 360, 45):
            radians = angle * pi / 180
            painter.drawLine(
                QPointF(10 + cos(radians) * 5.3, 10 + sin(radians) * 5.3),
                QPointF(10 + cos(radians) * 7, 10 + sin(radians) * 7),
            )
    elif mode == "dark":
        painter.drawArc(QRectF(4, 3, 13, 14), 70 * 16, 220 * 16)
        painter.drawArc(QRectF(8, 2, 9, 12), 90 * 16, 190 * 16)
    else:
        painter.drawRoundedRect(3, 4, 14, 12, 2, 2)
        painter.drawLine(10, 4, 10, 16)
        painter.drawLine(5, 7, 8, 7)
        painter.drawLine(5, 10, 8, 10)
    painter.end()
    return QIcon(pixmap)


def width_icon(color: str = "#68766F", inset: int = 0) -> QIcon:
    pixmap, painter = _canvas(color)
    left = 4 + inset
    right = 16 - inset
    painter.drawLine(left, 10, right, 10)
    painter.drawLine(left, 10, left + 3, 7)
    painter.drawLine(left, 10, left + 3, 13)
    painter.drawLine(right, 10, right - 3, 7)
    painter.drawLine(right, 10, right - 3, 13)
    painter.end()
    return QIcon(pixmap)


def translate_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawRoundedRect(3, 4, 8, 8, 2, 2)
    painter.drawRoundedRect(9, 8, 8, 8, 2, 2)
    painter.drawLine(5, 7, 9, 7)
    painter.drawLine(7, 5.5, 7, 9.5)
    painter.drawLine(11.5, 13, 14.5, 13)
    painter.drawLine(13, 11.5, 13, 14.5)
    painter.end()
    return QIcon(pixmap)


def batch_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    for top in (4, 11):
        painter.drawRoundedRect(3, top, 5, 5, 1.5, 1.5)
        painter.drawLine(10, top + 2, 17, top + 2)
    painter.drawLine(4, 6, 5, 7)
    painter.drawLine(5, 7, 7, 4)
    painter.end()
    return QIcon(pixmap)


def read_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawEllipse(QRectF(3, 3, 14, 14))
    painter.drawLine(6, 10, 9, 13)
    painter.drawLine(9, 13, 14, 7)
    painter.end()
    return QIcon(pixmap)


def unread_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawEllipse(QRectF(4, 4, 12, 12))
    painter.drawEllipse(QPointF(10, 10), 1.2, 1.2)
    painter.end()
    return QIcon(pixmap)


def star_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    points = []
    for index in range(10):
        radius = 7.2 if index % 2 == 0 else 3.4
        angle = -pi / 2 + index * pi / 5
        points.append(QPointF(10 + cos(angle) * radius, 10 + sin(angle) * radius))
    painter.drawPolygon(QPolygonF(points))
    painter.end()
    return QIcon(pixmap)


def delete_icon(color: str = "#B85B55") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawRoundedRect(6, 6, 8, 11, 2, 2)
    painter.drawLine(4.5, 5, 15.5, 5)
    painter.drawLine(8, 3, 12, 3)
    painter.drawLine(8.7, 8.5, 8.7, 14)
    painter.drawLine(11.3, 8.5, 11.3, 14)
    painter.end()
    return QIcon(pixmap)


def close_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawLine(6, 6, 14, 14)
    painter.drawLine(14, 6, 6, 14)
    painter.end()
    return QIcon(pixmap)
