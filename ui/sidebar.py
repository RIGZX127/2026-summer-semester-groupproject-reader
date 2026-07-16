"""Feed navigation sidebar."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from store.feed_store import FeedRow
from ui.icons import sidebar_icon

_TITLE_ROLE = int(Qt.ItemDataRole.UserRole) + 1
_COUNT_ROLE = int(Qt.ItemDataRole.UserRole) + 2
_ERROR_ROLE = int(Qt.ItemDataRole.UserRole) + 3


class Sidebar(QWidget):
    """Display feeds and emit navigation intentions."""

    feed_selected = Signal(int)
    add_feed_requested = Signal()
    sync_requested = Signal(int)
    ai_settings_requested = Signal()
    collapse_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(210)

        title = QLabel("Mercury")
        title.setObjectName("AppTitle")
        self.collapse_button = QPushButton()
        self.collapse_button.setObjectName("SidebarCollapseButton")
        self.collapse_button.setIcon(sidebar_icon())
        self.collapse_button.setIconSize(QSize(18, 18))
        self.collapse_button.setFixedSize(32, 32)
        self.collapse_button.setAccessibleName(self.tr("隐藏订阅源栏"))
        self.collapse_button.setToolTip(self.tr("隐藏订阅源栏"))
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.collapse_button)
        self.add_button = QPushButton(self.tr("＋ 添加订阅"))
        self.add_button.setAccessibleName(self.tr("添加订阅源"))
        self.add_button.setToolTip(self.tr("添加新的 RSS、Atom 或 JSON Feed"))
        self.sync_button = QPushButton(self.tr("同步当前订阅"))
        self.sync_button.setAccessibleName(self.tr("同步当前订阅"))
        self.sync_button.setToolTip(self.tr("获取当前订阅源的最新文章"))
        self.sync_button.setEnabled(False)
        self.add_button.setMinimumHeight(36)
        self.add_button.setProperty("buttonRole", "primary")
        self.sync_button.setMinimumHeight(36)
        self.sync_button.setProperty("buttonRole", "secondary")

        section = QLabel(self.tr("订阅源"))
        section.setObjectName("SidebarSection")
        self.feed_list = QListWidget()
        self.feed_list.setAccessibleName(self.tr("订阅源列表"))
        self.feed_list.setWordWrap(True)
        self.feed_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.feed_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.feed_list.setUniformItemSizes(False)

        self.ai_card = QWidget()
        self.ai_card.setObjectName("AIWorkspaceCard")
        ai_title = QLabel(self.tr("AI 工作台"))
        ai_title.setObjectName("AIWorkspaceTitle")
        self.ai_description = QLabel(self.tr("配置模型，使用文章摘要与全文翻译"))
        self.ai_description.setObjectName("AIWorkspaceDescription")
        self.ai_description.setWordWrap(True)
        self.ai_button = QPushButton(self.tr("打开 AI 工作台"))
        self.ai_button.setObjectName("AIWorkspaceButton")
        self.ai_button.setAccessibleName(self.tr("打开 AI 提供者和 Agent 设置"))
        self.ai_button.setToolTip(self.tr("配置模型、自动摘要和翻译选项"))
        ai_layout = QVBoxLayout(self.ai_card)
        ai_layout.setContentsMargins(12, 12, 12, 12)
        ai_layout.setSpacing(6)
        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(self.ai_description)
        ai_layout.addWidget(self.ai_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addSpacing(8)
        layout.addWidget(self.add_button)
        layout.addSpacing(8)
        layout.addWidget(section)
        layout.addWidget(self.feed_list, 1)
        layout.addWidget(self.ai_card)
        layout.addWidget(self.sync_button)

        self.add_button.clicked.connect(self.add_feed_requested)
        self.sync_button.clicked.connect(self._request_sync)
        self.ai_button.clicked.connect(self.ai_settings_requested)
        self.collapse_button.clicked.connect(self.collapse_requested)
        self.feed_list.currentItemChanged.connect(self._on_current_item_changed)

    def set_feeds(self, rows: list[tuple[FeedRow, int]]) -> None:
        selected_id = self.current_feed_id()
        self.feed_list.clear()
        restore_row = -1
        for row, unread in rows:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, row.id)
            item.setData(_TITLE_ROLE, row.title or row.url)
            item.setData(_COUNT_ROLE, unread)
            item.setData(_ERROR_ROLE, None)
            item.setToolTip(row.title or row.url)
            self.feed_list.addItem(item)
            self._refresh_item(item)
            if row.id == selected_id:
                restore_row = self.feed_list.count() - 1
        if restore_row >= 0:
            self.feed_list.setCurrentRow(restore_row)

    def current_feed_id(self) -> int | None:
        item = self.feed_list.currentItem()
        return int(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    def set_syncing(self, feed_id: int, syncing: bool) -> None:
        item = self._item_for_feed(feed_id)
        if item is not None:
            item.setData(_ERROR_ROLE, self.tr("同步中") if syncing else None)
            self._refresh_item(item)

    def set_feed_error(self, feed_id: int, message: str | None) -> None:
        item = self._item_for_feed(feed_id)
        if item is not None:
            item.setData(_ERROR_ROLE, self.tr("同步失败") if message else None)
            item.setToolTip(message or str(item.data(_TITLE_ROLE)))
            self._refresh_item(item)

    def _item_for_feed(self, feed_id: int) -> QListWidgetItem | None:
        for index in range(self.feed_list.count()):
            item = self.feed_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == feed_id:
                return item
        return None

    def _refresh_item(self, item: QListWidgetItem) -> None:
        title = str(item.data(_TITLE_ROLE))
        unread = int(item.data(_COUNT_ROLE) or 0)
        status = item.data(_ERROR_ROLE)
        suffix = f"  ·  {status}" if status else (f"  {unread}" if unread else "")
        item.setText(f"{title}{suffix}")

    def _on_current_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        feed_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.sync_button.setEnabled(feed_id is not None)
        if feed_id is not None:
            self.feed_selected.emit(int(feed_id))

    def _request_sync(self) -> None:
        feed_id = self.current_feed_id()
        if feed_id is not None:
            self.sync_requested.emit(feed_id)
