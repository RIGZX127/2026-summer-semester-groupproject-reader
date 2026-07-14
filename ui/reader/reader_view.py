"""Safe Phase 1 Reader container."""
from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from store.entry_store import EntryRow


class ReaderView(QWidget):
    retry_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ContentSurface")
        self.setMinimumWidth(380)
        self.last_html = ""
        self.stack = QStackedWidget()
        self.empty_page = QWidget()
        self.empty_label = QLabel(self.tr("选择一篇文章，开始安静阅读"))
        self.empty_label.setObjectName("StateTitle")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_hint = QLabel(self.tr("文章内容将在这里显示。"))
        empty_hint.setObjectName("StateMessage")
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_box = QVBoxLayout(self.empty_page)
        empty_box.addStretch()
        empty_box.addWidget(self.empty_label)
        empty_box.addWidget(empty_hint)
        empty_box.addStretch()

        self.loading_page = self._message_page(self.tr("正在准备文章…"), self.tr("请稍候，窗口仍可继续操作。"))
        self.error_page = self._message_page(self.tr("暂时无法显示文章"), self.tr("请检查网络后重试。"), True)
        self.web_view = QWebEngineView()
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            False,
        )
        for page in (self.empty_page, self.loading_page, self.error_page, self.web_view):
            self.stack.addWidget(page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.show_empty()

    def _message_page(self, title: str, message: str, retry: bool = False) -> QWidget:
        page = QWidget()
        title_label = QLabel(title)
        title_label.setObjectName("StateTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label = QLabel(message)
        message_label.setObjectName("StateMessage")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

    def show_empty(self) -> None:
        self.stack.setCurrentWidget(self.empty_page)

    def show_loading(self) -> None:
        self.stack.setCurrentWidget(self.loading_page)

    def show_entry(self, entry: EntryRow) -> None:
        title = html.escape(entry.title or self.tr("无标题"))
        author = html.escape(entry.author or self.tr("未知作者"))
        date = html.escape(entry.published_at or "")
        summary = html.escape(entry.summary or self.tr("该 Feed 没有提供摘要。"))
        self.last_html = f"""<!doctype html><html><head><meta charset=\"utf-8\"><style>
        body {{ margin: 0 auto; padding: 56px 48px; max-width: 760px; color: #26343F;
        background: #FCFBF8; font: 16px/1.72 system-ui, sans-serif; }}
        h1 {{ font-size: 31px; line-height: 1.24; letter-spacing: -0.3px; }}
        .meta {{ color: #71808B; margin: 12px 0 32px; }}
        .summary {{ white-space: pre-wrap; }}
        </style></head><body><h1>{title}</h1><div class=\"meta\">{author} · {date}</div>
        <div class=\"summary\">{summary}</div></body></html>"""
        self.web_view.setHtml(self.last_html)
        self.stack.setCurrentWidget(self.web_view)

    def show_error(self, message: str) -> None:
        labels = self.error_page.findChildren(QLabel)
        if len(labels) > 1:
            labels[1].setText(message)
        self.stack.setCurrentWidget(self.error_page)
