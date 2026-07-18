"""Smart Media Backup — 桌面 + Web 智能 SD 卡备份工具"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="smart-media-backup",
    version="1.0.0",
    author="Lu Guanlin",
    author_email="luguanlin20050927@icloud.com",
    description="插卡自动备份 → 按设备→事件→照片/视频分类整理 → Web 面板可视化",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/luguanlin/smart-media-backup",
    packages=find_packages(include=["smb", "smb.*"]),
    include_package_data=True,
    package_data={
        "smb": ["templates/*.html", "static/css/*.css", "static/js/*.js"],
    },
    install_requires=[
        "flask>=3.0",
        "flask-socketio>=5.3",
        "python-dateutil>=2.8",
        "psutil>=5.9",
        "humanize>=4.9",
    ],
    extras_require={
        "dev": ["pytest", "black"],
        "pi": [],
    },
    entry_points={
        "console_scripts": [
            "smb=smb.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Graphics",
        "Topic :: System :: Archiving :: Backup",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
