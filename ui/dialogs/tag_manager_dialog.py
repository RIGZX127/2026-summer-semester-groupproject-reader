"""Tag manager dialog — replace, add, and remove per-entry tags."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class TagChip(QWidget):
    """A single tag badge with a remove (x) button."""

    remove_clicked = Signal(str)

    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
        *,
        suggestion: bool = False,
    ) -> None:
        super().__init__(parent)
        self._text = text
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(text)
        label.setObjectName("TagChipLabel" if not suggestion else "TagSuggestionLabel")

        remove_btn = QPushButton("×" if not suggestion else "+")
        remove_btn.setObjectName(
            "TagRemoveButton" if not suggestion else "TagAddButton"
        )
        remove_btn.setFixedSize(20, 20)
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self._text))

        layout.addWidget(label)
        layout.addWidget(remove_btn)

    def tag_name(self) -> str:
        return self._text


class TagManagerDialog(QDialog):
    """Edit tags for a single entry.

    Displays current tags as removable chips, an input field for adding
    new tags, and optional AI suggestions as clickable chips.

    Usage::

        dialog = TagManagerDialog(current_tags, suggested_tags, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            names = dialog.tag_names()
    """

    def __init__(
        self,
        current_tags: list[str],
        suggested_tags: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("管理标签"))
        self.setMinimumWidth(440)
        self.setModal(True)

        self._tag_set: list[str] = list(current_tags)
        self._original: list[str] = list(current_tags)
        self._suggested = list(suggested_tags or [])

        # ── Title ──────────────────────────────────────────────────────
        title = QLabel(self.tr("管理标签"))
        title.setObjectName("SectionTitle")
        hint = QLabel(self.tr("点击 × 移除标签，在下框输入新标签并添加。"))
        hint.setObjectName("MutedLabel")

        # ── Current tags area ──────────────────────────────────────────
        self._chip_container = QWidget()
        self._chip_layout = QHBoxLayout(self._chip_container)
        self._chip_layout.setContentsMargins(0, 0, 0, 0)
        self._chip_layout.setSpacing(6)
        self._chip_layout.addStretch()

        chip_scroll = QScrollArea()
        chip_scroll.setWidgetResizable(True)
        chip_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chip_scroll.setFixedHeight(48)
        chip_scroll.setWidget(self._chip_container)

        # ── Add tag input ──────────────────────────────────────────────
        self._input = QLineEdit()
        self._input.setPlaceholderText(self.tr("输入标签名称，按回车添加"))
        self._input.setAccessibleName(self.tr("新标签名称"))
        self._input.returnPressed.connect(self._add_from_input)

        add_btn = QPushButton(self.tr("添加"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add_from_input)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        add_row.addWidget(self._input, 1)
        add_row.addWidget(add_btn)

        # ── Suggestions ────────────────────────────────────────────────
        suggestion_section = QWidget()
        suggestion_layout = QVBoxLayout(suggestion_section)
        suggestion_layout.setContentsMargins(0, 0, 0, 0)
        suggestion_layout.setSpacing(4)

        if self._suggested:
            sug_title = QLabel(self.tr("AI 建议标签（点击 + 添加）"))
            sug_title.setObjectName("MutedLabel")
            suggestion_layout.addWidget(sug_title)

            sug_chips = QWidget()
            sug_chips_layout = QHBoxLayout(sug_chips)
            sug_chips_layout.setContentsMargins(0, 0, 0, 0)
            sug_chips_layout.setSpacing(6)
            for name in self._suggested:
                if name not in self._tag_set:
                    chip = TagChip(name, suggestion=True)
                    chip.remove_clicked.connect(self._add_suggestion)
                    sug_chips_layout.addWidget(chip)
            sug_chips_layout.addStretch()
            suggestion_layout.addWidget(sug_chips)

        # ── Buttons ────────────────────────────────────────────────────
        self._cancel_btn = QPushButton(self.tr("取消"))
        self._save_btn = QPushButton(self.tr("保存"))
        self._save_btn.setObjectName("PrimaryButton")
        self._save_btn.setDefault(True)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._save_btn)

        # ── Main layout ────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(chip_scroll)
        layout.addLayout(add_row)
        layout.addWidget(suggestion_section)
        layout.addSpacing(8)
        layout.addLayout(btn_row)

        # ── Connections ────────────────────────────────────────────────
        self._cancel_btn.clicked.connect(self.reject)
        self._save_btn.clicked.connect(self.accept)

        # ── Initial chips ──────────────────────────────────────────────
        self._rebuild_chips()

    # ── Public API ─────────────────────────────────────────────────────────

    def tag_names(self) -> list[str]:
        """Return the final tag list after the dialog is accepted."""
        return list(self._tag_set)

    def reject(self) -> None:
        """Restore original tags on cancel."""
        self._tag_set[:] = self._original
        super().reject()

    # ── Internal ───────────────────────────────────────────────────────────

    def _rebuild_chips(self) -> None:
        """Recreate all chip widgets from ``_tag_set``."""
        # Remove existing chips (keep the stretch)
        while self._chip_layout.count() > 1:
            item = self._chip_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name in self._tag_set:
            chip = TagChip(name)
            chip.remove_clicked.connect(self._remove_tag)
            self._chip_layout.insertWidget(self._chip_layout.count() - 1, chip)

    def _remove_tag(self, name: str) -> None:
        if name in self._tag_set:
            self._tag_set.remove(name)
            self._rebuild_chips()

    def _add_tag(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            return
        if cleaned in self._tag_set:
            return
        self._tag_set.append(cleaned)
        self._rebuild_chips()

    def _add_from_input(self) -> None:
        self._add_tag(self._input.text())
        self._input.clear()
        self._input.setFocus()

    def _add_suggestion(self, name: str) -> None:
        self._add_tag(name)
