"""Reader mode and display controls."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QWidget,
)

from ui.reader.theme import Theme


class ReaderToolbar(QWidget):
    mode_changed = Signal(str)
    font_size_changed = Signal(int)
    theme_preference_changed = Signal(str)
    content_width_changed = Signal(int)

    def __init__(self, theme: Theme | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReaderToolbar")
        current = theme or Theme()
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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(self.reader_button)
        layout.addWidget(self.web_button)
        layout.addWidget(self.split_button)
        layout.addStretch()
        layout.addWidget(QLabel(self.tr("字号")))
        layout.addWidget(self.font_size)
        layout.addWidget(self.theme_combo)
        layout.addWidget(self.width_combo)

        self.font_size.valueChanged.connect(self.font_size_changed)
        self.theme_combo.currentIndexChanged.connect(
            lambda _index: self.theme_preference_changed.emit(str(self.theme_combo.currentData()))
        )
        self.width_combo.currentIndexChanged.connect(
            lambda _index: self.content_width_changed.emit(int(self.width_combo.currentData()))
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
