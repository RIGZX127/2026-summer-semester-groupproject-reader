"""Markdown note editor with delayed save requests."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, QTimer, Signal
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget


class NoteEditor(QWidget):
    """Edit one entry note and emit a save request after five seconds."""

    save_requested = Signal(int, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry_id: int | None = None
        self._dirty = False
        self.text_edit = QPlainTextEdit()
        self.text_edit.setObjectName("NoteTextEdit")
        self.text_edit.setPlaceholderText(self.tr("记录想法，支持 Markdown…"))
        self.text_edit.setAccessibleName(self.tr("文章笔记"))
        self.status_label = QLabel(self.tr("选择文章后可添加笔记"))
        self.status_label.setObjectName("NoteSaveStatus")
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(5000)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        layout.addWidget(self.text_edit, 1)
        layout.addWidget(self.status_label)

        self.text_edit.textChanged.connect(self._on_text_changed)
        self.autosave_timer.timeout.connect(self.flush)
        self.set_entry(None, "")

    @property
    def entry_id(self) -> int | None:
        return self._entry_id

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def set_entry(self, entry_id: int | None, body: str = "") -> None:
        self.autosave_timer.stop()
        self._entry_id = entry_id
        self._dirty = False
        with QSignalBlocker(self.text_edit):
            self.text_edit.setPlainText(body)
        self.text_edit.setEnabled(entry_id is not None)
        self.set_save_state("saved" if entry_id is not None else "disabled")

    def set_save_state(self, state: str) -> None:
        labels = {
            "disabled": self.tr("选择文章后可添加笔记"),
            "dirty": self.tr("未保存"),
            "saving": self.tr("正在保存…"),
            "saved": self.tr("已保存"),
            "error": self.tr("保存失败，将在下次编辑后重试"),
        }
        if state not in labels:
            raise ValueError(f"Unknown note save state: {state}")
        self.status_label.setText(labels[state])
        if state == "saved":
            self._dirty = False

    def flush(self) -> None:
        if self._entry_id is None or not self._dirty:
            return
        self.set_save_state("saving")
        self.save_requested.emit(self._entry_id, self.text_edit.toPlainText())

    def _on_text_changed(self) -> None:
        if self._entry_id is None:
            return
        self._dirty = True
        self.set_save_state("dirty")
        self.autosave_timer.start()
