"""组件级编排：查库 → 缺则取源码 → codeaudit → 写库。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from codeaudit.db import connect, default_db_path, list_all, lookup, upsert
from codeaudit.fetch_source import resolve_source
from codeaudit.report import write_reports
from codeaudit.scan import findings_as_dicts, scan_repo


def ensure_component(
    comp: dict[str, Any],
    *,
    db_path: Path | None = None,
    force: bool = False,
    max_files: int = 400,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """保证某组件有审计结果。

    comp 字段：
      name (必填), version, ecosystem, source_path, source_url
    """
    name = (comp.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "missing name", "component": comp}

    ecosystem = comp.get("ecosystem") or "unknown"
    version = comp.get("version") or "unknown"
    conn = connect(db_path)

    if not force:
        cached = lookup(conn, ecosystem, name, version)
        if cached and cached.get("status") in ("done", "cached"):
            return {
                "status": "cache_hit",
                "ecosystem": ecosystem,
                "name": name,
                "version": version,
                "findings_count": cached.get("findings_count", 0),
                "updated_at": cached.get("updated_at"),
                "from_db": True,
            }

    st, path, detail = resolve_source(
        name=name,
        version=version,
        source_path=comp.get("source_path"),
        source_url=comp.get("source_url"),
    )
    if st == "needs_source":
        upsert(
            conn,
            ecosystem=ecosystem,
            name=name,
            version=version,
            status="needs_source",
            findings=[],
            meta={"detail": detail},
            source_url=comp.get("source_url"),
            source_path=comp.get("source_path"),
        )
        return {
            "status": "needs_source",
            "name": name,
            "version": version,
            "detail": detail,
            "from_db": False,
        }
    if st != "ready" or path is None:
        upsert(
            conn,
            ecosystem=ecosystem,
            name=name,
            version=version,
            status="error",
            findings=[],
            meta={"detail": detail},
            source_url=comp.get("source_url"),
        )
        return {"status": "error", "name": name, "error": detail, "from_db": False}

    findings, meta = scan_repo(path, max_files=max_files)
    fdicts = findings_as_dicts(findings)

    if out_dir:
        dest = Path(out_dir) / f"{name}-{version}".replace("/", "_")
        write_reports(dest, path, findings, meta)

    upsert(
        conn,
        ecosystem=ecosystem,
        name=name,
        version=version,
        status="done",
        findings=fdicts,
        meta={**meta, "fetch": detail},
        source_url=comp.get("source_url"),
        source_path=str(path),
    )
    return {
        "status": "audited",
        "name": name,
        "version": version,
        "ecosystem": ecosystem,
        "findings_count": len(fdicts),
        "source_path": str(path),
        "from_db": False,
    }


def run_inventory(
    inventory_path: Path,
    *,
    db_path: Path | None = None,
    force: bool = False,
    max_files: int = 400,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    data = json.loads(inventory_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        components = data.get("components") or data.get("items") or []
    elif isinstance(data, list):
        components = data
    else:
        raise ValueError("清单须为 list 或含 components 的对象")

    results = []
    for comp in components:
        if not isinstance(comp, dict):
            continue
        results.append(
            ensure_component(
                comp,
                db_path=db_path,
                force=force,
                max_files=max_files,
                out_dir=out_dir,
            )
        )

    summary = {
        "inventory": str(inventory_path),
        "db": str(db_path or default_db_path()),
        "total": len(results),
        "cache_hit": sum(1 for r in results if r.get("status") == "cache_hit"),
        "audited": sum(1 for r in results if r.get("status") == "audited"),
        "needs_source": sum(1 for r in results if r.get("status") == "needs_source"),
        "error": sum(1 for r in results if r.get("status") == "error"),
        "results": results,
    }
    return summary
