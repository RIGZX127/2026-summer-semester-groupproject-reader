"""Export dialog — template selection, live preview, and destination."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ExportDialog(QDialog):
    """Choose a template and destination, preview the result, then export.

    Usage::

        dialog = ExportDialog(templates, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            template = dialog.selected_template()
            dest_dir = dialog.destination()
    """

    def __init__(
        self,
        templates: list[str],
        preview_text: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("导出文章"))
        self.setMinimumWidth(520)
        self.setMinimumHeight(460)
        self.setModal(True)

        # ── Title ──────────────────────────────────────────────────────
        title = QLabel(self.tr("导出文章"))
        title.setObjectName("SectionTitle")
        hint = QLabel(self.tr("选择模板、预览内容，然后选择导出目录。"))
        hint.setObjectName("MutedLabel")

        # ── Template selector ──────────────────────────────────────────
        tpl_label = QLabel(self.tr("模板"))
        self._template_combo = QComboBox()
        self._template_combo.addItems(templates)
        self._template_combo.setAccessibleName(self.tr("导出模板"))

        # ── Preview ────────────────────────────────────────────────────
        preview_label = QLabel(self.tr("预览"))
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText(self.tr("选择模板后将在此显示预览…"))
        self._preview.setAccessibleName(self.tr("导出预览"))
        self._preview.setMinimumHeight(160)
        self._preview.setPlainText(preview_text)

        # ── Destination ─────────────────────────────────────────────────
        dest_label = QLabel(self.tr("导出目录"))
        self._dest_edit = QLineEdit()
        self._dest_edit.setPlaceholderText(self.tr("选择或输入目录路径…"))
        self._dest_edit.setAccessibleName(self.tr("导出目录"))
        browse_btn = QPushButton(self.tr("浏览"))
        browse_btn.setMinimumWidth(80)

        dest_row = QHBoxLayout()
        dest_row.setSpacing(8)
        dest_row.addWidget(self._dest_edit, 1)
        dest_row.addWidget(browse_btn)

        # ── Buttons ────────────────────────────────────────────────────
        self._cancel_btn = QPushButton(self.tr("取消"))
        self._export_btn = QPushButton(self.tr("导出"))
        self._export_btn.setObjectName("PrimaryButton")
        self._export_btn.setDefault(True)
        self._export_btn.setEnabled(False)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._export_btn)

        # ── Main layout ────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(tpl_label)
        layout.addWidget(self._template_combo)
        layout.addWidget(preview_label)
        layout.addWidget(self._preview, 1)
        layout.addWidget(dest_label)
        layout.addLayout(dest_row)
        layout.addSpacing(8)
        layout.addLayout(btn_row)

        # ── Connections ────────────────────────────────────────────────
        self._cancel_btn.clicked.connect(self.reject)
        self._export_btn.clicked.connect(self.accept)
        browse_btn.clicked.connect(self._browse)
        self._dest_edit.textChanged.connect(self._validate)

    # ── Public API ─────────────────────────────────────────────────────────

    def selected_template(self) -> str:
        """Return the selected template name (e.g. ``single.md.j2``)."""
        return self._template_combo.currentText()

    def destination(self) -> str:
        """Return the chosen export directory path."""
        return self._dest_edit.text().strip()

    def set_preview(self, text: str) -> None:
        """Update the preview pane."""
        self._preview.setPlainText(text)

    # ── Internal ───────────────────────────────────────────────────────────

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, self.tr("选择导出目录")
        )
        if path:
            self._dest_edit.setText(path)

    def _validate(self) -> None:
        self._export_btn.setEnabled(bool(self._dest_edit.text().strip()))
