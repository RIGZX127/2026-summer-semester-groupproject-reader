from __future__ import annotations

from PySide6.QtCore import QSettings

from core.agent.runtime import AgentSignals, AgentUIEvent
from ui.reader.reader_view import ReaderView
from ui.reader.summary_panel import SummaryPanel


class FakeRuntime:
    def __init__(self) -> None:
        self.signals = AgentSignals()
        self.submissions: list[tuple[int, str, str]] = []
        self.cancelled: list[str] = []

    def submit(self, entry_id: int, agent_type: str) -> str:
        run_id = f"{agent_type}-{len(self.submissions) + 1}"
        self.submissions.append((entry_id, agent_type, run_id))
        return run_id

    def cancel(self, run_id: str) -> None:
        self.cancelled.append(run_id)


def test_summary_panel_tracks_run_and_ignores_stale_events(qtbot) -> None:
    runtime = FakeRuntime()
    panel = SummaryPanel(runtime)
    qtbot.addWidget(panel)
    panel.set_entry(42)

    panel._request_generate()
    assert panel.active_run_id == "summary-1"

    runtime.signals.chunk_received.emit(
        AgentUIEvent("stale", 42, "summary", "running", chunk="wrong")
    )
    assert "wrong" not in panel._content.toPlainText()

    runtime.signals.chunk_received.emit(
        AgentUIEvent("summary-1", 42, "summary", "running", chunk="correct")
    )
    assert "correct" in panel._content.toPlainText()


def test_summary_panel_cancel_preserves_generated_text(qtbot) -> None:
    runtime = FakeRuntime()
    panel = SummaryPanel(runtime)
    qtbot.addWidget(panel)
    panel.set_entry(7)
    panel._request_generate()
    runtime.signals.chunk_received.emit(
        AgentUIEvent("summary-1", 7, "summary", "running", chunk="partial")
    )

    panel._cancel_or_generate()
    runtime.signals.state_changed.emit(AgentUIEvent("summary-1", 7, "summary", "cancelled"))

    assert runtime.cancelled == ["summary-1"]
    assert "partial" in panel._content.toPlainText()
    assert panel.status == "cancelled"


def test_reader_auto_summary_is_debounced(tmp_path, qtbot) -> None:
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    settings.setValue("agent/auto_summary", True)
    runtime = FakeRuntime()
    view = ReaderView(settings=settings, agent_runtime=runtime)
    qtbot.addWidget(view)

    view.show_content("<p>one</p>", None, entry_id=1)
    view.show_content("<p>two</p>", None, entry_id=2)
    qtbot.wait(1100)

    assert [(entry_id, kind) for entry_id, kind, _ in runtime.submissions] == [(2, "summary")]


def test_translation_progress_and_display_modes(tmp_path, qtbot) -> None:
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    runtime = FakeRuntime()
    view = ReaderView(settings=settings, agent_runtime=runtime)
    qtbot.addWidget(view)
    view.show_content("<p>Original</p>", None, entry_id=9)

    view._request_translation()
    assert view.active_translation_run_id == "translation-1"

    runtime.signals.state_changed.emit(
        AgentUIEvent("translation-1", 9, "translation", "running", progress=0.5)
    )
    assert "50%" in view.toolbar.translate_button.text()

    result = (
        '{"html":"<div class=\\"mercury-trans-block\\">'
        '<div class=\\"mercury-original\\"><p>Original</p></div>'
        '<div class=\\"mercury-translated\\"><p>译文</p></div></div>"}'
    )
    runtime.signals.state_changed.emit(
        AgentUIEvent("translation-1", 9, "translation", "done", result_json=result)
    )
    assert view.toolbar.translation_mode.isHidden() is False

    view.set_translation_mode("translated")
    assert "译文" in view.last_html
    assert "mercury-original" not in view.last_html

    view.set_translation_mode("original")
    assert "Original" in view.last_html
