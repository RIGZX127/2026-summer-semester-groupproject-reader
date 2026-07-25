"""Build .qm translation files from .ts sources.

Usage:
    python resources/i18n/build_qm.py
    python resources/i18n/build_qm.py --watch  # recompile on .ts changes
"""

import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).parent
_TS_FILES = list(_HERE.glob("*.ts"))


def find_lrelease() -> str | None:
    """Locate the PySide6 lrelease executable."""
    import PySide6

    pyside_dir = Path(PySide6.__file__).parent
    for candidate in (
        pyside_dir / "lrelease.exe",
        pyside_dir / "lrelease",
    ):
        if candidate.exists():
            return str(candidate)
    return None


def compile_ts(ts_path: Path) -> bool:
    """Compile a single .ts to .qm, same basename."""
    lrelease = find_lrelease()
    if lrelease is None:
        print("ERROR: lrelease not found in PySide6 directory", file=sys.stderr)
        return False

    qm_path = ts_path.with_suffix(".qm")
    result = subprocess.run(
        [lrelease, str(ts_path), "-qm", str(qm_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR compiling {ts_path.name}: {result.stderr}", file=sys.stderr)
        return False

    size = qm_path.stat().st_size if qm_path.exists() else 0
    print(f"  {ts_path.name} → {qm_path.name}  ({size} bytes)")
    return True


def main() -> None:
    if not _TS_FILES:
        print("No .ts files found in", _HERE)
        return

    print(f"Compiling {len(_TS_FILES)} translation file(s)...")
    for ts in sorted(_TS_FILES):
        compile_ts(ts)
    print("Done.")


if __name__ == "__main__":
    main()
