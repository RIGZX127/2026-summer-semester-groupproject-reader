"""Clickable tag badge bar for the reader view."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class TagBar(QWidget):
    """Horizontal row of tag badge chips displayed above reader content.

    Emits ``tag_clicked`` when the user clicks a badge, allowing the
    sidebar or entry list to filter by that tag.
    """

    tag_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TagBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addStretch()

        self._tags: list[str] = []
        self._layout = layout
        self.hide()

    # ── Public API ─────────────────────────────────────────────────────────

    def tags(self) -> list[str]:
        """Return the currently displayed tag names."""
        return list(self._tags)

    def set_tags(self, tags: list[str]) -> None:
        """Replace all displayed tag chips."""
        self._tags = list(tags)

        # Remove existing chips (keep the trailing stretch)
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name in tags:
            chip = _TagBadge(name, self)
            chip.clicked.connect(lambda n=name: self.tag_clicked.emit(n))
            self._layout.insertWidget(self._layout.count() - 1, chip)

        self.setVisible(bool(tags))


class _TagBadge(QPushButton):
    """A single tag pill — clickable, no remove button."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("TagBadge")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
