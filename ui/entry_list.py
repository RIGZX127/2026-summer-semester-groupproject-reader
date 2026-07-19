"""Article list with explicit page states and bulk selection support."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QStackedWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from store.entry_store import EntryListItem
from ui.bulk_action_bar import BulkActionBar


class WrappingItemDelegate(QStyledItemDelegate):
    """Wrap list text and derive each row height from the current viewport width."""

    def initStyleOption(self, option: QStyleOptionViewItem, index) -> None:  # noqa: N802
        super().initStyleOption(option, index)
        option.features |= QStyleOptionViewItem.ViewItemFeature.WrapText
        option.textElideMode = Qt.TextElideMode.ElideNone

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:  # noqa: N802
        wrapped = QStyleOptionViewItem(option)
        self.initStyleOption(wrapped, index)
        view = self.parent()
        viewport_width = view.viewport().width() if isinstance(view, QListWidget) else 300
        text_width = max(80, viewport_width - 28)
        flags = int(Qt.TextFlag.TextWordWrap | Qt.TextFlag.TextExpandTabs)
        bounds = wrapped.fontMetrics.boundingRect(0, 0, text_width, 10_000, flags, wrapped.text)
        decoration = 22
        if wrapped.features & QStyleOptionViewItem.ViewItemFeature.HasDecoration:
            decoration += wrapped.decorationSize.width()
        height = max(bounds.height() + 20, super().sizeHint(option, index).height())
        return QSize(text_width + decoration, height)


class WrappingListWidget(QListWidget):
    """Recalculate wrapped row heights whenever the splitter changes width."""

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.scheduleDelayedItemsLayout()


class EntryListWidget(QWidget):
    entry_selected = Signal(int)
    retry_requested = Signal()
    search_requested = Signal(str)
    mark_read_requested = Signal(int, bool)
    star_requested = Signal(int)
    delete_requested = Signal(int)
    bulk_mark_read_requested = Signal(list)
    bulk_mark_unread_requested = Signal(list)
    bulk_delete_requested = Signal(list)
    VALID_STATES = frozenset({"empty", "loading", "content", "error", "offline", "disabled"})

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ContentSurface")
        self.setMinimumWidth(300)
        self.heading = QLabel(self.tr("文章"))
        self.heading.setObjectName("SectionTitle")
        self.loading_banner = QLabel(self.tr("正在加载文章…"))
        self.loading_banner.setObjectName("LoadingBanner")
        self.loading_banner.hide()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("搜索当前订阅源"))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setAccessibleName(self.tr("搜索当前订阅源的文章"))

        self.bulk_bar = BulkActionBar(self)

        self.stack = QStackedWidget()
        self.entry_list = WrappingListWidget()
        self.entry_list.setAccessibleName(self.tr("文章列表"))
        self.entry_list.setWordWrap(True)
        self.entry_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.entry_list.setUniformItemSizes(False)
        self.entry_list.setItemDelegate(WrappingItemDelegate(self.entry_list))
        self.entry_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entry_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.stack.addWidget(self.entry_list)

        self._state_pages: dict[str, QWidget] = {}
        for state_name, title, message in (
            ("empty", self.tr("这里还没有文章"), self.tr("添加订阅或选择其他订阅源。")),
            ("error", self.tr("文章加载失败"), self.tr("已有内容会保留，你可以重试。")),
            ("offline", self.tr("当前处于离线状态"), self.tr("网络恢复后可以重新同步。")),
            ("disabled", self.tr("文章列表暂不可用"), self.tr("请先选择一个订阅源。")),
        ):
            page = self._make_state_page(title, message, state_name in {"error", "offline"})
            self._state_pages[state_name] = page
            self.stack.addWidget(page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 20, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.heading)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.loading_banner)
        layout.addWidget(self.bulk_bar)
        layout.addWidget(self.stack, 1)
        self.entry_list.currentItemChanged.connect(self._on_current_item_changed)
        self.entry_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.entry_list.customContextMenuRequested.connect(self._show_context_menu)
        self.search_edit.returnPressed.connect(self._emit_search)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.bulk_bar.mark_read_requested.connect(self._emit_bulk_mark_read)
        self.bulk_bar.mark_unread_requested.connect(self._emit_bulk_mark_unread)
        self.bulk_bar.delete_requested.connect(self._emit_bulk_delete)
        self.bulk_bar.deselect_requested.connect(self._deselect_all)
        self.set_state("disabled")

    def _make_state_page(self, title: str, message: str, retry: bool) -> QWidget:
        page = QWidget()
        page.setProperty("statePage", True)
        title_label = QLabel(title)
        title_label.setObjectName("StateTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label = QLabel(message)
        message_label.setObjectName("StateMessage")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        box = QVBoxLayout(page)
        box.addStretch()
        box.addWidget(title_label)
        box.addWidget(message_label)
        if retry:
            button = QPushButton(self.tr("重试"))
            button.setAccessibleName(self.tr("重试加载文章"))
            button.clicked.connect(self.retry_requested)
            box.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
        box.addStretch()
        return page

    def set_state(self, state: str, message: str = "") -> None:
        if state not in self.VALID_STATES:
            raise ValueError(f"Unknown entry list state: {state}")
        self.loading_banner.setVisible(state == "loading")
        if state == "loading":
            if self.entry_list.count() == 0:
                self.stack.setCurrentWidget(self._state_pages["empty"])
            return
        if state == "content":
            self.stack.setCurrentWidget(self.entry_list)
            return
        page = self._state_pages[state]
        if message:
            labels = page.findChildren(QLabel)
            if len(labels) > 1:
                labels[1].setText(message)
        self.stack.setCurrentWidget(page)

    def set_entries(self, entries: list[EntryListItem]) -> None:
        selected_ids = set(self.selected_entry_ids())
        current_id = self.current_entry_id()
        with QSignalBlocker(self.entry_list):
            self.entry_list.clear()
            for entry in entries:
                read_state = self.tr("● 未读") if not entry.is_read else self.tr("已读")
                starred = self.tr("  ★ 收藏") if entry.is_starred else ""
                meta = " · ".join(part for part in (entry.author, entry.published_at or "") if part)
                item = QListWidgetItem(f"{read_state}{starred}\n{entry.title}\n{meta}")
                item.setData(Qt.ItemDataRole.UserRole, entry.id)
                item.setData(Qt.ItemDataRole.UserRole + 1, entry.is_read)
                item.setData(Qt.ItemDataRole.UserRole + 2, entry.is_starred)
                item.setToolTip(entry.title)
                self.entry_list.addItem(item)
                if entry.id in selected_ids:
                    item.setSelected(True)
                if entry.id == current_id:
                    self.entry_list.setCurrentItem(item)
        self.set_state("content" if entries else "empty")
        self._on_selection_changed()

    def current_entry_id(self) -> int | None:
        item = self.entry_list.currentItem()
        return int(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    def selected_entry_ids(self) -> list[int]:
        ids: list[int] = []
        for item in self.entry_list.selectedItems():
            entry_id = item.data(Qt.ItemDataRole.UserRole)
            if entry_id is not None:
                ids.append(int(entry_id))
        return ids

    def _emit_search(self) -> None:
        self.search_requested.emit(self.search_edit.text().strip())

    def _on_search_text_changed(self, text: str) -> None:
        if not text:
            self.search_requested.emit("")

    def _on_selection_changed(self) -> None:
        self.bulk_bar.update_count(len(self.selected_entry_ids()))

    def _show_context_menu(self, position) -> None:
        item = self.entry_list.itemAt(position)
        if item is None:
            return
        if not item.isSelected():
            self.entry_list.clearSelection()
            item.setSelected(True)
            self.entry_list.setCurrentItem(item)
        selected_ids = self.selected_entry_ids()
        menu = QMenu(self)
        if len(selected_ids) >= 2:
            mark_read_action = menu.addAction(self.tr("将选中文章标记为已读"))
            mark_unread_action = menu.addAction(self.tr("将选中文章标记为未读"))
            menu.addSeparator()
            delete_action = menu.addAction(self.tr("删除选中文章"))
            mark_read_action.triggered.connect(self._emit_bulk_mark_read)
            mark_unread_action.triggered.connect(self._emit_bulk_mark_unread)
            delete_action.triggered.connect(self._emit_bulk_delete)
        else:
            is_read = bool(item.data(Qt.ItemDataRole.UserRole + 1))
            is_starred = bool(item.data(Qt.ItemDataRole.UserRole + 2))
            read_action = menu.addAction(self.tr("标记未读") if is_read else self.tr("标记已读"))
            star_action = menu.addAction(self.tr("取消收藏") if is_starred else self.tr("收藏"))
            menu.addSeparator()
            delete_action = menu.addAction(self.tr("删除"))
            read_action.triggered.connect(lambda: self._emit_read_for_item(item, not is_read))
            star_action.triggered.connect(lambda: self._emit_star_for_item(item))
            delete_action.triggered.connect(lambda: self._emit_delete_for_item(item))
        menu.exec(self.entry_list.viewport().mapToGlobal(position))

    def _emit_read_for_item(self, item: QListWidgetItem, read: bool) -> None:
        self.mark_read_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)), read)

    def _emit_star_for_item(self, item: QListWidgetItem) -> None:
        self.star_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _emit_delete_for_item(self, item: QListWidgetItem) -> None:
        self.delete_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _emit_bulk_mark_read(self) -> None:
        ids = self.selected_entry_ids()
        if ids:
            self.bulk_mark_read_requested.emit(ids)

    def _emit_bulk_mark_unread(self) -> None:
        ids = self.selected_entry_ids()
        if ids:
            self.bulk_mark_unread_requested.emit(ids)

    def _emit_bulk_delete(self) -> None:
        ids = self.selected_entry_ids()
        if ids:
            self.bulk_delete_requested.emit(ids)

    def _deselect_all(self) -> None:
        self.entry_list.clearSelection()
        self.bulk_bar.update_count(0)

    def _on_current_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is not None:
            self.entry_selected.emit(int(current.data(Qt.ItemDataRole.UserRole)))
