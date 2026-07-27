"""Application settings dialog for Phase 3."""

from __future__ import annotations

from typing import Literal

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
from ui.settings.general_panel import GeneralPanel
from ui.settings.provider_panel import ProviderPanel


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: QSettings,
        parent: QWidget | None = None,
        usage_store: object | None = None,
        mode: Literal["general", "ai"] = "general",
    ) -> None:
        super().__init__(parent)
        is_ai = mode == "ai"
        self.setWindowTitle(self.tr("AI 设置") if is_ai else self.tr("ChenXing 设置"))
        self.setMinimumSize(620, 420 if is_ai else 300)
        self.resize(680, 460 if is_ai else 340)
        title = QLabel(self.tr("AI 设置") if is_ai else self.tr("通用设置"))
        title.setObjectName("SectionTitle")
        description = QLabel(
            self.tr("配置 AI 服务、摘要、翻译与用量统计。")
            if is_ai
            else self.tr("设置 ChenXing 的界面语言与通用偏好。")
        )
        description.setObjectName("MutedLabel")
        self.general_panel: GeneralPanel | None = None
        self.provider_panel: ProviderPanel | None = None
        self.agent_panel: AgentPanel | None = None
        self.tabs = QTabWidget()
        if is_ai:
            self.provider_panel = ProviderPanel(settings)
            self.agent_panel = AgentPanel(settings)
            self.tabs.addTab(self.provider_panel, self.tr("LLM 提供者"))
            self.tabs.addTab(self.agent_panel, self.tr("Agent"))
        else:
            self.general_panel = GeneralPanel(settings)
            self.tabs.addTab(self.general_panel, self.tr("通用"))

        # ── Usage panel (optional) ──────────────────────────────────
        self.usage_panel = None
        if is_ai and usage_store is not None:
            from ui.settings.usage_panel import UsagePanel

            self.usage_panel = UsagePanel(self)
            self.tabs.addTab(self.usage_panel, self.tr("用量统计"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)
