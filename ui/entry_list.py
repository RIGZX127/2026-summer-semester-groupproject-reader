"""Article list with explicit page states."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPalette, QResizeEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHBoxLayout,
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
from ui.icons import (
    COMPACT_CONTROL_SIZE,
    COMPACT_ICON_SIZE,
    batch_icon,
    close_icon,
)
from ui.tooltips import enable_immediate_tooltip

_READ_ROLE = int(Qt.ItemDataRole.UserRole) + 1
_STARRED_ROLE = int(Qt.ItemDataRole.UserRole) + 2


def _blend_color(foreground: QColor, background: QColor, ratio: float) -> QColor:
    """Blend semantic text and background colors for an adaptive read-state gray."""
    return QColor(
        round(foreground.red() * ratio + background.red() * (1 - ratio)),
        round(foreground.green() * ratio + background.green() * (1 - ratio)),
        round(foreground.blue() * ratio + background.blue() * (1 - ratio)),
    )


class WrappingItemDelegate(QStyledItemDelegate):
    """Wrap list text and derive each row height from the current viewport width."""

    def initStyleOption(self, option: QStyleOptionViewItem, index) -> None:  # noqa: N802
        super().initStyleOption(option, index)
        option.features |= QStyleOptionViewItem.ViewItemFeature.WrapText
        option.textElideMode = Qt.TextElideMode.ElideNone
        if bool(index.data(_READ_ROLE)):
            text_color = option.palette.color(QPalette.ColorRole.Text)
            background_color = option.palette.color(QPalette.ColorRole.Base)
            option.palette.setColor(
                QPalette.ColorRole.Text,
                _blend_color(text_color, background_color, 0.52),
            )
            option.font.setWeight(QFont.Weight.Normal)
        else:
            option.font.setWeight(QFont.Weight.DemiBold)

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
    search_scope_changed = Signal(str)
    mark_read_requested = Signal(int, bool)
    star_requested = Signal(int)
    delete_requested = Signal(int)
    add_to_collection_requested = Signal(int)
    export_markdown_requested = Signal(int)
    manage_tags_requested = Signal(int)
    generate_tags_requested = Signal(int)
    batch_mark_read_requested = Signal(list, bool)
    batch_star_requested = Signal(list)
    batch_delete_requested = Signal(list)
    batch_export_digest_requested = Signal(list)
    VALID_STATES = frozenset({"empty", "loading", "content", "error", "offline", "disabled"})

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ContentSurface")
        self.setMinimumWidth(300)
        self.heading = QLabel(self.tr("文章"))
        self.heading.setObjectName("SectionTitle")
        self.batch_button = QPushButton()
        self.batch_button.setObjectName("EntryHeaderIconButton")
        self.batch_button.setIcon(batch_icon())
        self.batch_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.batch_button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.batch_button.setAccessibleName(self.tr("批量管理文章"))
        self.batch_button.setToolTip(self.tr("批量管理文章"))
        enable_immediate_tooltip(self.batch_button)

        heading_row = QHBoxLayout()
        heading_row.setContentsMargins(0, 0, 0, 0)
        heading_row.addWidget(self.heading)
        heading_row.addStretch()
        heading_row.addWidget(self.batch_button)

        self.batch_toolbar = QWidget()
        self.batch_toolbar.setObjectName("EntryBatchToolbar")
        self.batch_count = QLabel(self.tr("已选择 0 篇"))
        self.batch_count.setObjectName("BatchCountLabel")
        self.batch_close_button = self._batch_action_button(
            close_icon(), self.tr("退出批量管理"), self.tr("退出批量管理")
        )
        batch_layout = QHBoxLayout(self.batch_toolbar)
        batch_layout.setContentsMargins(8, 6, 8, 6)
        batch_layout.setSpacing(4)
        batch_layout.addWidget(self.batch_count)
        batch_layout.addStretch()
        batch_layout.addWidget(self.batch_close_button)
        self.batch_toolbar.hide()
        self._batch_mode = False
        self.loading_banner = QLabel(self.tr("正在加载文章…"))
        self.loading_banner.setObjectName("LoadingBanner")
        self.loading_banner.hide()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("搜索当前订阅源"))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setAccessibleName(self.tr("搜索当前订阅源的文章"))
        self.search_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.search_scope = QComboBox()
        self.search_scope.setObjectName("SearchScopeSelector")
        self.search_scope.addItem(self.tr("当前"), "feed")
        self.search_scope.addItem(self.tr("全部"), "all")
        self.search_scope.setFixedWidth(76)
        self.search_scope.setAccessibleName(self.tr("文章搜索范围"))
        self.search_scope.setToolTip(self.tr("选择在当前订阅或全部订阅中搜索"))
        self.search_controls = QWidget()
        search_layout = QHBoxLayout(self.search_controls)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(6)
        search_layout.addWidget(self.search_edit, 1)
        search_layout.addWidget(self.search_scope)

        self.stack = QStackedWidget()
        self.entry_list = WrappingListWidget()
        self.entry_list.setAccessibleName(self.tr("文章列表"))
        self.entry_list.setWordWrap(True)
        self.entry_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.entry_list.setUniformItemSizes(False)
        self.entry_list.setItemDelegate(WrappingItemDelegate(self.entry_list))
        self.entry_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
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
        layout.setContentsMargins(18, 6, 12, 12)
        layout.setSpacing(12)
        layout.addLayout(heading_row)
        layout.addWidget(self.batch_toolbar)
        layout.addWidget(self.search_controls)
        layout.addWidget(self.loading_banner)
        layout.addWidget(self.stack, 1)
        self.entry_list.currentItemChanged.connect(self._on_current_item_changed)
        self.entry_list.itemSelectionChanged.connect(self._update_batch_actions)
        self.entry_list.customContextMenuRequested.connect(self._show_context_menu)
        self.search_edit.returnPressed.connect(self._emit_search)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_edit.customContextMenuRequested.connect(self._show_search_context_menu)
        self.search_scope.currentIndexChanged.connect(self._on_search_scope_changed)
        self.batch_button.clicked.connect(lambda: self.set_batch_mode(not self._batch_mode))
        self.batch_close_button.clicked.connect(lambda: self.set_batch_mode(False))
        self.set_state("disabled")

    def _batch_action_button(self, icon, accessible_name: str, tooltip: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("BatchActionButton")
        button.setIcon(icon)
        button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        button.setAccessibleName(accessible_name)
        button.setToolTip(tooltip)
        enable_immediate_tooltip(button)
        return button

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
        selected_id = self.current_entry_id()
        with QSignalBlocker(self.entry_list):
            self.entry_list.clear()
            for entry in entries:
                state_label = self.tr("已读") if entry.is_read else self.tr("未读")
                star_prefix = self.tr("★ ") if entry.is_starred else ""
                meta = " · ".join(part for part in (entry.author, entry.published_at or "") if part)
                visible_text = f"{star_prefix}{entry.title}"
                if meta:
                    visible_text += f"\n{meta}"
                item = QListWidgetItem(visible_text)
                item.setData(Qt.ItemDataRole.UserRole, entry.id)
                item.setData(_READ_ROLE, entry.is_read)
                item.setData(_STARRED_ROLE, entry.is_starred)
                accessible_state = self.tr("{0}：{1}").format(state_label, entry.title)
                if entry.is_starred:
                    accessible_state += self.tr("，已收藏")
                item.setData(Qt.ItemDataRole.AccessibleTextRole, accessible_state)
                item.setToolTip(self.tr("{0} · {1}").format(state_label, entry.title))
                self.entry_list.addItem(item)
                if entry.id == selected_id:
                    self.entry_list.setCurrentItem(item)
        self._update_batch_actions()
        self.set_state("content" if entries else "empty")

    def current_entry_id(self) -> int | None:
        item = self.entry_list.currentItem()
        return int(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    def selected_entry_ids(self) -> list[int]:
        return [
            int(item.data(Qt.ItemDataRole.UserRole)) for item in self.entry_list.selectedItems()
        ]

    def set_batch_mode(self, enabled: bool) -> None:
        self._batch_mode = enabled
        self.entry_list.clearSelection()
        self.entry_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
            if enabled
            else QAbstractItemView.SelectionMode.SingleSelection
        )
        self.batch_toolbar.setVisible(enabled)
        self.batch_button.setVisible(not enabled)
        self.search_controls.setVisible(not enabled)
        self.entry_list.setAccessibleName(
            self.tr("批量选择文章") if enabled else self.tr("文章列表")
        )
        self._update_batch_actions()

    def _update_batch_actions(self) -> None:
        count = len(self.entry_list.selectedItems()) if self._batch_mode else 0
        self.batch_count.setText(self.tr("已选择 {0} 篇").format(count))

    def _emit_search(self) -> None:
        self.search_requested.emit(self.search_edit.text().strip())

    def _on_search_text_changed(self, text: str) -> None:
        if not text:
            self.search_requested.emit("")

    def _create_search_context_menu(self) -> QMenu:
        menu = QMenu(self.search_edit)
        copy_action = menu.addAction(self.tr("复制"), self.search_edit.copy)
        paste_action = menu.addAction(self.tr("粘贴"), self.search_edit.paste)

        has_selection = self.search_edit.hasSelectedText()
        copy_action.setEnabled(has_selection)
        paste_action.setEnabled(QApplication.clipboard().mimeData().hasText())
        return menu

    def _show_search_context_menu(self, position) -> None:
        menu = self._create_search_context_menu()
        menu.exec(self.search_edit.mapToGlobal(position))

    def _on_search_scope_changed(self, _index: int) -> None:
        scope = str(self.search_scope.currentData())
        self._apply_search_scope(scope)
        self.search_scope_changed.emit(scope)

    def set_search_scope(self, scope: str, *, notify: bool = True) -> None:
        normalized = scope if scope in {"feed", "all"} else "feed"
        index = self.search_scope.findData(normalized)
        with QSignalBlocker(self.search_scope):
            self.search_scope.setCurrentIndex(max(0, index))
        self._apply_search_scope(normalized)
        if notify:
            self.search_scope_changed.emit(normalized)

    def _apply_search_scope(self, scope: str) -> None:
        is_global = scope == "all"
        self.heading.setText(self.tr("全部文章") if is_global else self.tr("文章"))
        self.search_edit.setPlaceholderText(
            self.tr("搜索全部订阅") if is_global else self.tr("搜索当前订阅源")
        )
        self.search_edit.setAccessibleName(
            self.tr("搜索全部订阅的文章")
            if is_global
            else self.tr("搜索当前订阅源的文章")
        )

    def _show_context_menu(self, position) -> None:
        item = self.entry_list.itemAt(position)
        if item is None:
            return
        if self._batch_mode:
            if not item.isSelected():
                self.entry_list.clearSelection()
                item.setSelected(True)
            menu = self._create_batch_context_menu()
            menu.exec(self.entry_list.viewport().mapToGlobal(position))
            return
        menu = QMenu(self)
        is_read = bool(item.data(_READ_ROLE))
        is_starred = bool(item.data(_STARRED_ROLE))
        read_action = menu.addAction(self.tr("标记未读") if is_read else self.tr("标记已读"))
        star_action = menu.addAction(self.tr("取消收藏") if is_starred else self.tr("收藏"))
        collection_action = menu.addAction(self.tr("添加到收藏夹…"))
        tags_action = menu.addAction(self.tr("管理标签…"))
        ai_tags_action = menu.addAction(self.tr("AI 生成标签"))
        export_action = menu.addAction(self.tr("导出 Markdown…"))
        menu.addSeparator()
        delete_action = menu.addAction(self.tr("删除"))
        read_action.triggered.connect(lambda: self._emit_read_for_item(item, not is_read))
        star_action.triggered.connect(lambda: self._emit_star_for_item(item))
        collection_action.triggered.connect(
            lambda: self._emit_add_to_collection_for_item(item)
        )
        tags_action.triggered.connect(lambda: self._emit_manage_tags_for_item(item))
        ai_tags_action.triggered.connect(
            lambda: self._emit_generate_tags_for_item(item)
        )
        export_action.triggered.connect(
            lambda: self._emit_export_markdown_for_item(item)
        )
        delete_action.triggered.connect(lambda: self._emit_delete_for_item(item))
        menu.exec(self.entry_list.viewport().mapToGlobal(position))

    def _create_batch_context_menu(self) -> QMenu:
        menu = QMenu(self)
        read_action = menu.addAction(self.tr("标记已读"))
        unread_action = menu.addAction(self.tr("标记未读"))
        star_action = menu.addAction(self.tr("切换收藏"))
        export_action = menu.addAction(self.tr("导出 Digest…"))
        delete_action = menu.addAction(self.tr("删除选中文章"))
        has_selection = bool(self.selected_entry_ids())
        for action in menu.actions():
            action.setEnabled(has_selection)
        read_action.triggered.connect(
            lambda _checked=False: self.batch_mark_read_requested.emit(
                self.selected_entry_ids(), True
            )
        )
        unread_action.triggered.connect(
            lambda _checked=False: self.batch_mark_read_requested.emit(
                self.selected_entry_ids(), False
            )
        )
        star_action.triggered.connect(
            lambda _checked=False: self.batch_star_requested.emit(self.selected_entry_ids())
        )
        export_action.triggered.connect(
            lambda _checked=False: self._emit_batch_export()
        )
        delete_action.triggered.connect(
            lambda _checked=False: self.batch_delete_requested.emit(self.selected_entry_ids())
        )
        return menu

    def _emit_read_for_item(self, item: QListWidgetItem, read: bool) -> None:
        self.mark_read_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)), read)

    def _emit_star_for_item(self, item: QListWidgetItem) -> None:
        self.star_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _emit_delete_for_item(self, item: QListWidgetItem) -> None:
        self.delete_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _emit_add_to_collection_for_item(self, item: QListWidgetItem) -> None:
        self.add_to_collection_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _emit_export_markdown_for_item(self, item: QListWidgetItem) -> None:
        self.export_markdown_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _emit_manage_tags_for_item(self, item: QListWidgetItem) -> None:
        self.manage_tags_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _emit_generate_tags_for_item(self, item: QListWidgetItem) -> None:
        self.generate_tags_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _emit_batch_export(self) -> None:
        entry_ids = self.selected_entry_ids()
        if entry_ids:
            self.batch_export_digest_requested.emit(entry_ids)

    def _on_current_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is not None:
            if self._batch_mode:
                return
            self.entry_selected.emit(int(current.data(Qt.ItemDataRole.UserRole)))
