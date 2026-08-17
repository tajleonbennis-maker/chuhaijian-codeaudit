"""本地只读启发式扫描 — 不发起网络请求、不执行代码。"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

SKIP_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    "target",
    ".idea",
    ".vscode",
}

TEXT_EXT = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".java",
    ".kt",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".sql",
    ".yml",
    ".yaml",
    ".json",
    ".env",
    ".toml",
    ".sh",
    ".bash",
    ".md",
    ".xml",
    ".html",
    ".vue",
}

# (id, severity, category, pattern, hint)
RULES: list[tuple[str, str, str, re.Pattern[str], str]] = [
    (
        "hardcoded-aws-key",
        "high",
        "secrets",
        re.compile(r"AKIA[0-9A-Z]{16}"),
        "疑似 AWS Access Key ID 硬编码，应改用密钥管理服务。",
    ),
    (
        "private-key-block",
        "critical",
        "secrets",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "检测到私钥 PEM 块，禁止提交到仓库。",
    ),
    (
        "generic-api-key-assign",
        "medium",
        "secrets",
        re.compile(
            r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[=:]\s*['\"][^'\"]{12,}['\"]"
        ),
        "疑似密钥/令牌字面量赋值，建议改为环境变量或密钥库。",
    ),
    (
        "sql-string-concat",
        "high",
        "injection",
        re.compile(
            r"(?i)(execute|query|raw)\s*\(.*(\+|format|f['\"]|%s|\{\w+\}).*(select|insert|update|delete)"
        ),
        "疑似 SQL 与用户可控数据拼接，优先参数化查询。",
    ),
    (
        "sql-fstring",
        "high",
        "injection",
        re.compile(r"(?i)f['\"][^'\"]*\b(SELECT|INSERT|UPDATE|DELETE)\b[^'\"]*\{"),
        "Python f-string 构造 SQL，存在注入风险。",
    ),
    (
        "shell-true",
        "high",
        "command-injection",
        re.compile(r"subprocess\.(?:call|run|Popen)\([^)]*shell\s*=\s*True"),
        "subprocess shell=True 易导致命令注入，避免拼接用户输入。",
    ),
    (
        "os-system",
        "high",
        "command-injection",
        re.compile(r"\bos\.system\s*\("),
        "os.system 调用，注意命令注入与可移植性。",
    ),
    (
        "eval-use",
        "high",
        "code-execution",
        re.compile(r"\beval\s*\("),
        "eval 可导致任意代码执行，避免处理不可信输入。",
    ),
    (
        "pickle-loads",
        "high",
        "deserialization",
        re.compile(r"\bpickle\.loads?\s*\("),
        "pickle 反序列化不可信数据不安全。",
    ),
    (
        "yaml-unsafe-load",
        "medium",
        "deserialization",
        re.compile(r"\byaml\.load\s*\([^)]*\)"),
        "yaml.load 默认可能不安全，优先 yaml.safe_load。",
    ),
    (
        "debug-true",
        "medium",
        "config",
        re.compile(r"(?i)(DEBUG\s*=\s*True|app\.debug\s*=\s*True|flask_env\s*=\s*development)"),
        "调试模式疑似开启，生产环境应关闭。",
    ),
    (
        "cors-star",
        "medium",
        "config",
        re.compile(r"(?i)Access-Control-Allow-Origin['\"]?\s*[:=]\s*['\"]\*['\"]"),
        "CORS 允许任意源，敏感接口需收紧策略。",
    ),
    (
        "md5-password",
        "medium",
        "crypto",
        re.compile(r"(?i)(md5|sha1)\s*\(.*password"),
        "弱哈希用于口令相关逻辑，应使用专门的口令哈希算法。",
    ),
    (
        "http-url-insecure",
        "low",
        "transport",
        re.compile(r"['\"]http://(?!localhost|127\.0\.0\.1)[^'\"]+['\"]"),
        "硬编码 http:// 非本地地址，注意明文传输风险。",
    ),
]


@dataclass
class Finding:
    rule_id: str
    severity: str
    category: str
    path: str
    line: int
    snippet: str
    message: str


def _iter_files(root: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in TEXT_EXT or name in {".env", "Dockerfile", "Jenkinsfile"}:
                files.append(p)
                if len(files) >= max_files:
                    return files
    return files


def scan_repo(root: Path, max_files: int = 400) -> tuple[list[Finding], dict]:
    files = _iter_files(root, max_files)
    findings: list[Finding] = []

    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(fp.relative_to(root)).replace("\\", "/")
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            for rule_id, severity, category, pattern, hint in RULES:
                if pattern.search(line):
                    snippet = line.strip()[:200]
                    findings.append(
                        Finding(
                            rule_id=rule_id,
                            severity=severity,
                            category=category,
                            path=rel,
                            line=i,
                            snippet=snippet,
                            message=hint,
                        )
                    )

    # 稳定排序：严重度 + 路径
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings.sort(key=lambda f: (sev_order.get(f.severity, 9), f.path, f.line))

    meta = {
        "repo": str(root),
        "files_scanned": len(files),
        "findings_count": len(findings),
        "mode": "read-only-heuristic",
        "network": False,
        "exploit": False,
    }
    return findings, meta


def findings_as_dicts(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]
