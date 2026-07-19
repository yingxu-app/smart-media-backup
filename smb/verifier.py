"""SHA256 校验器"""
import hashlib
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


class ChecksumVerifier:
    """文件校验和生成与验证"""

    def __init__(self):
        pass

    def hash_file(self, filepath: str) -> str:
        """计算文件 SHA256"""
        return self._hash_file(filepath)

    def _hash_file(self, filepath: str) -> str:
        sha = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                while True:
                    block = f.read(65536)
                    if not block:
                        break
                    sha.update(block)
            return sha.hexdigest()
        except OSError:
            return ""

    def generate_manifest(self, files: list[str], output_dir: str) -> str:
        """生成校验清单"""
        manifest = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            fut_map = {pool.submit(self._hash_file, fp): fp for fp in files}
            for fut in as_completed(fut_map):
                fp = fut_map[fut]
                rel = os.path.relpath(fp, output_dir)
                h = fut.result()
                if h:
                    manifest[rel] = h

        manifest_path = os.path.join(output_dir, "checksums.json")
        Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
        Path(manifest_path).write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
        )
        return manifest_path

    def verify_single(self, src: str, dst: str, src_hash: str = "") -> tuple:
        """验证单个源→目标文件，返回 (是否通过, 信息)"""
        if not src_hash:
            src_hash = self._hash_file(src)
        dst_hash = self._hash_file(dst)
        if not src_hash or not dst_hash:
            return False, "无法读取文件"
        ok = src_hash == dst_hash
        info = src_hash[:16] if ok else f"src={src_hash[:16]}... dst={dst_hash[:16]}..."
        return ok, info
