"""Phase 3 Agent preference panel."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class AgentPanel(QWidget):
    settings_saved = Signal()

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings

        self.auto_summary = QCheckBox(self.tr("文章加载后自动生成摘要（1 秒防抖）"))
        self.auto_summary.setChecked(settings.value("agent/auto_summary", False, type=bool))
        self.summary_language = QComboBox()
        self.summary_language.addItems(["简体中文", "English", "日本語"])
        self.summary_language.setCurrentText(
            str(settings.value("agent/summary_language", "简体中文"))
        )
        self.summary_detail = QComboBox()
        self.summary_detail.addItem(self.tr("简短（1–2 句）"), "brief")
        self.summary_detail.addItem(self.tr("标准（3–5 句）"), "standard")
        self.summary_detail.addItem(self.tr("详细要点"), "detailed")
        self.summary_detail.setCurrentIndex(
            max(0, self.summary_detail.findData(settings.value("agent/summary_detail", "standard")))
        )

        summary_box = QGroupBox(self.tr("摘要 Agent"))
        summary_form = QFormLayout(summary_box)
        summary_form.addRow(self.auto_summary)
        summary_form.addRow(self.tr("输出语言"), self.summary_language)
        summary_form.addRow(self.tr("详细程度"), self.summary_detail)

        self.translation_language = QComboBox()
        self.translation_language.addItems(["简体中文", "English", "日本語"])
        self.translation_language.setCurrentText(
            str(settings.value("agent/translation_language", "简体中文"))
        )
        self.translation_degree = QSpinBox()
        self.translation_degree.setRange(1, 5)
        self.translation_degree.setValue(settings.value("agent/translation_degree", 3, type=int))
        self.translation_degree.setAccessibleName(self.tr("翻译并发段落数"))

        translation_box = QGroupBox(self.tr("翻译 Agent"))
        translation_form = QFormLayout(translation_box)
        translation_form.addRow(self.tr("目标语言"), self.translation_language)
        translation_form.addRow(self.tr("并发段落数"), self.translation_degree)

        hint = QLabel(self.tr("提示词模板继续使用 resources/prompts 中的版本化模板。"))
        hint.setObjectName("MutedLabel")
        hint.setWordWrap(True)
        self.save_button = QPushButton(self.tr("保存 Agent 设置"))
        self.save_button.setProperty("buttonRole", "primary")
        self.status_label = QLabel("")
        actions = QHBoxLayout()
        actions.addWidget(self.status_label, 1)
        actions.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.addWidget(summary_box)
        layout.addWidget(translation_box)
        layout.addWidget(hint)
        layout.addStretch()
        layout.addLayout(actions)
        self.save_button.clicked.connect(self.save)

    def save(self) -> None:
        self._settings.setValue("agent/auto_summary", self.auto_summary.isChecked())
        self._settings.setValue("agent/summary_language", self.summary_language.currentText())
        self._settings.setValue("agent/summary_detail", self.summary_detail.currentData())
        self._settings.setValue(
            "agent/translation_language", self.translation_language.currentText()
        )
        self._settings.setValue("agent/translation_degree", self.translation_degree.value())
        self._settings.sync()
        self.status_label.setObjectName("SuccessLabel")
        self.status_label.setText(self.tr("Agent 设置已保存"))
        self.settings_saved.emit()
