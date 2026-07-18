"""Small line icons drawn with Qt for consistent cross-platform rendering."""

from __future__ import annotations

from math import cos, pi, sin

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF

COMPACT_CONTROL_SIZE = 30
COMPACT_ICON_SIZE = 18


def _canvas(color: str) -> tuple[QPixmap, QPainter]:
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
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
    painter.drawLine(10, 4, 10, 16)
    painter.drawLine(4, 10, 16, 10)
    painter.end()
    return QIcon(pixmap)


def sync_icon(color: str = "#EAF0ED") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawArc(QRectF(4, 4, 12, 12), 40 * 16, 250 * 16)
    painter.drawLine(14, 4, 16, 7)
    painter.drawLine(14, 4, 11, 5)
    painter.end()
    return QIcon(pixmap)


def settings_icon(color: str = "#EAF0ED") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawEllipse(QPointF(10, 10), 3.2, 3.2)
    for angle in range(0, 360, 45):
        radians = angle * pi / 180
        painter.drawLine(
            QPointF(10 + cos(radians) * 5.2, 10 + sin(radians) * 5.2),
            QPointF(10 + cos(radians) * 7.2, 10 + sin(radians) * 7.2),
        )
    painter.end()
    return QIcon(pixmap)


def agent_icon(color: str = "#EAF0ED") -> QIcon:
    """Draw a connected chat-agent mark distinct from the theme sun icon."""
    pixmap, painter = _canvas(color)
    painter.drawRoundedRect(3, 3, 14, 12, 3, 3)
    painter.drawLine(7, 15, 5, 18)
    painter.drawEllipse(QPointF(7, 9), 1.2, 1.2)
    painter.drawEllipse(QPointF(13, 9), 1.2, 1.2)
    painter.drawLine(QPointF(8.2, 9), QPointF(11.8, 9))
    painter.end()
    return QIcon(pixmap)


def feed_icon(color: str = "#7D9188") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawEllipse(QPointF(5, 15), 1.4, 1.4)
    painter.drawArc(QRectF(4, 8, 8, 8), 0, 90 * 16)
    painter.drawArc(QRectF(4, 4, 12, 12), 0, 90 * 16)
    painter.end()
    return QIcon(pixmap)


def reader_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawRoundedRect(4, 3, 12, 14, 2, 2)
    painter.drawLine(7, 7, 13, 7)
    painter.drawLine(7, 10, 13, 10)
    painter.drawLine(7, 13, 11, 13)
    painter.end()
    return QIcon(pixmap)


def web_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawEllipse(QRectF(3, 3, 14, 14))
    painter.drawEllipse(QRectF(7, 3, 6, 14))
    painter.drawLine(3, 10, 17, 10)
    painter.end()
    return QIcon(pixmap)


def split_view_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawRoundedRect(3, 4, 14, 12, 2, 2)
    painter.drawLine(10, 4, 10, 16)
    painter.end()
    return QIcon(pixmap)


def font_size_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    font = QFont()
    font.setPixelSize(15)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRectF(1, 1, 18, 18), Qt.AlignmentFlag.AlignCenter, "A")
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
    painter.drawLine(6, 7, 9, 7)
    painter.drawLine(7, 6, 7, 10)
    painter.drawLine(11, 13, 15, 13)
    painter.end()
    return QIcon(pixmap)


def batch_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    for top in (4, 11):
        painter.drawRoundedRect(3, top, 5, 5, 1, 1)
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
    painter.end()
    return QIcon(pixmap)


def star_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    points = []
    for index in range(10):
        radius = 7 if index % 2 == 0 else 3
        angle = -pi / 2 + index * pi / 5
        points.append(QPointF(10 + cos(angle) * radius, 10 + sin(angle) * radius))
    painter.drawPolygon(QPolygonF(points))
    painter.end()
    return QIcon(pixmap)


def delete_icon(color: str = "#B85B55") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawRoundedRect(6, 6, 8, 11, 1, 1)
    painter.drawLine(5, 5, 15, 5)
    painter.drawLine(8, 3, 12, 3)
    painter.drawLine(9, 8, 9, 14)
    painter.drawLine(11, 8, 11, 14)
    painter.end()
    return QIcon(pixmap)


def close_icon(color: str = "#68766F") -> QIcon:
    pixmap, painter = _canvas(color)
    painter.drawLine(5, 5, 15, 15)
    painter.drawLine(15, 5, 5, 15)
    painter.end()
    return QIcon(pixmap)
