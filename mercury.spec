# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Mercury RSS Reader (cross-platform).

Uses --onedir mode: all files are on disk, QWebEngineView can find its
renderer process directly.  Much more reliable than --onefile for Qt apps.
"""
import os
import sys

_root = os.getcwd()
_icon_ico = os.path.join(_root, "resources", "mercury.ico")
_icon_icns = os.path.join(_root, "resources", "mercury.icns")

a = Analysis(
    [os.path.join(_root, "main.py")],
    pathex=[_root],
    binaries=[],
    datas=[
        (os.path.join(_root, "resources", "prompts"),   "resources/prompts"),
        (os.path.join(_root, "resources", "templates"), "resources/templates"),
        (os.path.join(_root, "resources", "i18n"),      "resources/i18n"),
    ],
    hiddenimports=[
        # stdlib modules that PyInstaller 6.21 + Python 3.13 mishandles
        "platform",
        # Qt / async
        "qasync",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebChannel",
        # keyring backends — lazy-loaded, excluded from bundle
        # reader pipeline
        "readability",
        "markdownify",
        "mistune",
        # feed
        "feedparser",
        # HTTP
        "httpx",
        "httpcore",
        # LLM
        "openai",
        # templates
        "jinja2",
        "jinja2.ext",
        # parsing / data
        "bs4",
        "lxml",
        "yaml",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(_root, "pyi_rth_fixpath.py")],
    excludes=[
        "tkinter", "matplotlib", "numpy", "pandas", "scipy", "PIL",
        "keyring", "keyrings.alt", "jaraco.context", "jaraco.classes",
        "jaraco.functools", "importlib_metadata", "more_itertools",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Mercury",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_ico if os.path.exists(_icon_ico) else (_icon_icns if os.path.exists(_icon_icns) else None),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Mercury",
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Mercury.app",
        icon=_icon_icns if os.path.exists(_icon_icns) else None,
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
