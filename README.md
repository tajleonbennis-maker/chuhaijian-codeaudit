# 出海鉴 · 源码安全审计（chuhaijian-codeaudit）

白盒只读审计 + **组件结果库** + **锁文件依赖提取**。

```text
识别组件（deps / surface-map）
  → 查 ~/.chuhaijian/codeaudit.db
  → 有则跳过；无则取源码审计并入库
```

姊妹项目：[chuhaijian-surface-map](https://github.com/tajleonbennis-maker/chuhaijian-surface-map)

## 安装

```bash
pip install -e .
```

## 命令

```bash
# 扫仓库
codeaudit run --repo /path/to/repo --out ./out --emit-deps

# 只提取依赖清单
codeaudit deps --repo /path/to/repo --out ./components.json

# 清单审计（缓存命中则跳过）
codeaudit from-inventory --inventory ./components.json --out ./comp-out

codeaudit lookup --ecosystem npm --name express --version 4.18.2
codeaudit cache-list
```

支持锁文件线索：`package-lock.json` / `package.json` / `requirements*.txt` / `pyproject.toml` / `go.mod` / `Cargo.toml`。

## License

AGPL-3.0-or-later
