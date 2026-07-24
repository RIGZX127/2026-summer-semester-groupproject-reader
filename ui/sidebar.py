"""Feed navigation sidebar."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from store.feed_store import FeedRow
from ui.collections_widget import CollectionsWidget
from ui.icons import (
    COMPACT_CONTROL_SIZE,
    COMPACT_ICON_SIZE,
    add_icon,
    agent_icon,
    export_icon,
    feed_icon,
    import_icon,
    sidebar_icon,
    sync_icon,
)
from ui.tooltips import enable_immediate_tooltip

_TITLE_ROLE = int(Qt.ItemDataRole.UserRole) + 1
_COUNT_ROLE = int(Qt.ItemDataRole.UserRole) + 2
_ERROR_ROLE = int(Qt.ItemDataRole.UserRole) + 3


class Sidebar(QWidget):
    """Display feeds and emit navigation intentions."""

    feed_selected = Signal(int)
    add_feed_requested = Signal()
    sync_requested = Signal(int)
    sync_all_requested = Signal()
    feed_rename_requested = Signal(int, str)
    feed_delete_requested = Signal(int)
    ai_settings_requested = Signal()
    import_opml_requested = Signal()
    export_opml_requested = Signal()
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
        self.collapse_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.collapse_button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.collapse_button.setAccessibleName(self.tr("隐藏订阅源栏"))
        self.collapse_button.setToolTip(self.tr("隐藏订阅源栏"))
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.collapse_button)
        self.add_button = QPushButton()
        self.add_button.setObjectName("SidebarActionButton")
        self.add_button.setIcon(add_icon())
        self.add_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.add_button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.add_button.setAccessibleName(self.tr("添加订阅源"))
        self.add_button.setToolTip(self.tr("添加新的 RSS、Atom 或 JSON Feed"))
        self.sync_button = QPushButton()
        self.sync_button.setObjectName("SidebarActionButton")
        self.sync_button.setIcon(sync_icon())
        self.sync_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.sync_button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.sync_button.setAccessibleName(self.tr("同步订阅"))
        self.sync_button.setToolTip(self.tr("同步当前订阅或全部订阅"))
        self.sync_button.setEnabled(False)

        self.sync_menu = QMenu(self)
        self.sync_current_action = self.sync_menu.addAction(self.tr("同步当前订阅"))
        self.sync_all_action = self.sync_menu.addAction(self.tr("同步全部订阅"))
        self.sync_current_action.setEnabled(False)
        self.sync_current_action.triggered.connect(lambda _checked=False: self._request_sync())
        self.sync_all_action.triggered.connect(
            lambda _checked=False: self.sync_all_requested.emit()
        )

        self.ai_button = QPushButton()
        self.ai_button.setObjectName("SidebarActionButton")
        self.ai_button.setIcon(agent_icon())
        self.ai_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.ai_button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.ai_button.setAccessibleName(self.tr("AI 设置"))
        self.ai_button.setToolTip(self.tr("AI 设置"))
        self.ai_button.setProperty("iconRole", "agent")

        self.import_opml_button = QPushButton()
        self.import_opml_button.setObjectName("SidebarActionButton")
        self.import_opml_button.setIcon(import_icon())
        self.import_opml_button.setIconSize(
            QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE)
        )
        self.import_opml_button.setFixedSize(
            COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE
        )
        self.import_opml_button.setAccessibleName(self.tr("导入 OPML"))
        self.import_opml_button.setToolTip(self.tr("导入 OPML"))

        self.export_opml_button = QPushButton()
        self.export_opml_button.setObjectName("SidebarActionButton")
        self.export_opml_button.setIcon(export_icon())
        self.export_opml_button.setIconSize(
            QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE)
        )
        self.export_opml_button.setFixedSize(
            COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE
        )
        self.export_opml_button.setAccessibleName(self.tr("导出 OPML"))
        self.export_opml_button.setToolTip(self.tr("导出 OPML"))

        for button in (
            self.collapse_button,
            self.add_button,
            self.sync_button,
            self.ai_button,
            self.import_opml_button,
            self.export_opml_button,
        ):
            enable_immediate_tooltip(button)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(6)
        actions.addWidget(self.add_button)
        actions.addWidget(self.sync_button)
        actions.addWidget(self.ai_button)
        actions.addWidget(self.import_opml_button)
        actions.addWidget(self.export_opml_button)
        actions.addStretch()

        section = QLabel(self.tr("订阅源"))
        section.setObjectName("SidebarSection")
        self.feed_list = QListWidget()
        self.feed_list.setAccessibleName(self.tr("订阅源列表"))
        self.feed_list.setWordWrap(True)
        self.feed_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.feed_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.feed_list.setUniformItemSizes(False)
        self.feed_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.feed_menu = QMenu(self)
        self.feed_rename_action = self.feed_menu.addAction(self.tr("重命名订阅"))
        self.feed_delete_action = self.feed_menu.addAction(self.tr("删除订阅"))
        self.feed_rename_action.triggered.connect(
            lambda _checked=False: self._rename_current_feed()
        )
        self.feed_delete_action.triggered.connect(
            lambda _checked=False: self._request_delete_current_feed()
        )

        # Kept as a compatibility hook for older UI tests and integrations.
        self.ai_card = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 6, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addLayout(actions)
        layout.addWidget(section)
        layout.addWidget(self.feed_list, 1)
        self.collections = CollectionsWidget(self)
        layout.addWidget(self.collections, 1)

        self.add_button.clicked.connect(self.add_feed_requested)
        self.sync_button.clicked.connect(self._show_sync_menu)
        self.ai_button.clicked.connect(self.ai_settings_requested)
        self.import_opml_button.clicked.connect(self.import_opml_requested)
        self.export_opml_button.clicked.connect(self.export_opml_requested)
        self.collapse_button.clicked.connect(self.collapse_requested)
        self.feed_list.currentItemChanged.connect(self._on_current_item_changed)
        self.feed_list.customContextMenuRequested.connect(self._show_feed_menu)

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
            item.setIcon(feed_icon())
            self.feed_list.addItem(item)
            self._refresh_item(item)
            if row.id == selected_id:
                restore_row = self.feed_list.count() - 1
        if restore_row >= 0:
            self.feed_list.setCurrentRow(restore_row)
        self.sync_button.setEnabled(bool(rows))
        self.sync_current_action.setEnabled(self.current_feed_id() is not None)

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
        self.sync_current_action.setEnabled(feed_id is not None)
        if feed_id is not None:
            self.feed_selected.emit(int(feed_id))

    def _request_sync(self) -> None:
        feed_id = self.current_feed_id()
        if feed_id is not None:
            self.sync_requested.emit(feed_id)

    def _show_sync_menu(self) -> None:
        self.sync_current_action.setEnabled(self.current_feed_id() is not None)
        self.sync_menu.popup(self.sync_button.mapToGlobal(self.sync_button.rect().bottomLeft()))

    def _show_feed_menu(self, position) -> None:
        item = self.feed_list.itemAt(position)
        if item is None:
            return
        self.feed_list.setCurrentItem(item)
        self.feed_menu.popup(self.feed_list.viewport().mapToGlobal(position))

    def _rename_current_feed(self) -> None:
        item = self.feed_list.currentItem()
        if item is None:
            return
        feed_id = int(item.data(Qt.ItemDataRole.UserRole))
        current_title = str(item.data(_TITLE_ROLE))
        title, accepted = QInputDialog.getText(
            self,
            self.tr("重命名订阅"),
            self.tr("订阅名称"),
            QLineEdit.EchoMode.Normal,
            current_title,
        )
        title = title.strip()
        if accepted and title and title != current_title:
            self.feed_rename_requested.emit(feed_id, title)

    def _request_delete_current_feed(self) -> None:
        feed_id = self.current_feed_id()
        if feed_id is not None:
            self.feed_delete_requested.emit(feed_id)
