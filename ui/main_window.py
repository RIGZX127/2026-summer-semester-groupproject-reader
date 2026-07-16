"""Mercury's Phase 1 three-column main window."""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import QMainWindow, QMessageBox, QSplitter
from qasync import asyncSlot

from app.state import state
from core.reader.pipeline import ReaderFetchError
from store.feed_store import DuplicateFeedError
from ui.dialogs.add_feed_dialog import AddFeedDialog
from ui.entry_list import EntryListWidget
from ui.reader.reader_view import ReaderView
from ui.sidebar import Sidebar

if TYPE_CHECKING:
    from core.feed.sync import SyncService
    from core.reader.pipeline import ReaderPipeline
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore


class MainWindow(QMainWindow):
    """Coordinate UI components through the locked Phase 1 interfaces."""

    def __init__(
        self,
        feed_store: FeedStore,
        entry_store: EntryStore,
        sync_service: SyncService,
        settings: QSettings | None = None,
        reader_pipeline: ReaderPipeline | None = None,
        agent_runtime: object | None = None,
    ) -> None:
        super().__init__()
        self._feed_store = feed_store
        self._entry_store = entry_store
        self._sync_service = sync_service
        self._reader_pipeline = reader_pipeline
        self._agent_runtime = agent_runtime
        self._settings = settings or QSettings()
        self._feed_request_id: str | None = None
        self._entry_request_id: str | None = None
        self._add_dialog: AddFeedDialog | None = None
        self._selected_entry_id: int | None = None
        self._search_query = ""

        self.setWindowTitle(self.tr("Mercury RSS Reader"))
        self.setMinimumSize(1024, 640)
        self.resize(1280, 800)
        self.sidebar = Sidebar()
        self.entry_list = EntryListWidget()
        self.reader_view = ReaderView(
            settings=self._settings, agent_runtime=self._agent_runtime
        )
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.entry_list)
        self.splitter.addWidget(self.reader_view)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStretchFactor(2, 1)
        self.setCentralWidget(self.splitter)
        self.statusBar().showMessage(self.tr("准备就绪"))

        self.sidebar.add_feed_requested.connect(self.open_add_feed_dialog)
        self.sidebar.feed_selected.connect(self._select_feed_slot)
        self.sidebar.sync_requested.connect(self._sync_feed_slot)
        self.entry_list.entry_selected.connect(self._select_entry_slot)
        self.entry_list.retry_requested.connect(self._retry_entries)
        self.entry_list.search_requested.connect(self._search_entries_slot)
        self.entry_list.mark_read_requested.connect(self._mark_read_slot)
        self.entry_list.star_requested.connect(self._toggle_star_slot)
        self.entry_list.delete_requested.connect(self._delete_entry_slot)
        self.reader_view.retry_requested.connect(self._retry_reader)
        self._sync_service.signals.sync_started.connect(self._on_sync_started)
        self._sync_service.signals.sync_finished.connect(self._on_sync_finished)
        self._sync_service.signals.sync_error.connect(self._on_sync_error)
        self._sync_service.signals.sync_all_done.connect(self._on_sync_all_done)

        self.restore_ui_state()
        QTimer.singleShot(0, self._schedule_initial_load)

    def _schedule_initial_load(self) -> None:
        try:
            asyncio.get_running_loop().create_task(self.load_feeds())
        except RuntimeError:
            pass

    async def load_feeds(self) -> None:
        try:
            feeds = await self._feed_store.list_all()
            counts = await asyncio.gather(
                *(self._feed_store.unread_count(feed.id) for feed in feeds)
            )
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(self.tr("订阅源加载失败：{0}").format(str(exc)))
            return
        state.feeds = feeds
        self.sidebar.set_feeds(list(zip(feeds, counts, strict=True)))
        if not feeds:
            self.entry_list.set_state("disabled", self.tr("请先添加一个订阅源。"))

    def open_add_feed_dialog(self) -> None:
        dialog = AddFeedDialog(self)
        self._add_dialog = dialog
        dialog.url_submitted.connect(self._add_feed_slot)
        dialog.finished.connect(lambda _result: self._clear_add_dialog(dialog))
        dialog.show()
        dialog.url_edit.setFocus()

    def _clear_add_dialog(self, dialog: AddFeedDialog) -> None:
        if self._add_dialog is dialog:
            self._add_dialog = None

    async def add_feed(self, url: str) -> None:
        dialog = self._add_dialog
        if dialog is not None:
            dialog.set_submitting(True)
        try:
            feed = await self._feed_store.add(url)
            await self.load_feeds()
            await self.sync_feed(feed.id)
        except DuplicateFeedError:
            if dialog is not None:
                dialog.show_error(self.tr("已订阅该源。"))
                dialog.set_submitting(False)
            return
        except Exception as exc:  # noqa: BLE001
            if dialog is not None:
                dialog.show_error(self.tr("添加失败：{0}").format(str(exc)))
                dialog.set_submitting(False)
            return
        if dialog is not None:
            dialog.accept()
        self.statusBar().showMessage(self.tr("订阅添加成功"), 4000)

    async def select_feed(self, feed_id: int) -> None:
        state.selected_feed_id = feed_id
        self._selected_entry_id = None
        self._search_query = ""
        self.entry_list.search_edit.clear()
        request_id = str(uuid.uuid4())
        self._feed_request_id = request_id
        self.entry_list.set_state("loading")
        try:
            entries = await self._entry_store.list_by_feed(feed_id)
        except Exception as exc:  # noqa: BLE001
            if self._feed_request_id == request_id:
                self.entry_list.set_state("error", self.tr("加载失败：{0}").format(str(exc)))
            return
        if self._feed_request_id != request_id or state.selected_feed_id != feed_id:
            return
        self.entry_list.set_entries(entries)
        self.reader_view.show_empty()

    async def select_entry(self, entry_id: int) -> None:
        request_id = str(uuid.uuid4())
        self._entry_request_id = request_id
        self.reader_view.show_loading()
        self._selected_entry_id = entry_id
        try:
            entry = await self._entry_store.get(entry_id)
        except Exception as exc:  # noqa: BLE001
            if self._entry_request_id == request_id:
                self.reader_view.show_error(self.tr("加载失败：{0}").format(str(exc)))
            return
        if self._entry_request_id != request_id:
            return
        if entry is None:
            self.reader_view.show_error(self.tr("文章不存在或已被删除。"))
            return
        try:
            if not entry.is_read:
                await self._entry_store.mark_read(entry_id)
                await self.refresh_entries()
                await self.load_feeds()
            if self._reader_pipeline is None:
                self.reader_view.show_entry(entry)
                return
            result = await self._reader_pipeline.build(entry_id, request_id=request_id)
        except ReaderFetchError as exc:
            if self._entry_request_id == request_id:
                if entry.url and (exc.status_code in (403, 429) or exc.status_code is None):
                    # httpx 被拦截（Cloudflare 等）→ 降级到 QWebEngineView 直显
                    self.reader_view.show_web_fallback(entry)
                else:
                    self.reader_view.show_fallback(
                        entry,
                        self.tr("完整正文加载失败，当前显示 Feed 摘要：{0}").format(str(exc)),
                    )
            return
        except Exception as exc:  # noqa: BLE001
            if self._entry_request_id == request_id:
                self.reader_view.show_fallback(
                    entry,
                    self.tr("正文处理失败，当前显示 Feed 摘要：{0}").format(str(exc)),
                )
            return
        if self._entry_request_id != request_id or self._selected_entry_id != entry_id:
            return
        self.reader_view.show_content(result.html, entry.url)

    async def refresh_entries(self) -> None:
        feed_id = state.selected_feed_id
        if feed_id is None:
            return
        request_id = str(uuid.uuid4())
        self._feed_request_id = request_id
        try:
            if self._search_query:
                entries = await self._entry_store.search(self._search_query, feed_id=feed_id)
            else:
                entries = await self._entry_store.list_by_feed(feed_id)
        except Exception as exc:  # noqa: BLE001
            if self._feed_request_id == request_id:
                self.statusBar().showMessage(self.tr("文章刷新失败：{0}").format(str(exc)), 6000)
            return
        if self._feed_request_id == request_id and state.selected_feed_id == feed_id:
            self.entry_list.set_entries(entries)

    async def search_entries(self, query: str) -> None:
        self._search_query = query.strip()
        self.entry_list.set_state("loading")
        await self.refresh_entries()

    async def mark_entry_read(self, entry_id: int, read: bool) -> None:
        try:
            if read:
                await self._entry_store.mark_read(entry_id)
            else:
                await self._entry_store.mark_unread(entry_id)
            await self.refresh_entries()
            await self.load_feeds()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(self.tr("更新已读状态失败：{0}").format(str(exc)), 6000)

    async def toggle_entry_star(self, entry_id: int) -> None:
        try:
            starred = await self._entry_store.toggle_star(entry_id)
            await self.refresh_entries()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(self.tr("更新收藏失败：{0}").format(str(exc)), 6000)
            return
        message = self.tr("已收藏文章") if starred else self.tr("已取消收藏")
        self.statusBar().showMessage(message, 4000)

    def confirm_delete(self) -> bool:
        result = QMessageBox.question(
            self,
            self.tr("删除文章"),
            self.tr("确定要删除这篇文章吗？此操作当前无法撤销。"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Yes

    async def delete_entry(self, entry_id: int) -> None:
        if not self.confirm_delete():
            return
        try:
            await self._entry_store.soft_delete(entry_id)
            if self._selected_entry_id == entry_id:
                self._selected_entry_id = None
                self._entry_request_id = None
                self.reader_view.show_empty()
            await self.refresh_entries()
            await self.load_feeds()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(self.tr("删除失败：{0}").format(str(exc)), 6000)
            return
        self.statusBar().showMessage(self.tr("文章已删除"), 4000)

    async def sync_feed(self, feed_id: int) -> None:
        await self._sync_service.sync_feed(feed_id)

    @asyncSlot(int)
    async def _select_feed_slot(self, feed_id: int) -> None:
        await self.select_feed(feed_id)

    @asyncSlot(int)
    async def _select_entry_slot(self, entry_id: int) -> None:
        await self.select_entry(entry_id)

    @asyncSlot(int)
    async def _sync_feed_slot(self, feed_id: int) -> None:
        await self.sync_feed(feed_id)

    @asyncSlot(str)
    async def _add_feed_slot(self, url: str) -> None:
        await self.add_feed(url)

    @asyncSlot()
    async def _retry_entries(self) -> None:
        if state.selected_feed_id is not None:
            await self.select_feed(state.selected_feed_id)

    @asyncSlot()
    async def _retry_reader(self) -> None:
        if self._selected_entry_id is not None:
            await self.select_entry(self._selected_entry_id)

    @asyncSlot(str)
    async def _search_entries_slot(self, query: str) -> None:
        await self.search_entries(query)

    @asyncSlot(int, bool)
    async def _mark_read_slot(self, entry_id: int, read: bool) -> None:
        await self.mark_entry_read(entry_id, read)

    @asyncSlot(int)
    async def _toggle_star_slot(self, entry_id: int) -> None:
        await self.toggle_entry_star(entry_id)

    @asyncSlot(int)
    async def _delete_entry_slot(self, entry_id: int) -> None:
        await self.delete_entry(entry_id)

    def _on_sync_started(self, feed_id: int) -> None:
        self.sidebar.set_feed_error(feed_id, None)
        self.sidebar.set_syncing(feed_id, True)
        self.statusBar().showMessage(self.tr("正在同步订阅…"))

    def _on_sync_finished(self, feed_id: int, new_count: int) -> None:
        self.sidebar.set_syncing(feed_id, False)
        self.statusBar().showMessage(self.tr("同步完成，新增 {0} 篇文章").format(new_count), 5000)
        self._schedule_refresh_for_feed(feed_id)

    def _schedule_refresh_for_feed(self, feed_id: int) -> None:
        async def refresh() -> None:
            await self.load_feeds()
            if state.selected_feed_id == feed_id:
                await self.select_feed(feed_id)

        try:
            asyncio.get_running_loop().create_task(refresh())
        except RuntimeError:
            pass

    def _on_sync_error(self, feed_id: int, message: str) -> None:
        self.sidebar.set_syncing(feed_id, False)
        self.sidebar.set_feed_error(feed_id, message)
        self.statusBar().showMessage(self.tr("同步失败：{0}").format(message), 7000)
        if state.selected_feed_id == feed_id:
            self.entry_list.set_state("error", self.tr("同步失败，已有文章仍可阅读。"))

    def _on_sync_all_done(self, total_new: int, total_failed: int) -> None:
        self.statusBar().showMessage(
            self.tr("全部同步完成：新增 {0} 篇，失败 {1} 个源").format(total_new, total_failed),
            6000,
        )

    def restore_ui_state(self) -> None:
        geometry = self._settings.value("ui/main_window/geometry")
        window_state = self._settings.value("ui/main_window/state")
        splitter_state = self._settings.value("ui/main_window/splitter")
        restored = isinstance(geometry, QByteArray) and self.restoreGeometry(geometry)
        if isinstance(window_state, QByteArray):
            self.restoreState(window_state)
        if isinstance(splitter_state, QByteArray):
            self.splitter.restoreState(splitter_state)
        else:
            self.splitter.setSizes([240, 360, 680])
        if restored and not self._is_on_screen():
            self.resize(1280, 800)
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                self.move(screen.availableGeometry().center() - self.rect().center())

    def _is_on_screen(self) -> bool:
        frame = self.frameGeometry()
        return any(
            frame.intersects(screen.availableGeometry()) for screen in QGuiApplication.screens()
        )

    def save_ui_state(self) -> None:
        self._settings.setValue("ui/main_window/geometry", self.saveGeometry())
        self._settings.setValue("ui/main_window/state", self.saveState())
        self._settings.setValue("ui/main_window/splitter", self.splitter.saveState())
        self._settings.sync()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.save_ui_state()
        super().closeEvent(event)
