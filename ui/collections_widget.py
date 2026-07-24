"""Collection navigation for the sidebar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.icons import COMPACT_CONTROL_SIZE, COMPACT_ICON_SIZE, add_icon
from ui.tooltips import enable_immediate_tooltip

if TYPE_CHECKING:
    from store.collection_store import CollectionRow


class CollectionsWidget(QWidget):
    """Display collections and emit management intentions."""

    collection_selected = Signal(int)
    create_requested = Signal(str)
    rename_requested = Signal(int, str)
    delete_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.heading = QLabel(self.tr("收藏夹"))
        self.heading.setObjectName("SidebarSection")
        self.add_button = QPushButton()
        self.add_button.setIcon(add_icon())
        self.add_button.setIconSize(QSize(COMPACT_ICON_SIZE, COMPACT_ICON_SIZE))
        self.add_button.setFixedSize(COMPACT_CONTROL_SIZE, COMPACT_CONTROL_SIZE)
        self.add_button.setToolTip(self.tr("新建收藏夹"))
        self.add_button.setAccessibleName(self.tr("新建收藏夹"))
        enable_immediate_tooltip(self.add_button)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self.heading)
        header.addStretch()
        header.addWidget(self.add_button)

        self.collection_list = QListWidget()
        self.collection_list.setAccessibleName(self.tr("收藏夹列表"))
        self.collection_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.menu = QMenu(self)
        self.rename_action = self.menu.addAction(self.tr("重命名收藏夹"))
        self.delete_action = self.menu.addAction(self.tr("删除收藏夹"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self.collection_list)

        self.add_button.clicked.connect(self._request_create)
        self.collection_list.currentItemChanged.connect(self._on_current_item_changed)
        self.collection_list.customContextMenuRequested.connect(self._show_menu)
        self.rename_action.triggered.connect(self._request_rename)
        self.delete_action.triggered.connect(self._request_delete)

    def set_collections(self, rows: list[CollectionRow]) -> None:
        selected_id = self.current_collection_id()
        self.collection_list.clear()
        restore_row = -1
        for row in rows:
            text = row.name + (self.tr("（默认）") if row.is_default else "")
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, row.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, row.name)
            item.setToolTip(row.description or row.name)
            self.collection_list.addItem(item)
            if row.id == selected_id:
                restore_row = self.collection_list.count() - 1
        if restore_row >= 0:
            self.collection_list.setCurrentRow(restore_row)

    def current_collection_id(self) -> int | None:
        item = self.collection_list.currentItem()
        return int(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    def _on_current_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is not None:
            self.collection_selected.emit(
                int(current.data(Qt.ItemDataRole.UserRole))
            )

    def _request_create(self) -> None:
        name, accepted = QInputDialog.getText(
            self, self.tr("新建收藏夹"), self.tr("收藏夹名称")
        )
        name = name.strip()
        if accepted and name:
            self.create_requested.emit(name)

    def _show_menu(self, position) -> None:
        item = self.collection_list.itemAt(position)
        if item is None:
            return
        self.collection_list.setCurrentItem(item)
        self.menu.popup(self.collection_list.viewport().mapToGlobal(position))

    def _request_rename(self) -> None:
        item = self.collection_list.currentItem()
        if item is None:
            return
        collection_id = int(item.data(Qt.ItemDataRole.UserRole))
        old_name = str(item.data(Qt.ItemDataRole.UserRole + 1))
        name, accepted = QInputDialog.getText(
            self,
            self.tr("重命名收藏夹"),
            self.tr("收藏夹名称"),
            QLineEdit.EchoMode.Normal,
            old_name,
        )
        name = name.strip()
        if accepted and name and name != old_name:
            self.rename_requested.emit(collection_id, name)

    def _request_delete(self) -> None:
        collection_id = self.current_collection_id()
        if collection_id is not None:
            self.delete_requested.emit(collection_id)
