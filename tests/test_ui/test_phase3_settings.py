from __future__ import annotations

from PySide6.QtCore import QSettings

from ui.settings.agent_panel import AgentPanel
from ui.settings.provider_panel import ProviderPanel


def _settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "phase3.ini"), QSettings.Format.IniFormat)


def test_provider_panel_persists_configuration(tmp_path, qtbot) -> None:
    settings = _settings(tmp_path)
    panel = ProviderPanel(settings)
    qtbot.addWidget(panel)

    panel.name_edit.setText("Ollama Local")
    panel.base_url_edit.setText("http://localhost:11434/v1")
    panel.model_combo.addItem("qwen3")
    panel.model_combo.setCurrentText("qwen3")
    panel.api_key_edit.setText("local-key")
    panel.save()

    assert settings.value("llm/base_url") == "http://localhost:11434/v1"
    assert settings.value("llm/model") == "qwen3"
    assert panel.status_label.text() == "配置已保存"


def test_provider_panel_exposes_non_blocking_test_states(tmp_path, qtbot) -> None:
    panel = ProviderPanel(_settings(tmp_path))
    qtbot.addWidget(panel)

    panel.set_testing(True)
    assert panel.test_button.isEnabled() is False
    assert panel.status_label.text() == "正在测试连接…"

    panel.show_test_result(True, ["qwen3", "llama3"])
    assert panel.test_button.isEnabled() is True
    assert panel.model_combo.count() == 2
    assert "连接成功" in panel.status_label.text()


def test_agent_panel_persists_phase3_preferences(tmp_path, qtbot) -> None:
    settings = _settings(tmp_path)
    panel = AgentPanel(settings)
    qtbot.addWidget(panel)

    panel.auto_summary.setChecked(True)
    panel.summary_language.setCurrentText("简体中文")
    panel.summary_detail.setCurrentIndex(panel.summary_detail.findData("detailed"))
    panel.translation_language.setCurrentText("English")
    panel.translation_degree.setValue(5)
    panel.save()

    assert settings.value("agent/auto_summary", type=bool) is True
    assert settings.value("agent/summary_detail") == "detailed"
    assert settings.value("agent/translation_degree", type=int) == 5
