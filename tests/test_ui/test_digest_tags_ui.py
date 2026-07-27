from __future__ import annotations

import asyncio
from dataclasses import dataclass

from PySide6.QtCore import QSettings

from core.digest.exporter import DigestExporter, EntryDigest
from core.feed.sync import SyncSignals
from store.entry_store import EntryListItem
from ui.dialogs.tag_manager_dialog import TagManagerDialog
from ui.entry_list import EntryListWidget
from ui.main_window import MainWindow
from ui.reader.reader_view import ReaderView


class FakeFeedStore:
    async def list_all(self):
        return []


class FakeEntryStore:
    async def get(self, _entry_id: int):
        return None


class FakeSyncService:
    def __init__(self) -> None:
        self.signals = SyncSignals()


@dataclass
class FakeEntryTag:
    entry_id: int
    tag_id: int
    tag_name: str


@dataclass
class FakeTag:
    id: int
    name: str


class FakeTagStore:
    def __init__(self) -> None:
        self.tags = [FakeEntryTag(5, 1, "Python")]
        self.saved: list[tuple[int, list[int]]] = []

    async def get_entry_tags(self, _entry_id: int):
        return self.tags

    async def create(self, name: str):
        return FakeTag(len(name), name)

    async def set_entry_tags(self, entry_id: int, tag_ids: list[int]) -> None:
        self.saved.append((entry_id, tag_ids))


class FakeDigestController:
    def __init__(self) -> None:
        self.single: list[tuple[int, str]] = []
        self.multi: list[tuple[list[int], str]] = []
        self.multi_previews: list[tuple[list[int], str]] = []

    def list_templates(self) -> list[str]:
        return ["multi.md.j2"]

    async def preview_multi(self, entry_ids: list[int], template: str) -> str:
        self.multi_previews.append((entry_ids, template))
        return "# Digest\n\n- Article 5\n- Article 6"

    async def export_single(self, entry_id: int, path: str):
        self.single.append((entry_id, path))
        return type("Result", (), {"ok": True, "path": f"{path}/one.md", "error": ""})()

    async def export_multi(self, entry_ids: list[int], path: str):
        self.multi.append((entry_ids, path))
        return type("Result", (), {"ok": True, "path": f"{path}/digest.md", "error": ""})()


def _entry() -> EntryListItem:
    return EntryListItem(5, 1, "Article", "", "", "now", False, False)


def _window(tmp_path, qtbot) -> MainWindow:
    window = MainWindow(
        FakeFeedStore(),
        FakeEntryStore(),
        FakeSyncService(),
        QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
        tag_store=FakeTagStore(),
        digest_controller=FakeDigestController(),
    )
    qtbot.addWidget(window)
    return window


def test_entry_list_emits_single_and_batch_export(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)
    view.set_entries([_entry()])
    item = view.entry_list.item(0)
    with qtbot.waitSignal(view.export_markdown_requested, timeout=500) as signal:
        view._emit_export_markdown_for_item(item)
    assert signal.args == [5]

    view.set_batch_mode(True)
    item.setSelected(True)
    with qtbot.waitSignal(view.batch_export_digest_requested, timeout=500) as signal:
        view._emit_batch_export()
    assert signal.args == [[5]]


def test_export_calls_injected_digest_controller(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    asyncio.run(window.export_entry_markdown(5, "/tmp/export"))
    asyncio.run(window.export_entries_digest([5, 6], "/tmp/export"))
    assert window._digest_controller.single == [(5, "/tmp/export")]
    assert window._digest_controller.multi == [([5, 6], "/tmp/export")]


def test_batch_export_dialog_receives_preview_for_selected_entries(
    tmp_path, qtbot, monkeypatch
) -> None:
    from PySide6.QtWidgets import QDialog

    from ui.dialogs import export_dialog

    captured: dict[str, str] = {}

    class FakeExportDialog:
        def __init__(self, _templates, preview_text, parent=None):
            captured["preview"] = preview_text

        def exec(self):
            return QDialog.DialogCode.Rejected

    window = _window(tmp_path, qtbot)
    monkeypatch.setattr(export_dialog, "ExportDialog", FakeExportDialog)

    asyncio.run(window._show_export_dialog(entry_ids=[5, 6]))

    assert captured["preview"] == "# Digest\n\n- Article 5\n- Article 6"
    assert window._digest_controller.multi_previews == [([5, 6], "multi.md.j2")]


def test_multi_preview_renders_every_selected_article() -> None:
    preview = DigestExporter.preview_multi(
        [
            EntryDigest(5, "First article", published_at="2026-07-25"),
            EntryDigest(6, "Second article", published_at="2026-07-26"),
        ]
    )

    assert "共 2 篇文章" in preview
    assert "First article" in preview
    assert "Second article" in preview


def test_multi_preview_handles_article_with_missing_metadata() -> None:
    preview = DigestExporter.preview_multi(
        [
            EntryDigest(
                7,
                None,  # type: ignore[arg-type]
                url="",
                author="",
                published_at="",
                feed_title="",
                summary="",
            )
        ]
    )

    assert "## 1. 无标题" in preview
    assert "None" not in preview
    assert "[]()" not in preview
    assert "- **作者**：" not in preview
    assert "- **来源**：" not in preview


def test_multi_preview_keeps_markdown_layout_without_truncating() -> None:
    entries = [
        EntryDigest(
            index,
            f"Article {index}",
            summary='<p>Summary with <a href="https://example.com">a link</a>.</p>',
        )
        for index in range(1, 31)
    ]

    preview = DigestExporter.preview_multi(entries)

    assert "## 1. Article 1" in preview
    assert "## 30. Article 30" in preview
    assert "\n\n## 2." in preview
    assert "…（截断）" not in preview
    assert "<p>" not in preview
    assert "[a link](https://example.com)" in preview


def test_reader_displays_tags(qtbot) -> None:
    reader = ReaderView()
    qtbot.addWidget(reader)
    reader.set_tags(["Python", "RSS"])
    assert reader.tag_bar.tags() == ["Python", "RSS"]
    assert reader.tag_bar.isHidden() is False


def test_manual_tags_replace_entry_tags(tmp_path, qtbot, monkeypatch) -> None:
    window = _window(tmp_path, qtbot)
    monkeypatch.setattr(
        window,
        "_prompt_tag_names",
        lambda _current, suggested=None, entry_id=None: ["Python", "Qt"],
    )
    asyncio.run(window.manage_entry_tags(5))
    assert window._tag_store.saved == [(5, [6, 2])]
    assert window.reader_view.tag_bar.tags() == ["Python", "Qt"]


def test_tag_manager_generates_ai_suggestions_in_place(qtbot) -> None:
    dialog = TagManagerDialog(["Python"])
    qtbot.addWidget(dialog)

    assert dialog.ai_button.accessibleName() == "AI 生成标签"
    with qtbot.waitSignal(dialog.ai_tags_requested, timeout=500):
        dialog.ai_button.click()
    assert dialog.ai_button.isEnabled() is False

    dialog.set_ai_state("done", ["Qt", "Python"])
    assert dialog.ai_button.isEnabled() is True
    assert "Qt" in dialog.suggested_tag_names()
    assert dialog.tag_names() == ["Python"]
