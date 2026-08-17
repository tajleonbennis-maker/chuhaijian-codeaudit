# 出海鉴 · 源码安全审计（chuhaijian-codeaudit）

**白盒 / 只读** 源码安全审计：扫描本地仓库中的常见风险线索，输出 Markdown + JSON 报告。

> **不**访问业务 URL · **不**执行漏洞利用 · **不**生成打站 PoC

姊妹项目：[chuhaijian-surface-map](https://github.com/tajleonbennis-maker/chuhaijian-surface-map)

---

## 现在可用（v0.1）

基于**确定性启发式规则**的本地扫描（密钥形态、SQL 拼接线索、`shell=True`、`eval`、不安全反序列化、调试开关等）。可选调用国产/兼容 LLM 做中文摘要（`--llm`）。

### 安装

```bash
git clone https://github.com/tajleonbennis-maker/chuhaijian-codeaudit.git
cd chuhaijian-codeaudit
pip install -e .
```

### 运行

```bash
# 只读扫描本地仓库
codeaudit run --repo /path/to/your-repo --out ./out

# 可选：LLM 摘要（需 API Key）
export DEEPSEEK_API_KEY=sk-...
# 或 AUDIT_AI_API_KEY + AUDIT_AI_BASE_URL + AUDIT_AI_MODEL
codeaudit run --repo /path/to/your-repo --out ./out --llm
```

输出：

- `out/report.md` — 可读报告  
- `out/findings.json` — 结构化结果  

---

## 边界

| 会做 | 不会做 |
|------|--------|
| 只读读文件、模式匹配 | 访问线上目标 |
| 报告位置与修复建议方向 | 真实利用 / 攻击 payload |
| 可选 LLM 总结（防御性） | 修改业务数据 |

详见 [SAFETY.md](SAFETY.md)、[docs/scope.md](docs/scope.md)。

---

## License

AGPL-3.0-or-later（见 `pyproject.toml`）。
