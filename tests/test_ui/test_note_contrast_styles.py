"""Regression coverage for readable note-editor and reader-tab colours."""

from app.styles import application_stylesheet
from ui.theme import DARK_PALETTE, LIGHT_PALETTE


def test_note_editor_has_explicit_palette_colours() -> None:
    for palette in (LIGHT_PALETTE, DARK_PALETTE):
        stylesheet = application_stylesheet(palette)

        assert "QPlainTextEdit#NoteTextEdit" in stylesheet
        assert f"color: {palette.text}" in stylesheet
        assert f"background: {palette.control}" in stylesheet


def test_reader_tabs_define_selected_and_unselected_text_colours() -> None:
    for palette in (LIGHT_PALETTE, DARK_PALETTE):
        stylesheet = application_stylesheet(palette)

        assert "QTabWidget#ReaderBottomTabs QTabBar::tab" in stylesheet
        assert "QTabWidget#ReaderBottomTabs QTabBar::tab:selected" in stylesheet
        assert f"color: {palette.text_muted}" in stylesheet
        assert f"color: {palette.text}" in stylesheet
