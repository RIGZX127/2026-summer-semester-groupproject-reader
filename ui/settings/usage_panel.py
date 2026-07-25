"""LLM usage statistics panel — summary, breakdown, and daily timeline."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def _stat_card(title: str, value: str, parent: QWidget | None = None) -> QFrame:
    """Build a compact stat card with title + large value."""
    card = QFrame(parent)
    card.setObjectName("UsageStatCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(4)
    lbl_value = QLabel(value)
    lbl_value.setObjectName("UsageStatValue")
    lbl_title = QLabel(title)
    lbl_title.setObjectName("MutedLabel")
    lbl_title.setWordWrap(True)
    layout.addWidget(lbl_value)
    layout.addWidget(lbl_title)
    return card


class UsagePanel(QWidget):
    """Display LLM usage totals, grouped breakdown, and recent timeline.

    The panel is designed to be embedded inside a QTabWidget (settings dialog).
    Call ``refresh()`` after injection to populate data asynchronously.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        title = QLabel(self.tr("LLM 用量统计"))
        title.setObjectName("SectionTitle")
        hint = QLabel(self.tr("各 Agent 类型的 Token 消耗与调用次数。"))
        hint.setObjectName("MutedLabel")

        # ── Stat cards row ─────────────────────────────────────────────
        self._calls_card = _stat_card(self.tr("总调用"), "—")
        self._prompt_card = _stat_card(self.tr("Prompt Tokens"), "—")
        self._completion_card = _stat_card(self.tr("Completion Tokens"), "—")

        cards = QGridLayout()
        cards.setSpacing(12)
        cards.addWidget(self._calls_card, 0, 0)
        cards.addWidget(self._prompt_card, 0, 1)
        cards.addWidget(self._completion_card, 0, 2)

        # ── Breakdown grid ─────────────────────────────────────────────
        breakdown_label = QLabel(self.tr("按 Agent 类型"))
        breakdown_label.setObjectName("SidebarSection")

        self._grid = QGridLayout()
        self._grid.setSpacing(4)
        self._grid.setContentsMargins(0, 0, 0, 0)

        # ── Main layout ────────────────────────────────────────────────
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        content_layout.addWidget(title)
        content_layout.addWidget(hint)
        content_layout.addLayout(cards)
        content_layout.addWidget(breakdown_label)
        content_layout.addLayout(self._grid)
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    # ── Public API ─────────────────────────────────────────────────────────

    def set_placeholder(self) -> None:
        """Show placeholder values before real data loads."""
        for card_val in (self._calls_card, self._prompt_card, self._completion_card):
            lbl: QLabel = card_val.findChild(QLabel, "UsageStatValue")  # type: ignore[assignment]
            if lbl:
                lbl.setText("—")

    def set_summary(self, calls: int, prompt_tokens: int, completion_tokens: int) -> None:
        """Update the stat cards with real values."""
        self._calls_card.findChild(QLabel).setText(f"{calls:,}")
        self._prompt_card.findChild(QLabel).setText(f"{prompt_tokens:,}")
        self._completion_card.findChild(QLabel).setText(f"{completion_tokens:,}")

    def set_breakdown(
        self,
        rows: list[tuple[str, int, int, int]],
    ) -> None:
        """Populate the per-agent-type grid.

        Each row is (agent_type, calls, prompt_tokens, completion_tokens).
        """
        # Clear existing
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Header
        headers = [
            self.tr("类型"),
            self.tr("调用"),
            self.tr("Prompt"),
            self.tr("Completion"),
        ]
        for col, text in enumerate(headers):
            hdr = QLabel(text)
            hdr.setObjectName("MutedLabel")
            self._grid.addWidget(hdr, 0, col)

        for row_idx, (agent_type, calls, pt, ct) in enumerate(rows, start=1):
            items = [
                agent_type,
                f"{calls:,}",
                f"{pt:,}",
                f"{ct:,}",
            ]
            for col, text in enumerate(items):
                lbl = QLabel(text)
                if col == 0:
                    lbl.setObjectName("UsageAgentTypeLabel")
                self._grid.addWidget(lbl, row_idx, col)
