# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Mercury RSS Reader (cross-platform)."""
import os
import sys

_root = os.getcwd()
_icon = os.path.join(_root, "resources", "mercury.icns")
_has_icon = os.path.exists(_icon)

a = Analysis(
    [os.path.join(_root, "main.py")],
    pathex=[_root],
    binaries=[],
    datas=[(os.path.join(_root, "resources", "prompts"), "resources/prompts")],
    hiddenimports=[
        "qasync", "keyring.backends.fail", "keyring.backends.macOS",
        "keyring.backends.Windows", "readability", "markdownify",
        "mistune", "feedparser", "bs4", "lxml", "httpx", "openai",
        "jinja2", "yaml",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="Mercury",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon if _has_icon else None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Mercury.app",
        icon=_icon if _has_icon else None,
        bundle_identifier="com.mercury.reader",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "CFBundleName": "Mercury",
            "CFBundleDisplayName": "Mercury RSS Reader",
            "LSMinimumSystemVersion": "11.0",
        },
    )
