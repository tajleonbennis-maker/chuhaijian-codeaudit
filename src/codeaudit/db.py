"""组件审计结果库（SQLite）。

主键逻辑：ecosystem + name + version（小写归一）。
有记录则复用，避免对同一开源组件重复跑 codeaudit。
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_db_path() -> Path:
    env = os.environ.get("CODEAUDIT_DB")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".chuhaijian" / "codeaudit.db"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS component_audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ecosystem TEXT NOT NULL,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            source_url TEXT,
            source_path TEXT,
            status TEXT NOT NULL,
            findings_count INTEGER DEFAULT 0,
            findings_json TEXT,
            meta_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(ecosystem, name, version)
        );
        CREATE INDEX IF NOT EXISTS idx_comp_name ON component_audits(name);
        """
    )
    return conn


def component_key(ecosystem: str, name: str, version: str) -> tuple[str, str, str]:
    return (
        (ecosystem or "unknown").strip().lower(),
        (name or "").strip().lower(),
        (version or "unknown").strip().lower(),
    )


def lookup(
    conn: sqlite3.Connection,
    ecosystem: str,
    name: str,
    version: str,
) -> dict[str, Any] | None:
    eco, n, v = component_key(ecosystem, name, version)
    row = conn.execute(
        """SELECT * FROM component_audits
           WHERE ecosystem=? AND name=? AND version=?""",
        (eco, n, v),
    ).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def upsert(
    conn: sqlite3.Connection,
    *,
    ecosystem: str,
    name: str,
    version: str,
    status: str,
    findings: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
    source_url: str | None = None,
    source_path: str | None = None,
) -> dict[str, Any]:
    eco, n, v = component_key(ecosystem, name, version)
    now = datetime.now(timezone.utc).isoformat()
    findings = findings or []
    meta = meta or {}
    conn.execute(
        """INSERT INTO component_audits
           (ecosystem, name, version, source_url, source_path, status,
            findings_count, findings_json, meta_json, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(ecosystem, name, version) DO UPDATE SET
             source_url=excluded.source_url,
             source_path=excluded.source_path,
             status=excluded.status,
             findings_count=excluded.findings_count,
             findings_json=excluded.findings_json,
             meta_json=excluded.meta_json,
             updated_at=excluded.updated_at
        """,
        (
            eco,
            n,
            v,
            source_url,
            source_path,
            status,
            len(findings),
            json.dumps(findings, ensure_ascii=False),
            json.dumps(meta, ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.commit()
    return lookup(conn, eco, n, v) or {}


def list_all(conn: sqlite3.Connection, limit: int = 100) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM component_audits ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    try:
        d["findings"] = json.loads(d.pop("findings_json") or "[]")
    except json.JSONDecodeError:
        d["findings"] = []
    try:
        d["meta"] = json.loads(d.pop("meta_json") or "{}")
    except json.JSONDecodeError:
        d["meta"] = {}
    return d
