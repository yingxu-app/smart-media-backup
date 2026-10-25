#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查文档里的相对链接是否还能点开。

在仓库任意位置执行：

    python scripts/check_links.py          # 检查全部 *.md
    python scripts/check_links.py docs/    # 只查某个目录

退出码 0 表示全部可达，1 表示有断链。CI 的 Reliability tests 会跑这一步。

只检查仓库内的相对路径；http(s)、锚点、mailto 一律跳过。指向 `release/`、
`docs/snapshots/`、`docs/site-history/` 的路径属于「本机工作产物或已归档」，
不计为失败，只在末尾单独列出来。
"""

from __future__ import annotations

import os
import posixpath
import re
import subprocess
import sys

LINK_RE = re.compile(r"\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
REFDEF_RE = re.compile(r"(?m)^\[[^\]]+\]:\s*(\S+)")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")

SKIP_SCHEMES = ("http://", "https://", "mailto:", "#", "/", "<", "data:")
# 本机产物或已归档路径：文件不在库里是正常的
TOLERATED_PREFIXES = ("release/", "docs/snapshots/", "docs/site-history/", "artifacts/")


def git_files() -> list[str]:
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if out.returncode != 0:
        raise SystemExit("这里不是 git 仓库，请在仓库根目录执行。")
    return [p for p in out.stdout.split("\0") if p]


def normalize(target: str) -> str:
    target = target.strip()
    if "#" in target:
        target = target.split("#", 1)[0]
    return target


def main() -> int:
    only = os.path.normpath(sys.argv[1]).replace(os.sep, "/") if len(sys.argv) > 1 else ""
    files = [p for p in git_files() if p.endswith(".md")]
    if only and only != ".":
        files = [p for p in files if p.startswith(only.rstrip("/") + "/") or p == only]

    known = set(git_files())
    broken: list[tuple[str, str]] = []
    tolerated: list[tuple[str, str]] = []

    for path in files:
        if not os.path.exists(path):
            continue
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8", "surrogateescape")
        base = posixpath.dirname(path)

        targets = LINK_RE.findall(text) + REFDEF_RE.findall(text)
        # 反引号里写死的仓库路径也顺手校验一下
        targets += [
            code.strip()
            for code in INLINE_CODE_RE.findall(text)
            if "/" in code and code.endswith(".md")
        ]

        for raw in targets:
            target = normalize(raw)
            if not target or target.startswith(SKIP_SCHEMES) or "*" in target:
                continue
            candidates = [posixpath.normpath(posixpath.join(base, target))]
            if not target.startswith(("./", "../")):
                candidates.append(posixpath.normpath(target))

            if any(c in known or os.path.exists(c) for c in candidates):
                continue

            norm = candidates[0]
            if norm.startswith(TOLERATED_PREFIXES) or any(
                target.startswith(p) for p in TOLERATED_PREFIXES
            ):
                tolerated.append((path, raw))
                continue
            broken.append((path, raw))

    if broken:
        print(f"发现 {len(broken)} 条断链：\n")
        for path, target in broken:
            print(f"  {path}\n    -> {target}")
        print()

    if tolerated:
        print(f"{len(tolerated)} 条指向本机产物或已归档目录（不计失败）：")
        for path, target in tolerated[:10]:
            print(f"  {path} -> {target}")
        if len(tolerated) > 10:
            print(f"  ... 另有 {len(tolerated) - 10} 条")
        print()

    print(f"检查 {len(files)} 个 markdown 文件：{len(broken)} 条断链，{len(tolerated)} 条容忍。")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
