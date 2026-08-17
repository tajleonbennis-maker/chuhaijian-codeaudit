# 出海鉴 · 源码安全审计（chuhaijian-codeaudit）

**白盒 / 只读** 源码审计，并支持 **组件级结果库**：同一组件版本审过一次，后续清单直接命中缓存。

> 不访问业务攻击面利用 · 不执行 exploit

姊妹项目：[chuhaijian-surface-map](https://github.com/tajleonbennis-maker/chuhaijian-surface-map)

---

## 安装

```bash
pip install -e .
```

## 1）扫本地仓库

```bash
codeaudit run --repo /path/to/repo --out ./out
```

## 2）组件清单 + 缓存（推荐与 surface-map 衔接）

```bash
# 清单里带 name/version/source_url 或 source_path
codeaudit from-inventory --inventory components.json --out ./comp-out

# 再跑一次同一清单 → 已入库的会显示 cache_hit
codeaudit from-inventory --inventory components.json

codeaudit lookup --name express --version 4.18.2 --ecosystem npm
codeaudit cache-list
```

流程说明见 [docs/component-pipeline.md](docs/component-pipeline.md)。

---

## License

AGPL-3.0-or-later
