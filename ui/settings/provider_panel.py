"""LLM provider configuration panel.

The panel only collects input and exposes connection-test intent.  Network
work belongs to an injected controller/runtime.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProviderPanel(QWidget):
    """Edit one OpenAI-compatible provider and report test states."""

    test_requested = Signal(dict)
    configuration_saved = Signal()

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings

        self.name_edit = QLineEdit(str(settings.value("llm/name", "本地模型")))
        self.base_url_edit = QLineEdit(str(settings.value("llm/base_url", "")))
        self.base_url_edit.setPlaceholderText("http://localhost:11434/v1")
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        model = str(settings.value("llm/model", ""))
        if model:
            self.model_combo.addItem(model)
        self.api_key_edit = QLineEdit(str(settings.value("llm/api_key", "")))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText(self.tr("本地模型可留空"))

        self.status_label = QLabel(self.tr("尚未测试连接"))
        self.status_label.setObjectName("MutedLabel")
        self.status_label.setWordWrap(True)
        self.test_button = QPushButton(self.tr("测试连接"))
        self.test_button.setAccessibleName(self.tr("测试 LLM 提供者连接"))
        self.save_button = QPushButton(self.tr("保存配置"))
        self.save_button.setProperty("buttonRole", "primary")

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow(self.tr("名称"), self.name_edit)
        form.addRow(self.tr("服务地址"), self.base_url_edit)
        form.addRow(self.tr("模型"), self.model_combo)
        form.addRow(self.tr("API Key"), self.api_key_edit)

        actions = QHBoxLayout()
        actions.addWidget(self.status_label, 1)
        actions.addWidget(self.test_button)
        actions.addWidget(self.save_button)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addStretch()

        self.test_button.clicked.connect(self._request_test)
        self.save_button.clicked.connect(self.save)

    def configuration(self) -> dict[str, str]:
        return {
            "name": self.name_edit.text().strip(),
            "base_url": self.base_url_edit.text().strip(),
            "model": self.model_combo.currentText().strip(),
            "api_key": self.api_key_edit.text(),
        }

    def save(self) -> None:
        config = self.configuration()
        self._settings.setValue("llm/name", config["name"])
        self._settings.setValue("llm/base_url", config["base_url"])
        self._settings.setValue("llm/model", config["model"])
        self._settings.setValue("llm/api_key", config["api_key"])
        self._settings.sync()
        self.status_label.setObjectName("SuccessLabel")
        self.status_label.setText(self.tr("配置已保存"))
        self.configuration_saved.emit()

    def _request_test(self) -> None:
        config = self.configuration()
        if not config["base_url"]:
            self.show_test_result(False, [], self.tr("请先填写服务地址。"))
            return
        self.set_testing(True)
        self.test_requested.emit(config)

    def set_testing(self, testing: bool) -> None:
        self.test_button.setEnabled(not testing)
        self.save_button.setEnabled(not testing)
        if testing:
            self.status_label.setObjectName("MutedLabel")
            self.status_label.setText(self.tr("正在测试连接…"))

    def show_test_result(self, success: bool, models: list[str], error: str = "") -> None:
        self.set_testing(False)
        if success:
            current = self.model_combo.currentText()
            self.model_combo.clear()
            self.model_combo.addItems(models)
            if current and current not in models:
                self.model_combo.addItem(current)
            if current:
                self.model_combo.setCurrentText(current)
            self.status_label.setObjectName("SuccessLabel")
            self.status_label.setText(self.tr("连接成功，发现 {0} 个模型").format(len(models)))
        else:
            self.status_label.setObjectName("ErrorLabel")
            self.status_label.setText(self.tr("连接失败：{0}").format(error or self.tr("未知错误")))
        self.style().unpolish(self.status_label)
        self.style().polish(self.status_label)
