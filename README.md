# 出海鉴 · 源码安全审计（chuhaijian-codeaudit）

**白盒 / 只读** 的源码安全审计工具：分析你授权的代码仓库，识别潜在安全风险与改进点。

> 本项目**不**对线上系统发包、**不**执行漏洞利用、**不**生成可直接打目标的 exploit PoC。

姊妹项目：[chuhaijian-surface-map](https://github.com/tajleonbennis-maker/chuhaijian-surface-map)（授权目标攻击面测绘）

---

## 做什么 / 不做什么

| 会做 | 不会做 |
|------|--------|
| 只读扫描本地/挂载的源码仓库 | 访问业务 URL、登录、发业务请求 |
| 识别框架、入口、鉴权点、危险 sink 线索 | 执行注入 / XSS / 越权等真实攻击 |
| 输出发现位置 + 风险说明 + 修复建议 | 输出可复制利用步骤打生产 |
| SARIF / Markdown / SQLite 报告 | 修改目标应用状态 |

---

## 快速开始（规划中）

```bash
# 配置 LLM（支持国产模型 DeepSeek / 通义 / GLM 等，见 docs/）
cp .env.example .env

# 对授权仓库做只读审计
python -m codeaudit run --repo /path/to/your-repo --out ./out
```

当前仓库为**产品骨架与范围定义**。核心审计流水线将从 Shannon 的 pre-recon / 静态分析能力剥离并重写 prompt 护栏后迁入。

---

## 与完整 AI 渗透的关系

| 项目 | 范围 |
|------|------|
| **chuhaijian-codeaudit**（本仓库） | 源码只读审计 |
| **chuhaijian-surface-map** | 授权目标非侵入测绘 |
| 完整渗透（私有/企业） | 含漏洞验证与利用 — **不在本公开产品内** |

历史参考实现曾基于 [Keygraph Shannon](https://github.com/KeygraphHQ/shannon)（AGPL-3.0）。本产品重新划定范围，**刻意去掉 exploit 与对活目标的破坏性能力**。

---

## 目录规划

```text
chuhaijian-codeaudit/
├── README.md
├── SAFETY.md              # 使用边界与授权要求
├── docs/
│   └── scope.md           # 产品范围与威胁模型
├── prompts/               # 审计 agent 提示词（禁止利用类输出）
├── src/                   # 审计引擎（规划中）
└── scripts/               # 配置 / 报告导出辅助
```

---

## 授权与合规

- 仅对**你拥有或已获书面授权**的代码库运行。
- 不要对不可信、对抗性仓库做无审查的全自动分析（存在 prompt injection 风险）。
- 报告需人工复核，模型结论可能误报或漏报。

详见 [SAFETY.md](SAFETY.md)。

---

## License

计划采用 **AGPL-3.0**（与上游生态一致）。最终以仓库根目录 `LICENSE` 为准。
