from __future__ import annotations

import asyncio
from dataclasses import dataclass

from PySide6.QtCore import QSettings

from core.feed.sync import SyncSignals
from store.entry_store import EntryListItem
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


def test_reader_displays_tags(qtbot) -> None:
    reader = ReaderView()
    qtbot.addWidget(reader)
    reader.set_tags(["Python", "RSS"])
    assert reader.tags_label.text() == "Python  ·  RSS"
    assert reader.tags_label.isHidden() is False


def test_manual_tags_replace_entry_tags(tmp_path, qtbot, monkeypatch) -> None:
    window = _window(tmp_path, qtbot)
    monkeypatch.setattr(window, "_prompt_tag_names", lambda _current: ["Python", "Qt"])
    asyncio.run(window.manage_entry_tags(5))
    assert window._tag_store.saved == [(5, [6, 2])]
    assert window.reader_view.tags_label.text() == "Python  ·  Qt"
