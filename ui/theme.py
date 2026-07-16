"""Semantic color palettes shared by Qt widgets and the Reader."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ThemePreference = Literal["system", "light", "dark"]
EffectiveTheme = Literal["light", "dark"]


@dataclass(frozen=True)
class Palette:
    window: str
    surface: str
    surface_alt: str
    surface_hover: str
    surface_pressed: str
    control: str
    sidebar: str
    sidebar_hover: str
    sidebar_selected: str
    text: str
    text_muted: str
    text_disabled: str
    text_on_accent: str
    border: str
    border_strong: str
    focus: str
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_soft: str
    success: str
    warning: str
    error: str
    error_soft: str
    code_surface: str


LIGHT_PALETTE = Palette(
    "#F6F4EE",
    "#FFFDF8",
    "#EFEEE8",
    "#E7ECE9",
    "#DCE5E1",
    "#FFFEFA",
    "#162A3A",
    "#213B48",
    "#315B68",
    "#26343F",
    "#68766F",
    "#9A9F9B",
    "#FFFFFF",
    "#D8DDD8",
    "#B9C4BE",
    "#75AAA4",
    "#4F827D",
    "#43746F",
    "#38645F",
    "#E1ECE8",
    "#3F7D68",
    "#A76E2F",
    "#B65757",
    "#F6E5E3",
    "#ECEBE5",
)
DARK_PALETTE = Palette(
    "#0A0D12",
    "#10151C",
    "#171D26",
    "#202832",
    "#2A3440",
    "#171D26",
    "#080B10",
    "#121923",
    "#1B2A3D",
    "#ECEEF1",
    "#9AA4B1",
    "#66717E",
    "#FFFFFF",
    "#242C36",
    "#364251",
    "#79A1DD",
    "#557FC0",
    "#6590D2",
    "#466DAC",
    "#1D2B3E",
    "#69A38A",
    "#CEA16A",
    "#D27B80",
    "#3D262C",
    "#151B23",
)


def palette_for(theme: EffectiveTheme) -> Palette:
    return DARK_PALETTE if theme == "dark" else LIGHT_PALETTE
