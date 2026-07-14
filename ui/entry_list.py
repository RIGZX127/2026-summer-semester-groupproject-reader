"""Article list with explicit page states."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from store.entry_store import EntryListItem


class EntryListWidget(QWidget):
    entry_selected = Signal(int)
    retry_requested = Signal()
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

        self.stack = QStackedWidget()
        self.entry_list = QListWidget()
        self.entry_list.setAccessibleName(self.tr("文章列表"))
        self.entry_list.setTextElideMode(Qt.TextElideMode.ElideRight)
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
        layout.addWidget(self.loading_banner)
        layout.addWidget(self.stack, 1)
        self.entry_list.currentItemChanged.connect(self._on_current_item_changed)
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
        self.entry_list.clear()
        for entry in entries:
            unread = "● " if not entry.is_read else ""
            starred = "  ☆" if entry.is_starred else ""
            meta = " · ".join(part for part in (entry.author, entry.published_at or "") if part)
            item = QListWidgetItem(f"{unread}{entry.title}{starred}\n{meta}")
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            item.setToolTip(entry.title)
            self.entry_list.addItem(item)
        self.set_state("content" if entries else "empty")

    def _on_current_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is not None:
            self.entry_selected.emit(int(current.data(Qt.ItemDataRole.UserRole)))
