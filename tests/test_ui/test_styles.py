from app.styles import COLORS, RADIUS, SPACING, application_stylesheet


def test_design_tokens_match_modern_focus_direction() -> None:
    assert COLORS["sidebar"] == "#192838"
    assert COLORS["accent"] == "#4B7F92"
    assert COLORS["surface"] == "#FCFBF8"
    assert SPACING["unit"] == 8
    assert RADIUS["control"] == 7


def test_application_stylesheet_contains_accessible_states() -> None:
    qss = application_stylesheet()
    assert "QWidget#Sidebar" in qss
    assert "QListWidget::item:selected" in qss
    assert "QPushButton:focus" in qss
    assert 'QLineEdit[validationError="true"]' in qss
