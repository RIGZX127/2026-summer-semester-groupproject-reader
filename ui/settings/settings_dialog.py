"""Application settings dialog for Phase 3."""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.settings.agent_panel import AgentPanel
from ui.settings.provider_panel import ProviderPanel


class SettingsDialog(QDialog):
    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("AI 工作台 · 设置"))
        self.setMinimumSize(620, 500)
        title = QLabel(self.tr("AI 工作台"))
        title.setObjectName("SectionTitle")
        description = QLabel(self.tr("连接模型，并配置摘要与翻译 Agent。"))
        description.setObjectName("MutedLabel")
        self.provider_panel = ProviderPanel(settings)
        self.agent_panel = AgentPanel(settings)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.provider_panel, self.tr("LLM 提供者"))
        self.tabs.addTab(self.agent_panel, self.tr("Agent"))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)
