"""BulkActionBar: 文章批量操作工具条。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class BulkActionBar(QWidget):
    """选中多篇文章时显示的批量操作工具条。"""

    mark_read_requested = Signal()
    mark_unread_requested = Signal()
    delete_requested = Signal()
    deselect_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BulkActionBar")

        self._count_label = QLabel(self.tr("已选 0 篇"))
        self._count_label.setObjectName("BulkCountLabel")

        self._read_btn = QPushButton(self.tr("全部已读"))
        self._read_btn.setToolTip(self.tr("将所有选中文章标记为已读"))
        self._read_btn.setAccessibleName(self.tr("批量标记已读"))

        self._unread_btn = QPushButton(self.tr("全部未读"))
        self._unread_btn.setToolTip(self.tr("将所有选中文章标记为未读"))
        self._unread_btn.setAccessibleName(self.tr("批量标记未读"))

        self._delete_btn = QPushButton(self.tr("批量删除"))
        self._delete_btn.setObjectName("BulkDeleteButton")
        self._delete_btn.setProperty("buttonRole", "danger")
        self._delete_btn.setToolTip(self.tr("删除所有选中文章"))
        self._delete_btn.setAccessibleName(self.tr("批量删除选中文章"))

        self._deselect_btn = QPushButton(self.tr("取消选择"))
        self._deselect_btn.setToolTip(self.tr("取消当前多选"))
        self._deselect_btn.setAccessibleName(self.tr("取消选择"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)
        layout.addWidget(self._count_label)
        layout.addStretch()
        layout.addWidget(self._read_btn)
        layout.addWidget(self._unread_btn)
        layout.addWidget(self._delete_btn)
        layout.addWidget(self._deselect_btn)

        self._read_btn.clicked.connect(self.mark_read_requested)
        self._unread_btn.clicked.connect(self.mark_unread_requested)
        self._delete_btn.clicked.connect(self.delete_requested)
        self._deselect_btn.clicked.connect(self.deselect_requested)
        self.hide()

    def update_count(self, count: int) -> None:
        self._count_label.setText(self.tr("已选 {0} 篇").format(count))
        self.setVisible(count >= 2)
