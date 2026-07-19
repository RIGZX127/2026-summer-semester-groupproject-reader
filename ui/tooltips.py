"""Immediate, accessible tooltip behavior for compact icon controls."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtWidgets import QToolTip, QWidget


class _ImmediateToolTipFilter(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if isinstance(watched, QWidget):
            if event.type() == QEvent.Type.Enter and watched.toolTip():
                position = watched.mapToGlobal(watched.rect().bottomLeft()) + QPoint(0, 4)
                QToolTip.showText(position, watched.toolTip(), watched)
            elif event.type() in {QEvent.Type.Leave, QEvent.Type.Hide}:
                QToolTip.hideText()
        return super().eventFilter(watched, event)


def enable_immediate_tooltip(widget: QWidget) -> None:
    """Show an icon control's existing tooltip as soon as the pointer enters."""
    widget.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
    widget.setProperty("immediateToolTip", True)
    tooltip_filter = _ImmediateToolTipFilter(widget)
    widget.installEventFilter(tooltip_filter)
    widget._immediate_tooltip_filter = tooltip_filter  # type: ignore[attr-defined]
