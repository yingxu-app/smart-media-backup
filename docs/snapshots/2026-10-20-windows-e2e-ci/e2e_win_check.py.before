# -*- coding: utf-8 -*-
"""影序 YINGXU — Windows 端到端真实备份验收（模拟来源卡，隔离配置目录）。

不触碰用户真实配置：SMB_CONFIG_DIR 指向临时目录。
产物全部落在临时目录，验证完可整体删除。
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "smart-media-backup")
sys.path.insert(0, PROJ)

WORK = tempfile.mkdtemp(prefix="yingxu-e2e-")
CONFIG_DIR = os.path.join(WORK, "config")
SOURCE = os.path.join(WORK, "FAKE_SD")
TARGET = os.path.join(WORK, "backup-target")
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(TARGET, exist_ok=True)

# 必须在 import smb 之前设置，隔离真实 ~/.config/smb
os.environ["SMB_CONFIG_DIR"] = CONFIG_DIR

_PORT = 8098
BASE = f"http://127.0.0.1:{_PORT}"
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))

results = []


def log(ok, name, detail=""):
    results.append({"ok": ok, "name": name, "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def req(method, path, payload=None, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    h = {"User-Agent": "yingxu-e2e"}
    if data:
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode()


def make_fakesd():
    """造一张假的相机卡：3 个设备目录、照片/视频混合、含一个 RAW。"""
    from PIL import Image

    for dev, sub in [("Sony ILCE-7M4", "100MSDCF"), ("DJI Mavic 3", "DCIM")]:
        d = os.path.join(SOURCE, dev, sub) if dev.startswith("Sony") else os.path.join(SOURCE, "DCIM")
        os.makedirs(d, exist_ok=True)
        for i in range(4):
            img = Image.new("RGB", (64, 48), (i * 40 % 255, 90, 160))
            img.save(os.path.join(d, f"DSC0{1000 + i}.JPG"), "JPEG")
    # 一个 RAW 占位
    with open(os.path.join(SOURCE, "Sony ILCE-7M4", "100MSDCF", "DSC0999.ARW"), "wb") as f:
        f.write(b"II*\x00" + os.urandom(4096))
    # 一个视频
    vid = os.path.join(SOURCE, "DCIM", "C0001.MP4")
    with open(vid, "wb") as f:
        f.write(os.urandom(512 * 1024))
    total = sum(len(fs) for _r, _d, fs in os.walk(SOURCE))
    return total


def start_server():
    from smb import server as srv
    srv._open_browser_on_start = False
    threading.Thread(
        target=lambda: srv.socketio.run(srv.app, host="127.0.0.1", port=_PORT,
                                        debug=False, allow_unsafe_werkzeug=True),
        daemon=True, name="e2e-server").start()
    for _ in range(60):
        if req("GET", "/api/health", timeout=1)[0]:
            return True
        time.sleep(0.25)
    return False


def tree(root):
    out = []
    for r, ds, fs in os.walk(root):
        rel = os.path.relpath(r, root)
        for f in fs:
            out.append(os.path.join(rel, f).replace("\\", "/"))
    return sorted(out)


def main():
    print("=" * 78)
    print("影序 YINGXU — Windows 端到端真实备份验收")
    print(f"工作目录: {WORK}")
    print("=" * 78)

    n = make_fakesd()
    print(f"模拟来源卡已生成: {n} 个文件\n")

    if not start_server():
        print("服务启动失败")
        return 1
    print("服务就绪\n")

    TERMINAL = ("done", "completed", "partial", "failed", "error", "cancelled")

    def wait_done(limit=240):
        st = {}
        for _ in range(limit):
            c, b = req("GET", "/api/status", timeout=10)
            try:
                st = json.loads(b).get("progress", {})
            except Exception:
                st = {}
            if st.get("status") in TERMINAL:
                return st
            time.sleep(0.25)
        return st

    # 1) 扫描（离线，不应触发 AI）
    # 说明：/api/scan 接受存在的目录作为来源（盘符根或手动选择的本地文件夹），
    # 只有真正不存在的路径才会被拒绝。这里用临时目录模拟来源，应能正常扫描。
    code, body = req("POST", "/api/scan", payload={"mount_point": SOURCE})
    scan = json.loads(body) if code == 200 else {}
    log(code == 200, "扫描接口可响应", f"HTTP {code}")
    log("error" not in scan, "来源目录被接受并扫描（含手动选择的本地文件夹）",
        f"error={scan.get('error')!r} files={len(scan.get('files') or [])}")

    # 不存在的路径必须被明确拒绝，不能静默吞掉。
    code2, body2 = req("POST", "/api/scan", payload={"mount_point": SOURCE + "-不存在"})
    log(code2 == 200 and "error" in json.loads(body2 or b"{}"),
        "不存在的来源路径被明确拒绝", f"HTTP {code2}")

    # 2) 启动备份
    payload = {
        "mount_point": SOURCE,
        "event_name": "Windows验收测试",
        "backup_root": TARGET,
        "sort_order": ["date", "device", "type"],
    }
    code, body = req("POST", "/api/start_backup", payload)
    log(code == 200, "启动备份请求", f"HTTP {code} {body[:120]!r}")

    # 3) 等完成
    status = wait_done()

    st = status.get("status")
    log(st == "done", "备份任务完成", f"status={st} error={status.get('error_message')!r}")
    log(status.get("copied_files", 0) == n,
        "复制文件数正确", f"copied={status.get('copied_files')} 期望={n}")
    # 实时进度载荷现在应含校验计数：完成阶段会把 verified/failed 写入进度。
    log(status.get("verified_files", -1) == n and status.get("failed_files", -1) == 0,
        "实时进度载荷含校验计数", f"verified={status.get('verified_files')} failed={status.get('failed_files')}")

    # 4) 目标目录结构
    tfiles = tree(TARGET)
    media = [f for f in tfiles if not f.endswith("checksums.json") and not f.startswith("_Windows预览/")]
    log(len(media) == n, "目标文件数量与来源一致", f"target={len(media)} source={n}")
    checks = [f for f in tfiles if f.endswith("checksums.json")]
    log(len(checks) >= 1, "生成 SHA256 校验清单", f"{len(checks)} 个 checksums.json")
    previews = [f for f in tfiles if "_Windows预览" in f]
    log(len(previews) > 0, "生成 Windows 缩略图预览树", f"{len(previews)} 个预览文件")
    log(any("/照片/" in f or "/视频/" in f for f in tfiles) or any("照片" in f for f in tfiles),
        "按 照片/视频 分类", "")
    print("    目标树样例:")
    for f in tfiles[:12]:
        print("      " + f)

    # 校验结果以报告为准（实时进度载荷不含 verified/failed 字段）
    reports = list(Path(CONFIG_DIR).glob("reports/backup-*/report_*.json"))
    verified = failed = -1
    if reports:
        rep = json.loads(sorted(reports)[-1].read_text(encoding="utf-8"))
        verified = rep.get("verified_files", -1)
        failed = rep.get("failed_files", -1)
    log(verified == n and failed == 0, "SHA-256 校验全部通过（报告）",
        f"verified={verified} failed={failed} 期望={n}")

    # 5) 增量跳过（同目标同事件再跑一次）
    first_media = sorted(f for f in tree(TARGET) if not f.endswith("checksums.json"))
    req("POST", "/api/start_backup", payload)
    status = wait_done()
    log(status.get("copied_files", -1) == 0, "二次备份零重复复制",
        f"copied={status.get('copied_files')} skipped={status.get('skipped_files')}")
    second_media = sorted(f for f in tree(TARGET) if not f.endswith("checksums.json"))
    log(second_media == first_media, "二次备份未新增/改名任何文件",
        f"首轮={len(first_media)} 个，二轮={len(second_media)} 个")
    if second_media != first_media:
        print("    新增:", sorted(set(second_media) - set(first_media))[:8])
        print("    消失:", sorted(set(first_media) - set(second_media))[:8])

    # 6) 历史与报告
    c, b = req("GET", "/api/history")
    hist = json.loads(b)
    items = hist.get("backups") or hist.get("items") or []
    log(len(items) >= 1, "历史记录已写入", f"{len(items)} 条")
    if items:
        bid = items[0].get("id")
        for fmt in ("json", "csv", "markdown"):
            c2, b2 = req("GET", f"/api/history/{bid}/report/{fmt}")
            log(c2 == 200 and len(b2) > 20, f"导出 {fmt} 报告", f"HTTP {c2} {len(b2)}B")
        c3, b3 = req("GET", f"/api/history/{bid}")
        log(c3 == 200, "历史详情可读", f"HTTP {c3}")

    # 7) 来源未被改动
    src_after = tree(SOURCE)
    log(len(src_after) == n, "原卡素材零改动", f"source={len(src_after)} 期望={n}")

    print()
    print("=" * 78)
    bad = [r for r in results if not r["ok"]]
    print(f"合计 {len(results)} 项，通过 {len(results) - len(bad)}，失败 {len(bad)}")
    for r in bad:
        print(f"  FAIL {r['name']} — {r['detail']}")
    print("=" * 78)

    out = os.path.join(ROOT, "e2e-result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"work_dir": WORK, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"报告: {out}")
    print(f"现场保留在: {WORK}")
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
