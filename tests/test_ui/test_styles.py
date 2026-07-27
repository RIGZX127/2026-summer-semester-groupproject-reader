from app.styles import RADIUS, SPACING, application_stylesheet
from ui.theme import LIGHT_PALETTE


def test_design_tokens_match_modern_focus_direction() -> None:
    p = LIGHT_PALETTE
    assert p.sidebar == "#162A3A"
    assert p.accent == "#4F827D"
    assert p.surface == "#FFFDF8"
    assert SPACING["unit"] == 8
    assert RADIUS["control"] == 8


def test_application_stylesheet_contains_accessible_states() -> None:
    qss = application_stylesheet()
    assert "QWidget#Sidebar" in qss
    assert "QListWidget::item:selected" in qss
    assert "QPushButton:focus" in qss
    assert "QToolTip" in qss
    assert 'QLineEdit[validationError="true"]' in qss


def test_application_stylesheet_has_reader_toolbar_control_states() -> None:
    qss = application_stylesheet()
    assert "QWidget#ReaderToolbar" in qss
    assert 'QComboBox[readerControl="true"]' in qss
    assert 'QSpinBox[readerControl="true"]' in qss
    assert "QPushButton:checked" in qss
    assert "QPushButton#ReaderPopupButton" in qss
    assert "min-width: 36px; max-width: 36px" in qss
    assert "padding: 0; background" in qss
    assert "QWidget#SummaryHeaderBar" in qss


def test_buttons_are_compact_and_settings_text_uses_theme_colors() -> None:
    qss = application_stylesheet()
    assert "padding: 0 10px" in qss
    assert "QTabBar::tab" in qss
    assert "QLabel { color:" in qss


def test_tag_manager_surface_and_compact_toolbar_boxes_use_theme() -> None:
    qss = application_stylesheet()
    assert "QScrollArea#TagChipScrollArea" in qss
    assert "QWidget#TagChipContainer" in qss
    assert "QPushButton#TagAIButton" in qss
    assert "QWidget#ReaderToolbar QPushButton {" in qss
    assert "margin: 2px" in qss


def test_all_icon_buttons_have_no_resting_boxes() -> None:
    qss = application_stylesheet()
    assert "QPushButton#TagAIButton { color: #26343F; background: transparent" in qss
    assert (
        "QWidget#Sidebar QPushButton#SidebarActionButton { min-width: 36px; "
        "max-width: 36px;\n        min-height: 36px; max-height: 36px; padding: 0; "
        "background: transparent;\n        border-color: transparent;"
    ) in qss
    assert (
        "QPushButton#EntryHeaderIconButton, QPushButton#BatchActionButton { "
        "min-width: 36px; max-width: 36px;\n        min-height: 36px; "
        "max-height: 36px; padding: 0; background: transparent;\n        "
        "border-color: transparent;"
    ) in qss
    assert (
        "QWidget#ReaderToolbar QPushButton#ReaderPopupButton { min-width: 36px; "
        "max-width: 36px;\n        min-height: 36px; max-height: 36px; padding: 0; "
        "background: transparent;\n        border: 1px solid transparent;"
    ) in qss
