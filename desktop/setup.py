"""
py2app setup — builds Smart Media Backup.app
Usage: python setup.py py2app
"""
import sys
import os
from setuptools import setup

APP_NAME = "Smart Media Backup"

# Ensure the smb package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

APP = ["app.py"]
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.luguanlin.smart-media-backup",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleExecutable": APP_NAME,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSSupportsAutomaticTermination": False,
        "CFBundleInfoDictionaryVersion": "6.0",
        "NSHumanReadableCopyright": "© 2025 陆冠霖",
    },
    "packages": ["smb", "flask", "flask_socketio", "engineio", "socketio",
                  "psutil", "humanize", "dateutil", "werkzeug", "jinja2",
                  "markupsafe", "itsdangerous", "click", "bidict"],
    "includes": ["encodings.utf_8", "encodings.latin_1"],
    "resources": [
        ("../smb/templates", "smb/templates"),
        ("../smb/static", "smb/static"),
    ],
    "site_packages": True,
}

setup(
    name=APP_NAME,
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
