from __future__ import annotations

import asyncio

from PySide6.QtCore import QSettings

from core.feed.sync import SyncSignals
from store.entry_store import EntryListItem, EntryRow
from store.feed_store import FeedRow
from ui.main_window import MainWindow


class FakeFeedStore:
    def __init__(self) -> None:
        self.feeds = [FeedRow(1, "https://example.com/rss", "Example", "", None, "now", "now")]
        self.updated: list[tuple[int, str]] = []
        self.deleted: list[int] = []

    async def list_all(self):
        return self.feeds

    async def unread_count(self, _feed_id: int) -> int:
        return 4

    async def add(self, url: str, title: str = "", description: str = ""):
        row = FeedRow(2, url, title, description, None, "now", "now")
        self.feeds.append(row)
        return row

    async def update(self, feed_id: int, title: str | None = None, favicon_url=None) -> None:
        self.updated.append((feed_id, title or ""))
        self.feeds = [
            FeedRow(
                row.id,
                row.url,
                title if row.id == feed_id and title is not None else row.title,
                row.description,
                row.favicon_url,
                row.created_at,
                row.updated_at,
            )
            for row in self.feeds
        ]

    async def delete(self, feed_id: int) -> None:
        self.deleted.append(feed_id)
        self.feeds = [row for row in self.feeds if row.id != feed_id]


class FakeEntryStore:
    def __init__(self) -> None:
        self.delay_by_feed: dict[int, float] = {}
        self.marked_read: list[int] = []
        self.marked_unread: list[int] = []
        self.starred: list[int] = []
        self.deleted: list[int] = []
        self.search_calls: list[tuple[str, int | None]] = []

    async def list_by_feed(self, feed_id: int, limit: int = 50, offset: int = 0):
        await asyncio.sleep(self.delay_by_feed.get(feed_id, 0))
        return [
            EntryListItem(feed_id * 10, feed_id, f"Entry {feed_id}", "S", "A", "now", False, False)
        ]

    async def get(self, entry_id: int):
        return EntryRow(
            entry_id,
            1,
            "g",
            None,
            "Entry",
            "Summary",
            "A",
            "now",
            False,
            False,
            False,
            "now",
        )

    async def mark_read(self, entry_id: int) -> None:
        self.marked_read.append(entry_id)

    async def mark_unread(self, entry_id: int) -> None:
        self.marked_unread.append(entry_id)

    async def toggle_star(self, entry_id: int) -> bool:
        self.starred.append(entry_id)
        return True

    async def soft_delete(self, entry_id: int) -> None:
        self.deleted.append(entry_id)

    async def search(self, query: str, feed_id: int | None = None, limit: int = 50):
        self.search_calls.append((query, feed_id))
        return []


class FakeSyncService:
    def __init__(self) -> None:
        self.signals = SyncSignals()
        self.called: list[int] = []
        self.sync_all_calls = 0

    async def sync_feed(self, feed_id: int) -> int:
        self.called.append(feed_id)
        self.signals.sync_started.emit(feed_id)
        self.signals.sync_finished.emit(feed_id, 1)
        return 1

    async def sync_all(self, concurrency: int = 5) -> tuple[int, int]:
        self.sync_all_calls += 1
        self.signals.sync_all_done.emit(2, 0)
        return 2, 0


def _window(tmp_path, qtbot) -> MainWindow:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(FakeFeedStore(), FakeEntryStore(), FakeSyncService(), settings)
    qtbot.addWidget(window)
    return window


def test_main_window_has_three_columns_and_comfortable_minimum(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    assert window.splitter.count() == 3
    assert window.minimumWidth() >= 1024
    assert window.minimumHeight() >= 640


def test_sidebar_icon_opens_settings_without_top_menu(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    assert window.menuBar().actions() == []
    window.sidebar.ai_button.click()
    assert window._settings_dialog is not None


def test_reader_can_hide_sidebar_and_enter_focus_mode(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    window.sidebar.collapse_button.click()
    assert window.sidebar.isHidden() is True
    assert window.entry_list.isHidden() is False
    assert window.reader_view.toolbar.sidebar_restore_button.isHidden() is False

    window.reader_view.toolbar.focus_button.click()
    assert window.sidebar.isHidden() is True
    assert window.entry_list.isHidden() is True

    window.reader_view.toolbar.focus_button.click()
    assert window.sidebar.isHidden() is True
    assert window.entry_list.isHidden() is False

    window.reader_view.toolbar.sidebar_restore_button.click()
    assert window.sidebar.isHidden() is False
    assert window.reader_view.toolbar.sidebar_restore_button.isHidden() is True


def test_load_feeds_populates_sidebar(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    asyncio.run(window.load_feeds())
    assert window.sidebar.feed_list.count() == 1
    assert "4" in window.sidebar.feed_list.item(0).text()


def test_older_feed_request_cannot_replace_newer_selection(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    window._entry_store.delay_by_feed = {1: 0.02, 2: 0}

    async def choose() -> None:
        old = asyncio.create_task(window.select_feed(1))
        await asyncio.sleep(0)
        await window.select_feed(2)
        await old

    asyncio.run(choose())
    assert "Entry 2" in window.entry_list.entry_list.item(0).text()


def test_splitter_sizes_are_saved(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    window.splitter.setSizes([230, 350, 700])
    window.save_ui_state()
    saved = window._settings.value("ui/main_window/splitter")
    assert saved is not None


def test_batch_article_actions_reuse_existing_store_operations(
    tmp_path, qtbot, monkeypatch
) -> None:
    window = _window(tmp_path, qtbot)
    store = window._entry_store

    asyncio.run(window.batch_mark_entries_read([1, 2], True))
    asyncio.run(window.batch_mark_entries_read([3], False))
    asyncio.run(window.batch_toggle_entries_star([1, 3]))
    monkeypatch.setattr(window, "confirm_batch_delete", lambda _count: True)
    asyncio.run(window.batch_delete_entries([2, 3]))

    assert store.marked_read == [1, 2]
    assert store.marked_unread == [3]
    assert store.starred == [1, 3]
    assert store.deleted == [2, 3]


def test_sync_all_reuses_injected_service(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    asyncio.run(window.sync_all_feeds())
    assert window._sync_service.sync_all_calls == 1


def test_feed_rename_and_delete_reuse_injected_store(tmp_path, qtbot, monkeypatch) -> None:
    window = _window(tmp_path, qtbot)
    asyncio.run(window.rename_feed(1, "Renamed"))
    monkeypatch.setattr(window, "confirm_feed_delete", lambda _title: True)
    asyncio.run(window.delete_feed(1))

    assert window._feed_store.updated == [(1, "Renamed")]
    assert window._feed_store.deleted == [1]


def test_global_search_passes_none_feed_scope(tmp_path, qtbot) -> None:
    window = _window(tmp_path, qtbot)
    window._search_scope = "all"
    asyncio.run(window.search_entries("python"))
    assert window._entry_store.search_calls[-1] == ("python", None)
