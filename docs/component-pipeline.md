# 组件流水线

## 白盒（有仓库）

```bash
codeaudit deps --repo ./app --out components.json
# application 项已带 source_path，可直接审
codeaudit from-inventory --inventory components.json --out ./comp-out
```

开源依赖默认 `needs_source`，可按需补：

```json
{
  "name": "express",
  "version": "4.18.2",
  "ecosystem": "npm",
  "source_url": "https://github.com/expressjs/express.git"
}
```

## 黑盒（surface-map）

```bash
surfacemap run --url https://authorized.example --emit-components --i-am-authorized --out ./out
# 编辑 out/components.json 补源码后再：
codeaudit from-inventory --inventory ./out/components.json
```

## 缓存

- DB: `CODEAUDIT_DB` 或 `~/.chuhaijian/codeaudit.db`
- 源码缓存: `CODEAUDIT_SOURCE_CACHE` 或 `~/.chuhaijian/source-cache`
