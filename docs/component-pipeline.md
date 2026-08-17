# 组件识别 → codeaudit 缓存流水线

## 流程

```text
surface-map（或手工）识别组件
        │
        ▼
  components.json 清单
        │
        ▼
codeaudit from-inventory
        │
        ├─ 库中已有 (ecosystem, name, version) → cache_hit，跳过
        ├─ 无记录但有 source_path / source_url → 取源码 → 扫描 → 入库
        └─ 无源码线索 → needs_source（等人补 URL/路径）
```

## 清单格式

```json
{
  "target": "https://example.com",
  "components": [
    {
      "name": "express",
      "version": "4.18.2",
      "ecosystem": "npm",
      "source_url": "https://github.com/expressjs/express.git"
    },
    {
      "name": "my-app",
      "version": "git",
      "ecosystem": "application",
      "source_path": "/path/to/authorized-repo"
    }
  ]
}
```

## 命令

```bash
# 批量：有缓存跳过
codeaudit from-inventory --inventory components.json --out ./comp-out

# 查询单组件
codeaudit lookup --ecosystem npm --name express --version 4.18.2

# 列出缓存
codeaudit cache-list
```

数据库默认：`~/.chuhaijian/codeaudit.db`  
可用环境变量 `CODEAUDIT_DB` 覆盖。

## 边界

- 只读审计，不利用
- 仅克隆清单里给出的公开 git URL 或本地授权路径
- 不自动破解私有源码
