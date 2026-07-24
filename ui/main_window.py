"""Mercury's Phase 1 three-column main window."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
)
from qasync import asyncSlot

from app.state import state
from core.reader.pipeline import ReaderFetchError
from store.entry_store import EntryListItem
from store.feed_store import DuplicateFeedError
from ui.dialogs.add_feed_dialog import AddFeedDialog
from ui.entry_list import EntryListWidget
from ui.reader.reader_view import ReaderView
from ui.settings.settings_dialog import SettingsDialog
from ui.sidebar import Sidebar

if TYPE_CHECKING:
    from core.digest.controller import DigestController
    from core.feed.opml_controller import OPMLController
    from core.feed.sync import SyncService
    from core.reader.pipeline import ReaderPipeline
    from store.collection_store import CollectionStore
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore
    from store.note_store import NoteStore
    from store.tag_store import TagStore


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
        tag_store: TagStore | None = None,
        note_store: NoteStore | None = None,
        digest_controller: DigestController | None = None,
        opml_controller: OPMLController | None = None,
        collection_store: CollectionStore | None = None,
    ) -> None:
        super().__init__()
        self._feed_store = feed_store
        self._entry_store = entry_store
        self._sync_service = sync_service
        self._reader_pipeline = reader_pipeline
        self._agent_runtime = agent_runtime
        self._tag_store = tag_store
        self._note_store = note_store
        self._digest_controller = digest_controller
        self._opml_controller = opml_controller
        self._collection_store = collection_store
        self._settings = settings or QSettings()
        self._feed_request_id: str | None = None
        self._entry_request_id: str | None = None
        self._add_dialog: AddFeedDialog | None = None
        self._settings_dialog: SettingsDialog | None = None
        self._selected_entry_id: int | None = None
        self._search_query = ""
        self._search_scope = "feed"
        self._sidebar_visible_before_focus = True
        self._active_tagging_run_id: str | None = None
        self._tagging_entry_id: int | None = None

        self.setWindowTitle(self.tr("Mercury RSS Reader"))
        self.setMinimumSize(1024, 640)
        self.resize(1280, 800)
        self.sidebar = Sidebar()
        self.entry_list = EntryListWidget()
        self.reader_view = ReaderView(settings=self._settings, agent_runtime=self._agent_runtime)
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
        self.sidebar.sync_all_requested.connect(self._sync_all_slot)
        self.sidebar.feed_rename_requested.connect(self._rename_feed_slot)
        self.sidebar.feed_delete_requested.connect(self._delete_feed_slot)
        self.sidebar.ai_settings_requested.connect(self.open_settings_dialog)
        self.sidebar.import_opml_requested.connect(self._import_opml_slot)
        self.sidebar.export_opml_requested.connect(self._export_opml_slot)
        self.sidebar.collapse_requested.connect(self._hide_sidebar)
        self.entry_list.entry_selected.connect(self._select_entry_slot)
        self.entry_list.retry_requested.connect(self._retry_entries)
        self.entry_list.search_requested.connect(self._search_entries_slot)
        self.entry_list.search_scope_changed.connect(self._search_scope_slot)
        self.entry_list.mark_read_requested.connect(self._mark_read_slot)
        self.entry_list.star_requested.connect(self._toggle_star_slot)
        self.entry_list.delete_requested.connect(self._delete_entry_slot)
        self.entry_list.add_to_collection_requested.connect(
            self._add_to_collection_slot
        )
        self.entry_list.export_markdown_requested.connect(
            self._export_markdown_slot
        )
        self.entry_list.manage_tags_requested.connect(self._manage_tags_slot)
        self.entry_list.generate_tags_requested.connect(self._generate_tags_slot)
        self.entry_list.batch_mark_read_requested.connect(self._batch_mark_read_slot)
        self.entry_list.batch_star_requested.connect(self._batch_toggle_star_slot)
        self.entry_list.batch_delete_requested.connect(self._batch_delete_slot)
        self.entry_list.batch_export_digest_requested.connect(
            self._batch_export_digest_slot
        )
        self.reader_view.retry_requested.connect(self._retry_reader)
        self.reader_view.note_editor.save_requested.connect(self._save_note_slot)
        self.sidebar.collections.collection_selected.connect(
            self._select_collection_slot
        )
        self.sidebar.collections.create_requested.connect(
            self._create_collection_slot
        )
        self.sidebar.collections.rename_requested.connect(
            self._rename_collection_slot
        )
        self.sidebar.collections.delete_requested.connect(
            self._delete_collection_slot
        )
        self.sidebar.collections.setVisible(self._collection_store is not None)
        self.reader_view.note_editor.setEnabled(self._note_store is not None)
        if self._agent_runtime is not None:
            self._agent_runtime.signals.state_changed.connect(
                self._on_tagging_state_changed
            )
        self.reader_view.toolbar.sidebar_restore_requested.connect(self._show_sidebar)
        self.reader_view.toolbar.focus_mode_changed.connect(self._set_focus_mode)
        self._sync_service.signals.sync_started.connect(self._on_sync_started)
        self._sync_service.signals.sync_finished.connect(self._on_sync_finished)
        self._sync_service.signals.sync_error.connect(self._on_sync_error)
        self._sync_service.signals.sync_all_done.connect(self._on_sync_all_done)

        self.restore_ui_state()
        QTimer.singleShot(0, self._schedule_initial_load)

    def _schedule_initial_load(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.load_feeds())
            if self._collection_store is not None:
                loop.create_task(self.load_collections())
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
        self.reader_view.note_editor.flush()
        self.reader_view.note_editor.set_entry(None, "")
        state.selected_feed_id = feed_id
        self._selected_entry_id = None
        self._search_query = ""
        self._search_scope = "feed"
        self.entry_list.set_search_scope("feed", notify=False)
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
        if self._selected_entry_id != entry_id:
            self.reader_view.note_editor.flush()
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
            self.reader_view.note_editor.set_entry(None, "")
            self.reader_view.show_error(self.tr("文章不存在或已被删除。"))
            return
        await self.load_entry_tags(entry_id, request_id)
        await self.load_note(entry_id, request_id)
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
        self.reader_view.show_content(result.html, entry.url, entry.id)

    def open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self._settings, self)
        self._settings_dialog = dialog
        dialog.provider_panel.test_requested.connect(self._provider_test_slot)
        dialog.provider_panel.configuration_saved.connect(self._on_llm_config_saved)
        dialog.agent_panel.settings_saved.connect(self._on_agent_settings_saved)
        dialog.finished.connect(lambda _result: self._clear_settings_dialog(dialog))
        dialog.show()

    def _on_llm_config_saved(self) -> None:
        from app.app import reconfigure_agent_runtime

        ok = reconfigure_agent_runtime(self._settings)
        if ok:
            self.statusBar().showMessage(
                self.tr("LLM 配置已生效，AI 功能立即可用。"), 6000
            )
        else:
            self.statusBar().showMessage(
                self.tr("LLM 配置已保存。请填写完整的服务地址和模型名称后重新保存。"), 8000
            )

    def _on_agent_settings_saved(self) -> None:
        """Agent 偏好（语言/详细程度/并发度）变更后同步到运行时。"""
        from app.app import reconfigure_agent_runtime

        reconfigure_agent_runtime(self._settings)
        self.statusBar().showMessage(
            self.tr("Agent 设置已保存，摘要和翻译将使用新的偏好。"), 5000
        )

    def _clear_settings_dialog(self, dialog: SettingsDialog) -> None:
        if self._settings_dialog is dialog:
            self._settings_dialog = None

    @asyncSlot(object)
    async def _provider_test_slot(self, config: dict[str, str]) -> None:
        dialog = self._settings_dialog
        if dialog is None:
            return
        from core.agent.providers import LLMRouter, ProviderConfig

        provider = ProviderConfig(
            name=config["name"] or "provider",
            base_url=config["base_url"],
            model=config["model"] or "model",
        )
        if config["api_key"]:
            provider.set_api_key(config["api_key"])
        router = LLMRouter(primary=provider)
        success, models, error = await router.test_connection(provider)
        if self._settings_dialog is dialog:
            dialog.provider_panel.show_test_result(success, models, error)

    async def refresh_entries(self) -> None:
        feed_id = state.selected_feed_id
        global_search = self._search_scope == "all" and bool(self._search_query)
        if feed_id is None and not global_search:
            return
        request_id = str(uuid.uuid4())
        self._feed_request_id = request_id
        try:
            if self._search_query:
                search_feed_id = None if self._search_scope == "all" else feed_id
                entries = await self._entry_store.search(
                    self._search_query, feed_id=search_feed_id
                )
            else:
                if feed_id is None:
                    return
                entries = await self._entry_store.list_by_feed(feed_id)
        except Exception as exc:  # noqa: BLE001
            if self._feed_request_id == request_id:
                self.statusBar().showMessage(self.tr("文章刷新失败：{0}").format(str(exc)), 6000)
            return
        selection_is_current = self._search_scope == "all" or state.selected_feed_id == feed_id
        if self._feed_request_id == request_id and selection_is_current:
            self.entry_list.set_entries(entries)

    async def search_entries(self, query: str) -> None:
        self._search_query = query.strip()
        if self._search_scope == "all" and not self._search_query:
            self.entry_list.set_entries([])
            self.entry_list.set_state("disabled", self.tr("输入关键词搜索全部订阅。"))
            return
        self.entry_list.set_state("loading")
        await self.refresh_entries()

    async def set_search_scope(self, scope: str) -> None:
        self._search_scope = scope if scope in {"feed", "all"} else "feed"
        if self._search_query:
            await self.search_entries(self._search_query)
        elif self._search_scope == "all":
            self.entry_list.set_entries([])
            self.entry_list.set_state("disabled", self.tr("输入关键词搜索全部订阅。"))
        elif state.selected_feed_id is not None:
            await self.select_feed(state.selected_feed_id)

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
            if self._collection_store is not None:
                if starred:
                    await self._collection_store.quick_star(entry_id)
                else:
                    await self._collection_store.quick_unstar(entry_id)
                await self.load_collections()
            await self.refresh_entries()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(self.tr("更新收藏失败：{0}").format(str(exc)), 6000)
            return
        message = self.tr("已收藏文章") if starred else self.tr("已取消收藏")
        self.statusBar().showMessage(message, 4000)

    async def load_collections(self) -> None:
        if self._collection_store is None:
            return
        try:
            rows = await self._collection_store.list_all()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("收藏夹加载失败：{0}").format(str(exc)), 6000
            )
            return
        self.sidebar.collections.set_collections(rows)

    async def select_collection(self, collection_id: int) -> None:
        if self._collection_store is None:
            return
        state.selected_feed_id = None
        self._selected_entry_id = None
        self.reader_view.note_editor.flush()
        self.reader_view.note_editor.set_entry(None, "")
        self.reader_view.show_empty()
        self.entry_list.set_state("loading")
        try:
            entry_ids = await self._collection_store.get_entries(collection_id)
            entry_rows = await asyncio.gather(
                *(self._entry_store.get(entry_id) for entry_id in entry_ids)
            )
        except Exception as exc:  # noqa: BLE001
            self.entry_list.set_state(
                "error", self.tr("收藏夹文章加载失败：{0}").format(str(exc))
            )
            return
        entries = [
            EntryListItem(
                row.id,
                row.feed_id,
                row.title,
                (row.summary or "")[:120],
                row.author,
                row.published_at,
                row.is_read,
                row.is_starred,
            )
            for row in entry_rows
            if row is not None
        ]
        self.entry_list.heading.setText(self.tr("收藏夹文章"))
        self.entry_list.set_entries(entries)

    async def create_collection(self, name: str) -> None:
        if self._collection_store is None:
            return
        try:
            await self._collection_store.create(name)
            await self.load_collections()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("新建收藏夹失败：{0}").format(str(exc)), 6000
            )

    async def rename_collection(self, collection_id: int, name: str) -> None:
        if self._collection_store is None:
            return
        try:
            await self._collection_store.update(collection_id, name=name)
            await self.load_collections()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("重命名收藏夹失败：{0}").format(str(exc)), 6000
            )

    async def delete_collection(self, collection_id: int) -> None:
        if self._collection_store is None:
            return
        result = QMessageBox.question(
            self,
            self.tr("删除收藏夹"),
            self.tr("确定删除这个收藏夹吗？文章本身不会被删除。"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        try:
            await self._collection_store.delete(collection_id)
            await self.load_collections()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("删除收藏夹失败：{0}").format(str(exc)), 6000
            )

    def _choose_collection(self, rows: list) -> int | None:
        names = [row.name for row in rows]
        name, accepted = QInputDialog.getItem(
            self,
            self.tr("添加到收藏夹"),
            self.tr("选择收藏夹"),
            names,
            0,
            False,
        )
        if not accepted:
            return None
        return next((row.id for row in rows if row.name == name), None)

    async def add_entry_to_collection(self, entry_id: int) -> None:
        if self._collection_store is None:
            return
        try:
            rows = await self._collection_store.list_all()
            if not rows:
                created = await self._collection_store.create(
                    self.tr("默认收藏夹"), is_default=True
                )
                rows = [created]
            collection_id = self._choose_collection(rows)
            if collection_id is None:
                return
            await self._collection_store.add_entry(collection_id, entry_id)
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("添加到收藏夹失败：{0}").format(str(exc)), 6000
            )
            return
        self.statusBar().showMessage(self.tr("已添加到收藏夹"), 4000)

    async def load_note(self, entry_id: int, request_id: str | None = None) -> None:
        if self._note_store is None:
            self.reader_view.note_editor.set_entry(None, "")
            return
        try:
            note = await self._note_store.get(entry_id)
        except Exception:  # noqa: BLE001
            if request_id is None or request_id == self._entry_request_id:
                self.reader_view.note_editor.set_entry(entry_id, "")
                self.reader_view.note_editor.set_save_state("error")
            return
        if request_id is not None and request_id != self._entry_request_id:
            return
        self.reader_view.note_editor.set_entry(entry_id, note.body if note else "")

    async def save_note(self, entry_id: int, body: str) -> None:
        if self._note_store is None:
            return
        try:
            await self._note_store.save(entry_id, body)
        except Exception:  # noqa: BLE001
            if self.reader_view.note_editor.entry_id == entry_id:
                self.reader_view.note_editor.set_save_state("error")
            return
        if self.reader_view.note_editor.entry_id == entry_id:
            self.reader_view.note_editor.set_save_state("saved")

    async def export_entry_markdown(self, entry_id: int, dest_dir: str) -> None:
        if self._digest_controller is None:
            self.statusBar().showMessage(self.tr("导出功能当前不可用"), 5000)
            return
        try:
            result = await self._digest_controller.export_single(entry_id, dest_dir)
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("导出失败：{0}").format(str(exc)), 6000
            )
            return
        if result.ok:
            self.statusBar().showMessage(
                self.tr("Markdown 已导出：{0}").format(str(result.path)), 6000
            )
        else:
            self.statusBar().showMessage(
                self.tr("导出失败：{0}").format(result.error or self.tr("未知错误")),
                6000,
            )

    async def export_entries_digest(
        self, entry_ids: list[int], dest_dir: str
    ) -> None:
        if not entry_ids or self._digest_controller is None:
            return
        try:
            result = await self._digest_controller.export_multi(entry_ids, dest_dir)
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("Digest 导出失败：{0}").format(str(exc)), 6000
            )
            return
        if result.ok:
            self.entry_list.set_batch_mode(False)
            self.statusBar().showMessage(
                self.tr("Digest 已导出：{0}").format(str(result.path)), 6000
            )
        else:
            self.statusBar().showMessage(
                self.tr("Digest 导出失败：{0}").format(
                    result.error or self.tr("未知错误")
                ),
                6000,
            )

    async def load_entry_tags(
        self, entry_id: int, request_id: str | None = None
    ) -> list[str]:
        if self._tag_store is None:
            self.reader_view.set_tags([])
            return []
        try:
            rows = await self._tag_store.get_entry_tags(entry_id)
        except Exception as exc:  # noqa: BLE001
            if request_id is None or request_id == self._entry_request_id:
                self.statusBar().showMessage(
                    self.tr("标签加载失败：{0}").format(str(exc)), 5000
                )
            return []
        if request_id is not None and request_id != self._entry_request_id:
            return []
        names = [row.tag_name for row in rows]
        if self._selected_entry_id in {None, entry_id}:
            self.reader_view.set_tags(names)
        return names

    def _prompt_tag_names(self, current: list[str]) -> list[str] | None:
        value, accepted = QInputDialog.getText(
            self,
            self.tr("管理标签"),
            self.tr("输入标签，用逗号分隔"),
            text=", ".join(current),
        )
        if not accepted:
            return None
        names: list[str] = []
        seen: set[str] = set()
        for raw_name in value.replace("，", ",").split(","):
            name = raw_name.strip()
            normalized = name.casefold()
            if name and normalized not in seen:
                names.append(name)
                seen.add(normalized)
        return names

    async def manage_entry_tags(
        self, entry_id: int, suggested: list[str] | None = None
    ) -> None:
        if self._tag_store is None:
            return
        current = await self.load_entry_tags(entry_id)
        names = suggested if suggested is not None else self._prompt_tag_names(current)
        if names is None:
            return
        try:
            tags = [await self._tag_store.create(name) for name in names]
            await self._tag_store.set_entry_tags(entry_id, [tag.id for tag in tags])
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("标签保存失败：{0}").format(str(exc)), 6000
            )
            return
        if self._selected_entry_id in {None, entry_id}:
            self.reader_view.set_tags(names)
        self.statusBar().showMessage(self.tr("标签已保存"), 4000)

    def generate_entry_tags(self, entry_id: int) -> None:
        if self._agent_runtime is None:
            self.statusBar().showMessage(self.tr("请先配置 AI 服务"), 5000)
            return
        try:
            self._tagging_entry_id = entry_id
            self._active_tagging_run_id = self._agent_runtime.submit(
                entry_id, "tagging"
            )
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("AI 标签任务启动失败：{0}").format(str(exc)), 6000
            )
            return
        self.statusBar().showMessage(self.tr("正在生成标签…"))

    def _on_tagging_state_changed(self, event: object) -> None:
        from core.agent.runtime import AgentUIEvent

        evt: AgentUIEvent = event
        if (
            evt.agent_type != "tagging"
            or evt.entry_id != self._tagging_entry_id
            or evt.run_id != self._active_tagging_run_id
        ):
            return
        if evt.status == "error":
            self.statusBar().showMessage(
                self.tr("AI 标签生成失败：{0}").format(evt.error or self.tr("未知错误")),
                6000,
            )
            return
        if evt.status != "done" or not evt.result_json:
            return
        try:
            result = json.loads(evt.result_json)
            suggestions = [
                str(name).strip()
                for name in result.get("tags", [])
                if str(name).strip()
            ]
        except (json.JSONDecodeError, TypeError, AttributeError):
            suggestions = []
        if not suggestions:
            self.statusBar().showMessage(self.tr("AI 未生成可用标签"), 5000)
            return
        accepted = QMessageBox.question(
            self,
            self.tr("确认 AI 标签"),
            self.tr("是否保存以下标签？\n{0}").format("、".join(suggestions)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if accepted == QMessageBox.StandardButton.Yes:
            try:
                asyncio.get_running_loop().create_task(
                    self.manage_entry_tags(evt.entry_id, suggestions)
                )
            except RuntimeError:
                self.statusBar().showMessage(self.tr("标签保存任务无法启动"), 5000)

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

    async def batch_mark_entries_read(self, entry_ids: list[int], read: bool) -> None:
        if not entry_ids:
            return
        try:
            for entry_id in entry_ids:
                if read:
                    await self._entry_store.mark_read(entry_id)
                else:
                    await self._entry_store.mark_unread(entry_id)
            await self.refresh_entries()
            await self.load_feeds()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("批量更新已读状态失败：{0}").format(str(exc)), 6000
            )
            return
        self.statusBar().showMessage(self.tr("已更新 {0} 篇文章").format(len(entry_ids)), 4000)

    async def batch_toggle_entries_star(self, entry_ids: list[int]) -> None:
        if not entry_ids:
            return
        try:
            for entry_id in entry_ids:
                await self._entry_store.toggle_star(entry_id)
            await self.refresh_entries()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(self.tr("批量收藏失败：{0}").format(str(exc)), 6000)
            return
        self.statusBar().showMessage(
            self.tr("已切换 {0} 篇文章的收藏状态").format(len(entry_ids)), 4000
        )

    def confirm_batch_delete(self, count: int) -> bool:
        result = QMessageBox.question(
            self,
            self.tr("批量删除文章"),
            self.tr("确定删除选中的 {0} 篇文章吗？此操作当前无法撤销。").format(count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Yes

    async def batch_delete_entries(self, entry_ids: list[int]) -> None:
        if not entry_ids or not self.confirm_batch_delete(len(entry_ids)):
            return
        try:
            for entry_id in entry_ids:
                await self._entry_store.soft_delete(entry_id)
            if self._selected_entry_id in entry_ids:
                self._selected_entry_id = None
                self._entry_request_id = None
                self.reader_view.show_empty()
            await self.refresh_entries()
            await self.load_feeds()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(self.tr("批量删除失败：{0}").format(str(exc)), 6000)
            return
        self.entry_list.set_batch_mode(False)
        self.statusBar().showMessage(self.tr("已删除 {0} 篇文章").format(len(entry_ids)), 4000)

    async def import_opml_file(self, path: str) -> None:
        if self._opml_controller is None:
            QMessageBox.warning(self, self.tr("导入 OPML"), self.tr("OPML 控制器未初始化。"))
            return
        self.statusBar().showMessage(self.tr("正在导入 OPML…"))
        try:
            result = await self._opml_controller.import_feeds_from_opml(path)
            await self.load_feeds()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.tr("导入 OPML 失败"), str(exc))
            self.statusBar().showMessage(self.tr("OPML 导入失败"), 6000)
            return
        self.statusBar().showMessage(
            self.tr("OPML 导入完成：新增 {0} 个，跳过 {1} 个，失败 {2} 个").format(
                len(result.success), len(result.skipped), len(result.failed)
            ),
            8000,
        )

    async def export_opml_file(self, path: str) -> None:
        if self._opml_controller is None:
            QMessageBox.warning(self, self.tr("导出 OPML"), self.tr("OPML 控制器未初始化。"))
            return
        if not path.lower().endswith((".opml", ".xml")):
            path += ".opml"
        self.statusBar().showMessage(self.tr("正在导出 OPML…"))
        try:
            out_path = await self._opml_controller.export_feeds_to_opml(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.tr("导出 OPML 失败"), str(exc))
            self.statusBar().showMessage(self.tr("OPML 导出失败"), 6000)
            return
        self.statusBar().showMessage(self.tr("OPML 已导出：{0}").format(out_path), 8000)

    async def sync_feed(self, feed_id: int) -> None:
        await self._sync_service.sync_feed(feed_id)

    async def sync_all_feeds(self) -> None:
        self.statusBar().showMessage(self.tr("正在同步全部订阅…"))
        try:
            await self._sync_service.sync_all()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("同步全部订阅失败：{0}").format(str(exc)), 7000
            )

    async def rename_feed(self, feed_id: int, title: str) -> None:
        title = title.strip()
        if not title:
            return
        try:
            await self._feed_store.update(feed_id, title=title, favicon_url=None)
            await self.load_feeds()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("重命名订阅失败：{0}").format(str(exc)), 6000
            )
            return
        self.statusBar().showMessage(self.tr("订阅已重命名"), 4000)

    def confirm_feed_delete(self, title: str) -> bool:
        result = QMessageBox.question(
            self,
            self.tr("删除订阅"),
            self.tr("确定删除“{0}”吗？该订阅下的文章也会被移除。").format(title),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Yes

    async def delete_feed(self, feed_id: int) -> None:
        feed_title = next(
            (feed.title or feed.url for feed in state.feeds if feed.id == feed_id),
            self.tr("该订阅源"),
        )
        if not self.confirm_feed_delete(feed_title):
            return
        try:
            await self._feed_store.delete(feed_id)
            if state.selected_feed_id == feed_id:
                state.selected_feed_id = None
                self._selected_entry_id = None
                self._feed_request_id = None
                self._entry_request_id = None
                self.entry_list.search_edit.clear()
                self.entry_list.set_entries([])
                self.entry_list.set_state("disabled", self.tr("请选择其他订阅源。"))
                self.reader_view.show_empty()
            await self.load_feeds()
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(
                self.tr("删除订阅失败：{0}").format(str(exc)), 6000
            )
            return
        self.statusBar().showMessage(self.tr("订阅已删除"), 4000)

    @asyncSlot(int)
    async def _select_feed_slot(self, feed_id: int) -> None:
        await self.select_feed(feed_id)

    @asyncSlot(int)
    async def _select_entry_slot(self, entry_id: int) -> None:
        await self.select_entry(entry_id)

    @asyncSlot(int)
    async def _sync_feed_slot(self, feed_id: int) -> None:
        await self.sync_feed(feed_id)

    @asyncSlot()
    async def _sync_all_slot(self) -> None:
        await self.sync_all_feeds()

    @asyncSlot(int, str)
    async def _rename_feed_slot(self, feed_id: int, title: str) -> None:
        await self.rename_feed(feed_id, title)

    @asyncSlot(int)
    async def _delete_feed_slot(self, feed_id: int) -> None:
        await self.delete_feed(feed_id)

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

    @asyncSlot(str)
    async def _search_scope_slot(self, scope: str) -> None:
        await self.set_search_scope(scope)

    @asyncSlot(int, bool)
    async def _mark_read_slot(self, entry_id: int, read: bool) -> None:
        await self.mark_entry_read(entry_id, read)

    @asyncSlot(int)
    async def _toggle_star_slot(self, entry_id: int) -> None:
        await self.toggle_entry_star(entry_id)

    @asyncSlot(int)
    async def _delete_entry_slot(self, entry_id: int) -> None:
        await self.delete_entry(entry_id)

    @asyncSlot(int)
    async def _add_to_collection_slot(self, entry_id: int) -> None:
        await self.add_entry_to_collection(entry_id)

    @asyncSlot(int)
    async def _export_markdown_slot(self, entry_id: int) -> None:
        path = QFileDialog.getExistingDirectory(self, self.tr("选择 Markdown 导出目录"))
        if path:
            await self.export_entry_markdown(entry_id, path)

    @asyncSlot(list)
    async def _batch_export_digest_slot(self, entry_ids: list[int]) -> None:
        path = QFileDialog.getExistingDirectory(self, self.tr("选择 Digest 导出目录"))
        if path:
            await self.export_entries_digest(entry_ids, path)

    @asyncSlot(int)
    async def _manage_tags_slot(self, entry_id: int) -> None:
        await self.manage_entry_tags(entry_id)

    @asyncSlot(int)
    async def _generate_tags_slot(self, entry_id: int) -> None:
        self.generate_entry_tags(entry_id)

    @asyncSlot(int)
    async def _select_collection_slot(self, collection_id: int) -> None:
        await self.select_collection(collection_id)

    @asyncSlot(str)
    async def _create_collection_slot(self, name: str) -> None:
        await self.create_collection(name)

    @asyncSlot(int, str)
    async def _rename_collection_slot(self, collection_id: int, name: str) -> None:
        await self.rename_collection(collection_id, name)

    @asyncSlot(int)
    async def _delete_collection_slot(self, collection_id: int) -> None:
        await self.delete_collection(collection_id)

    @asyncSlot(int, str)
    async def _save_note_slot(self, entry_id: int, body: str) -> None:
        await self.save_note(entry_id, body)


    @asyncSlot(list, bool)
    async def _batch_mark_read_slot(self, entry_ids: list[int], read: bool) -> None:
        await self.batch_mark_entries_read(entry_ids, read)

    @asyncSlot(list)
    async def _batch_toggle_star_slot(self, entry_ids: list[int]) -> None:
        await self.batch_toggle_entries_star(entry_ids)

    @asyncSlot(list)
    async def _batch_delete_slot(self, entry_ids: list[int]) -> None:
        await self.batch_delete_entries(entry_ids)

    @asyncSlot()
    async def _import_opml_slot(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self.tr("导入 OPML"),
            "",
            self.tr("OPML 文件 (*.opml *.xml);;所有文件 (*.*)"),
        )
        if path:
            await self.import_opml_file(path)

    @asyncSlot()
    async def _export_opml_slot(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            self.tr("导出 OPML"),
            "mercury_subscriptions.opml",
            self.tr("OPML 文件 (*.opml);;XML 文件 (*.xml);;所有文件 (*.*)"),
        )
        if path:
            await self.export_opml_file(path)

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
        self.reader_view.save_ui_state()
        self._settings.sync()

    def _hide_sidebar(self) -> None:
        self.sidebar.hide()
        self.reader_view.toolbar.show_sidebar_restore(True)

    def _show_sidebar(self) -> None:
        self.sidebar.show()
        self.reader_view.toolbar.show_sidebar_restore(False)

    def _set_focus_mode(self, enabled: bool) -> None:
        if enabled:
            self._sidebar_visible_before_focus = not self.sidebar.isHidden()
            self.sidebar.hide()
            self.entry_list.hide()
            self.reader_view.toolbar.show_sidebar_restore(False)
        else:
            self.sidebar.setVisible(self._sidebar_visible_before_focus)
            self.entry_list.show()
            self.reader_view.toolbar.show_sidebar_restore(not self._sidebar_visible_before_focus)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.reader_view.note_editor.flush()
        self.save_ui_state()
        super().closeEvent(event)
