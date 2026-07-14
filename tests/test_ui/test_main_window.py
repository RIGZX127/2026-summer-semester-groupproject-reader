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

    async def list_all(self):
        return self.feeds

    async def unread_count(self, _feed_id: int) -> int:
        return 4

    async def add(self, url: str, title: str = "", description: str = ""):
        row = FeedRow(2, url, title, description, None, "now", "now")
        self.feeds.append(row)
        return row


class FakeEntryStore:
    def __init__(self) -> None:
        self.delay_by_feed: dict[int, float] = {}

    async def list_by_feed(self, feed_id: int, limit: int = 50, offset: int = 0):
        await asyncio.sleep(self.delay_by_feed.get(feed_id, 0))
        return [
            EntryListItem(
                feed_id * 10, feed_id, f"Entry {feed_id}", "S", "A", "now", False, False
            )
        ]

    async def get(self, entry_id: int):
        return EntryRow(
            entry_id, 1, "g", None, "Entry", "Summary", "A", "now",
            False, False, False, "now",
        )


class FakeSyncService:
    def __init__(self) -> None:
        self.signals = SyncSignals()
        self.called: list[int] = []

    async def sync_feed(self, feed_id: int) -> int:
        self.called.append(feed_id)
        self.signals.sync_started.emit(feed_id)
        self.signals.sync_finished.emit(feed_id, 1)
        return 1


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
