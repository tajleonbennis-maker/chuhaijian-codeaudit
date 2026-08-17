# 出海鉴 · 源码安全审计（chuhaijian-codeaudit）

只读源码审计 + **组件结果库** + **锁文件依赖解析**。

## 安装

```bash
pip install -e .
```

## 常用命令

```bash
# 扫仓库
codeaudit run --repo /path/to/repo --out ./out --emit-deps

# 只抽依赖
codeaudit deps --repo /path/to/repo --out ./components.json

# 清单审计（有缓存则跳过）
codeaudit from-inventory --inventory ./components.json --out ./comp-out

codeaudit lookup --ecosystem npm --name lodash --version 4.17.21
codeaudit cache-list
```

详见 [docs/component-pipeline.md](docs/component-pipeline.md)

姊妹项目：[surface-map](https://github.com/tajleonbennis-maker/chuhaijian-surface-map)

## License

AGPL-3.0-or-later
