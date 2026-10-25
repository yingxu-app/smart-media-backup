"""CLI 命令行接口"""
import sys
import argparse
from .server import main as web_main
from .config import config


def main():
    parser = argparse.ArgumentParser(
        prog="smb",
        description="Smart Media Backup — 智能 SD 卡媒体备份"
    )
    parser.add_argument("command", nargs="?", default="web", choices=["web", "scan"])

    args = parser.parse_args()

    if args.command == "web":
        web_main()
    elif args.command == "scan":
        from .detector import list_removable_volumes
        vols = list_removable_volumes()
        if not vols:
            print("📡 未检测到 SD 卡")
        else:
            for v in vols:
                print(f"  📷 {v['name']}  ({v['mount_point']})")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
