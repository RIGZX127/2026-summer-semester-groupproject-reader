from PySide6.QtCore import QSettings

from ui.reader.theme_manager import ThemeManager


def test_theme_manager_persists_reader_preferences(tmp_path) -> None:
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    manager = ThemeManager(settings)
    manager.set_font_size(20)
    manager.set_color_scheme("dark")
    manager.set_content_width(920)

    restored = ThemeManager(settings)
    assert restored.theme.font_size == 20
    assert restored.theme.color_scheme == "dark"
    assert restored.theme.content_width == 920


def test_reader_css_contains_responsive_overflow_rules(tmp_path) -> None:
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    css = ThemeManager(settings).reader_css()
    assert "max-width: 100%" in css
    assert "overflow-x: auto" in css
    assert "overflow-wrap: anywhere" in css


def test_reader_width_fills_pane_without_breakpoint_shrinking(tmp_path) -> None:
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    manager = ThemeManager(settings)

    assert "width: 100%" in manager.reader_css()
    assert "max-width: none" in manager.reader_css()
    assert "clamp(18px, 6vw, 72px)" in manager.reader_css()
    assert "@media (max-width: 700px)" not in manager.reader_css()

    manager.set_content_width(920)
    assert "width: 100%" in manager.reader_css()
    assert "clamp(16px, 4vw, 48px)" in manager.reader_css()
