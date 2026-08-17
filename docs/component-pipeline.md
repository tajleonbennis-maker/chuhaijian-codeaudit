# 组件流水线（更新）

## A. 黑盒（surface-map）

```bash
surfacemap run --url https://授权目标 --out ./out --i-am-authorized --emit-components
# 编辑 components.json 补 source_path / source_url
codeaudit from-inventory --inventory ./out/components.json --out ./comp-out
```

## B. 白盒锁文件（codeaudit 原生，推荐）

```bash
# 从仓库锁文件抽出依赖清单
codeaudit deps --repo /path/to/app --out ./components.json

# 或 run 时一并导出
codeaudit run --repo /path/to/app --out ./out --emit-deps

# 有缓存跳过；无源码标 needs_source
codeaudit from-inventory --inventory ./out/components.json --out ./comp-out
```

支持：`package-lock.json` / `package.json` / `requirements.txt` / `pyproject.toml` / `go.mod` / `Cargo.toml` / `pom.xml`

## 缓存键

`(ecosystem, name, version)` → `~/.chuhaijian/codeaudit.db`
