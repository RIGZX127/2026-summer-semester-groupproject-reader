"""Reader theme value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    font_size: int = 17
    content_width: int = 760
    color_scheme: str = "light"
    background: str = "#FCFBF8"
    text_color: str = "#26343F"
    muted_color: str = "#71808B"
    surface_color: str = "#F2F0EB"
