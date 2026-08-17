"""写出 Markdown / JSON 报告。"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from codeaudit.scan import Finding, findings_as_dicts


def write_reports(
    out_dir: Path,
    repo: Path,
    findings: list[Finding],
    meta: dict,
    llm_note: str | None = None,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meta": meta,
        "findings": findings_as_dicts(findings),
        "llm_summary": llm_note,
    }
    json_path = out_dir / "findings.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    written.append(json_path)

    sev = Counter(f.severity for f in findings)
    lines = [
        "# 出海鉴 · 源码只读审计报告",
        "",
        f"- 仓库: `{repo}`",
        f"- 时间: {data['generated_at']}",
        f"- 扫描文件数: {meta.get('files_scanned', 0)}",
        f"- 线索数: {len(findings)}",
        f"- 模式: **只读启发式**（无网络、无利用）",
        "",
        "## 严重度分布",
        "",
    ]
    for k in ("critical", "high", "medium", "low"):
        if sev.get(k):
            lines.append(f"- {k}: {sev[k]}")
    lines.append("")

    if llm_note:
        lines.extend(["## LLM 摘要（辅助，需人工复核）", "", llm_note.strip(), ""])

    lines.extend(["## 发现列表", ""])
    if not findings:
        lines.append("_未命中内置规则。不代表无风险，请结合人工与专项工具复核。_")
    else:
        for i, f in enumerate(findings, 1):
            lines.extend(
                [
                    f"### {i}. [{f.severity}] {f.rule_id}",
                    "",
                    f"- 类别: {f.category}",
                    f"- 位置: `{f.path}:{f.line}`",
                    f"- 说明: {f.message}",
                    f"- 片段: `{f.snippet}`",
                    "",
                ]
            )

    lines.extend(
        [
            "---",
            "",
            "**声明**: 本报告由自动化只读扫描生成，可能误报或漏报；",
            "不得将本输出视为已验证可利用漏洞，也不得用于未授权攻击。",
            "",
        ]
    )

    md_path = out_dir / "report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    written.append(md_path)
    return written
