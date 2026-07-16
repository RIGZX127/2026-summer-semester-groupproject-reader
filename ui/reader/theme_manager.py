"""Persist Reader preferences and generate scoped CSS."""

from __future__ import annotations

from PySide6.QtCore import QSettings

from ui.reader.theme import Theme
from ui.theme import LIGHT_PALETTE, Palette


class ThemeManager:
    FONT_RANGE = range(14, 25)
    WIDTHS = frozenset({640, 760, 920})
    SCHEMES = frozenset({"light", "dark"})
    HORIZONTAL_GUTTERS = {
        640: "clamp(20px, 8vw, 96px)",
        760: "clamp(18px, 6vw, 72px)",
        920: "clamp(16px, 4vw, 48px)",
    }

    def __init__(self, settings: QSettings | None = None, palette: Palette = LIGHT_PALETTE) -> None:
        self._settings = settings or QSettings()
        self._palette = palette
        self._theme = self._load()

    @property
    def theme(self) -> Theme:
        return self._theme

    def _load(self) -> Theme:
        font_size = int(self._settings.value("reader/font_size", 17))
        width = int(self._settings.value("reader/content_width", 760))
        scheme = str(self._settings.value("reader/color_scheme", "light"))
        if font_size not in self.FONT_RANGE:
            font_size = 17
        if width not in self.WIDTHS:
            width = 760
        if scheme not in self.SCHEMES:
            scheme = "light"
        return self._make_theme(font_size, width, scheme)

    @staticmethod
    def _make_theme(font_size: int, width: int, scheme: str) -> Theme:
        if scheme == "dark":
            return Theme(font_size, width, scheme, "#171A1D", "#E8EAED", "#A7AFB7", "#23272B")
        return Theme(font_size, width, scheme)

    def _save(self) -> None:
        self._settings.setValue("reader/font_size", self._theme.font_size)
        self._settings.setValue("reader/content_width", self._theme.content_width)
        self._settings.setValue("reader/color_scheme", self._theme.color_scheme)
        self._settings.sync()

    def set_font_size(self, value: int) -> None:
        if value not in self.FONT_RANGE:
            raise ValueError("Reader font size must be between 14 and 24")
        self._theme = self._make_theme(value, self._theme.content_width, self._theme.color_scheme)
        self._save()

    def set_content_width(self, value: int) -> None:
        if value not in self.WIDTHS:
            raise ValueError("Unsupported Reader content width")
        self._theme = self._make_theme(self._theme.font_size, value, self._theme.color_scheme)
        self._save()

    def set_color_scheme(self, value: str) -> None:
        if value not in self.SCHEMES:
            raise ValueError("Unsupported Reader color scheme")
        self._theme = self._make_theme(self._theme.font_size, self._theme.content_width, value)
        self._save()

    def set_palette(self, palette: Palette, scheme: str) -> None:
        self._palette = palette
        self._theme = self._make_theme(self._theme.font_size, self._theme.content_width, scheme)

    def reader_css(self) -> str:
        theme = self._theme
        palette = self._palette
        horizontal_gutter = self.HORIZONTAL_GUTTERS[theme.content_width]
        return f"""
        :root {{ color-scheme: {theme.color_scheme}; }}
        html {{ background: {palette.surface}; }}
        body {{ box-sizing: border-box; width: 100%; max-width: none; margin: 0;
          padding: clamp(24px, 5vw, 48px) {horizontal_gutter} clamp(44px, 7vw, 72px);
          color: {palette.text}; background: {palette.surface};
          font: {theme.font_size}px/1.76 Georgia, "Noto Serif SC", "Source Han Serif SC", serif;
          overflow-wrap: anywhere; }}
        h1, h2, h3 {{ line-height: 1.28; }}
        .meta {{ color: {palette.text_muted}; font-family: system-ui, sans-serif; }}
        a {{ color: {palette.accent}; text-decoration-thickness: 1px; text-underline-offset: 3px; }}
        img, video, svg {{ max-width: 100%; height: auto; }}
        table, pre {{ display: block; max-width: 100%; overflow-x: auto; }}
        pre, code {{ background: {palette.code_surface}; border-radius: 7px; }}
        code {{ font-family: "Cascadia Code", "SFMono-Regular", Consolas, monospace; }}
        pre {{ padding: 16px; }}
        blockquote {{ margin-left: 0; padding: 2px 0 2px 18px; color: {palette.text_muted};
          border-left: 3px solid {palette.accent}; }}
        hr {{ border: 0; border-top: 1px solid {palette.border}; }}
        h1, h2, h3, p, li {{ overflow-wrap: anywhere; }}
        """

    def wrap_html(self, fragment: str) -> str:
        return (
            '<!doctype html><html><head><meta charset="utf-8"><style>'
            + self.reader_css()
            + "</style></head><body>"
            + fragment
            + "</body></html>"
        )
