"""Reader mode and display controls."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Signal
from PySide6.QtGui import QActionGroup, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QWidget,
)

from ui.icons import (
    COMPACT_CONTROL_SIZE,
    COMPACT_ICON_SIZE,
    expand_icon,
    font_size_icon,
    reader_icon,
    restore_icon,
    sidebar_icon,
    split_view_icon,
    stateful_icon,
    theme_icon,
    translate_icon,
    web_icon,
    width_icon,
)
from ui.reader.theme import Theme
from ui.tooltips import enable_immediate_tooltip


class PopupIconButton(QPushButton):
    """Square icon button backed by a popup menu of labeled choices."""

    currentIndexChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReaderPopupButton")
        self._menu = QMenu(self)
        self._group = QActionGroup(self)
        self._group.setExclusive(True)
        self._current_index = -1
        self._display_icon = QIcon()
        self.clicked.connect(self._show_popup)

    def addItem(self, icon: QIcon, text: str, data: object) -> None:  # noqa: N802
        action = self._menu.addAction(icon, text)
        action.setCheckable(True)
        action.setData(data)
        self._group.addAction(action)
        index = len(self._menu.actions()) - 1
        action.triggered.connect(lambda _checked, item=index: self.setCurrentIndex(item))
        if self._current_index < 0:
            self.setCurrentIndex(0)

    def set_display_icon(self, icon: QIcon) -> None:
        self._display_icon = icon
        self._refresh_icon()

    def count(self) -> int:
        return len(self._menu.actions())

    def itemData(self, index: int) -> object:  # noqa: N802
        return self._menu.actions()[index].data()

    def itemText(self, index: int) -> str:  # noqa: N802
        return self._menu.actions()[index].text()

    def itemIcon(self, index: int) -> QIcon:  # noqa: N802
        return self._menu.actions()[index].icon()

    def currentData(self) -> object:  # noqa: N802
        return self.itemData(self._current_index)

    def findData(self, data: object) -> int:  # noqa: N802
        return next(
            (index for index in range(self.count()) if self.itemData(index) == data),
            -1,
        )

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        if not 0 <= index < self.count() or index == self._current_index:
            return
        self._current_index = index
        self._menu.actions()[index].setChecked(True)
        self._refresh_icon()
        self.currentIndexChanged.emit(index)

    def _refresh_icon(self) -> None:
        if self._current_index < 0:
            return
        action_icon = self.itemIcon(self._current_index)
        self.setIcon(self._display_icon if not self._display_icon.isNull() else action_icon)

    def _show_popup(self) -> None:
        self._menu.popup(self.mapToGlobal(QPoint(0, self.height())))


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
        self.sidebar_restore_button.setIcon(sidebar_icon("#4E5E57"))
        self.sidebar_restore_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.sidebar_restore_button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.sidebar_restore_button.setAccessibleName(self.tr("显示订阅源栏"))
        self.sidebar_restore_button.setToolTip(self.tr("显示订阅源栏"))
        self.sidebar_restore_button.setObjectName("SidebarRestoreButton")
        self.sidebar_restore_button.hide()
        self.focus_button = QPushButton()
        self.focus_button.setCheckable(True)
        self.focus_button.setIcon(expand_icon("#4E5E57"))
        self.focus_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.focus_button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.focus_button.setAccessibleName(self.tr("进入或退出专注阅读"))
        self.focus_button.setToolTip(self.tr("隐藏订阅源和文章列表，让 Reader 占满窗口"))
        self.focus_button.setObjectName("FocusModeButton")
        self.reader_button = self._mode_button(
            stateful_icon(reader_icon("#4E5E57"), reader_icon("#FFFFFF")),
            self.tr("Reader"),
            "reader",
        )
        self.web_button = self._mode_button(
            stateful_icon(web_icon("#4E5E57"), web_icon("#FFFFFF")),
            self.tr("Web"),
            "web",
        )
        self.split_button = self._mode_button(
            stateful_icon(split_view_icon("#4E5E57"), split_view_icon("#FFFFFF")),
            self.tr("双栏"),
            "split",
        )
        self.reader_button.setChecked(True)

        group = QButtonGroup(self)
        group.setExclusive(True)
        for button in (self.reader_button, self.web_button, self.split_button):
            group.addButton(button)

        self.font_size = PopupIconButton()
        for value in range(14, 25):
            self.font_size.addItem(QIcon(), str(value), value)
        self.font_size.set_display_icon(font_size_icon("#4E5E57"))
        self.font_size.setCurrentIndex(self.font_size.findData(current.font_size))
        self.font_size.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.font_size.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.font_size.setAccessibleName(self.tr("正文字号"))
        self.font_size.setToolTip(self.tr("正文字号：{0}").format(current.font_size))
        self.font_size.setProperty("readerControl", True)
        self.font_size.setProperty("compactIcon", True)

        self.theme_combo = PopupIconButton()
        self.theme_combo.addItem(
            theme_icon("#4E5E57", mode="system"), self.tr("跟随系统"), "system"
        )
        self.theme_combo.addItem(theme_icon("#4E5E57", mode="light"), self.tr("浅色"), "light")
        self.theme_combo.addItem(theme_icon("#4E5E57", mode="dark"), self.tr("深色"), "dark")
        self.theme_combo.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.theme_combo.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.theme_combo.setAccessibleName(self.tr("应用主题"))
        self.theme_combo.setToolTip(self.tr("应用主题：跟随系统"))
        self.theme_combo.setProperty("readerControl", True)
        self.theme_combo.setProperty("compactIcon", True)

        self.width_combo = PopupIconButton()
        for label, inset, width in (
            (self.tr("窄"), 3, 640),
            (self.tr("中"), 1, 760),
            (self.tr("宽"), 0, 920),
        ):
            self.width_combo.addItem(width_icon("#4E5E57", inset=inset), label, width)
        self.width_combo.setCurrentIndex(self.width_combo.findData(current.content_width))
        self.width_combo.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.width_combo.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.width_combo.setAccessibleName(self.tr("内容宽度"))
        self.width_combo.setToolTip(self.tr("正文边距与内容宽度"))
        self.width_combo.setProperty("readerControl", True)
        self.width_combo.setProperty("compactIcon", True)

        self.translate_button = QPushButton()
        self.translate_button.setObjectName("TranslateButton")
        self.translate_button.setIcon(translate_icon("#4E5E57"))
        self.translate_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.translate_button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.translate_button.setAccessibleName(self.tr("翻译当前文章"))
        self.translate_button.setToolTip(self.tr("使用 AI 翻译当前文章；运行时再次点击可取消"))
        self.translate_button.setEnabled(False)
        self._translation_status = "idle"

        self.translation_mode = QComboBox()
        self.translation_mode.addItem(self.tr("原文"), "original")
        self.translation_mode.addItem(self.tr("双语"), "bilingual")
        self.translation_mode.addItem(self.tr("仅译文"), "translated")
        self.translation_mode.setFixedWidth(88)
        self.translation_mode.setAccessibleName(self.tr("译文显示方式"))
        self.translation_mode.setToolTip(self.tr("切换原文、双语或仅译文"))
        self.translation_mode.setProperty("readerControl", True)
        self.translation_mode.hide()

        for control in (
            self.sidebar_restore_button,
            self.reader_button,
            self.web_button,
            self.split_button,
            self.translate_button,
            self.font_size,
            self.theme_combo,
            self.width_combo,
            self.focus_button,
        ):
            enable_immediate_tooltip(control)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)
        layout.addWidget(self.sidebar_restore_button)
        layout.addWidget(self.reader_button)
        layout.addWidget(self.web_button)
        layout.addWidget(self.split_button)
        layout.addWidget(self.translate_button)
        layout.addWidget(self.translation_mode)
        layout.addStretch()
        layout.addWidget(self.font_size)
        layout.addWidget(self.theme_combo)
        layout.addWidget(self.width_combo)
        layout.addWidget(self.focus_button)

        self.font_size.currentIndexChanged.connect(self._font_size_changed)
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        self.width_combo.currentIndexChanged.connect(self._width_changed)
        self.translate_button.clicked.connect(self._translation_clicked)
        self.sidebar_restore_button.clicked.connect(self.sidebar_restore_requested)
        self.focus_button.toggled.connect(self._focus_toggled)
        self.translation_mode.currentIndexChanged.connect(
            lambda _index: self.translation_mode_changed.emit(
                str(self.translation_mode.currentData())
            )
        )

    def _mode_button(self, icon: QIcon, label: str, mode: str) -> QPushButton:
        button = QPushButton()
        button.setIcon(icon)
        button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        button.setCheckable(True)
        button.setAccessibleName(self.tr("阅读模式：{0}").format(label))
        button.setToolTip(self.tr("切换到 {0} 模式").format(label))
        button.clicked.connect(lambda checked: checked and self.mode_changed.emit(mode))
        return button

    def _theme_changed(self, _index: int) -> None:
        labels = {
            "system": self.tr("跟随系统"),
            "light": self.tr("浅色"),
            "dark": self.tr("深色"),
        }
        value = str(self.theme_combo.currentData())
        self.theme_combo.setToolTip(self.tr("应用主题：{0}").format(labels[value]))
        self.theme_preference_changed.emit(value)

    def _font_size_changed(self, _index: int) -> None:
        value = int(self.font_size.currentData())
        self.font_size.setToolTip(self.tr("正文字号：{0}").format(value))
        self.font_size_changed.emit(value)

    def _width_changed(self, _index: int) -> None:
        labels = {640: self.tr("窄"), 760: self.tr("中"), 920: self.tr("宽")}
        value = int(self.width_combo.currentData())
        self.width_combo.setToolTip(self.tr("正文宽度：{0}").format(labels[value]))
        self.content_width_changed.emit(value)

    def set_theme_preference(self, value: str) -> None:
        index = self.theme_combo.findData(value)
        if index < 0:
            index = 0
        blocked = self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(index)
        self.theme_combo.blockSignals(blocked)
        labels = {
            "system": self.tr("跟随系统"),
            "light": self.tr("浅色"),
            "dark": self.tr("深色"),
        }
        self.theme_combo.setToolTip(
            self.tr("应用主题：{0}").format(labels.get(value, labels["system"]))
        )

    def set_article_available(self, available: bool) -> None:
        if self._translation_status not in {"queued", "running"}:
            self.translate_button.setEnabled(available)

    def set_translation_state(self, status: str, progress: float = 0.0) -> None:
        self._translation_status = status
        if status == "queued":
            self.translate_button.setText("")
            self.translate_button.setToolTip(self.tr("翻译任务排队中"))
            self.translate_button.setFixedWidth(COMPACT_CONTROL_SIZE)
            self.translate_button.setEnabled(False)
        elif status == "running":
            percent = max(0, min(100, round(progress * 100)))
            self.translate_button.setText("")
            self.translate_button.setToolTip(self.tr("翻译中 {0}%，点击取消").format(percent))
            self.translate_button.setFixedWidth(COMPACT_CONTROL_SIZE)
            self.translate_button.setEnabled(True)
        elif status == "error":
            self.translate_button.setText("")
            self.translate_button.setToolTip(self.tr("翻译失败，点击重试"))
            self.translate_button.setFixedWidth(COMPACT_CONTROL_SIZE)
            self.translate_button.setEnabled(True)
        elif status == "cancelled":
            self.translate_button.setText("")
            self.translate_button.setToolTip(self.tr("翻译已取消，点击继续"))
            self.translate_button.setFixedWidth(COMPACT_CONTROL_SIZE)
            self.translate_button.setEnabled(True)
        else:
            self.translate_button.setText("")
            self.translate_button.setToolTip(
                self.tr("重新翻译当前文章")
                if status == "done"
                else self.tr("使用 AI 翻译当前文章；运行时再次点击可取消")
            )
            self.translate_button.setFixedWidth(COMPACT_CONTROL_SIZE)
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
        self.focus_button.setIcon(restore_icon() if enabled else expand_icon("#4E5E57"))
        self.focus_button.setToolTip(
            self.tr("退出专注阅读")
            if enabled
            else self.tr("隐藏订阅源和文章列表，让 Reader 占满窗口")
        )
        self.focus_mode_changed.emit(enabled)

    def show_sidebar_restore(self, visible: bool) -> None:
        self.sidebar_restore_button.setVisible(visible)
