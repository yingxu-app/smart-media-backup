"""Upload all remaining project files to GitHub via API"""
import json, base64, subprocess, os, sys

REPO = "luguanlin20050927/smart-media-backup"
ROOT = os.path.expanduser("~/smart-media-backup")
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()

FILES = [
    "smb/__init__.py", "smb/server.py", "smb/config.py",
    "smb/backup.py", "smb/organizer.py", "smb/verifier.py",
    "smb/detector.py", "smb/db.py", "smb/cli.py",
    "smb/baidu.py", "smb/ai_namer.py",
    "smb/templates/base.html", "smb/templates/dashboard.html",
    "smb/templates/history.html", "smb/templates/settings.html",
    "smb/static/css/app.css", "smb/static/js/app.js",
    "smb/static/img/icon.svg",
    "website/index.html",
    "desktop/smb.spec", "desktop/smb-win.spec",
    "desktop/app.py", "desktop/setup.py",
    "scripts/generate_icon.py", "scripts/upload_github.py",
    ".gitignore",
]

for rel_path in FILES:
    abs_path = os.path.join(ROOT, rel_path)
    if not os.path.isfile(abs_path):
        print(f"  ⏭  {rel_path} (不存在)")
        continue

    with open(abs_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    data = json.dumps({"message": f"Add {rel_path}", "content": content})

    # Check if exists
    check = subprocess.run(
        ["curl", "-s", "-H", f"Authorization: Bearer {TOKEN}",
         f"https://api.github.com/repos/{REPO}/contents/{rel_path}"],
        capture_output=True, text=True
    )
    try:
        existing = json.loads(check.stdout)
        sha = existing.get("sha", "")
    except (json.JSONDecodeError, KeyError):
        sha = ""
    if sha:
        data_obj = json.loads(data)
        data_obj["sha"] = sha
        data = json.dumps(data_obj)

    result = subprocess.run(
        ["curl", "-s", "-X", "PUT",
         "-H", f"Authorization: Bearer {TOKEN}",
         "-H", "Accept: application/vnd.github.v3+json",
         f"https://api.github.com/repos/{REPO}/contents/{rel_path}",
         "-d", data],
        capture_output=True, text=True
    )

    try:
        resp = json.loads(result.stdout)
        if "content" in resp:
            print(f"  ✅ {rel_path}")
        else:
            msg = resp.get("message", "?")[:60]
            if "sha" in str(resp.get("message", "")):
                print(f"  ⚠️  {rel_path}: 需要 sha,重试中...")
                # Retry with sha from error
                import re
                sha_match = re.search(r'"sha":"([a-f0-9]+)"', result.stdout)
                if sha_match:
                    data_o = json.loads(data)
                    data_o["sha"] = sha_match.group(1)
                    retry = subprocess.run(
                        ["curl", "-s", "-X", "PUT",
                         "-H", f"Authorization: Bearer {TOKEN}",
                         "-H", "Accept: application/vnd.github.v3+json",
                         f"https://api.github.com/repos/{REPO}/contents/{rel_path}",
                         "-d", json.dumps(data_o)],
                        capture_output=True, text=True
                    )
                    r2 = json.loads(retry.stdout)
                    if "content" in r2:
                        print(f"  ✅ {rel_path} (重试成功)")
                    else:
                        print(f"  ❌ {rel_path}: {r2.get('message','?')[:60]}")
            else:
                print(f"  ❌ {rel_path}: {msg}")
    except json.JSONDecodeError:
        print(f"  ❌ {rel_path}: 响应解析失败")

print(f"\n✅ 上传完成")
