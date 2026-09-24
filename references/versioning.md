# 版本管理规范

> 本文档定义 agent-plugin-creator 技能及其产出物的版本号管理体系。

## 目录

- [三层版本号体系](#三层版本号体系)
- [SemVer 迭代标准](#semver-迭代标准)
- [版本号统一管理机制](#版本号统一管理机制)
- [产出物版本标注](#产出物版本标注)
- [版本升级检查清单](#版本升级检查清单)
- [历史版本](#历史版本)

## 三层版本号体系

| 层级 | 版本号位置 | 迭代标准 | 管理者 |
|------|-----------|---------|--------|
| **技能本身** | SKILL.md 头部 / CHANGELOG.md / provenance.json | SemVer | 技能开发者 |
| **产出的插件** | plugin.json 的 `version` 字段 | SemVer，默认 0.1.0 | 插件用户 |
| **反向封装的技能** | metadata.wrapper-version + 子技能原始版本 | wrapper-version 跟随技能版本 | 自动生成 |

## SemVer 迭代标准

版本号格式：`MAJOR.MINOR.PATCH`

### MAJOR (x.0.0) — 不兼容的变更

触发条件：
- 脚本接口变更（参数名、返回值格式变化）
- SKILL.md 结构大改（工作流重写、步骤删除）
- 删除已有功能
- 不兼容的配置格式变化

示例：v1.0.0 → v2.0.0

### MINOR (x.y.0) — 向下兼容的功能新增

触发条件：
- 新增脚本
- 新增工作流或步骤
- 新增验证环节（如 official 资源接入）
- 新增产出物字段（如 generated-by 标注）
- 现有功能的显著增强

示例：v1.1.0 → v1.2.0

### PATCH (x.y.z) — 向下兼容的问题修正

触发条件：
- Bug 修复
- 文档优化（错别字、表述改进）
- 测试补充
- 性能优化（不改变行为）
- 边界情况处理改进

示例：v1.2.0 → v1.2.1

## 版本号统一管理机制

### 1. 单一来源

`provenance.json` 是版本号的唯一来源（single source of truth）：

```json
{
  "version": "1.2.0"
}
```

SKILL.md 头部和 CHANGELOG.md 的版本号必须与 provenance.json 一致。

### 2. 三处同步更新

每次版本更新必须同步更新以下三处：

| 文件 | 更新内容 |
|------|---------|
| `provenance.json` | `version` 字段 + `last_updated` 日期 |
| `SKILL.md` | 头部 `> **版本**: vX.Y.Z` |
| `CHANGELOG.md` | 顶部新增 `## [X.Y.Z] - YYYY-MM-DD` 条目 |

### 3. CHANGELOG 强制规范

每次版本更新必须在 CHANGELOG.md 中记录：

```markdown
## [X.Y.Z] - YYYY-MM-DD

简短描述本次版本的核心变更。

### 新增
- 新增功能1
- 新增功能2

### 修复
- 修复的bug1

### 优化
- 优化项1
```

### 4. 版本一致性检查

`release_audit.py` 自动检查三处版本号一致性：
- SKILL.md 头部版本号 vs provenance.json
- CHANGELOG.md 最新条目版本号 vs provenance.json

不一致时报告 `BLOCKED` 状态，阻止发布。

## 产出物版本标注

### 产出的插件

wizard.py 生成的 plugin.json 自动添加 `generated-by` 字段：

```json
{
  "generated-by": {
    "tool": "agent-plugin-creator",
    "version": "1.2.0"
  }
}
```

用途：追溯插件是由哪个版本的技能生成的，便于问题排查。

### 反向封装的技能

plugin_to_skill.py 生成的封装层 SKILL.md metadata 自动标注：

```yaml
metadata:
  source: agent-plugin
  plugin-version: 1.0.0
  wrapper-version: 1.2.0
  generated-by:
    tool: agent-plugin-creator
    version: 1.2.0
```

- `plugin-version`：原始插件的版本号
- `wrapper-version`：封装工具（即本技能）的版本号，跟随技能版本
- `generated-by`：生成工具和版本

## 版本升级检查清单

每次升级版本前，确认以下事项：

- [ ] 确定版本号类型（MAJOR/MINOR/PATCH）
- [ ] 更新 provenance.json 的 version 和 last_updated
- [ ] 更新 SKILL.md 头部版本号
- [ ] 在 CHANGELOG.md 顶部添加新版本条目
- [ ] 运行 release_audit.py 确认版本一致性检查通过
- [ ] 运行全量测试确认无回归
- [ ] 重新打包生成移植包

## 历史版本

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| v1.2.0 | 2026-09-22 | official/ 资源全量接入 + 版本号统一管理体系 |
| v1.1.0 | 2026-09-22 | 方法论对齐 + 反向封装深度修复 |
| v1.0.1 | 2026-09-22 | 正式版标准修复 |
| v1.0.0 | 2026-09-17 | 初始正式版 |
