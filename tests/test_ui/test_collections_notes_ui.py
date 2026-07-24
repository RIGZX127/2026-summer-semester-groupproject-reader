from __future__ import annotations

import asyncio
from dataclasses import dataclass

from PySide6.QtCore import QSettings

from core.feed.sync import SyncSignals
from store.entry_store import EntryListItem, EntryRow
from store.feed_store import FeedRow
from ui.collections_widget import CollectionsWidget
from ui.entry_list import EntryListWidget
from ui.main_window import MainWindow
from ui.reader.note_editor import NoteEditor


@dataclass
class FakeCollection:
    id: int
    name: str
    description: str = ""
    sort_order: int = 0
    is_default: bool = False
    created_at: str = "now"
    updated_at: str = "now"


@dataclass
class FakeNote:
    entry_id: int
    body: str


class FakeFeedStore:
    async def list_all(self):
        return [FeedRow(1, "https://example.com/rss", "Example", "", None, "now", "now")]

    async def unread_count(self, _feed_id: int) -> int:
        return 0


class FakeEntryStore:
    def __init__(self) -> None:
        self.starred: list[int] = []

    async def list_by_feed(self, _feed_id: int, limit: int = 50, offset: int = 0):
        return []

    async def get(self, entry_id: int):
        return EntryRow(
            entry_id, 1, f"g-{entry_id}", None, f"Entry {entry_id}", "Summary",
            "Author", "now", True, False, False, "now",
        )

    async def toggle_star(self, entry_id: int) -> bool:
        self.starred.append(entry_id)
        return True


class FakeCollectionStore:
    def __init__(self) -> None:
        self.rows = [FakeCollection(7, "课程资料")]
        self.entry_queries: list[int] = []
        self.added: list[tuple[int, int]] = []
        self.quick_starred: list[int] = []

    async def list_all(self):
        return self.rows

    async def get_entries(self, collection_id: int, search: str = "", limit: int = 50):
        self.entry_queries.append(collection_id)
        return [5]

    async def add_entry(self, collection_id: int, entry_id: int) -> None:
        self.added.append((collection_id, entry_id))

    async def quick_star(self, entry_id: int):
        self.quick_starred.append(entry_id)
        return self.rows[0]


class FakeNoteStore:
    def __init__(self) -> None:
        self.saved: list[tuple[int, str]] = []

    async def get(self, entry_id: int):
        return FakeNote(entry_id, "已有笔记")

    async def save(self, entry_id: int, body: str):
        self.saved.append((entry_id, body))
        return FakeNote(entry_id, body)


class FakeSyncService:
    def __init__(self) -> None:
        self.signals = SyncSignals()


def _entry(entry_id: int = 1) -> EntryListItem:
    return EntryListItem(entry_id, 1, "Article", "Summary", "Author", "now", False, False)


def _window(tmp_path, qtbot) -> MainWindow:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(
        FakeFeedStore(),
        FakeEntryStore(),
        FakeSyncService(),
        settings,
        note_store=FakeNoteStore(),
        collection_store=FakeCollectionStore(),
    )
    qtbot.addWidget(window)
    return window


def test_collections_widget_lists_rows_and_emits_selection(qtbot) -> None:
    widget = CollectionsWidget()
    qtbot.addWidget(widget)
    widget.set_collections([FakeCollection(3, "课程资料")])
    with qtbot.waitSignal(widget.collection_selected, timeout=500) as signal:
        widget.collection_list.setCurrentRow(0)
    assert signal.args == [3]


def test_entry_list_emits_add_to_collection(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)
    view.set_entries([_entry()])
    with qtbot.waitSignal(view.add_to_collection_requested, timeout=500) as signal:
        view._emit_add_to_collection_for_item(view.entry_list.item(0))
    assert signal.args == [1]


def test_main_window_loads_collection_entries(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    asyncio.run(window.load_collections())
    asyncio.run(window.select_collection(7))
    assert window.sidebar.collections.collection_list.count() == 1
    assert window._collection_store.entry_queries == [7]
    assert "Entry 5" in window.entry_list.entry_list.item(0).text()


def test_main_window_adds_article_to_collection(tmp_path, qtbot, monkeypatch) -> None:
    window = _window(tmp_path, qtbot)
    monkeypatch.setattr(window, "_choose_collection", lambda _rows: 7)
    asyncio.run(window.add_entry_to_collection(5))
    assert window._collection_store.added == [(7, 5)]


def test_star_also_updates_default_collection(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    asyncio.run(window.toggle_entry_star(5))
    assert window._collection_store.quick_starred == [5]


def test_note_editor_emits_save_after_timeout(qtbot) -> None:
    editor = NoteEditor()
    qtbot.addWidget(editor)
    editor.autosave_timer.setInterval(20)
    editor.set_entry(9, "")
    with qtbot.waitSignal(editor.save_requested, timeout=500) as signal:
        editor.text_edit.setPlainText("重点")
    assert signal.args == [9, "重点"]


def test_select_entry_loads_note_and_save_updates_store(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    asyncio.run(window.select_entry(5))
    assert window.reader_view.note_editor.text_edit.toPlainText() == "已有笔记"
    asyncio.run(window.save_note(5, "更新"))
    assert window._note_store.saved == [(5, "更新")]
