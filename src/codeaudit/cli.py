#!/usr/bin/env python3
"""CLI: codeaudit run --repo PATH --out DIR"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from codeaudit.report import write_reports
from codeaudit.scan import scan_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codeaudit",
        description="出海鉴源码只读审计 — 不访问线上目标、不执行利用",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="扫描本地仓库并生成报告")
    run_p.add_argument("--repo", required=True, help="源码根目录（只读）")
    run_p.add_argument("--out", default="./out", help="报告输出目录")
    run_p.add_argument("--max-files", type=int, default=400, help="最多分析文件数")
    run_p.add_argument("--llm", action="store_true", help="若配置了 API Key，则追加 LLM 摘要")

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
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
