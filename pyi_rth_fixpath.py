"""PyInstaller runtime hook: fix mixed path separators on Windows.

PyInstaller 6.21 + Python 3.13 on Windows sometimes constructs paths with
mixed ``\\`` and ``/`` separators (e.g. ``_internal\\Lib/platform.py``)
when resolving stdlib modules through frozen importers.

This hook patches *all* loaders that might be used, not just FrozenImporter.
"""
import os
import sys


def _normalize_path(path: str) -> str:
    """Replace forward slashes with the platform separator."""
    if "/" in path and os.sep != "/":
        return path.replace("/", os.sep)
    return path


def _patch_loader(loader_class, attr: str = "get_data") -> None:
    """Monkey-patch a loader method to normalize its path argument."""
    original = getattr(loader_class, attr, None)
    if original is None:
        return

    def _wrapper(self, path):
        return original(self, _normalize_path(path))

    try:
        setattr(loader_class, attr, _wrapper)
    except (TypeError, AttributeError):
        pass


def _apply_fixes() -> None:
    """Patch all known frozen importers."""
    try:
        from pyimod02_importers import FrozenImporter
        _patch_loader(FrozenImporter, "get_data")
    except ImportError:
        pass

    # Also patch importlib's file-based loaders as a safety net
    try:
        from importlib.machinery import SourceFileLoader, SourcelessFileLoader
        _patch_loader(SourceFileLoader, "get_data")
        _patch_loader(SourcelessFileLoader, "get_data")
    except ImportError:
        pass

    # Patch ExtensionFileLoader for native modules
    try:
        from importlib.machinery import ExtensionFileLoader
        _patch_loader(ExtensionFileLoader, "get_data")
    except ImportError:
        pass

    # Also patch importlib._bootstrap_external directly for get_data calls
    # that bypass the loader
    try:
        import importlib._bootstrap_external as _bootstrap_external
        _patch_loader(_bootstrap_external, "get_data")
    except (ImportError, AttributeError):
        pass


if getattr(sys, "frozen", False) and sys.platform == "win32":
    _apply_fixes()
