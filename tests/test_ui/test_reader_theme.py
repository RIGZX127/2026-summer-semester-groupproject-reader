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


def test_reader_width_adapts_to_wide_and_focus_panes(tmp_path) -> None:
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    manager = ThemeManager(settings)

    assert "width: 100%" in manager.reader_css()
    assert "max-width: none" in manager.reader_css()
    assert "clamp(18px, 6vw, 72px)" in manager.reader_css()
    assert "--reader-content-width: clamp(760px, 78vw, 1240px)" in manager.reader_css()
    assert "body > *" in manager.reader_css()
    assert "max-width: min(100%, var(--reader-content-width))" in manager.reader_css()
    assert "p > img:only-child" in manager.reader_css()
    assert "width: 100%" in manager.reader_css()

    manager.set_content_width(920)
    assert "--reader-content-width: clamp(920px, 88vw, 1440px)" in manager.reader_css()
    assert "clamp(16px, 4vw, 48px)" in manager.reader_css()
