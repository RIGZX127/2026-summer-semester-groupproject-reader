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
    assert 'QLineEdit[validationError="true"]' in qss


def test_application_stylesheet_has_reader_toolbar_control_states() -> None:
    qss = application_stylesheet()
    assert "QWidget#ReaderToolbar" in qss
    assert 'QComboBox[readerControl="true"]' in qss
    assert 'QSpinBox[readerControl="true"]' in qss
    assert "QPushButton:checked" in qss
