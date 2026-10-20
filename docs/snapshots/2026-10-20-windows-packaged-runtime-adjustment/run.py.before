"""影序 桌面本地窗口入口：启动本地服务并嵌入原生 WebView（macOS WebKit / Windows WebView2），而不是打开浏览器。"""
import os
import sys
import threading
import time
import urllib.request

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


def main():
    from smb.server import main as server_main
    from smb.config import config
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
        else:
            window.load_html("<body style='background:#0a0a0b;color:#fecaca;font-family:-apple-system,'Segoe UI',sans-serif;padding:48px'><h2>影序启动失败</h2><p>本地服务未能在 15 秒内启动，请退出后重试。</p></body>")

    # macOS 显式用 cocoa；Windows/Linux 自动选择（Windows 优先 WebView2/edgechromium）
    gui = "cocoa" if sys.platform == "darwin" else None
    webview.start(load_workbench, gui=gui)


if __name__ == "__main__":
    main()
