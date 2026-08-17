#!/usr/bin/env python3
"""CLI: codeaudit run | deps | from-inventory | lookup | cache-list"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from codeaudit.report import write_reports
from codeaudit.scan import scan_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codeaudit",
        description="出海鉴源码只读审计 — 组件缓存 + 锁文件依赖提取",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="扫描本地仓库并生成报告")
    run_p.add_argument("--repo", required=True, help="源码根目录（只读）")
    run_p.add_argument("--out", default="./out", help="报告输出目录")
    run_p.add_argument("--max-files", type=int, default=400)
    run_p.add_argument("--llm", action="store_true")
    run_p.add_argument(
        "--emit-deps",
        action="store_true",
        help="同时从锁文件提取 components.json",
    )

    deps_p = sub.add_parser("deps", help="仅从锁文件/清单提取依赖组件")
    deps_p.add_argument("--repo", required=True)
    deps_p.add_argument("--out", default="./components.json")
    deps_p.add_argument("--max-deps", type=int, default=500)

    inv_p = sub.add_parser(
        "from-inventory",
        help="读组件清单：库中有则跳过，无则取源码审计并入库",
    )
    inv_p.add_argument("--inventory", required=True, help="components.json 路径")
    inv_p.add_argument("--db", help="SQLite 路径，默认 ~/.chuhaijian/codeaudit.db")
    inv_p.add_argument("--out", help="可选：为新审计的组件写报告目录")
    inv_p.add_argument("--force", action="store_true", help="忽略缓存强制重扫")
    inv_p.add_argument("--max-files", type=int, default=400)

    look_p = sub.add_parser("lookup", help="查询某组件是否已在库中")
    look_p.add_argument("--name", required=True)
    look_p.add_argument("--version", default="unknown")
    look_p.add_argument("--ecosystem", default="unknown")
    look_p.add_argument("--db")

    list_p = sub.add_parser("cache-list", help="列出缓存中的组件审计")
    list_p.add_argument("--db")
    list_p.add_argument("--limit", type=int, default=50)

    args = parser.parse_args(argv)

    if args.cmd == "run":
        repo = Path(args.repo).resolve()
        if not repo.is_dir():
            print(f"[ERR] 不是目录: {repo}", file=sys.stderr)
            return 1
        print(f"[codeaudit] 扫描 {repo} (只读)")
        findings, meta = scan_repo(repo, max_files=args.max_files)
        llm_note = None
        if args.llm:
            from codeaudit.llm_summary import maybe_llm_summary

            llm_note = maybe_llm_summary(repo, findings, meta)
        out = Path(args.out).resolve()
        paths = write_reports(out, repo, findings, meta, llm_note=llm_note)
        print(f"[OK] 发现 {len(findings)} 条线索")
        for p in paths:
            print(f"  → {p}")
        if args.emit_deps:
            from codeaudit.lockfiles import inventory_from_repo

            inv = inventory_from_repo(repo)
            inv_path = out / "components.json"
            inv_path.write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  → deps: {inv_path} ({len(inv.get('components') or [])} 项)")
            print("  下一步: codeaudit from-inventory --inventory", str(inv_path))
        return 0

    if args.cmd == "deps":
        from codeaudit.lockfiles import inventory_from_repo

        repo = Path(args.repo).resolve()
        if not repo.is_dir():
            print(f"[ERR] 不是目录: {repo}", file=sys.stderr)
            return 1
        inv = inventory_from_repo(repo, max_deps=args.max_deps)
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
        n = len(inv.get("components") or [])
        print(f"[OK] 提取 {n} 个组件 → {out}")
        print("下一步: codeaudit from-inventory --inventory", str(out))
        print("提示: 开源包默认无 source_url，需补全或只审 application 的 source_path")
        return 0

    if args.cmd == "from-inventory":
        from codeaudit.pipeline import run_inventory

        inv = Path(args.inventory).resolve()
        if not inv.is_file():
            print(f"[ERR] 清单不存在: {inv}", file=sys.stderr)
            return 1
        db = Path(args.db).resolve() if args.db else None
        out = Path(args.out).resolve() if args.out else None
        summary = run_inventory(
            inv,
            db_path=db,
            force=args.force,
            max_files=args.max_files,
            out_dir=out,
        )
        print(
            f"[OK] total={summary['total']} cache_hit={summary['cache_hit']} "
            f"audited={summary['audited']} needs_source={summary['needs_source']} "
            f"error={summary['error']}"
        )
        print(f"  db: {summary['db']}")
        for r in summary["results"]:
            print(
                f"  - {r.get('name')}@{r.get('version')}: {r.get('status')} "
                f"findings={r.get('findings_count', '-')}"
            )
        summary_path = (out or inv.parent) / "inventory_audit_summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  → {summary_path}")
        return 0

    if args.cmd == "lookup":
        from codeaudit.db import connect, lookup

        db = Path(args.db).resolve() if args.db else None
        conn = connect(db)
        row = lookup(conn, args.ecosystem, args.name, args.version)
        if not row:
            print("miss")
            return 1
        print(json.dumps({k: row[k] for k in row if k != "findings"}, ensure_ascii=False, indent=2))
        print(f"findings_count: {row.get('findings_count')}")
        return 0

    if args.cmd == "cache-list":
        from codeaudit.db import connect, list_all

        db = Path(args.db).resolve() if args.db else None
        rows = list_all(connect(db), limit=args.limit)
        for r in rows:
            print(
                f"{r.get('ecosystem')}:{r.get('name')}@{r.get('version')} "
                f"status={r.get('status')} findings={r.get('findings_count')} "
                f"updated={r.get('updated_at')}"
            )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
