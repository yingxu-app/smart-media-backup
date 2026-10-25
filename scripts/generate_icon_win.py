"""生成 Smart Media Backup Windows 图标 (.ico) — 复用 generate_icon.py 的绘制逻辑"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.generate_icon import draw_icon  # noqa: E402

OUTPUT = Path(__file__).resolve().parent.parent / "desktop" / "icon.ico"

SIZES = [16, 24, 32, 48, 64, 128, 256]


def main():
    images = [draw_icon(px) for px in SIZES]
    images[-1].save(
        OUTPUT,
        format="ICO",
        sizes=[(px, px) for px in SIZES],
        append_images=images[:-1],
    )
    print(f"✅ Windows 图标生成完成: {OUTPUT} ({os.path.getsize(OUTPUT) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
