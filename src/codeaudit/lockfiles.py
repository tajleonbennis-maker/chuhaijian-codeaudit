"""从锁文件/清单解析依赖组件（只读，无网络）。

支持：
- package-lock.json / package.json (npm)
- requirements.txt / pyproject.toml 简单依赖行 (pypi)
- go.mod (go)
- Cargo.toml 依赖段 (crates，粗解析)
- pom.xml 依赖块 (maven，粗解析)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def parse_repo_deps(root: Path, max_packages: int = 500) -> list[dict[str, Any]]:
    root = root.resolve()
    comps: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(name: str, version: str, ecosystem: str, evidence: str) -> None:
        if not name or len(comps) >= max_packages:
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
                "source_url": None,
                "source_path": None,
            }
        )

    # npm package-lock
    for lock_name in ("package-lock.json", "npm-shrinkwrap.json"):
        p = root / lock_name
        if p.is_file():
            _parse_npm_lock(p, add)

    pkg = root / "package.json"
    if pkg.is_file():
        _parse_package_json(pkg, add)

    req = root / "requirements.txt"
    if req.is_file():
        _parse_requirements(req, add)

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        _parse_pyproject(pyproject, add)

    gomod = root / "go.mod"
    if gomod.is_file():
        _parse_gomod(gomod, add)

    cargo = root / "Cargo.toml"
    if cargo.is_file():
        _parse_cargo_toml(cargo, add)

    pom = root / "pom.xml"
    if pom.is_file():
        _parse_pom(pom, add)

    return comps


def inventory_from_repo(root: Path, max_packages: int = 500) -> dict[str, Any]:
    comps = parse_repo_deps(root, max_packages=max_packages)
    return {
        "target": str(root),
        "source": "lockfile-parse",
        "note": "依赖来自锁文件/清单；补 source_url 后可 from-inventory 深审；已入库则跳过",
        "components": comps,
    }


def _parse_npm_lock(path: Path, add) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return
    packages = data.get("packages") or {}
    if isinstance(packages, dict):
        for key, meta in packages.items():
            if not key or key == "":
                continue
            if not isinstance(meta, dict):
                continue
            name = key.split("node_modules/")[-1]
            if not name or name.startswith("."):
                continue
            ver = str(meta.get("version") or "unknown")
            add(name, ver, "npm", f"{path.name}:{name}")
        return
    deps = data.get("dependencies") or {}
    if isinstance(deps, dict):
        _walk_npm_deps(deps, add, path.name)


def _walk_npm_deps(deps: dict, add, evidence_prefix: str) -> None:
    for name, meta in deps.items():
        if not isinstance(meta, dict):
            continue
        ver = str(meta.get("version") or "unknown").lstrip("^")
        add(name, ver, "npm", f"{evidence_prefix}:{name}")
        nested = meta.get("dependencies") or {}
        if isinstance(nested, dict):
            _walk_npm_deps(nested, add, evidence_prefix)


def _parse_package_json(path: Path, add) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return
    for field in ("dependencies", "devDependencies", "optionalDependencies"):
        block = data.get(field) or {}
        if not isinstance(block, dict):
            continue
        for name, ver in block.items():
            add(str(name), str(ver).lstrip("^~>="), "npm", f"package.json:{field}")


def _parse_requirements(path: Path, add) -> None:
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # package==1.2.3 / package>=1
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*([=<>!~]+)\s*([A-Za-z0-9_.+-]+)", line)
        if m:
            add(m.group(1), m.group(3), "pypi", "requirements.txt")
            continue
        m2 = re.match(r"^([A-Za-z0-9_.-]+)\s*$", line)
        if m2:
            add(m2.group(1), "unknown", "pypi", "requirements.txt")


def _parse_pyproject(path: Path, add) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    # 粗解析 project.dependencies 数组
    in_deps = False
    for line in text.splitlines():
        if re.search(r"^\s*dependencies\s*=\s*\[", line):
            in_deps = True
            rest = line.split("[", 1)[-1]
            _py_dep_tokens(rest, add)
            if "]" in rest:
                in_deps = False
            continue
        if in_deps:
            _py_dep_tokens(line, add)
            if "]" in line:
                in_deps = False


def _py_dep_tokens(line: str, add) -> None:
    for m in re.finditer(r"['\"]([A-Za-z0-9_.-]+)([>=<!~]+([A-Za-z0-9_.+-]+))?['\"]", line):
        name = m.group(1)
        ver = m.group(3) or "unknown"
        add(name, ver, "pypi", "pyproject.toml")


def _parse_gomod(path: Path, add) -> None:
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("require "):
            # require github.com/foo/bar v1.2.3
            parts = line[len("require ") :].split()
            if len(parts) >= 2:
                add(parts[0], parts[1], "go", "go.mod")
            continue
        if not line or line.startswith("//") or line in ("require (", ")"):
            continue
        # inside require block: module version
        parts = line.split()
        if len(parts) >= 2 and not parts[0] in ("module", "go", "replace", "exclude"):
            if parts[0].startswith("github.com") or "/" in parts[0]:
                add(parts[0], parts[1], "go", "go.mod")


def _parse_cargo_toml(path: Path, add) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    section = None
    for line in text.splitlines():
        if re.match(r"^\[dependencies\]", line) or re.match(r"^\[dev-dependencies\]", line):
            section = "dep"
            continue
        if line.startswith("["):
            section = None
            continue
        if section != "dep":
            continue
        m = re.match(r"^([A-Za-z0-9_-]+)\s*=\s*\"([^\"]+)\"", line)
        if m:
            add(m.group(1), m.group(2), "crates", "Cargo.toml")
            continue
        m2 = re.match(r"^([A-Za-z0-9_-]+)\s*=\s*\{[^}]*version\s*=\s*\"([^\"]+)\"", line)
        if m2:
            add(m2.group(1), m2.group(2), "crates", "Cargo.toml")


def _parse_pom(path: Path, add) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(
        r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*(?:<version>([^<]*)</version>)?",
        text,
        re.S,
    ):
        group, art, ver = m.group(1).strip(), m.group(2).strip(), (m.group(3) or "unknown").strip()
        add(f"{group}:{art}", ver or "unknown", "maven", "pom.xml")
