# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Smart Media Backup macOS .app"""

import sys
import os
from pathlib import Path

# Paths
ROOT = Path(os.getcwd()).resolve().parent
SMB = ROOT / "smb"

print(f"[SMB Build] ROOT={ROOT}")

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
        "smb.organizer", "smb.verifier", "smb.db", "smb.cli",
        "flask", "flask_socketio", "engineio", "engineio.async_drivers",
        "engineio.async_drivers.threading", "socketio",
        "psutil", "humanize", "dateutil", "dateutil.parser",
        "werkzeug", "jinja2", "markupsafe", "itsdangerous", "click",
        "bidict", "encodings.utf_8", "encodings.latin_1",
        "json", "sqlite3", "threading", "webbrowser",
        "os", "sys", "time", "shutil", "hashlib",
        "concurrent", "concurrent.futures",
        "http", "http.server",
        "email", "email.mime",
        "html", "html.parser",
        "xml", "xml.etree", "xml.etree.ElementTree",
        "socket", "ssl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "PyQt5", "PySide2", "PySide6",
        "matplotlib", "scipy", "numpy",
        "pandas", "notebook", "jupyter",
        "boto3", "botocore",
        "cv2", "PIL",
    ],
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
)

app = BUNDLE(
    exe,
    [],
    name="Smart Media Backup.app",
    icon="/Users/nanyu/smart-media-backup/desktop/icon.icns",
    bundle_identifier="com.luguanlin.smart-media-backup",
    info_plist={
        "CFBundleName": "Smart Media Backup",
        "CFBundleDisplayName": "Smart Media Backup",
        "CFBundleIdentifier": "com.luguanlin.smart-media-backup",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleExecutable": "Smart Media Backup",
        "CFBundleInfoDictionaryVersion": "6.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSHumanReadableCopyright": "© 2025 陆冠霖",
        "NSSupportsAutomaticTermination": False,
        "LSBackgroundOnly": False,
        "CFBundlePackageType": "APPL",
    },
)
