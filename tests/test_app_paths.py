from __future__ import annotations

from pathlib import Path

from app.paths import user_data_dir


def test_windows_data_dir_uses_local_app_data(tmp_path: Path) -> None:
    result = user_data_dir(
        platform_name="win32",
        environ={"LOCALAPPDATA": str(tmp_path)},
        home=tmp_path / "home",
    )

    assert result == tmp_path / "Mercury"


def test_windows_data_dir_falls_back_to_home_appdata(tmp_path: Path) -> None:
    home = tmp_path / "home"

    result = user_data_dir(platform_name="win32", environ={}, home=home)

    assert result == home / "AppData" / "Local" / "Mercury"


def test_linux_data_dir_honours_xdg_data_home(tmp_path: Path) -> None:
    result = user_data_dir(
        platform_name="linux",
        environ={"XDG_DATA_HOME": str(tmp_path)},
        home=tmp_path / "home",
    )

    assert result == tmp_path / "Mercury"


def test_macos_data_dir_uses_application_support(tmp_path: Path) -> None:
    home = tmp_path / "home"

    result = user_data_dir(platform_name="darwin", environ={}, home=home)

    assert result == home / "Library" / "Application Support" / "Mercury"
