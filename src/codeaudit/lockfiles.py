"""从常见锁文件/清单提取依赖组件（只读，无网络）。

产出结构与 from-inventory 一致，便于：
  识别组件 → 查库 → 无则补 source 再审
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def extract_from_repo(repo: Path, max_deps: int = 500) -> list[dict[str, Any]]:
    repo = repo.resolve()
    comps: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(name: str, version: str, ecosystem: str, evidence: str, source_url: str | None = None) -> None:
        if not name or len(comps) >= max_deps:
            return
        key = f"{ecosystem}:{name}:{version}".lower()
        if key in seen:
            return
        seen.add(key)
        comps.append(
            {
                "name": name,
                "version": version or "unknown",
                "ecosystem": ecosystem,
                "evidence": [evidence],
                "source_url": source_url,
                "source_path": None,
            }
        )

    # package-lock.json (npm)
    for lock in repo.rglob("package-lock.json"):
        if _ignored(lock, repo):
            continue
        try:
            data = json.loads(lock.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            continue
        rel = str(lock.relative_to(repo))
        packages = data.get("packages") or {}
        if isinstance(packages, dict):
            for pkg_path, meta in packages.items():
                if not pkg_path or not isinstance(meta, dict):
                    continue
                name = meta.get("name")
                if not name and pkg_path.startswith("node_modules/"):
                    name = pkg_path.split("node_modules/")[-1]
                ver = str(meta.get("version") or "unknown")
                if name:
                    add(str(name), ver, "npm", rel)
        deps = data.get("dependencies") or {}
        if isinstance(deps, dict):
            _walk_npm_deps(deps, add, rel)

    # package.json (direct deps only, if no lock hit yet for name)
    for pkg in repo.rglob("package.json"):
        if _ignored(pkg, repo) or pkg.name != "package.json":
            continue
        if "node_modules" in pkg.parts:
            continue
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            continue
        rel = str(pkg.relative_to(repo))
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            block = data.get(section) or {}
            if not isinstance(block, dict):
                continue
            for name, ver in block.items():
                add(str(name), str(ver).lstrip("^~>="), "npm", f"{rel}:{section}")

    # requirements*.txt
    for req in list(repo.rglob("requirements.txt")) + list(repo.rglob("requirements-*.txt")):
        if _ignored(req, repo):
            continue
        rel = str(req.relative_to(repo))
        for line in req.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # package==1.2.3 / package>=1.0
            m = re.match(r"^([A-Za-z0-9_.-]+)\s*([=<>!~]+)\s*([A-Za-z0-9_.+-]+)", line)
            if m:
                add(m.group(1), m.group(3), "pypi", rel)
            else:
                name = re.split(r"[\s=<>!~\[]", line)[0]
                if name:
                    add(name, "unknown", "pypi", rel)

    # pyproject.toml dependencies (粗解析)
    for pyproject in repo.rglob("pyproject.toml"):
        if _ignored(pyproject, repo):
            continue
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        rel = str(pyproject.relative_to(repo))
        for m in re.finditer(
            r"['\"]([A-Za-z0-9_.-]+)([>=<~!]=?)([^'\"]+)['\"]",
            text,
        ):
            add(m.group(1), m.group(3).strip(), "pypi", rel)

    # go.mod
    for gomod in repo.rglob("go.mod"):
        if _ignored(gomod, repo):
            continue
        rel = str(gomod.relative_to(repo))
        for line in gomod.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("require "):
                # require path v1.2.3
                parts = line[len("require ") :].split()
                if len(parts) >= 2:
                    add(parts[0], parts[1], "go", rel)
            elif re.match(r"^[a-z0-9./\-]+\s+v\d", line) and not line.startswith("module "):
                parts = line.split()
                if len(parts) >= 2:
                    add(parts[0], parts[1], "go", rel)

    # Cargo.toml dependencies section (name only / simple version)
    for cargo in repo.rglob("Cargo.toml"):
        if _ignored(cargo, repo):
            continue
        rel = str(cargo.relative_to(repo))
        text = cargo.read_text(encoding="utf-8", errors="ignore")
        in_deps = False
        for line in text.splitlines():
            if re.match(r"\[.*dependencies.*\]", line):
                in_deps = True
                continue
            if line.startswith("[") and in_deps:
                in_deps = False
            if not in_deps:
                continue
            m = re.match(r"\s*([A-Za-z0-9_\-]+)\s*=\s*\"([^\"]+)\"", line)
            if m:
                add(m.group(1), m.group(2), "cargo", rel)

    return comps


def inventory_from_repo(repo: Path, max_deps: int = 500) -> dict[str, Any]:
    comps = extract_from_repo(repo, max_deps=max_deps)
    # 应用本体
    comps.insert(
        0,
        {
            "name": repo.name or "application",
            "version": "local",
            "ecosystem": "application",
            "evidence": ["repo_root"],
            "source_path": str(repo.resolve()),
            "source_url": None,
        },
    )
    return {
        "target": str(repo.resolve()),
        "source": "lockfile-scan",
        "components": comps,
    }


def _walk_npm_deps(deps: dict, add, rel: str, depth: int = 0) -> None:
    if depth > 6:
        return
    for name, meta in deps.items():
        if not isinstance(meta, dict):
            continue
        ver = str(meta.get("version") or "unknown")
        add(str(name), ver, "npm", rel)
        nested = meta.get("dependencies")
        if isinstance(nested, dict):
            _walk_npm_deps(nested, add, rel, depth + 1)


def _ignored(path: Path, root: Path) -> bool:
    parts = set(path.relative_to(root).parts)
    skip = {".git", "node_modules", "vendor", "dist", "build", ".venv", "venv", "target"}
    return bool(parts & skip)
