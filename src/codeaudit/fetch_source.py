"""为开源组件准备本地源码目录（只读审计用）。

支持：
- 已有本地 path
- git URL（浅克隆到缓存目录）

不自动对未授权私有仓库爆破；无 source 时返回 needs_source。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path


def cache_root() -> Path:
    env = os.environ.get("CODEAUDIT_SOURCE_CACHE")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".chuhaijian" / "source-cache"


def resolve_source(
    *,
    name: str,
    version: str,
    source_path: str | None = None,
    source_url: str | None = None,
) -> tuple[str, Path | None, str]:
    """返回 (status, path, detail)。

    status: ready | needs_source | error
    """
    if source_path:
        p = Path(source_path).expanduser().resolve()
        if p.is_dir():
            return "ready", p, "local_path"
        return "error", None, f"路径不存在: {p}"

    if source_url:
        url = source_url.strip()
        if not (url.startswith("https://") or url.startswith("git@")):
            return "error", None, "仅支持 https git URL 或本地 path"
        dest = cache_root() / _slug(name, version, url)
        if dest.is_dir() and any(dest.iterdir()):
            return "ready", dest, "cache_hit"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", url, str(dest)],
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
            return "ready", dest, "cloned"
        except FileNotFoundError:
            return "error", None, "系统未安装 git"
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or str(e))[:300]
            return "error", None, f"git clone 失败: {err}"
        except subprocess.TimeoutExpired:
            return "error", None, "git clone 超时"

    return "needs_source", None, "清单未提供 source_path / source_url"


def _slug(name: str, version: str, url: str) -> str:
    h = hashlib.sha256(f"{name}|{version}|{url}".encode()).hexdigest()[:12]
    safe = "".join(c if c.isalnum() or c in "-_." else "-" for c in f"{name}-{version}")[:40]
    return f"{safe}-{h}"
