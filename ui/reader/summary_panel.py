"""Collapsible AI summary panel with streaming support and line-height control."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from core.agent.runtime import AgentRuntime

_LINE_HEIGHT_PRESETS: dict[str, float] = {
    "compact": 1.4,
    "standard": 1.7,
    "loose": 2.1,
}
_SETTINGS_KEY_LINE_HEIGHT = "ui/summary_panel/line_height_preset"


class SummaryPanel(QFrame):
    """Collapsible panel displaying AI-generated article summary."""

    generate_requested = Signal(int)  # entry_id
    expanded_changed = Signal(bool)

    def __init__(
        self,
        runtime: AgentRuntime | None = None,
        parent: QWidget | None = None,
        settings: QSettings | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SummaryPanel")
        self._runtime = runtime
        self._settings = settings or QSettings()
        self._entry_id: int | None = None
        self._active_run_id: str | None = None
        self._pending_text = ""
        self._collapsed = True
        self._status = "idle"
        saved = self._settings.value(_SETTINGS_KEY_LINE_HEIGHT, "standard")
        self._line_height_preset = str(saved) if str(saved) in _LINE_HEIGHT_PRESETS else "standard"

        self._header = QPushButton(self.tr("▶ AI 摘要"))
        self._header.setObjectName("SummaryHeader")
        self._header.setCheckable(True)
        self._header.setChecked(False)
        self._header.setFlat(True)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.clicked.connect(self._toggle)

        self._status_label = QLabel("")
        self._status_label.setObjectName("SummaryStatus")

        self._line_height_combo = QComboBox()
        self._line_height_combo.setObjectName("SummaryLineHeightCombo")
        self._line_height_combo.setAccessibleName(self.tr("摘要行间距"))
        self._line_height_combo.setToolTip(self.tr("调整摘要文本行间距"))
        self._line_height_combo.addItem(self.tr("紧凑"), "compact")
        self._line_height_combo.addItem(self.tr("标准"), "standard")
        self._line_height_combo.addItem(self.tr("宽松"), "loose")
        index = self._line_height_combo.findData(self._line_height_preset)
        if index >= 0:
            self._line_height_combo.setCurrentIndex(index)
        self._line_height_combo.setProperty("readerControl", True)
        self._line_height_combo.currentIndexChanged.connect(self._on_line_height_changed)

        self._generate_btn = QPushButton(self.tr("生成摘要"))
        self._generate_btn.setObjectName("SummaryGenerateBtn")
        self._generate_btn.setToolTip(self.tr("让 AI 为当前文章生成摘要"))
        self._generate_btn.clicked.connect(self._cancel_or_generate)
        self._generate_btn.hide()

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.addWidget(self._header)
        header_row.addStretch()
        header_row.addWidget(self._status_label)
        header_row.addWidget(self._line_height_combo)
        header_row.addWidget(self._generate_btn)

        self._separator = QFrame()
        self._separator.setFrameShape(QFrame.Shape.HLine)
        self._separator.setFrameShadow(QFrame.Shadow.Sunken)
        self._separator.setObjectName("SummarySeparator")
        self._separator.hide()

        self._body = QWidget()
        self._body.setObjectName("SummaryBody")

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.hide()

        self._content = QTextBrowser()
        self._content.setObjectName("SummaryContent")
        self._content.setOpenExternalLinks(True)
        self._content.setReadOnly(True)
        self._content.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._content.setMinimumHeight(40)
        self._content.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding
        )
        self._content.hide()

        self._placeholder = QLabel(self.tr("点击「生成摘要」让 AI 帮你快速了解这篇文章的重点。"))
        self._placeholder.setObjectName("SummaryPlaceholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)

        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(12, 8, 12, 12)
        body_layout.setSpacing(6)
        body_layout.addWidget(self._progress)
        body_layout.addWidget(self._content)
        body_layout.addWidget(self._placeholder)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(header_row)
        root.addWidget(self._separator)
        root.addWidget(self._body)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        self._body.hide()

        if self._runtime is not None:
            self._runtime.signals.state_changed.connect(self._on_state_changed)
            self._runtime.signals.chunk_received.connect(self._on_chunk_received)

    @property
    def active_run_id(self) -> str | None:
        return self._active_run_id

    @property
    def status(self) -> str:
        return self._status

    def set_entry(self, entry_id: int | None) -> None:
        self._entry_id = entry_id
        self._active_run_id = None
        self._pending_text = ""
        self._content.clear()
        self._content.hide()
        self._progress.hide()
        self._placeholder.show()
        self._generate_btn.show()
        self._status_label.setText("")
        self._status = "idle"
        self._generate_btn.setText(self.tr("生成摘要"))
        self._collapsed = True
        self._header.setChecked(False)
        self._header.setText(self.tr("▶ AI 摘要"))
        self._body.hide()
        self._separator.hide()

    def _toggle(self) -> None:
        self._collapsed = not self._collapsed
        expanded = not self._collapsed
        self._body.setVisible(expanded)
        self._separator.setVisible(expanded)
        self._header.setText(self.tr("▼ AI 摘要") if expanded else self.tr("▶ AI 摘要"))
        self.expanded_changed.emit(expanded)

    def _current_line_height(self) -> float:
        return _LINE_HEIGHT_PRESETS.get(self._line_height_preset, 1.7)

    def _on_line_height_changed(self, _index: int) -> None:
        self._line_height_preset = str(self._line_height_combo.currentData())
        self._settings.setValue(_SETTINGS_KEY_LINE_HEIGHT, self._line_height_preset)
        self._settings.sync()
        if self._content.isVisible() and self._pending_text:
            self._render_text(self._pending_text)

    def _request_generate(self) -> None:
        if self._entry_id is None:
            return
        if self._runtime is None:
            self._placeholder.setText(self.tr("AI Agent 未配置。请在设置中添加 LLM 提供者。"))
            return
        self.generate_requested.emit(self._entry_id)
        try:
            self._active_run_id = self._runtime.submit(self._entry_id, "summary")
        except Exception as exc:  # noqa: BLE001
            self._set_status("error")
            self._placeholder.setText(self.tr("任务提交失败：{0}").format(str(exc)))
            self._placeholder.show()
            return
        self._pending_text = ""
        self._content.clear()
        self._content.hide()
        self._placeholder.hide()
        self._progress.show()
        self._generate_btn.hide()
        self._set_status("queued")
        if self._collapsed:
            self._toggle()

    def request_auto_generate(self) -> None:
        self._request_generate()
        if self._active_run_id is not None:
            self._status_label.setText(self.tr("自动摘要已排队"))

    def _cancel_or_generate(self) -> None:
        if self._active_run_id and self._status in {"queued", "running"}:
            if self._runtime is not None:
                self._runtime.cancel(self._active_run_id)
            return
        self._request_generate()

    def _set_status(self, status: str) -> None:
        self._status = status
        labels = {
            "idle": "",
            "queued": self.tr("排队中…"),
            "running": self.tr("生成中…"),
            "done": self.tr("摘要就绪"),
            "error": self.tr("生成失败"),
            "cancelled": self.tr("已取消"),
        }
        self._status_label.setText(labels[status])
        busy = status in {"queued", "running"}
        self._progress.setVisible(busy)
        self._generate_btn.setText(self.tr("取消") if busy else self.tr("重新生成"))
        self._generate_btn.setVisible(status != "idle" or self._entry_id is not None)

    def _on_state_changed(self, event: object) -> None:
        from core.agent.runtime import AgentUIEvent

        evt: AgentUIEvent = event
        if evt.entry_id != self._entry_id or evt.agent_type != "summary":
            return
        if self._active_run_id is None and evt.status in {"queued", "running"}:
            self._active_run_id = evt.run_id
        if evt.run_id != self._active_run_id:
            return
        if evt.status in {"queued", "running"}:
            self._set_status(evt.status)
        elif evt.status == "done":
            self._set_status("done")
            if evt.result_json:
                self._render_result(evt.result_json)
            elif self._pending_text:
                self._render_text(self._pending_text)
        elif evt.status == "error":
            self._set_status("error")
            error_msg = evt.error or self.tr("未知错误")
            self._placeholder.setText(error_msg)
            self._placeholder.show()
        elif evt.status == "cancelled":
            self._set_status("cancelled")

    def _on_chunk_received(self, event: object) -> None:
        from core.agent.runtime import AgentUIEvent

        evt: AgentUIEvent = event
        if evt.entry_id != self._entry_id or evt.agent_type != "summary":
            return
        if evt.run_id != self._active_run_id:
            return
        self._pending_text += evt.chunk
        self._render_text(self._pending_text)

    def _render_result(self, result_json: str) -> None:
        import json
        import mistune

        try:
            data = json.loads(result_json)
            text = data.get("summary", "") or data.get("text", "") or str(data)
        except (json.JSONDecodeError, TypeError):
            text = result_json
        self._pending_text = text
        renderer = mistune.HTMLRenderer()
        md = mistune.create_markdown(renderer=renderer, plugins=["table", "strikethrough", "url"])
        html = md(text)
        self._content.setHtml(self._wrap_styles(html))
        self._content.show()

    def _render_text(self, text: str) -> None:
        import mistune

        renderer = mistune.HTMLRenderer()
        md = mistune.create_markdown(renderer=renderer, plugins=["table", "strikethrough", "url"])
        html = md(text)
        self._content.setHtml(self._wrap_styles(html))
        self._content.show()
        scrollbar = self._content.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def _wrap_styles(self, html: str) -> str:
        line_height = self._current_line_height()
        return (
            '<!doctype html><html><head><meta charset="utf-8"><style>'
            "body { font-family: system-ui, -apple-system, sans-serif; "
            f"font-size: 14px; line-height: {line_height}; padding: 8px 4px; }}"
            "h1,h2,h3 { line-height: 1.3; }"
            "p { margin: 0.5em 0; }"
            "ul,ol { padding-left: 1.5em; }"
            "code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; "
            "font-size: 0.92em; }"
            "pre { background: #f5f5f5; padding: 12px; border-radius: 8px; overflow-x: auto; }"
            "blockquote { border-left: 3px solid #ccc; margin-left: 0; "
            "padding-left: 14px; color: #666; }"
            "</style></head><body>" + html + "</body></html>"
        )
