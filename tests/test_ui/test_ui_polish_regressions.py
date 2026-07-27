from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QPushButton

from app.styles import application_stylesheet
from ui.dialogs.export_dialog import ExportDialog
from ui.dialogs.tag_manager_dialog import TagChip, TagManagerDialog
from ui.reader.reader_toolbar import ReaderToolbar
from ui.reader.reader_view import ReaderView
from ui.settings.settings_dialog import SettingsDialog
from ui.sidebar import Sidebar
from ui.theme import DARK_PALETTE, LIGHT_PALETTE


def test_tag_action_keeps_small_glyph_inside_36_pixel_target(qtbot) -> None:
    chip = TagChip("Python")
    qtbot.addWidget(chip)

    button = chip.findChild(QPushButton, "TagRemoveButton")

    assert button.minimumWidth() >= 36
    assert button.minimumHeight() >= 36
    assert button.iconSize().width() <= 20
    assert button.toolTip()
    assert button.accessibleName()


def test_tag_area_grows_with_rows_and_only_scrolls_after_cap(qtbot) -> None:
    short_dialog = TagManagerDialog(["Python"])
    long_dialog = TagManagerDialog([f"Long tag {index}" for index in range(30)])
    qtbot.addWidget(short_dialog)
    qtbot.addWidget(long_dialog)
    short_dialog.resize(440, 320)
    long_dialog.resize(440, 520)
    short_dialog.show()
    long_dialog.show()
    qtbot.waitUntil(lambda: short_dialog.tag_scroll.height() > 0)
    qtbot.waitUntil(lambda: long_dialog.tag_scroll.height() > 0)

    assert short_dialog.tag_scroll.height() < long_dialog.tag_scroll.height()
    assert short_dialog.tag_scroll.verticalScrollBar().isVisible() is False
    assert long_dialog.tag_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


def test_export_preview_uses_semantic_theme_surface_in_both_themes(qtbot) -> None:
    dialog = ExportDialog(["multi.md.j2"], "Readable preview")
    qtbot.addWidget(dialog)

    assert dialog.preview_text() == "Readable preview"
    assert dialog.preview.objectName() == "ExportPreview"
    for palette in (LIGHT_PALETTE, DARK_PALETTE):
        stylesheet = application_stylesheet(palette)
        dialog.setStyleSheet(stylesheet)
        assert dialog.preview.styleSheet() == ""
        assert "QPlainTextEdit#ExportPreview" in stylesheet


def test_ai_unconfigured_banner_is_shared_and_opens_settings(qtbot) -> None:
    view = ReaderView(agent_runtime=None)
    qtbot.addWidget(view)
    view.show()
    view.show_content("<p>Article</p>", None, entry_id=7)

    view.summary_panel._request_generate()

    assert view.ai_banner.isVisible()
    assert view.ai_banner_message.text() == "尚未配置 AI 服务"
    with qtbot.waitSignal(view.settings_requested, timeout=500):
        qtbot.mouseClick(view.ai_settings_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(view.ai_banner_close_button, Qt.MouseButton.LeftButton)
    assert view.ai_banner.isHidden()

    view._request_translation()
    assert view.ai_banner.isVisible()
    view.ai_banner.hide()
    view.notify_ai_unconfigured("tagging")
    assert view.ai_banner.isVisible()


def test_bottom_tabs_expand_on_open_and_focus_restores_previous_state(tmp_path, qtbot) -> None:
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    view = ReaderView(settings=settings)
    qtbot.addWidget(view)
    view.resize(900, 700)
    view.show()
    qtbot.waitUntil(lambda: sum(view.reader_splitter.sizes()) > 0)

    assert view.bottom_panel_collapsed
    view.open_bottom_tab(1)
    qtbot.waitUntil(lambda: not view.bottom_panel_collapsed)
    expanded_height = view.reader_splitter.sizes()[1]
    assert view.bottom_tabs.currentIndex() == 1
    assert expanded_height >= 180

    view.set_focus_mode(True)
    assert view.bottom_panel_collapsed
    view.set_focus_mode(False)
    assert not view.bottom_panel_collapsed
    assert view.bottom_tabs.currentIndex() == 1
    assert view.reader_splitter.sizes()[1] == expanded_height


def test_settings_is_shorter_and_usage_starts_with_empty_state(tmp_path, qtbot) -> None:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    dialog = SettingsDialog(settings, usage_store=object(), mode="ai")
    qtbot.addWidget(dialog)

    assert dialog.minimumHeight() <= 440
    assert dialog.usage_panel is not None
    assert dialog.usage_panel.empty_state.text() == "暂无调用记录"
    assert dialog.usage_panel.empty_state.isHidden() is False

    dialog.usage_panel.set_summary(1, 10, 5)
    assert dialog.usage_panel.empty_state.isHidden()


def test_toolbar_sidebar_and_filter_targets_are_at_least_36_pixels(qtbot) -> None:
    toolbar = ReaderToolbar()
    sidebar = Sidebar()
    qtbot.addWidget(toolbar)
    qtbot.addWidget(sidebar)

    toolbar_targets = (
        toolbar.sidebar_restore_button,
        toolbar.reader_button,
        toolbar.web_button,
        toolbar.split_button,
        toolbar.translate_button,
        toolbar.focus_button,
    )
    sidebar_targets = (
        sidebar.collapse_button,
        sidebar.add_button,
        sidebar.sync_button,
        sidebar.ai_button,
        sidebar.import_opml_button,
        sidebar.export_opml_button,
        sidebar.tag_filter_clear_btn,
    )
    for button in (*toolbar_targets, *sidebar_targets):
        assert button.minimumWidth() >= 36
        assert button.minimumHeight() >= 36
