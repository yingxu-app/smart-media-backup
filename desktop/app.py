"""
Entry point for the macOS .app bundle.
Launches the Flask server and opens the default browser.
"""
import sys
import os
import webbrowser
import threading

# Ensure the project root is on the path
_app_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_app_dir, "..")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Import and run the SMB server
from smb.server import app, socketio, config
from smb.detector import SDCardWatcher
from smb import db

def main():
    # Init DB
    db.init_db()

    # Start SD card watcher in background
    watcher = SDCardWatcher(interval=2.0)
    watcher.start()

    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{config.web_port}")

    threading.Thread(target=open_browser, daemon=True).start()

    # Start Flask-SocketIO server
    print(f"""
╔══════════════════════════════════════════╗
║     🖼  Smart Media Backup  v1.0         ║
║                                          ║
║  Smart Media Backup 已启动               ║
║  浏览器将自动打开                        ║
║                                          ║
║  如需手动访问:                           ║
║    http://localhost:{config.web_port}      ║
║                                          ║
║  关闭此窗口即停止服务                     ║
╚══════════════════════════════════════════╝
""")

    host = "0.0.0.0" if config.pocket_lan_enabled else config.web_host
    socketio.run(app, host=host, port=config.web_port,
                 debug=False, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main()
