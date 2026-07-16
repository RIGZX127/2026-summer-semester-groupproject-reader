"""Reader mode and display controls."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QWidget,
)

from ui.icons import expand_icon, restore_icon, sidebar_icon
from ui.reader.theme import Theme


class ReaderToolbar(QWidget):
    mode_changed = Signal(str)
    font_size_changed = Signal(int)
    theme_preference_changed = Signal(str)
    content_width_changed = Signal(int)
    translation_requested = Signal()
    translation_cancel_requested = Signal()
    translation_mode_changed = Signal(str)
    sidebar_restore_requested = Signal()
    focus_mode_changed = Signal(bool)

    def __init__(self, theme: Theme | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReaderToolbar")
        current = theme or Theme()
        self.sidebar_restore_button = QPushButton()
        self.sidebar_restore_button.setIcon(sidebar_icon("#68766F"))
        self.sidebar_restore_button.setIconSize(QSize(18, 18))
        self.sidebar_restore_button.setFixedSize(34, 34)
        self.sidebar_restore_button.setAccessibleName(self.tr("显示订阅源栏"))
        self.sidebar_restore_button.setToolTip(self.tr("显示订阅源栏"))
        self.sidebar_restore_button.setObjectName("SidebarRestoreButton")
        self.sidebar_restore_button.hide()
        self.focus_button = QPushButton()
        self.focus_button.setCheckable(True)
        self.focus_button.setIcon(expand_icon())
        self.focus_button.setIconSize(QSize(18, 18))
        self.focus_button.setFixedSize(34, 34)
        self.focus_button.setAccessibleName(self.tr("进入或退出专注阅读"))
        self.focus_button.setToolTip(self.tr("隐藏订阅源和文章列表，让 Reader 占满窗口"))
        self.focus_button.setObjectName("FocusModeButton")
        self.reader_button = self._mode_button(self.tr("Reader"), "reader")
        self.web_button = self._mode_button(self.tr("Web"), "web")
        self.split_button = self._mode_button(self.tr("双栏"), "split")
        self.reader_button.setChecked(True)

        group = QButtonGroup(self)
        group.setExclusive(True)
        for button in (self.reader_button, self.web_button, self.split_button):
            group.addButton(button)

        self.font_size = QSpinBox()
        self.font_size.setRange(14, 24)
        self.font_size.setValue(current.font_size)
        self.font_size.setSuffix(self.tr(" px"))
        self.font_size.setAccessibleName(self.tr("正文字号"))
        self.font_size.setProperty("readerControl", True)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.tr("跟随系统"), "system")
        self.theme_combo.addItem(self.tr("浅色"), "light")
        self.theme_combo.addItem(self.tr("深色"), "dark")
        self.theme_combo.setAccessibleName(self.tr("应用主题"))
        self.theme_combo.setProperty("readerControl", True)

        self.width_combo = QComboBox()
        for label, width in ((self.tr("窄"), 640), (self.tr("中"), 760), (self.tr("宽"), 920)):
            self.width_combo.addItem(label, width)
        self.width_combo.setCurrentIndex(self.width_combo.findData(current.content_width))
        self.width_combo.setAccessibleName(self.tr("内容宽度"))
        self.width_combo.setProperty("readerControl", True)

        self.translate_button = QPushButton(self.tr("翻译"))
        self.translate_button.setAccessibleName(self.tr("翻译当前文章"))
        self.translate_button.setToolTip(self.tr("使用 AI 翻译当前文章；运行时再次点击可取消"))
        self.translate_button.setEnabled(False)
        self._translation_status = "idle"

        self.translation_mode = QComboBox()
        self.translation_mode.addItem(self.tr("原文"), "original")
        self.translation_mode.addItem(self.tr("双语"), "bilingual")
        self.translation_mode.addItem(self.tr("仅译文"), "translated")
        self.translation_mode.setAccessibleName(self.tr("译文显示方式"))
        self.translation_mode.setProperty("readerControl", True)
        self.translation_mode.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(self.sidebar_restore_button)
        layout.addWidget(self.reader_button)
        layout.addWidget(self.web_button)
        layout.addWidget(self.split_button)
        layout.addWidget(self.translate_button)
        layout.addWidget(self.translation_mode)
        layout.addStretch()
        layout.addWidget(QLabel(self.tr("字号")))
        layout.addWidget(self.font_size)
        layout.addWidget(self.theme_combo)
        layout.addWidget(self.width_combo)
        layout.addWidget(self.focus_button)

        self.font_size.valueChanged.connect(self.font_size_changed)
        self.theme_combo.currentIndexChanged.connect(
            lambda _index: self.theme_preference_changed.emit(str(self.theme_combo.currentData()))
        )
        self.width_combo.currentIndexChanged.connect(
            lambda _index: self.content_width_changed.emit(int(self.width_combo.currentData()))
        )
        self.translate_button.clicked.connect(self._translation_clicked)
        self.sidebar_restore_button.clicked.connect(self.sidebar_restore_requested)
        self.focus_button.toggled.connect(self._focus_toggled)
        self.translation_mode.currentIndexChanged.connect(
            lambda _index: self.translation_mode_changed.emit(
                str(self.translation_mode.currentData())
            )
        )

    def _mode_button(self, text: str, mode: str) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumSize(58, 36)
        button.setCheckable(True)
        button.setAccessibleName(self.tr("阅读模式：{0}").format(text))
        button.setToolTip(self.tr("切换到 {0} 模式").format(text))
        button.clicked.connect(lambda checked: checked and self.mode_changed.emit(mode))
        return button

    def set_theme_preference(self, value: str) -> None:
        index = self.theme_combo.findData(value)
        if index < 0:
            index = 0
        blocked = self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(index)
        self.theme_combo.blockSignals(blocked)

    def set_article_available(self, available: bool) -> None:
        if self._translation_status not in {"queued", "running"}:
            self.translate_button.setEnabled(available)

    def set_translation_state(self, status: str, progress: float = 0.0) -> None:
        self._translation_status = status
        if status == "queued":
            self.translate_button.setText(self.tr("翻译排队中"))
            self.translate_button.setEnabled(False)
        elif status == "running":
            percent = max(0, min(100, round(progress * 100)))
            self.translate_button.setText(self.tr("取消 {0}%").format(percent))
            self.translate_button.setEnabled(True)
        elif status == "error":
            self.translate_button.setText(self.tr("重试翻译"))
            self.translate_button.setEnabled(True)
        elif status == "cancelled":
            self.translate_button.setText(self.tr("继续翻译"))
            self.translate_button.setEnabled(True)
        else:
            self.translate_button.setText(
                self.tr("重新翻译") if status == "done" else self.tr("翻译")
            )
            self.translate_button.setEnabled(True)

    def show_translation_modes(self, visible: bool) -> None:
        self.translation_mode.setVisible(visible)

    def set_translation_mode(self, mode: str) -> None:
        index = self.translation_mode.findData(mode)
        if index >= 0:
            blocked = self.translation_mode.blockSignals(True)
            self.translation_mode.setCurrentIndex(index)
            self.translation_mode.blockSignals(blocked)

    def _translation_clicked(self) -> None:
        if self._translation_status == "running":
            self.translation_cancel_requested.emit()
        else:
            self.translation_requested.emit()

    def _focus_toggled(self, enabled: bool) -> None:
        self.focus_button.setIcon(restore_icon() if enabled else expand_icon())
        self.focus_button.setToolTip(
            self.tr("退出专注阅读")
            if enabled
            else self.tr("隐藏订阅源和文章列表，让 Reader 占满窗口")
        )
        self.focus_mode_changed.emit(enabled)

    def show_sidebar_restore(self, visible: bool) -> None:
        self.sidebar_restore_button.setVisible(visible)
