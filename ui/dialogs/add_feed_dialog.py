"""Dialog for collecting and validating a Feed URL."""
from __future__ import annotations

from urllib.parse import urlparse

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AddFeedDialog(QDialog):
    """Collect a URL and emit a normalized value without performing I/O."""

    url_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("添加订阅"))
        self.setModal(True)
        self.setMinimumWidth(440)

        title = QLabel(self.tr("添加新的订阅源"))
        title.setObjectName("SectionTitle")
        hint = QLabel(self.tr("输入 RSS、Atom 或 JSON Feed 地址。"))
        hint.setObjectName("MutedLabel")
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/feed.xml")
        self.url_edit.setAccessibleName(self.tr("订阅源地址"))
        self.error_label = QLabel()
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.cancel_button = QPushButton(self.tr("取消"))
        self.submit_button = QPushButton(self.tr("添加"))
        self.submit_button.setObjectName("PrimaryButton")
        self.submit_button.setDefault(True)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.submit_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(4)
        layout.addWidget(self.url_edit)
        layout.addWidget(self.error_label)
        layout.addSpacing(8)
        layout.addLayout(buttons)

        self.cancel_button.clicked.connect(self.reject)
        self.submit_button.clicked.connect(self._submit)
        self.url_edit.textChanged.connect(self.clear_error)

    def url(self) -> str:
        return self._normalize(self.url_edit.text())

    def set_submitting(self, submitting: bool) -> None:
        self.url_edit.setEnabled(not submitting)
        self.submit_button.setEnabled(not submitting)
        self.submit_button.setText(self.tr("正在添加…") if submitting else self.tr("添加"))

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()
        self.url_edit.setProperty("validationError", True)
        self._refresh_url_style()
        self.url_edit.setFocus()

    def clear_error(self) -> None:
        self.error_label.hide()
        self.url_edit.setProperty("validationError", False)
        self._refresh_url_style()

    def _refresh_url_style(self) -> None:
        style = self.url_edit.style()
        style.unpolish(self.url_edit)
        style.polish(self.url_edit)

    def _submit(self) -> None:
        url = self.url()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or " " in parsed.netloc:
            self.show_error(self.tr("请输入有效的 http 或 https 订阅地址。"))
            return
        self.clear_error()
        self.url_submitted.emit(url)

    @staticmethod
    def _normalize(value: str) -> str:
        value = value.strip()
        if value and "://" not in value:
            value = f"https://{value}"
        return value
