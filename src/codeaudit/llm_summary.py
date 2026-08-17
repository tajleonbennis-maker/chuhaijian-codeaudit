"""可选：调用 OpenAI 兼容 Chat Completions 生成中文摘要（不要求、不执行利用）。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from codeaudit.scan import Finding


def maybe_llm_summary(repo: Path, findings: list[Finding], meta: dict) -> str | None:
    api_key = os.environ.get("AUDIT_AI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("[llm] 未设置 AUDIT_AI_API_KEY / DEEPSEEK_API_KEY，跳过 LLM 摘要")
        return None

    base = os.environ.get("AUDIT_AI_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("AUDIT_AI_MODEL", "deepseek-chat")

    sample = findings[:30]
    payload_findings = [
        {"rule": f.rule_id, "sev": f.severity, "path": f.path, "line": f.line, "msg": f.message}
        for f in sample
    ]
    user = (
        "你是安全审计助手。根据下列只读静态扫描线索，用中文写简短摘要："
        "1) 主要风险主题 2) 建议优先修复顺序 3) 需要人工确认的点。"
        "禁止给出可直接攻击线上系统的 exploit 步骤或 payload。\n\n"
        f"仓库: {repo}\n元数据: {json.dumps(meta, ensure_ascii=False)}\n"
        f"线索: {json.dumps(payload_findings, ensure_ascii=False)}"
    )

    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你只做防御性代码审计总结，不提供攻击利用细节。",
            },
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }

    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"[llm] 调用失败: {e}")
        return None
