"""Small line icons drawn with Qt for consistent cross-platform rendering."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


def _canvas(color: str) -> tuple[QPixmap, QPainter]:
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    return pixmap, painter


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
