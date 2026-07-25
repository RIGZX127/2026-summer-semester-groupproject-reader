"""OPML import preview dialog — select feeds before importing."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class OPMLImportDialog(QDialog):
    """Select an OPML file, preview detected feeds, choose which to import.

    Usage::

        dialog = OPMLImportDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            urls = dialog.selected_urls()
            titles = dialog.selected_titles()
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("导入 OPML"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setModal(True)

        self._feed_urls: list[str] = []
        self._feed_titles: list[str] = []

        # ── File selector ──────────────────────────────────────────────
        title = QLabel(self.tr("从 OPML 文件导入订阅源"))
        title.setObjectName("SectionTitle")
        hint = QLabel(self.tr("选择 OPML 文件后，可勾选要导入的订阅源。"))
        hint.setObjectName("MutedLabel")

        self._path_label = QLabel(self.tr("未选择文件"))
        self._path_label.setWordWrap(True)
        browse_btn = QPushButton(self.tr("浏览"))
        browse_btn.setMinimumWidth(80)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        file_row.addWidget(self._path_label, 1)
        file_row.addWidget(browse_btn)

        # ── Feed list ──────────────────────────────────────────────────
        list_label = QLabel(self.tr("检测到的订阅源"))
        self._list = QListWidget()
        self._list.setAccessibleName(self.tr("订阅源列表"))

        self._select_all_btn = QPushButton(self.tr("全选"))
        self._deselect_all_btn = QPushButton(self.tr("取消全选"))
        select_row = QHBoxLayout()
        select_row.setSpacing(6)
        select_row.addWidget(self._select_all_btn)
        select_row.addWidget(self._deselect_all_btn)
        select_row.addStretch()

        # ── Buttons ────────────────────────────────────────────────────
        self._cancel_btn = QPushButton(self.tr("取消"))
        self._import_btn = QPushButton(self.tr("导入选中"))
        self._import_btn.setObjectName("PrimaryButton")
        self._import_btn.setDefault(True)
        self._import_btn.setEnabled(False)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._import_btn)

        # ── Main layout ────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(file_row)
        layout.addWidget(list_label)
        layout.addWidget(self._list, 1)
        layout.addLayout(select_row)
        layout.addSpacing(8)
        layout.addLayout(btn_row)

        # ── Connections ────────────────────────────────────────────────
        self._cancel_btn.clicked.connect(self.reject)
        self._import_btn.clicked.connect(self.accept)
        browse_btn.clicked.connect(self._browse)
        self._select_all_btn.clicked.connect(self._select_all)
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        self._list.itemChanged.connect(self._validate)

    # ── Public API ─────────────────────────────────────────────────────────

    def selected_urls(self) -> list[str]:
        """Return URLs of the checked feeds."""
        return [
            self._feed_urls[i]
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.CheckState.Checked
        ]

    def selected_titles(self) -> list[str]:
        """Return titles of the checked feeds (same order as selected_urls)."""
        return [
            self._feed_titles[i]
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.CheckState.Checked
        ]

    # ── Internal ───────────────────────────────────────────────────────────

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("选择 OPML 文件"),
            "",
            self.tr("OPML 文件 (*.opml *.xml);;所有文件 (*.*)"),
        )
        if not path:
            return
        self._path_label.setText(path)
        self._parse_file(path)

    def _parse_file(self, path: str) -> None:
        from core.feed.opml import import_opml

        try:
            with open(path, "r", encoding="utf-8") as fh:
                feeds = import_opml(fh.read())
        except Exception:
            self._list.clear()
            self._list.addItem(self.tr("无法解析 OPML 文件。"))
            self._import_btn.setEnabled(False)
            return

        self._feed_urls = []
        self._feed_titles = []
        self._list.clear()

        for feed_url in feeds:
            item = QListWidgetItem()
            item.setText(feed_url.title or feed_url.url)
            item.setToolTip(feed_url.url)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self._list.addItem(item)
            self._feed_urls.append(feed_url.url)
            self._feed_titles.append(feed_url.title or feed_url.url)

        self._validate()

    def _select_all(self) -> None:
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _validate(self) -> None:
        has_checked = any(
            self._list.item(i).checkState() == Qt.CheckState.Checked
            for i in range(self._list.count())
        )
        self._import_btn.setEnabled(has_checked)
