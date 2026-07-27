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
from ui.icons import COMPACT_ICON_SIZE, agent_icon
from ui.theme import LIGHT_PALETTE


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

    ai_tags_requested = Signal()

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
        self.ai_button = QPushButton()
        self.ai_button.setObjectName("TagAIButton")
        self.ai_button.setIcon(agent_icon(LIGHT_PALETTE.text))
        self.ai_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.ai_button.setFixedSize(36, 36)
        self.ai_button.setToolTip(self.tr("使用 AI 生成标签"))
        self.ai_button.setAccessibleName(self.tr("AI 生成标签"))
        self.ai_button.clicked.connect(self._request_ai_tags)
        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.ai_button)
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

        self._ai_status = QLabel()
        self._ai_status.setObjectName("MutedLabel")
        self._suggestion_section = QWidget()
        self._suggestion_layout = QVBoxLayout(self._suggestion_section)
        self._suggestion_layout.setContentsMargins(0, 0, 0, 0)
        self._suggestion_layout.setSpacing(4)
        self._rebuild_suggestions()

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
        layout.addLayout(title_row)
        layout.addWidget(hint)
        layout.addWidget(self.tag_scroll)
        layout.addLayout(add_row)
        layout.addWidget(self._ai_status)
        layout.addWidget(self._suggestion_section)
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

    def suggested_tag_names(self) -> list[str]:
        return list(self._suggested)

    def set_ai_state(
        self,
        status: str,
        suggestions: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        running = status in {"queued", "running"}
        self.ai_button.setEnabled(not running)
        if running:
            self._ai_status.setText(self.tr("正在生成标签…"))
        elif status == "error":
            self._ai_status.setText(self.tr("生成失败：{0}").format(error or self.tr("未知错误")))
        else:
            self._ai_status.clear()
        if suggestions is not None:
            self._suggested = list(dict.fromkeys(suggestions))
            self._rebuild_suggestions()

    def _request_ai_tags(self) -> None:
        self.set_ai_state("queued")
        self.ai_tags_requested.emit()

    def _rebuild_suggestions(self) -> None:
        while self._suggestion_layout.count():
            item = self._suggestion_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        available = [name for name in self._suggested if name not in self._tag_set]
        self._suggestion_section.setVisible(bool(available))
        if not available:
            return
        suggestion_title = QLabel(self.tr("AI 建议标签（点击 + 添加）"))
        suggestion_title.setObjectName("MutedLabel")
        self._suggestion_layout.addWidget(suggestion_title)
        suggestion_container = QWidget()
        suggestion_flow = FlowLayout(
            suggestion_container,
            horizontal_spacing=4,
            vertical_spacing=4,
        )
        for name in available:
            chip = TagChip(name, suggestion=True)
            chip.remove_clicked.connect(self._add_suggestion)
            suggestion_flow.addWidget(chip)
        self._suggestion_layout.addWidget(suggestion_container)

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
        self._rebuild_suggestions()
