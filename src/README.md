# src/

审计引擎实现位置（规划中）。

建议模块划分：

- `ingest/` — 仓库索引与忽略规则  
- `agents/` — LLM 只读分析  
- `rules/` — 可选确定性规则  
- `report/` — Markdown / SARIF / SQLite  

不包含 exploit、browser 攻击、对 webUrl 的 mutative 客户端。
