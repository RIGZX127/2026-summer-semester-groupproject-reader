"""Export dialog with a theme-aware, readable live preview."""

from __future__ import annotations

from PySide6.QtCore import Signal
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
    """Choose a template and destination, preview the result, then export."""

    template_changed = Signal(str)

    def __init__(
        self,
        templates: list[str],
        preview_text: str = "",
        selected_template: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("导出文章"))
        self.setMinimumSize(520, 440)
        self.setModal(True)

        title = QLabel(self.tr("导出文章"))
        title.setObjectName("SectionTitle")
        hint = QLabel(self.tr("选择模板、预览内容，然后选择导出目录。"))
        hint.setObjectName("MutedLabel")

        template_label = QLabel(self.tr("模板"))
        self._template_combo = QComboBox()
        self._template_combo.addItems(templates)
        if selected_template in templates:
            self._template_combo.setCurrentText(selected_template)
        self._template_combo.setAccessibleName(self.tr("导出模板"))

        preview_label = QLabel(self.tr("预览"))
        self.preview = QPlainTextEdit()
        self.preview.setObjectName("ExportPreview")
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText(self.tr("选择模板后将在此显示预览…"))
        self.preview.setAccessibleName(self.tr("导出预览"))
        self.preview.setMinimumHeight(160)
        self._preview = self.preview
        self.set_preview(preview_text)

        destination_label = QLabel(self.tr("导出目录"))
        self._dest_edit = QLineEdit()
        self._dest_edit.setPlaceholderText(self.tr("选择或输入目录路径…"))
        self._dest_edit.setAccessibleName(self.tr("导出目录"))
        browse_button = QPushButton(self.tr("浏览"))
        browse_button.setMinimumWidth(80)
        destination_row = QHBoxLayout()
        destination_row.setSpacing(8)
        destination_row.addWidget(self._dest_edit, 1)
        destination_row.addWidget(browse_button)

        self._cancel_btn = QPushButton(self.tr("取消"))
        self._export_btn = QPushButton(self.tr("导出"))
        self._export_btn.setObjectName("PrimaryButton")
        self._export_btn.setDefault(True)
        self._export_btn.setEnabled(False)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self._cancel_btn)
        button_row.addWidget(self._export_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(template_label)
        layout.addWidget(self._template_combo)
        layout.addWidget(preview_label)
        layout.addWidget(self.preview, 1)
        layout.addWidget(destination_label)
        layout.addLayout(destination_row)
        layout.addSpacing(4)
        layout.addLayout(button_row)

        self._cancel_btn.clicked.connect(self.reject)
        self._export_btn.clicked.connect(self.accept)
        browse_button.clicked.connect(self._browse)
        self._dest_edit.textChanged.connect(self._validate)
        self._template_combo.currentTextChanged.connect(self.template_changed)

    def selected_template(self) -> str:
        return self._template_combo.currentText()

    def destination(self) -> str:
        return self._dest_edit.text().strip()

    def set_preview(self, text: str) -> None:
        visible_text = text if text.strip() else self.tr("没有可预览的文章内容。")
        self.preview.setPlainText(visible_text)

    def preview_text(self) -> str:
        return self.preview.toPlainText()

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, self.tr("选择导出目录"))
        if path:
            self._dest_edit.setText(path)

    def _validate(self) -> None:
        self._export_btn.setEnabled(bool(self._dest_edit.text().strip()))
