"""生成 Smart Media Backup 应用图标 (.icns)"""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

ICONSET = "/tmp/smb.iconset"
OUTPUT = os.path.expanduser("~/smart-media-backup/desktop/icon.icns")

SIZES = [
    (16, "16x16"),
    (32, "16x16@2x"),
    (32, "32x32"),
    (64, "32x32@2x"),
    (128, "128x128"),
    (256, "128x128@2x"),
    (256, "256x256"),
    (512, "256x256@2x"),
    (512, "512x512"),
    (1024, "512x512@2x"),
]


def draw_icon(size: int) -> Image.Image:
    """绘制 SMB 图标：深色圆角方块 + 相机 + SD 卡符号"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角矩形背景
    r = size * 0.18
    bg_color = (19, 22, 32, 255)  # #131620
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=r, fill=bg_color)

    # 边框
    border_color = (37, 42, 58, 255)  # #252a3a
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=r, outline=border_color, width=max(1, size // 64))

    # 相机图标主体
    cx, cy = size * 0.5, size * 0.45
    bw = size * 0.52  # 机身宽
    bh = size * 0.34  # 机身高度
    bx1 = cx - bw / 2
    bx2 = cx + bw / 2
    by1 = cy - bh / 2
    by2 = cy + bh / 2
    cr = size * 0.06

    # 机身
    body_color = (74, 222, 128, 230)  # #4ade80
    draw.rounded_rectangle([(bx1, by1), (bx2, by2)], radius=cr, fill=body_color)

    # 镜头
    lens_r = size * 0.12
    lens_x, lens_y = cx, cy
    draw.ellipse(
        [(lens_x - lens_r, lens_y - lens_r), (lens_x + lens_r, lens_y + lens_r)],
        fill=(11, 13, 20, 255), outline=(74, 222, 128, 200), width=max(1, size // 64)
    )
    # 镜头内圈
    inner_r = size * 0.06
    draw.ellipse(
        [(lens_x - inner_r, lens_y - inner_r), (lens_x + inner_r, lens_y + inner_r)],
        fill=(74, 222, 128, 180)
    )

    # 闪光灯
    flash_x = bx2 - size * 0.08
    flash_y = by1 - size * 0.04
    flash_s = size * 0.04
    draw.ellipse(
        [(flash_x - flash_s, flash_y - flash_s), (flash_x + flash_s, flash_y + flash_s)],
        fill=(251, 191, 36, 220)  # #fbbf24
    )

    # SD 卡符号（底部）
    sd_y = size * 0.78
    sd_w = size * 0.18
    sd_h = size * 0.06
    sd_x1 = cx - sd_w / 2
    sd_x2 = cx + sd_w / 2
    sd_y1 = sd_y - sd_h / 2
    sd_y2 = sd_y + sd_h / 2
    draw.rounded_rectangle(
        [(sd_x1, sd_y1), (sd_x2, sd_y2)], radius=max(1, size // 80),
        fill=(100, 116, 139, 200)
    )
    # SD 卡缺口
    notch_w = size * 0.04
    notch_x1 = cx - notch_w / 2
    draw.rectangle(
        [(notch_x1, sd_y1), (notch_x1 + notch_w, sd_y1 + sd_h * 0.5)],
        fill=bg_color
    )

    return img


def main():
    os.makedirs(ICONSET, exist_ok=True)

    for px, name in SIZES:
        img = draw_icon(px)
        path = os.path.join(ICONSET, f"icon_{name}.png")
        img.save(path)
        print(f"  ✓ {name} ({px}x{px})")

    # 用 iconutil 转 .icns
    subprocess.run(
        ["iconutil", "-c", "icns", ICONSET, "-o", OUTPUT],
        check=True
    )
    print(f"\n✅ 图标生成完成: {OUTPUT}")
    print(f"   大小: {os.path.getsize(OUTPUT) / 1024:.1f} KB")

    # 清理
    import shutil
    shutil.rmtree(ICONSET, ignore_errors=True)


if __name__ == "__main__":
    main()
