"""General application preferences."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class GeneralPanel(QWidget):
    """Persist application-wide presentation preferences."""

    settings_saved = Signal()

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings

        self.language_combo = QComboBox()
        self.language_combo.setAccessibleName(self.tr("界面语言"))
        self.language_combo.addItem(self.tr("跟随系统"), "system")
        self.language_combo.addItem(self.tr("简体中文"), "zh_CN")
        self.language_combo.addItem("English", "en")
        saved_language = str(settings.value("ui/language", "system"))
        index = self.language_combo.findData(saved_language or "system")
        self.language_combo.setCurrentIndex(max(0, index))

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addRow(self.tr("界面语言"), self.language_combo)

        self.mark_read_delay = QSpinBox()
        self.mark_read_delay.setRange(0, 300)
        self.mark_read_delay.setSuffix(self.tr(" 秒"))
        self.mark_read_delay.setAccessibleName(self.tr("标记已读等待时间"))
        self.mark_read_delay.setValue(int(settings.value("reading/mark_read_delay_seconds", 0)))
        self.mark_read_delay.setToolTip(
            self.tr("文章持续停留达到该时间后标记为已读；0 表示立即标记")
        )
        form.addRow(self.tr("标记已读等待时间"), self.mark_read_delay)

        hint = QLabel(self.tr("语言更改将在下次启动 ChenXing 时生效。"))
        hint.setObjectName("MutedLabel")
        hint.setWordWrap(True)

        self.status_label = QLabel()
        self.status_label.setObjectName("MutedLabel")
        self.save_button = QPushButton(self.tr("保存通用设置"))
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self.save)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addWidget(self.status_label, 1)
        actions.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addStretch()
        layout.addLayout(actions)

    def save(self) -> None:
        """Save the selected language for the next application start."""
        self._settings.setValue("ui/language", self.language_combo.currentData())
        self._settings.setValue("reading/mark_read_delay_seconds", self.mark_read_delay.value())
        self._settings.sync()
        self.status_label.setText(self.tr("语言设置已保存，重启应用后生效"))
        self.settings_saved.emit()
