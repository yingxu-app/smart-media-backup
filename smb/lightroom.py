"""Lightroom 目录集成 — 生成可导入的目录结构"""
import os
import json
from pathlib import Path
from datetime import datetime


def generate_lr_catalog(backup_root: str, event_name: str, devices: list[dict],
                        total_files: int, backup_time: str) -> str:
    """生成 Lightroom 可导入的 XMP 侧边栏 + 目录结构说明"""
    # 生成 XMP 关键词文件
    xmp_dir = Path(backup_root) / "_Lightroom" / event_name
    xmp_dir.mkdir(parents=True, exist_ok=True)

    # 写入目录结构说明
    readme = f"""# Lightroom 导入指南 — {event_name}

备份时间: {backup_time}
文件总数: {total_files}

## 目录结构

{backup_root}/
"""
    for d in devices:
        name = d.get("name", "Unknown")
        readme += f"""├── {name}/
│   ├── {event_name}/
│   │   ├── 照片/    ← RAW + 照片文件
│   │   ├── 视频/    ← 视频文件
│   │   └── 废片待确认/  ← AI筛选的废片
"""
    readme += """
## Lightroom 导入步骤
1. 打开 Lightroom → 文件 → 导入照片和视频
2. 源: 选择上面的设备目录
3. 目标: 选择"移动到新位置"并指定目录
4. 导入预设: 可选择"添加关键词" → 输入事件名称
"""

    readme_path = xmp_dir / "导入指南.md"
    readme_path.write_text(readme, encoding="utf-8")

    # 生成元数据 JSON（可用 LR 插件导入）
    meta = {
        "event": event_name,
        "date": backup_time,
        "total_files": total_files,
        "devices": devices,
        "keywords": [event_name],
    }
    meta_path = xmp_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    return str(xmp_dir)
