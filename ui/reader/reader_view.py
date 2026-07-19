"""Reader, original web page, split mode, and Phase 3 Agent surfaces."""

from __future__ import annotations

import html
import json

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLabel, QPushButton, QSplitter, QStackedWidget, QVBoxLayout, QWidget

from store.entry_store import EntryRow
from ui.reader.reader_toolbar import ReaderToolbar
from ui.reader.summary_panel import SummaryPanel
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
        agent_runtime: object | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ContentSurface")
        self.setMinimumWidth(380)
        self._settings = settings or QSettings()
        self._agent_runtime = agent_runtime
        self.app_theme_controller = ThemeController(self._settings, parent=self)
        self.theme_manager = ThemeManager(self._settings, self.app_theme_controller.palette)
        self.theme_manager.set_palette(
            self.app_theme_controller.palette, self.app_theme_controller.effective_theme
        )
        self.toolbar = ReaderToolbar(self.theme_manager.theme)
        self.toolbar.set_theme_preference(self.app_theme_controller.preference)
        self.summary_panel = SummaryPanel(runtime=agent_runtime, parent=self, settings=self._settings)
        self.current_mode = "reader"
        self.current_url: str | None = None
        self.last_html = ""
        self._original_fragment = ""
        self._bilingual_fragment = ""
        self._translated_fragment = ""
        self._translation_mode = "original"
        self._active_translation_run_id: str | None = None
        self._current_entry_id: int | None = None

        self._auto_summary_timer = QTimer(self)
        self._auto_summary_timer.setSingleShot(True)
        self._auto_summary_timer.setInterval(1000)
        self._auto_summary_timer.timeout.connect(self._trigger_auto_summary)

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
        self.web_view = self.reader_web_view
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
        self.reader_splitter = QSplitter(Qt.Orientation.Vertical)
        self.reader_splitter.setObjectName("ReaderSummarySplitter")
        self.reader_splitter.setChildrenCollapsible(False)
        self.reader_splitter.addWidget(self.stack)
        self.reader_splitter.addWidget(self.summary_panel)
        self.reader_splitter.setStretchFactor(0, 1)
        self.reader_splitter.setStretchFactor(1, 0)
        layout.addWidget(self.reader_splitter, 1)

        self.toolbar.mode_changed.connect(self.set_mode)
        self.toolbar.font_size_changed.connect(self._set_font_size)
        self.toolbar.theme_preference_changed.connect(self.app_theme_controller.set_preference)
        self.app_theme_controller.theme_changed.connect(self._on_app_theme_changed)
        self.toolbar.content_width_changed.connect(self._set_content_width)
        self.toolbar.translation_requested.connect(self._request_translation)
        self.toolbar.translation_cancel_requested.connect(self._cancel_translation)
        self.toolbar.translation_mode_changed.connect(self.set_translation_mode)
        self.summary_panel.expanded_changed.connect(self._on_summary_expanded)
        if self._agent_runtime is not None:
            self._agent_runtime.signals.state_changed.connect(self._on_agent_state_changed)
            self._agent_runtime.signals.chunk_received.connect(self._on_agent_chunk)
        self.show_empty()
        splitter_state = self._settings.value("ui/reader/vertical_splitter")
        if splitter_state is not None:
            self.reader_splitter.restoreState(splitter_state)
        else:
            self.reader_splitter.setSizes([720, 48])
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
        self._auto_summary_timer.stop()
        self.toolbar.set_article_available(False)
        self.stack.setCurrentWidget(self.empty_page)

    def show_loading(self) -> None:
        self._auto_summary_timer.stop()
        self.stack.setCurrentWidget(self.loading_page)

    def show_content(
        self, rendered_html: str, url: str | None, entry_id: int | None = None
    ) -> None:
        self.current_url = url
        self._original_fragment = rendered_html
        self._bilingual_fragment = ""
        self._translated_fragment = ""
        self._translation_mode = "original"
        self.last_html = self.theme_manager.wrap_html(rendered_html)
        self.reader_web_view.setHtml(self.last_html)
        if url:
            self.original_web_view.setUrl(QUrl(url))
            self.web_stack.setCurrentWidget(self.original_web_view)
        else:
            self.web_stack.setCurrentWidget(self.no_url_page)
        self._apply_mode()
        self.stack.setCurrentWidget(self.content_stack)
        if entry_id is not None:
            self._current_entry_id = entry_id
            self._active_translation_run_id = None
            self.summary_panel.set_entry(entry_id)
            self.toolbar.set_translation_state("idle")
            self.toolbar.show_translation_modes(False)
            self.toolbar.set_article_available(True)
            self._schedule_auto_summary()

    def show_entry(self, entry: EntryRow) -> None:
        title = html.escape(entry.title or self.tr("无标题"))
        author = html.escape(entry.author or self.tr("未知作者"))
        date = html.escape(entry.published_at or "")
        summary = html.escape(entry.summary or self.tr("该 Feed 没有提供摘要。"))
        self.show_content(
            f'<h1>{title}</h1><div class="meta">{author} · {date}</div>'
            f'<div class="summary"><p>{summary}</p></div>',
            entry.url,
            entry.id,
        )

    def show_fallback(self, entry: EntryRow, message: str) -> None:
        safe_message = html.escape(message)
        safe_title = html.escape(entry.title or self.tr("无标题"))
        safe_summary = html.escape(entry.summary or self.tr("该 Feed 没有提供摘要。"))
        self.show_content(
            f'<p role="alert"><strong>{safe_message}</strong></p>'
            f"<h1>{safe_title}</h1><p>{safe_summary}</p>",
            entry.url,
            entry.id,
        )

    def show_web_fallback(self, entry: EntryRow) -> None:
        if not entry.url:
            self.show_fallback(entry, self.tr("Reader 模式不可用且该文章无原文链接。"))
            return
        self.current_url = entry.url
        self.last_html = ""
        self.original_web_view.setUrl(QUrl(entry.url))
        self.web_stack.setCurrentWidget(self.original_web_view)
        self.current_mode = "web"
        self._apply_mode()
        self.stack.setCurrentWidget(self.content_stack)
        self._current_entry_id = entry.id
        self.summary_panel.set_entry(entry.id)
        self.toolbar.set_article_available(True)

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
        self.splitter.setSizes(
            [1, 0]
            if self.current_mode == "reader"
            else [0, 1]
            if self.current_mode == "web"
            else [1, 1]
        )
        self.content_stack.setCurrentWidget(self.splitter)

    def _rerender_reader(self) -> None:
        fragment = self._fragment_for_translation_mode()
        if fragment:
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

    @property
    def active_translation_run_id(self) -> str | None:
        return self._active_translation_run_id

    def _schedule_auto_summary(self) -> None:
        self._auto_summary_timer.stop()
        if self._settings.value("agent/auto_summary", False, type=bool):
            self._auto_summary_timer.start()

    def _trigger_auto_summary(self) -> None:
        if self._current_entry_id is not None:
            self.summary_panel.request_auto_generate()

    def _request_translation(self) -> None:
        if self._agent_runtime is None or self._current_entry_id is None:
            self.toolbar.set_translation_state("error")
            return
        try:
            self._active_translation_run_id = self._agent_runtime.submit(
                self._current_entry_id, "translation"
            )
        except Exception:  # noqa: BLE001
            self.toolbar.set_translation_state("error")
            return
        self.toolbar.set_translation_state("queued")

    def _cancel_translation(self) -> None:
        if self._agent_runtime is not None and self._active_translation_run_id:
            self._agent_runtime.cancel(self._active_translation_run_id)

    def _on_agent_state_changed(self, event: object) -> None:
        from core.agent.runtime import AgentUIEvent

        evt: AgentUIEvent = event
        if evt.agent_type != "translation" or evt.entry_id != self._current_entry_id:
            return
        if self._active_translation_run_id is None and evt.status in {"queued", "running"}:
            self._active_translation_run_id = evt.run_id
        if evt.run_id != self._active_translation_run_id:
            return
        self.toolbar.set_translation_state(evt.status, evt.progress)
        if evt.status == "done" and evt.result_json:
            try:
                result = json.loads(evt.result_json)
            except (json.JSONDecodeError, TypeError):
                result = {}
            bilingual = str(result.get("html", ""))
            if bilingual:
                self._set_translation_html(bilingual)

    def _on_agent_chunk(self, event: object) -> None:
        from core.agent.runtime import AgentUIEvent

        evt: AgentUIEvent = event
        if (
            evt.agent_type == "translation"
            and evt.entry_id == self._current_entry_id
            and evt.run_id == self._active_translation_run_id
            and "mercury-trans-block" in evt.chunk
        ):
            self._set_translation_html(evt.chunk)

    def _set_translation_html(self, bilingual_html: str) -> None:
        from bs4 import BeautifulSoup

        self._bilingual_fragment = bilingual_html
        soup = BeautifulSoup(bilingual_html, "html.parser")
        self._translated_fragment = "\n".join(
            str(node) for node in soup.select(".mercury-translated")
        )
        self.toolbar.show_translation_modes(True)
        self.set_translation_mode("bilingual")

    def set_translation_mode(self, mode: str) -> None:
        if mode not in {"original", "bilingual", "translated"}:
            raise ValueError(f"Unknown translation mode: {mode}")
        if mode != "original" and not self._bilingual_fragment:
            return
        self._translation_mode = mode
        self.toolbar.set_translation_mode(mode)
        self._rerender_reader()

    def _fragment_for_translation_mode(self) -> str:
        if self._translation_mode == "bilingual" and self._bilingual_fragment:
            return self._bilingual_fragment
        if self._translation_mode == "translated" and self._translated_fragment:
            return self._translated_fragment
        return self._original_fragment

    def _on_summary_expanded(self, expanded: bool) -> None:
        if not expanded:
            return
        sizes = self.reader_splitter.sizes()
        if len(sizes) == 2 and sizes[1] < 140:
            total = sum(sizes)
            self.reader_splitter.setSizes([max(240, total - 200), 200])

    def save_ui_state(self) -> None:
        self._settings.setValue("ui/reader/vertical_splitter", self.reader_splitter.saveState())
        self._settings.sync()
