# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Smart Media Backup Windows .exe
Run: pyinstaller smb-win.spec --noconfirm
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMB = ROOT / "smb"
ICON = str(ROOT / "desktop" / "icon.icns")

block_cipher = None

a = Analysis(
    [str(SMB / "server.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(SMB / "templates"), "smb/templates"),
        (str(SMB / "static"), "smb/static"),
    ],
    hiddenimports=[
        "smb", "smb.config", "smb.detector", "smb.backup",
        "smb.organizer", "smb.verifier", "smb.db", "smb.cli", "smb.baidu", "smb.ai_namer",
        "flask", "flask_socketio", "engineio", "engineio.async_drivers.threading",
        "socketio", "psutil", "humanize", "dateutil", "werkzeug", "jinja2",
        "markupsafe", "itsdangerous", "click", "bidict", "requests",
        "json", "sqlite3", "threading", "webbrowser", "hashlib",
        "concurrent", "concurrent.futures",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "matplotlib", "scipy", "numpy", "pandas", "cv2"],
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
    name="Smart Media Backup",
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
    icon=ICON if os.path.exists(ICON) else None,
)

# Windows doesn't need BUNDLE (that's for .app)
