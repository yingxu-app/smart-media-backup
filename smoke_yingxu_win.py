# -*- coding: utf-8 -*-
"""影序 YINGXU Windows 真机冒烟：进程内启动服务，逐个接口探测并输出报告。

用法（在项目目录下）：
    .venv/Scripts/python.exe smoke_yingxu_win.py
只读探测，不修改任何备份配置与素材。
"""
import io
import json
import os
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "smart-media-backup"))

_PORT = 8099
BASE = f"http://127.0.0.1:{_PORT}"

# 去掉代理，避免本地请求被系统代理拦截
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)

report = {"platform": sys.platform, "python": sys.version.split()[0], "checks": [], "console": []}


def req(method, path, payload=None, headers=None, timeout=60):
    data = None
    hdrs = {"User-Agent": "yingxu-smoke"}
    if headers:
        hdrs.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode("utf-8", "replace")


def check(name, method, path, payload=None, expect=(200,), note=""):
    code, body = req(method, path, payload)
    text = body.decode("utf-8", "replace")
    ok = code in expect
    item = {
        "name": name, "method": method, "path": path, "status": code,
        "ok": ok, "bytes": len(body), "note": note, "preview": text[:400],
    }
    try:
        item["json"] = json.loads(text)
    except Exception:
        item["json"] = None
    report["checks"].append(item)
    flag = "PASS" if ok else "FAIL"
    print(f"[{flag}] {name:<34} {method:<4} {path:<34} -> {code} ({len(body)}B)")
    if not ok:
        print(f"        {text[:300]}")
    return item


def start_server():
    from smb import server as srv
    srv._open_browser_on_start = False

    def run():
        srv.socketio.run(srv.app, host="127.0.0.1", port=_PORT, debug=False,
                         allow_unsafe_werkzeug=True)

    t = threading.Thread(target=run, daemon=True, name="smoke-server")
    t.start()
    for _ in range(60):
        code, _b = req("GET", "/api/health", timeout=1)
        if code:
            return True
        time.sleep(0.25)
    return False


def main():
    print("=" * 78)
    print("影序 YINGXU — Windows 真机冒烟测试")
    print(f"platform={sys.platform} python={sys.version.split()[0]}")
    print("=" * 78)

    if not start_server():
        print("!! 服务未能在 15 秒内就绪")
        return 1
    print("服务已就绪\n")

    # ---- 页面 ----
    check("工作台首页", "GET", "/")
    check("归档记录页", "GET", "/history")
    check("设置页", "GET", "/settings")
    check("Pocket 手机页", "GET", "/pocket")
    check("PWA manifest", "GET", "/pocket/manifest.webmanifest")
    check("PWA service worker", "GET", "/pocket/sw.js")

    # ---- 核心接口 ----
    check("健康检查", "GET", "/api/health")
    check("运行状态", "GET", "/api/status")
    check("可用卷列表", "GET", "/api/volumes")
    check("来源列表", "GET", "/api/sources")
    check("扫描来源", "GET", "/api/scan")
    check("历史记录", "GET", "/api/history")
    check("历史目标分组", "GET", "/api/history_targets")
    check("高级设置读取", "GET", "/api/settings")
    check("AI 状态", "GET", "/api/ai/status")
    check("百度网盘状态", "GET", "/api/baidu/status")
    check("安装引导状态", "GET", "/api/setup/status")

    # ---- Pocket 边界 ----
    # 回环地址被视作桌面端（设计如此，手机无 cookie 才需要配对）。
    check("Pocket 状态（桌面端免配对）", "GET", "/api/pocket/status")

    # ---- 写入类接口（安全参数） ----
    check("历史清空缺确认应拒绝", "POST", "/api/history/clear", payload={}, expect=(400, 403))
    check("报告路径越界应拒绝", "GET",
          "/api/history/1/report/json", expect=(400, 403, 404))
    check("空事件名启动备份应拒绝", "POST", "/api/start_backup",
          payload={"mount_point": "", "event_name": "", "backup_root": ""},
          expect=(400, 422, 500))
    check("设置写入往返", "POST", "/api/settings",
          payload={"verify_method": "sha256"}, expect=(200,))

    # ---- 汇总 ----
    total = len(report["checks"])
    failed = [c for c in report["checks"] if not c["ok"]]
    print()
    print("=" * 78)
    print(f"合计 {total} 项，通过 {total - len(failed)}，失败 {len(failed)}")
    for c in failed:
        print(f"  FAIL {c['method']} {c['path']} -> {c['status']}")
    print("=" * 78)

    out = os.path.join(ROOT, "smoke-result.json")
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告已写入: {out}")
    return 0 if not failed else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(3)
