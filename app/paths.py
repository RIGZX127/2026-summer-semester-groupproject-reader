"""Cross-platform application data paths."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path


def user_data_dir(
    *,
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return Mercury's writable per-user data directory."""
    current_platform = platform_name or sys.platform
    current_environ = os.environ if environ is None else environ
    current_home = Path.home() if home is None else home

    if current_platform == "win32":
        local_app_data = current_environ.get("LOCALAPPDATA")
        root = Path(local_app_data) if local_app_data else current_home / "AppData" / "Local"
        return root / "Mercury"

    if current_platform == "darwin":
        return current_home / "Library" / "Application Support" / "Mercury"

    xdg_data_home = current_environ.get("XDG_DATA_HOME")
    root = Path(xdg_data_home) if xdg_data_home else current_home / ".local" / "share"
    return root / "Mercury"


def ensure_user_data_dir() -> Path:
    """Create and return Mercury's writable per-user data directory."""
    path = user_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path
