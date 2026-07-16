"""Global UI theme preference, persistence, and runtime application."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from ui.theme import EffectiveTheme, Palette, ThemePreference, palette_for


class ThemeController(QObject):
    theme_changed = Signal(str)
    SETTINGS_KEY = "ui/theme_preference"
    VALID_PREFERENCES = frozenset({"system", "light", "dark"})

    def __init__(
        self,
        settings: QSettings | None = None,
        system_theme_reader: Callable[[], EffectiveTheme] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings or QSettings()
        self._system_theme_reader = system_theme_reader or self._read_system_theme
        value = str(self._settings.value(self.SETTINGS_KEY, "system"))
        self._preference: ThemePreference = cast(
            ThemePreference, value if value in self.VALID_PREFERENCES else "system"
        )
        self._effective_theme = self._resolve()
        hints = QGuiApplication.styleHints()
        if hints is not None and hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda _scheme: self.refresh_system_theme())

    @property
    def preference(self) -> ThemePreference:
        return self._preference

    @property
    def effective_theme(self) -> EffectiveTheme:
        return self._effective_theme

    @property
    def palette(self) -> Palette:
        return palette_for(self._effective_theme)

    def set_preference(self, value: str) -> None:
        if value not in self.VALID_PREFERENCES:
            raise ValueError("Unsupported application theme preference")
        previous = self._effective_theme
        self._preference = cast(ThemePreference, value)
        self._settings.setValue(self.SETTINGS_KEY, value)
        self._settings.sync()
        self._effective_theme = self._resolve()
        self.apply()
        if self._effective_theme != previous:
            self.theme_changed.emit(self._effective_theme)

    def refresh_system_theme(self) -> None:
        if self._preference != "system":
            return
        previous = self._effective_theme
        self._effective_theme = self._resolve()
        if previous != self._effective_theme:
            self.apply()
            self.theme_changed.emit(self._effective_theme)

    def apply(self) -> None:
        from app.styles import application_stylesheet

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(application_stylesheet(self.palette))

    def _resolve(self) -> EffectiveTheme:
        if self._preference == "system":
            try:
                return self._system_theme_reader()
            except Exception:  # noqa: BLE001
                return "light"
        return cast(EffectiveTheme, self._preference)

    @staticmethod
    def _read_system_theme() -> EffectiveTheme:
        hints = QGuiApplication.styleHints()
        if hints is not None and hints.colorScheme() == Qt.ColorScheme.Dark:
            return "dark"
        return "light"
