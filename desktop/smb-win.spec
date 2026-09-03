# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Smart Media Backup Windows 桌面版
入口: desktop/run.py (pywebview 窗口壳 + 本地 Flask 服务)
Run: pyinstaller desktop/smb-win.spec --noconfirm
"""
import os
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
SMB = ROOT / "smb"
DESKTOP = ROOT / "desktop"

block_cipher = None

a = Analysis(
    [str(DESKTOP / "run.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(SMB / "templates"), "smb/templates"),
        (str(SMB / "static"), "smb/static"),
        (str(DESKTOP / "icon.ico"), "desktop"),
    ],
    hiddenimports=[
        "smb", "smb.config", "smb.detector", "smb.backup",
        "smb.organizer", "smb.verifier", "smb.db", "smb.cli", "smb.baidu", "smb.ai_namer",
        "smb.windows_preview", "smb.waste_filter", "smb.lightroom", "smb.phash",
        "flask", "flask_socketio", "engineio", "engineio.async_drivers.threading",
        "socketio", "psutil", "humanize", "dateutil", "werkzeug", "jinja2",
        "markupsafe", "itsdangerous", "click", "bidict", "requests",
        "json", "sqlite3", "threading", "webbrowser", "hashlib",
        "concurrent", "concurrent.futures",
        "webview", "clr_loader", "pythonnet",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6", "matplotlib", "scipy", "numpy", "pandas", "cv2"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="影序 YINGXU",
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
    icon=str(DESKTOP / "icon.ico"),
)

# Windows doesn't need BUNDLE (that's for .app)
