"""LLM provider configuration panel with multi-preset support.

Users can save multiple named model configurations as presets and
switch between them with a single click.  The active preset is
always synced to the legacy ``llm/*`` QSettings keys so that the
existing ``_build_agent_runtime`` / ``reconfigure_agent_runtime``
paths require no changes.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ── QSettings key constants ───────────────────────────────────────────────
_PRESETS_COUNT = "llm/presets/count"
_PRESET_PREFIX = "llm/presets"  # → llm/presets/{i}/{name|base_url|model|api_key}
_ACTIVE_INDEX = "llm/active_preset_index"

# Legacy keys — always synced with active preset for backward compat
_LEGACY_NAME = "llm/name"
_LEGACY_BASE_URL = "llm/base_url"
_LEGACY_MODEL = "llm/model"
_LEGACY_API_KEY = "llm/api_key"

_DEFAULT_PRESET_NAME = "本地模型"
_MAX_PRESETS = 10


# ── Helpers ────────────────────────────────────────────────────────────────


def _preset_key(index: int, field: str) -> str:
    """Build a QSettings key for a preset field, e.g. ``llm/presets/0/name``."""
    return f"{_PRESET_PREFIX}/{index}/{field}"


def _load_presets(settings: QSettings) -> list[dict[str, str]]:
    """Load all presets from QSettings, returning a list of field dicts.

    On first run (no presets yet), migrates the existing legacy config
    into a single preset so users don't lose their current setup.
    """
    count = settings.value(_PRESETS_COUNT, 0, type=int)
    if count <= 0:
        # ── First-run migration ───────────────────────────────────────
        legacy_name = str(settings.value(_LEGACY_NAME, ""))
        legacy_url = str(settings.value(_LEGACY_BASE_URL, ""))
        legacy_model = str(settings.value(_LEGACY_MODEL, ""))
        legacy_key = str(settings.value(_LEGACY_API_KEY, ""))

        if legacy_url or legacy_model:
            # Existing legacy config → create first preset from it
            presets = [
                {
                    "name": legacy_name or _DEFAULT_PRESET_NAME,
                    "base_url": legacy_url,
                    "model": legacy_model,
                    "api_key": legacy_key,
                }
            ]
        else:
            # Fresh start — one empty preset
            presets = [
                {
                    "name": _DEFAULT_PRESET_NAME,
                    "base_url": "",
                    "model": "",
                    "api_key": "",
                }
            ]
        _save_presets(settings, presets, 0)
        return presets

    presets: list[dict[str, str]] = []
    for i in range(count):
        presets.append(
            {
                "name": str(settings.value(_preset_key(i, "name"), _DEFAULT_PRESET_NAME)),
                "base_url": str(settings.value(_preset_key(i, "base_url"), "")),
                "model": str(settings.value(_preset_key(i, "model"), "")),
                "api_key": str(settings.value(_preset_key(i, "api_key"), "")),
            }
        )
    return presets


def _save_presets(settings: QSettings, presets: list[dict[str, str]], active: int) -> None:
    """Persist all presets to QSettings and mark the active index."""
    # Remove old preset keys first (in case count decreased)
    old_count = settings.value(_PRESETS_COUNT, 0, type=int)
    for i in range(old_count):
        for field in ("name", "base_url", "model", "api_key"):
            settings.remove(_preset_key(i, field))

    settings.setValue(_PRESETS_COUNT, len(presets))
    for i, p in enumerate(presets):
        settings.setValue(_preset_key(i, "name"), p["name"])
        settings.setValue(_preset_key(i, "base_url"), p["base_url"])
        settings.setValue(_preset_key(i, "model"), p["model"])
        settings.setValue(_preset_key(i, "api_key"), p["api_key"])
    settings.setValue(_ACTIVE_INDEX, active)

    # ── Sync legacy keys from active preset ───────────────────────────
    active_preset = presets[active]
    settings.setValue(_LEGACY_NAME, active_preset["name"])
    settings.setValue(_LEGACY_BASE_URL, active_preset["base_url"])
    settings.setValue(_LEGACY_MODEL, active_preset["model"])
    settings.setValue(_LEGACY_API_KEY, active_preset["api_key"])
    settings.sync()


# ── Preset Bar Widget ──────────────────────────────────────────────────────


class PresetBar(QWidget):
    """Horizontal row of clickable preset buttons + add / delete controls."""

    current_changed = Signal(int)  # emitted when user clicks a preset button
    add_requested = Signal()       # emitted when "+" is clicked
    delete_requested = Signal(int) # emitted when "✕" is clicked, carries active index

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._active_index = 0

        self._button_layout = QHBoxLayout()
        self._button_layout.setContentsMargins(0, 0, 0, 0)
        self._button_layout.setSpacing(4)

        self._add_btn = QPushButton("+")
        self._add_btn.setToolTip("新建模型预设")
        self._add_btn.setFixedWidth(32)
        self._add_btn.clicked.connect(self._on_add_clicked)

        self._del_btn = QPushButton("✕")
        self._del_btn.setToolTip("删除当前预设")
        self._del_btn.setFixedWidth(32)
        self._del_btn.clicked.connect(self._on_delete_clicked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(4)
        layout.addLayout(self._button_layout)
        layout.addWidget(self._add_btn)
        layout.addWidget(self._del_btn)
        layout.addStretch()

    # ── Public API ─────────────────────────────────────────────────────────

    def rebuild(self, names: list[str], active_index: int, can_delete: bool) -> None:
        """Rebuild preset buttons from a list of preset names."""
        # Clear existing buttons
        for btn in self._buttons:
            self._button_layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()

        self._active_index = active_index
        self._del_btn.setEnabled(can_delete)
        self._add_btn.setEnabled(len(names) < _MAX_PRESETS)

        for i, name in enumerate(names):
            btn = QPushButton(name[:12])  # truncated for compact display
            btn.setCheckable(True)
            btn.setChecked(i == active_index)
            btn.setToolTip(name)
            btn.clicked.connect(self._make_click_handler(i))
            self._button_layout.addWidget(btn)
            self._buttons.append(btn)

    def set_active(self, index: int) -> None:
        """Update checked state without emitting signal."""
        self._active_index = index
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _make_click_handler(self, index: int):
        """Return a callable that emits current_changed for the given index."""

        def handler():
            if index != self._active_index:
                self._active_index = index
                for i, btn in enumerate(self._buttons):
                    btn.setChecked(i == index)
                self.current_changed.emit(index)

        return handler

    def _on_add_clicked(self) -> None:
        self.add_requested.emit()

    def _on_delete_clicked(self) -> None:
        self.delete_requested.emit(self._active_index)


# ── Provider Panel ─────────────────────────────────────────────────────────


class ProviderPanel(QWidget):
    """Edit one OpenAI-compatible provider and report test states.

    Now supports multiple named presets that persist to QSettings.
    Switching presets auto-saves the current form and triggers
    ``configuration_saved`` so the LLM router hot-reloads.
    """

    test_requested = Signal(dict)
    configuration_saved = Signal()

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings

        # ── State ─────────────────────────────────────────────────────
        self._presets = _load_presets(settings)
        self._active_index = settings.value(_ACTIVE_INDEX, 0, type=int)
        if self._active_index >= len(self._presets):
            self._active_index = 0

        # ── Preset bar ────────────────────────────────────────────────
        self._preset_bar = PresetBar(self)
        self._preset_bar.add_requested.connect(self._add_preset)
        self._preset_bar.delete_requested.connect(self._delete_preset)
        self._preset_bar.current_changed.connect(self._on_preset_switched)
        self._refresh_preset_bar()

        # ── Form fields ───────────────────────────────────────────────
        self.name_edit = QLineEdit()
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("http://localhost:11434/v1")
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText(self.tr("本地模型可留空"))

        # Load active preset into form
        self._load_active_preset_to_form()

        self.status_label = QLabel(self.tr("尚未测试连接"))
        self.status_label.setObjectName("MutedLabel")
        self.status_label.setWordWrap(True)
        self.test_button = QPushButton(self.tr("测试连接"))
        self.test_button.setAccessibleName(self.tr("测试 LLM 提供者连接"))
        self.save_button = QPushButton(self.tr("保存配置"))
        self.save_button.setProperty("buttonRole", "primary")

        # ── Layout ────────────────────────────────────────────────────
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow(self.tr("名称"), self.name_edit)
        form.addRow(self.tr("服务地址"), self.base_url_edit)
        form.addRow(self.tr("模型"), self.model_combo)
        form.addRow(self.tr("API Key"), self.api_key_edit)

        actions = QHBoxLayout()
        actions.addWidget(self.status_label, 1)
        actions.addWidget(self.test_button)
        actions.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)
        layout.addWidget(self._preset_bar)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addStretch()

        self.test_button.clicked.connect(self._request_test)
        self.save_button.clicked.connect(self.save)

    # ── Preset management ──────────────────────────────────────────────────

    def _refresh_preset_bar(self) -> None:
        """Rebuild the button bar from current preset state."""
        names = [p["name"] for p in self._presets]
        can_delete = len(self._presets) > 1
        self._preset_bar.rebuild(names, self._active_index, can_delete)

    def _load_active_preset_to_form(self) -> None:
        """Populate form fields from the active preset."""
        p = self._presets[self._active_index]
        self.name_edit.setText(p["name"])
        self.base_url_edit.setText(p["base_url"])
        self.model_combo.clear()
        if p["model"]:
            self.model_combo.addItem(p["model"])
        self.api_key_edit.setText(p["api_key"])

    def _sync_form_to_active_preset(self) -> None:
        """Write current form values into the active preset dict."""
        self._presets[self._active_index] = {
            "name": self.name_edit.text().strip(),
            "base_url": self.base_url_edit.text().strip(),
            "model": self.model_combo.currentText().strip(),
            "api_key": self.api_key_edit.text(),
        }

    def _on_preset_switched(self, index: int) -> None:
        """User clicked a different preset button."""
        if index == self._active_index:
            return
        # Save current form to the outgoing preset
        self._sync_form_to_active_preset()
        # Switch
        self._active_index = index
        self._load_active_preset_to_form()
        # Persist + trigger hot-reload
        _save_presets(self._settings, self._presets, self._active_index)
        self.status_label.setObjectName("SuccessLabel")
        self.status_label.setText(self.tr("已切换到「{0}」").format(self._presets[index]["name"]))
        self.configuration_saved.emit()

    def _add_preset(self) -> None:
        """Create a new empty preset and switch to it."""
        if len(self._presets) >= _MAX_PRESETS:
            return

        name, ok = QInputDialog.getText(
            self,
            self.tr("新建模型预设"),
            self.tr("请输入预设名称："),
            text=self.tr("新模型 {0}").format(len(self._presets) + 1),
        )
        if not ok or not name.strip():
            return

        # Save current form to current preset before adding
        self._sync_form_to_active_preset()

        new_preset = {
            "name": name.strip(),
            "base_url": "",
            "model": "",
            "api_key": "",
        }
        self._presets.append(new_preset)
        self._active_index = len(self._presets) - 1
        _save_presets(self._settings, self._presets, self._active_index)
        self._load_active_preset_to_form()
        self._refresh_preset_bar()
        self.status_label.setObjectName("MutedLabel")
        self.status_label.setText(self.tr("已创建「{0}」，请填写服务地址和模型。").format(name.strip()))

    def _delete_preset(self, index: int) -> None:
        """Delete a preset.  Refuses to delete the last one."""
        if len(self._presets) <= 1:
            return

        preset_name = self._presets[index]["name"]
        reply = QMessageBox.question(
            self,
            self.tr("删除预设"),
            self.tr("确定要删除预设「{0}」吗？此操作不可撤销。").format(preset_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        del self._presets[index]
        # Adjust active index
        if self._active_index >= len(self._presets):
            self._active_index = len(self._presets) - 1
        elif self._active_index > index:
            self._active_index -= 1
        # If we deleted the active preset, load the new active one
        if self._active_index == index or self._active_index < index:
            # active_index already adjusted to a valid preset
            pass

        _save_presets(self._settings, self._presets, self._active_index)
        self._load_active_preset_to_form()
        self._refresh_preset_bar()
        self.status_label.setObjectName("SuccessLabel")
        self.status_label.setText(self.tr("预设「{0}」已删除").format(preset_name))
        self.configuration_saved.emit()

    # ── Public API ─────────────────────────────────────────────────────────

    def configuration(self) -> dict[str, str]:
        return {
            "name": self.name_edit.text().strip(),
            "base_url": self.base_url_edit.text().strip(),
            "model": self.model_combo.currentText().strip(),
            "api_key": self.api_key_edit.text(),
        }

    def save(self) -> None:
        """Save current form values to the active preset + legacy keys."""
        self._sync_form_to_active_preset()
        _save_presets(self._settings, self._presets, self._active_index)
        self._refresh_preset_bar()
        self.status_label.setObjectName("SuccessLabel")
        self.status_label.setText(self.tr("配置已保存"))
        self.configuration_saved.emit()

    def _request_test(self) -> None:
        config = self.configuration()
        if not config["base_url"]:
            self.show_test_result(False, [], self.tr("请先填写服务地址。"))
            return
        self.set_testing(True)
        self.test_requested.emit(config)

    def set_testing(self, testing: bool) -> None:
        self.test_button.setEnabled(not testing)
        self.save_button.setEnabled(not testing)
        if testing:
            self.status_label.setObjectName("MutedLabel")
            self.status_label.setText(self.tr("正在测试连接…"))

    def show_test_result(self, success: bool, models: list[str], error: str = "") -> None:
        self.set_testing(False)
        if success:
            current = self.model_combo.currentText()
            self.model_combo.clear()
            self.model_combo.addItems(models)
            if current and current not in models:
                self.model_combo.addItem(current)
            if current:
                self.model_combo.setCurrentText(current)
            self.status_label.setObjectName("SuccessLabel")
            self.status_label.setText(self.tr("连接成功，发现 {0} 个模型").format(len(models)))
        else:
            self.status_label.setObjectName("ErrorLabel")
            self.status_label.setText(self.tr("连接失败：{0}").format(error or self.tr("未知错误")))
        self.style().unpolish(self.status_label)
        self.style().polish(self.status_label)
