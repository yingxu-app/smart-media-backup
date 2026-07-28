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
    [str(ROOT / "desktop" / "run.py")],
    pathex=[str(ROOT), str(ROOT / "desktop")],
    binaries=[],
    datas=[
        (str(SMB / "templates"), "smb/templates"),
        (str(SMB / "static"), "smb/static"),
    ],
    hiddenimports=[
        "smb", "smb.config", "smb.detector", "smb.backup",
        "smb.organizer", "smb.verifier", "smb.db", "smb.cli",
        "smb.phash", "smb.lightroom", "smb.baidu", "smb.ai_namer",
        "smb.waste_filter", "smb.windows_preview",
        "flask", "flask_socketio", "engineio", "engineio.async_drivers",
        "engineio.async_drivers.threading", "socketio",
        "psutil", "humanize", "dateutil", "dateutil.parser",
        "werkzeug", "jinja2", "markupsafe", "itsdangerous", "click",
        "bidict", "encodings.utf_8", "encodings.latin_1",
        "json", "sqlite3", "threading", "webbrowser",
        "webview", "webview.platforms.cocoa",
        "objc", "AppKit", "Cocoa", "WebKit",
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
        "matplotlib",
        "pandas", "notebook", "jupyter",
        "boto3", "botocore",
        "cv2",
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
    [],
    name="影序 YINGXU",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    exclude_binaries=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="影序 YINGXU",
)

app = BUNDLE(
    coll,
    [],
    name="影序 YINGXU.app",
    icon=str(ROOT / "desktop" / "icon.icns"),
    bundle_identifier="com.luguanlin.yingxu",
    info_plist={
        "CFBundleName": "影序 YINGXU",
        "CFBundleDisplayName": "影序 YINGXU",
        "CFBundleIdentifier": "com.luguanlin.yingxu",
        "CFBundleVersion": "1.0.26",
        "CFBundleShortVersionString": "1.0.26",
        "CFBundleExecutable": "影序 YINGXU",
        "CFBundleInfoDictionaryVersion": "6.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSHumanReadableCopyright": "© 2025 陆冠霖",
        "NSSupportsAutomaticTermination": False,
        "LSBackgroundOnly": False,
        "CFBundlePackageType": "APPL",
    },
)
