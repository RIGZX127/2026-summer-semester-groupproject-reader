"""Tag manager dialog with wrapping, accessible tag actions."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
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

from ui.flow_layout import FlowLayout


class TagChip(QWidget):
    """A tag badge with a compact glyph and a full-size click target."""

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
        self.setObjectName("TagSuggestionChip" if suggestion else "TagChip")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 2, 2)
        layout.setSpacing(2)

        label = QLabel(text)
        label.setObjectName("TagSuggestionLabel" if suggestion else "TagChipLabel")
        layout.addWidget(label)

        button = QPushButton("+" if suggestion else "×")
        button.setObjectName("TagAddButton" if suggestion else "TagRemoveButton")
        button.setMinimumSize(36, 36)
        button.setMaximumSize(36, 36)
        button.setIconSize(QSize(16, 16))
        action_name = (
            self.tr("添加建议标签：{0}").format(text)
            if suggestion
            else self.tr("移除标签：{0}").format(text)
        )
        button.setToolTip(action_name)
        button.setAccessibleName(action_name)
        button.clicked.connect(lambda: self.remove_clicked.emit(self._text))
        layout.addWidget(button)

    def tag_name(self) -> str:
        return self._text


class TagManagerDialog(QDialog):
    """Edit current tags and apply optional AI suggestions."""

    _MIN_TAG_AREA_HEIGHT = 52
    _MAX_TAG_AREA_HEIGHT = 172

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
        self._tag_set = list(current_tags)
        self._original = list(current_tags)
        self._suggested = list(suggested_tags or [])

        title = QLabel(self.tr("管理标签"))
        title.setObjectName("SectionTitle")
        hint = QLabel(self.tr("移除现有标签，或输入新标签后添加。"))
        hint.setObjectName("MutedLabel")

        self._chip_container = QWidget()
        self._chip_container.setObjectName("TagChipContainer")
        self._chip_layout = FlowLayout(
            self._chip_container,
            margin=6,
            horizontal_spacing=4,
            vertical_spacing=4,
        )
        self.tag_scroll = QScrollArea()
        self.tag_scroll.setObjectName("TagChipScrollArea")
        self.tag_scroll.setWidgetResizable(True)
        self.tag_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tag_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tag_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tag_scroll.setWidget(self._chip_container)
        self.tag_scroll.viewport().installEventFilter(self)

        self._input = QLineEdit()
        self._input.setPlaceholderText(self.tr("输入标签名称，按回车添加"))
        self._input.setAccessibleName(self.tr("新标签名称"))
        self._input.returnPressed.connect(self._add_from_input)
        add_button = QPushButton(self.tr("添加"))
        add_button.setObjectName("PrimaryButton")
        add_button.clicked.connect(self._add_from_input)
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        add_row.addWidget(self._input, 1)
        add_row.addWidget(add_button)

        suggestion_section = QWidget()
        suggestion_layout = QVBoxLayout(suggestion_section)
        suggestion_layout.setContentsMargins(0, 0, 0, 0)
        suggestion_layout.setSpacing(4)
        if self._suggested:
            suggestion_title = QLabel(self.tr("AI 建议标签（点击 + 添加）"))
            suggestion_title.setObjectName("MutedLabel")
            suggestion_layout.addWidget(suggestion_title)
            suggestion_container = QWidget()
            suggestion_flow = FlowLayout(
                suggestion_container,
                horizontal_spacing=4,
                vertical_spacing=4,
            )
            for name in self._suggested:
                if name not in self._tag_set:
                    chip = TagChip(name, suggestion=True)
                    chip.remove_clicked.connect(self._add_suggestion)
                    suggestion_flow.addWidget(chip)
            suggestion_layout.addWidget(suggestion_container)

        self._cancel_btn = QPushButton(self.tr("取消"))
        self._save_btn = QPushButton(self.tr("保存"))
        self._save_btn.setObjectName("PrimaryButton")
        self._save_btn.setDefault(True)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self._cancel_btn)
        button_row.addWidget(self._save_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.tag_scroll)
        layout.addLayout(add_row)
        layout.addWidget(suggestion_section)
        layout.addSpacing(4)
        layout.addLayout(button_row)

        self._cancel_btn.clicked.connect(self.reject)
        self._save_btn.clicked.connect(self.accept)
        self._rebuild_chips()

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802
        if watched is self.tag_scroll.viewport() and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._sync_tag_area_height)
        return super().eventFilter(watched, event)

    def tag_names(self) -> list[str]:
        return list(self._tag_set)

    def reject(self) -> None:
        self._tag_set[:] = self._original
        super().reject()

    def _rebuild_chips(self) -> None:
        while self._chip_layout.count():
            item = self._chip_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        for name in self._tag_set:
            chip = TagChip(name)
            chip.remove_clicked.connect(self._remove_tag)
            self._chip_layout.addWidget(chip)
        QTimer.singleShot(0, self._sync_tag_area_height)

    def _sync_tag_area_height(self) -> None:
        viewport_width = max(300, self.tag_scroll.viewport().width())
        content_height = self._chip_layout.heightForWidth(viewport_width)
        desired = max(self._MIN_TAG_AREA_HEIGHT, content_height + 4)
        self.tag_scroll.setFixedHeight(min(self._MAX_TAG_AREA_HEIGHT, desired))
        self._chip_container.setMinimumHeight(content_height)

    def _remove_tag(self, name: str) -> None:
        if name in self._tag_set:
            self._tag_set.remove(name)
            self._rebuild_chips()

    def _add_tag(self, name: str) -> None:
        cleaned = name.strip()
        if cleaned and cleaned not in self._tag_set:
            self._tag_set.append(cleaned)
            self._rebuild_chips()

    def _add_from_input(self) -> None:
        self._add_tag(self._input.text())
        self._input.clear()
        self._input.setFocus()

    def _add_suggestion(self, name: str) -> None:
        self._add_tag(name)
