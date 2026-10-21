"""影序 桌面本地窗口入口：启动本地服务并嵌入原生 WebView（macOS WebKit / Windows WebView2），而不是打开浏览器。"""
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _wait_until_ready(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{url}/api/status", timeout=0.5).read()
            return True
        except Exception:
            time.sleep(0.15)
    return False


def _make_console_output_encoding_safe() -> None:
    """Keep localized diagnostics from crashing background threads on legacy Windows code pages."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(errors="backslashreplace")
        except (OSError, ValueError):
            pass


def _write_json_atomically(path: Path, payload: dict) -> None:
    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _run_windows_ui_probe(window, base_url: str, report_path: str) -> None:
    """Exercise the real pywebview window only in the Windows VM E2E job."""
    results = []

    def record(ok: bool, name: str, detail: str = "") -> None:
        results.append({"ok": bool(ok), "name": name, "detail": detail})

    def snapshot():
        return window.evaluate_js(
            r"""(() => ({
              url: location.href,
              title: document.title,
              navLabels: Array.from(document.querySelectorAll('.sidebar-nav .nav-label'))
                .map(node => node.textContent.trim()),
              activeNav: document.querySelector('.sidebar-nav .nav-item.active')?.getAttribute('href') || '',
              mainMetrics: (() => {
                const main = document.querySelector('#mainContent.main');
                const rect = main?.getBoundingClientRect();
                return {
                  found: Boolean(main),
                  width: rect?.width || 0,
                  height: rect?.height || 0,
                  textLength: (main?.innerText || '').trim().length,
                };
              })(),
            }))()"""
        )

    try:
        deadline = time.monotonic() + 40
        initial = None
        while time.monotonic() < deadline:
            try:
                current_url = window.get_current_url() or ""
                if current_url.startswith(base_url):
                    state = snapshot()
                    if state and state.get("navLabels"):
                        initial = state
                        break
            except Exception:
                pass
            time.sleep(0.25)

        expected = ["复制新内容", "转移老内容", "归档记录", "偏好设置"]
        record(initial is not None, "pywebview 加载桌面工作台", str((initial or {}).get("url", "")))
        if initial:
            record(initial.get("title") == "影序 YINGXU", "窗口显示影序标题", str(initial.get("title")))
            record(initial.get("navLabels") == expected, "侧边栏四个主要页面可见", str(initial.get("navLabels")))
            main = initial.get("mainMetrics") or {}
            main_visible = (
                main.get("found") is True
                and main.get("width", 0) > 0
                and main.get("height", 0) > 0
                and main.get("textLength", 0) > 0
            )
            record(main_visible, "主工作区已渲染", json.dumps(main, ensure_ascii=False))

            for route, label in (("/history", "归档记录"), ("/settings", "偏好设置")):
                window.evaluate_js(
                    f"document.querySelector(\".sidebar-nav a[href='{route}']\")?.click(); true;"
                )
                route_deadline = time.monotonic() + 15
                state = None
                while time.monotonic() < route_deadline:
                    try:
                        state = snapshot()
                        if state and state.get("url", "").split("?", 1)[0].rstrip("/").endswith(route):
                            break
                    except Exception:
                        pass
                    time.sleep(0.25)
                record(bool(state and state.get("url", "").split("?", 1)[0].rstrip("/").endswith(route)),
                       f"点击侧边栏打开{label}", str((state or {}).get("url", "")))
                record(bool(state and state.get("activeNav") == route),
                       f"{label}导航状态正确", str((state or {}).get("activeNav", "")))
    except Exception as error:
        record(False, "pywebview UI probe 未处理异常", f"{type(error).__name__}: {error}")
    finally:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomically(path, {"passed": bool(results) and all(r["ok"] for r in results), "results": results})


def main():
    _make_console_output_encoding_safe()
    from smb.server import main as server_main
    from smb.config import config

    # Deterministic packaged-service mode for Windows runner E2E. Normal desktop
    # launches continue through the native pywebview window below.
    if os.environ.get("YINGXU_E2E_HEADLESS") == "1":
        server_main(open_browser=False, host_override="127.0.0.1")
        return

    import webview

    url = f"http://127.0.0.1:{config.web_port}"
    threading.Thread(
        target=server_main,
        # 桌面页仍只通过 127.0.0.1 打开；监听局域网是为了经过配对的 Pocket。
        kwargs={"open_browser": False, "host_override": "0.0.0.0"},
        daemon=True,
        name="yingxu-local-server",
    ).start()

    # 先显示轻量启动页，再切入工作台，避免出现一段黑屏。
    splash = """<!doctype html><html><head><meta charset='utf-8'><style>
    html,body{margin:0;width:100%;height:100%;background:#0a0a0b;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
    body{display:grid;place-items:center}.box{text-align:center}.logo{width:64px;height:64px;margin:0 auto 20px;border:1px solid #4ade80;border-radius:18px;display:grid;place-items:center;color:#4ade80;font-size:28px;box-shadow:0 0 32px rgba(74,222,128,.16)}
    h1{font-size:20px;letter-spacing:.08em;margin:0 0 9px}.sub{color:#8b93a1;font-size:13px}.bar{width:150px;height:3px;margin:22px auto 0;background:#1b2220;border-radius:3px;overflow:hidden}.bar:after{content:'';display:block;width:44%;height:100%;background:#4ade80;border-radius:3px;animation:load 1s ease-in-out infinite alternate}@keyframes load{to{transform:translateX(240%)}}
    </style></head><body><div class='box'><div class='logo'>▣</div><h1>影序 YINGXU</h1><div class='sub'>正在准备本地工作台</div><div class='bar'></div></div></body></html>"""
    window = webview.create_window(
        "影序 YINGXU",
        html=splash,
        width=1320,
        height=860,
        min_size=(1040, 700),
        confirm_close=True,
        background_color="#0a0a0b",
    )
    # Windows: 设置窗口图标
    if sys.platform.startswith("win"):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            window.icon = icon_path

    def load_workbench():
        if _wait_until_ready(url):
            window.load_url(url)
            report_path = os.environ.get("YINGXU_E2E_UI_REPORT")
            if report_path:
                threading.Thread(
                    target=_run_windows_ui_probe,
                    args=(window, url, report_path),
                    daemon=True,
                    name="yingxu-windows-ui-e2e",
                ).start()
        else:
            window.load_html("<body style='background:#0a0a0b;color:#fecaca;font-family:-apple-system,'Segoe UI',sans-serif;padding:48px'><h2>影序启动失败</h2><p>本地服务未能在 15 秒内启动，请退出后重试。</p></body>")

    # macOS 显式用 cocoa；Windows/Linux 自动选择（Windows 优先 WebView2/edgechromium）
    gui = "cocoa" if sys.platform == "darwin" else None
    webview.start(load_workbench, gui=gui)


if __name__ == "__main__":
    main()
