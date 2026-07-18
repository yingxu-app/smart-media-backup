"""
百度网盘自动上传模块
────────────────
流程:
  1. 用户在 Web 设置页填入 API Key + Secret Key
  2. 点击授权 → 浏览器打开百度 OAuth 页面 → 拿到授权码
  3. 粘贴授权码 → 程序换到 access_token (有效期1个月)
  4. 备份完成后自动触发上传
"""

import os
import json
import time
import hashlib
import threading
import requests
from pathlib import Path
from typing import Optional, Callable

from .config import CONFIG_DIR

# 百度 OAuth 端点
BAIDU_AUTH_URL = "https://openapi.baidu.com/oauth/2.0/authorize"
BAIDU_TOKEN_URL = "https://openapi.baidu.com/oauth/2.0/token"
BAIDU_API_BASE = "https://pan.baidu.com/rest/2.0/xpan/file"

# Token 存储路径
TOKEN_PATH = CONFIG_DIR / "baidu_token.json"
BAIDU_SETTINGS_PATH = CONFIG_DIR / "baidu_settings.json"


class BaiduPan:
    """百度网盘客户端"""

    def __init__(self):
        self.api_key = ""
        self.secret_key = ""
        self.app_id = ""
        self.access_token = ""
        self.refresh_token = ""
        self.expires_at = 0
        self._load()

    # ──────────── 配置 ────────────

    def configure(self, api_key: str, secret_key: str, app_id: str = ""):
        """设置 API 凭证"""
        self.api_key = api_key
        self.secret_key = secret_key
        self.app_id = app_id
        self._save_settings()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key)

    def is_authorized(self) -> bool:
        return bool(self.access_token) and time.time() < self.expires_at

    def _load(self):
        """从磁盘加载配置"""
        if BAIDU_SETTINGS_PATH.exists():
            s = json.loads(BAIDU_SETTINGS_PATH.read_text())
            self.api_key = s.get("api_key", "")
            self.secret_key = s.get("secret_key", "")
            self.app_id = s.get("app_id", "")
        if TOKEN_PATH.exists():
            t = json.loads(TOKEN_PATH.read_text())
            self.access_token = t.get("access_token", "")
            self.refresh_token = t.get("refresh_token", "")
            self.expires_at = t.get("expires_at", 0)

    def _save_settings(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        BAIDU_SETTINGS_PATH.write_text(json.dumps({
            "api_key": self.api_key,
            "secret_key": self.secret_key,
            "app_id": self.app_id,
        }, indent=2, ensure_ascii=False))

    def _save_token(self, data: dict):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.access_token = data.get("access_token", "")
        self.refresh_token = data.get("refresh_token", "")
        # expires_in 秒，提前 10 分钟刷新
        expires_in = data.get("expires_in", 2592000)  # 默认 30 天
        self.expires_at = time.time() + expires_in - 600
        TOKEN_PATH.write_text(json.dumps({
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }, indent=2))

    # ──────────── OAuth 流程 ────────────

    def get_auth_url(self) -> str:
        """获取用户授权 URL（用户在浏览器打开）"""
        from urllib.parse import urlencode
        params = {
            "response_type": "code",
            "client_id": self.api_key,
            "redirect_uri": "oob",
            "scope": "basic,netdisk",
            "display": "page",
        }
        return f"{BAIDU_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> bool:
        """用户粘贴授权码 → 换 access_token"""
        try:
            resp = requests.post(BAIDU_TOKEN_URL, data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.api_key,
                "client_secret": self.secret_key,
                "redirect_uri": "oob",
            }, timeout=15)
            data = resp.json()
            if "access_token" in data:
                self._save_token(data)
                return True
            else:
                print(f"[百度] 授权失败: {data.get('error_description', data)}")
                return False
        except requests.RequestException as e:
            print(f"[百度] 网络错误: {e}")
            return False

    def refresh_access_token(self) -> bool:
        """刷新 access_token"""
        if not self.refresh_token:
            return False
        try:
            resp = requests.post(BAIDU_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            }, timeout=15)
            data = resp.json()
            if "access_token" in data:
                self._save_token(data)
                return True
            return False
        except requests.RequestException:
            return False

    # ──────────── API 请求 ────────────

    def _ensure_token(self) -> bool:
        """确保 token 有效，过期则刷新"""
        if self.is_authorized():
            return True
        if self.refresh_token:
            return self.refresh_access_token()
        return False

    def _api_get(self, params: dict) -> Optional[dict]:
        """GET 请求百度 API"""
        if not self._ensure_token():
            return None
        params["access_token"] = self.access_token
        try:
            resp = requests.get(BAIDU_API_BASE, params=params, timeout=15)
            return resp.json()
        except requests.RequestException as e:
            print(f"[百度] API 请求失败: {e}")
            return None

    def _api_post(self, params: dict, files=None, data=None) -> Optional[dict]:
        """POST 请求百度 API"""
        if not self._ensure_token():
            return None
        params["access_token"] = self.access_token
        url = f"{BAIDU_API_BASE}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        try:
            resp = requests.post(url, files=files, data=data, timeout=60)
            return resp.json()
        except requests.RequestException as e:
            print(f"[百度] API 请求失败: {e}")
            return None

    # ──────────── 文件操作 ────────────

    def list_files(self, dir_path: str = "/") -> list:
        """列出百度网盘目录下的文件"""
        result = self._api_get({
            "method": "list",
            "dir": dir_path,
            "order": "time",
            "desc": "1",
            "num": "100",
        })
        if result and "list" in result:
            return result["list"]
        return []

    def mkdir(self, dir_path: str) -> bool:
        """创建目录"""
        result = self._api_post({
            "method": "create",
        }, data={
            "path": dir_path,
            "size": "0",
            "isdir": "1",
            # 需要 URL 编码 block_list
            "block_list": "[]",
        })
        if result and result.get("errno") in (0, -9):  # -9 = 已存在
            return True
        return False

    def get_quota(self) -> dict:
        """获取网盘容量信息"""
        result = self._api_get({"method": "info"})
        if result:
            return {
                "total": result.get("total", 0),
                "used": result.get("used", 0),
                "free": result.get("total", 0) - result.get("used", 0),
            }
        return {"total": 0, "used": 0, "free": 0}

    def upload_file(self, local_path: str, remote_dir: str,
                    progress_callback: Optional[Callable] = None) -> bool:
        """
        上传单个文件到百度网盘。
        local_path: 本地文件路径
        remote_dir: 远程目录
        progress_callback: 进度回调 (bytes_copied, total_bytes)
        """
        if not os.path.isfile(local_path):
            return False

        file_size = os.path.getsize(local_path)
        file_name = os.path.basename(local_path)
        remote_path = f"{remote_dir.rstrip('/')}/{file_name}"

        # 小文件直接上传 (< 4MB)
        if file_size < 4 * 1024 * 1024:
            return self._upload_small(local_path, remote_path)

        # 大文件分片上传
        return self._upload_slice(local_path, remote_path, file_size, progress_callback)

    def _upload_small(self, local_path: str, remote_path: str) -> bool:
        """小文件直接上传"""
        with open(local_path, "rb") as f:
            result = self._api_post({
                "method": "upload",
                "path": remote_path,
            }, files={"file": f})
        return result is not None and result.get("errno") == 0

    def _upload_slice(self, local_path: str, remote_path: str,
                      file_size: int, progress_callback=None) -> bool:
        """大文件分片上传（百度 superfile 模式）"""
        import math

        # 1. precreate — 预创建文件
        slice_size = 4 * 1024 * 1024  # 4MB 分片
        total_slices = math.ceil(file_size / slice_size)

        # 计算文件 MD5（百度要求）
        file_md5 = self._md5_file(local_path)

        result = self._api_post({
            "method": "precreate",
        }, data={
            "path": remote_path,
            "size": str(file_size),
            "isdir": "0",
            "block_list": "[]",
            "autoinit": "1",
        })

        if not result or result.get("errno") not in (0, -9):
            return False

        upload_id = result.get("uploadid", "")

        # 2. upload — 逐个分片上传
        uploaded = 0
        with open(local_path, "rb") as f:
            for part_num in range(total_slices):
                chunk = f.read(slice_size)
                part_md5 = hashlib.md5(chunk).hexdigest()

                retry = 3
                while retry > 0:
                    up_result = self._api_post({
                        "method": "upload",
                        "type": "tmpfile",
                        "path": remote_path,
                        "uploadid": upload_id,
                        "partseq": str(part_num),
                    }, files={"file": chunk})
                    if up_result and up_result.get("errno") == 0:
                        uploaded += len(chunk)
                        if progress_callback:
                            progress_callback(uploaded, file_size)
                        break
                    retry -= 1
                    time.sleep(1)

                if retry == 0:
                    return False

        # 3. create — 合并文件
        block_list = []
        with open(local_path, "rb") as f:
            for _ in range(total_slices):
                chunk = f.read(slice_size)
                block_list.append(hashlib.md5(chunk).hexdigest())

        result = self._api_post({
            "method": "create",
        }, data={
            "path": remote_path,
            "size": str(file_size),
            "isdir": "0",
            "uploadid": upload_id,
            "block_list": json.dumps(block_list),
        })

        return result is not None and result.get("errno") == 0

    # ──────────── 工具 ────────────

    @staticmethod
    def _md5_file(filepath: str) -> str:
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()


# 全局单例
baidu = BaiduPan()
