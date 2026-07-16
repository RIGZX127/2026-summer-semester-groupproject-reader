"""Reader, original web page, and split-mode container."""

from __future__ import annotations

import html

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLabel, QPushButton, QSplitter, QStackedWidget, QVBoxLayout, QWidget

from store.entry_store import EntryRow
from ui.reader.reader_toolbar import ReaderToolbar
from ui.reader.theme_manager import ThemeManager
from ui.theme_controller import ThemeController


class ExternalLinkPage(QWebEnginePage):
    """Open user-clicked Reader links in the system browser."""

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):  # noqa: N802
        if navigation_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)


class ReaderView(QWidget):
    retry_requested = Signal()
    VALID_MODES = frozenset({"reader", "web", "split"})

    def __init__(
        self,
        parent: QWidget | None = None,
        settings: QSettings | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ContentSurface")
        self.setMinimumWidth(380)
        self.app_theme_controller = ThemeController(settings, parent=self)
        self.theme_manager = ThemeManager(settings, self.app_theme_controller.palette)
        self.theme_manager.set_palette(
            self.app_theme_controller.palette,
            self.app_theme_controller.effective_theme,
        )
        self.toolbar = ReaderToolbar(self.theme_manager.theme)
        self.toolbar.set_theme_preference(self.app_theme_controller.preference)
        self.current_mode = "reader"
        self.current_url: str | None = None
        self.last_html = ""

        self.stack = QStackedWidget()
        self.empty_page = self._message_page(
            self.tr("选择一篇文章，开始安静阅读"), self.tr("文章内容将在这里显示。")
        )
        self.empty_label = self.empty_page.findChildren(QLabel)[0]
        self.loading_page = self._message_page(
            self.tr("正在准备文章…"), self.tr("请稍候，窗口仍可继续操作。")
        )
        self.error_page = self._message_page(
            self.tr("暂时无法显示文章"), self.tr("请检查网络后重试。"), True
        )

        self.reader_web_view = QWebEngineView()
        self.web_view = self.reader_web_view  # Phase 1 compatibility
        self.reader_web_view.setPage(ExternalLinkPage(self.reader_web_view))
        reader_settings = self.reader_web_view.settings()
        reader_settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, False)
        reader_settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False
        )
        reader_settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )

        self.original_web_view = QWebEngineView()
        self.no_url_page = self._message_page(
            self.tr("无法打开原网页"), self.tr("该文章没有提供原文链接。")
        )
        self.web_stack = QStackedWidget()
        self.web_stack.addWidget(self.no_url_page)
        self.web_stack.addWidget(self.original_web_view)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.reader_web_view)
        self.splitter.addWidget(self.web_stack)
        self.splitter.setSizes([600, 600])

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.splitter)
        for page in (self.empty_page, self.loading_page, self.error_page, self.content_stack):
            self.stack.addWidget(page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.stack, 1)

        self.toolbar.mode_changed.connect(self.set_mode)
        self.toolbar.font_size_changed.connect(self._set_font_size)
        self.toolbar.theme_preference_changed.connect(self.app_theme_controller.set_preference)
        self.app_theme_controller.theme_changed.connect(self._on_app_theme_changed)
        self.toolbar.content_width_changed.connect(self._set_content_width)
        self.show_empty()
        QTimer.singleShot(0, self.app_theme_controller.apply)

    def _message_page(self, title: str, message: str, retry: bool = False) -> QWidget:
        page = QWidget()
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

    def show_empty(self) -> None:
        self.stack.setCurrentWidget(self.empty_page)

    def show_loading(self) -> None:
        self.stack.setCurrentWidget(self.loading_page)

    def show_content(self, rendered_html: str, url: str | None) -> None:
        self.current_url = url
        self.last_html = self.theme_manager.wrap_html(rendered_html)
        self.reader_web_view.setHtml(self.last_html)
        if url:
            self.original_web_view.setUrl(QUrl(url))
            self.web_stack.setCurrentWidget(self.original_web_view)
        else:
            self.web_stack.setCurrentWidget(self.no_url_page)
        self._apply_mode()
        self.stack.setCurrentWidget(self.content_stack)

    def show_entry(self, entry: EntryRow) -> None:
        title = html.escape(entry.title or self.tr("无标题"))
        author = html.escape(entry.author or self.tr("未知作者"))
        date = html.escape(entry.published_at or "")
        summary = html.escape(entry.summary or self.tr("该 Feed 没有提供摘要。"))
        self.show_content(
            f'<h1>{title}</h1><div class="meta">{author} · {date}</div>'
            f'<div class="summary"><p>{summary}</p></div>',
            entry.url,
        )

    def show_fallback(self, entry: EntryRow, message: str) -> None:
        safe_message = html.escape(message)
        safe_title = html.escape(entry.title or self.tr("无标题"))
        safe_summary = html.escape(entry.summary or self.tr("该 Feed 没有提供摘要。"))
        self.show_content(
            f'<p role="alert"><strong>{safe_message}</strong></p>'
            f"<h1>{safe_title}</h1><p>{safe_summary}</p>",
            entry.url,
        )

    def show_web_fallback(self, entry: EntryRow) -> None:
        """httpx 被网站拦截时，降级到 QWebEngineView 直显原网页。"""
        if not entry.url:
            self.show_fallback(
                entry,
                self.tr("Reader 模式不可用且该文章无原文链接。"),
            )
            return
        self.current_url = entry.url
        self.last_html = ""
        self.original_web_view.setUrl(QUrl(entry.url))
        self.web_stack.setCurrentWidget(self.original_web_view)
        self.current_mode = "web"
        self._apply_mode()
        self.stack.setCurrentWidget(self.content_stack)

    def show_error(self, message: str) -> None:
        labels = self.error_page.findChildren(QLabel)
        if len(labels) > 1:
            labels[1].setText(message)
        self.stack.setCurrentWidget(self.error_page)

    def set_mode(self, mode: str) -> None:
        if mode not in self.VALID_MODES:
            raise ValueError(f"Unknown Reader mode: {mode}")
        self.current_mode = mode
        self._apply_mode()

    def _apply_mode(self) -> None:
        self.reader_web_view.setVisible(self.current_mode in {"reader", "split"})
        self.web_stack.setVisible(self.current_mode in {"web", "split"})
        if self.current_mode == "reader":
            self.splitter.setSizes([1, 0])
        elif self.current_mode == "web":
            self.splitter.setSizes([0, 1])
        else:
            self.splitter.setSizes([1, 1])
        self.content_stack.setCurrentWidget(self.splitter)

    def _rerender_reader(self) -> None:
        if not self.last_html:
            return
        body_start = self.last_html.find("<body>")
        body_end = self.last_html.rfind("</body>")
        fragment = self.last_html[body_start + 6 : body_end] if body_start >= 0 else self.last_html
        self.last_html = self.theme_manager.wrap_html(fragment)
        self.reader_web_view.setHtml(self.last_html)

    def _set_font_size(self, value: int) -> None:
        self.theme_manager.set_font_size(value)
        self._rerender_reader()

    def _on_app_theme_changed(self, value: str) -> None:
        self.theme_manager.set_palette(self.app_theme_controller.palette, value)
        self.toolbar.set_theme_preference(self.app_theme_controller.preference)
        self._rerender_reader()

    def _set_content_width(self, value: int) -> None:
        self.theme_manager.set_content_width(value)
        self._rerender_reader()
