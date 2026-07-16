"""Collapsible AI summary panel with streaming support.

Integrates with AgentRuntime when available; degrades gracefully otherwise.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
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


class SummaryPanel(QFrame):
    """Collapsible panel displaying AI-generated article summary."""

    generate_requested = Signal(int)  # entry_id

    def __init__(
        self,
        runtime: AgentRuntime | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SummaryPanel")
        self._runtime = runtime
        self._entry_id: int | None = None
        self._active_run_id: str | None = None
        self._pending_text = ""
        self._collapsed = True

        # ── Header bar ──────────────────────────────────────────────
        self._header = QPushButton(self.tr("✨ AI 摘要"))
        self._header.setObjectName("SummaryHeader")
        self._header.setCheckable(True)
        self._header.setChecked(False)
        self._header.setFlat(True)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.clicked.connect(self._toggle)

        self._status_label = QLabel("")
        self._status_label.setObjectName("SummaryStatus")

        self._generate_btn = QPushButton(self.tr("生成摘要"))
        self._generate_btn.setObjectName("SummaryGenerateBtn")
        self._generate_btn.setToolTip(self.tr("让 AI 为当前文章生成摘要"))
        self._generate_btn.clicked.connect(self._request_generate)
        self._generate_btn.hide()

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.addWidget(self._header)
        header_row.addStretch()
        header_row.addWidget(self._status_label)
        header_row.addWidget(self._generate_btn)

        # ── Collapsible body ────────────────────────────────────────
        self._body = QWidget()
        self._body.setObjectName("SummaryBody")

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.hide()

        self._content = QTextBrowser()
        self._content.setObjectName("SummaryContent")
        self._content.setOpenExternalLinks(True)
        self._content.setReadOnly(True)
        self._content.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._content.setMinimumHeight(60)
        self._content.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding
        )
        self._content.hide()

        self._placeholder = QLabel(
            self.tr("点击「生成摘要」让 AI 帮你快速了解这篇文章的重点。")
        )
        self._placeholder.setObjectName("SummaryPlaceholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)

        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(12, 8, 12, 12)
        body_layout.setSpacing(8)
        body_layout.addWidget(self._progress)
        body_layout.addWidget(self._content)
        body_layout.addWidget(self._placeholder)

        # ── Root layout ─────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(header_row)
        root.addWidget(self._body)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._body.hide()

        # ── Wire AgentRuntime signals ─────────────────────────────
        if self._runtime is not None:
            self._runtime.signals.state_changed.connect(self._on_state_changed)
            self._runtime.signals.chunk_received.connect(self._on_chunk_received)

    # ── Public API ──────────────────────────────────────────────────

    def set_entry(self, entry_id: int | None) -> None:
        """Reset panel for a new article entry."""
        self._entry_id = entry_id
        self._active_run_id = None
        self._pending_text = ""
        self._content.clear()
        self._content.hide()
        self._progress.hide()
        self._placeholder.show()
        self._generate_btn.show()
        self._status_label.setText("")
        self._collapsed = True
        self._header.setChecked(False)
        self._body.hide()

    # ── Slots ───────────────────────────────────────────────────────

    def _toggle(self) -> None:
        self._collapsed = not self._collapsed
        self._body.setVisible(not self._collapsed)

    def _request_generate(self) -> None:
        if self._entry_id is None:
            return
        if self._runtime is None:
            self._placeholder.setText(
                self.tr("⚠️ AI Agent 未配置。请在设置中添加 LLM 提供者。")
            )
            return
        self.generate_requested.emit(self._entry_id)
        self._pending_text = ""
        self._content.clear()
        self._content.hide()
        self._placeholder.hide()
        self._progress.show()
        self._generate_btn.hide()
        self._status_label.setText(self.tr("思考中…"))
        # auto-expand
        if self._collapsed:
            self._toggle()

    def _on_state_changed(self, event: object) -> None:
        """Handle AgentUIEvent from AgentRuntime."""
        from core.agent.runtime import AgentUIEvent

        evt: AgentUIEvent = event
        if evt.entry_id != self._entry_id or evt.agent_type != "summary":
            return

        if evt.status == "running":
            self._active_run_id = evt.run_id
            self._status_label.setText(self.tr("思考中…"))
            self._progress.show()
        elif evt.status == "done":
            self._active_run_id = None
            self._progress.hide()
            self._status_label.setText(self.tr("✅ 摘要就绪"))
            self._generate_btn.setText(self.tr("重新生成"))
            self._generate_btn.show()
            if evt.result_json:
                self._render_result(evt.result_json)
            elif self._pending_text:
                self._render_text(self._pending_text)
        elif evt.status == "error":
            self._active_run_id = None
            self._progress.hide()
            self._status_label.setText(self.tr("❌ 生成失败"))
            self._generate_btn.show()
            error_msg = evt.error or self.tr("未知错误")
            self._placeholder.setText(f"⚠️ {error_msg}")
            self._placeholder.show()
        elif evt.status == "cancelled":
            self._active_run_id = None
            self._progress.hide()
            self._status_label.setText(self.tr("已取消"))
            self._generate_btn.show()

    def _on_chunk_received(self, event: object) -> None:
        """Stream partial summary text."""
        from core.agent.runtime import AgentUIEvent

        evt: AgentUIEvent = event
        if evt.entry_id != self._entry_id or evt.agent_type != "summary":
            return
        self._pending_text += evt.chunk
        self._render_text(self._pending_text)

    def _render_result(self, result_json: str) -> None:
        import json

        try:
            data = json.loads(result_json)
            text = data.get("summary", "") or data.get("text", "") or str(data)
        except (json.JSONDecodeError, TypeError):
            text = result_json

        import mistune

        renderer = mistune.HTMLRenderer()
        md = mistune.create_markdown(renderer=renderer, plugins=["table", "strikethrough", "url"])
        html = md(text)
        self._content.setHtml(self._wrap_styles(html))
        self._content.show()

    def _render_text(self, text: str) -> None:
        """Render streaming markdown text."""
        import mistune

        renderer = mistune.HTMLRenderer()
        md = mistune.create_markdown(renderer=renderer, plugins=["table", "strikethrough", "url"])
        html = md(text)
        self._content.setHtml(self._wrap_styles(html))
        self._content.show()
        # Auto-scroll to bottom
        scrollbar = self._content.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def _wrap_styles(self, html: str) -> str:
        return (
            '<!doctype html><html><head><meta charset="utf-8"><style>'
            "body { font-family: system-ui, -apple-system, sans-serif; "
            "font-size: 14px; line-height: 1.7; padding: 8px 4px; }"
            "h1,h2,h3 { line-height: 1.3; }"
            "p { margin: 0.5em 0; }"
            "ul,ol { padding-left: 1.5em; }"
            "code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; "
            "font-size: 0.92em; }"
            "pre { background: #f5f5f5; padding: 12px; border-radius: 8px; "
            "overflow-x: auto; }"
            "blockquote { border-left: 3px solid #ccc; margin-left: 0; "
            "padding-left: 14px; color: #666; }"
            "</style></head><body>" + html + "</body></html>"
        )
