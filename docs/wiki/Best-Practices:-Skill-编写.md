# 最佳实践：Skill 编写

## 核心原则

### 1. Description 是触发器，不是描述

**错误**：
```markdown
description: 一个用于代码审查的技能
```

**正确**：
```markdown
description: 代码审查技能。当用户要求审查代码、Code Review、CR、检查代码质量、查找bug、审查MR/PR、审查diff时使用。提供代码缺陷检测、最佳实践建议和安全审查。
```

**要点**：
- 包含触发场景关键词（中文+英文）
- 说明什么时候使用，而不是做什么
- 避免 undertrigger（触发不足）

### 2. 渐进式披露 (Progressive Disclosure)

SKILL.md 只保留核心工作流和决策逻辑，详细内容放到 `references/` 目录。

**结构**：
```
my-skill/
├── SKILL.md              # 核心工作流（精简）
├── references/
│   ├── detailed-guide.md # 详细指南
│   ├── api-reference.md  # API 参考
│   └── examples.md       # 示例
├── scripts/              # 确定性逻辑
└── assets/               # 模板和资源
```

### 3. Gotchas 是最重要的部分

> "每个 Skill 都需要 Gotchas section，这是你最应该花时间写的部分。" — Anthropic 工程师

**Gotchas 应包含**：
- 常见错误和陷阱
- 边界情况处理
- 与预期不符的行为
- 性能注意事项
- 安全注意事项

**示例**：
```markdown
## Gotchas

- `validate_plugin.py` 在 Python 3.9 上不支持 `str | None` 语法，必须使用 `Optional[str]`
- MCP stdio 服务器不能打印任何调试信息到 stdout，会破坏 JSON-RPC
- `audit_plugin.py` 会扫描 SKILL.md 中的密钥模式，测试用例中的假密钥可能触发误报
- 插件 name 不允许包含点号（.），但 Skill name 允许
```

### 4. 脚本存储 + 生成代码

- **重复执行的确定性逻辑** → `scripts/`（Python/Bash/Node）
- **详细文档和领域知识** → `references/`
- **模板和资源文件** → `assets/`

**不要**把复杂逻辑写在 SKILL.md 中让 AI 自由发挥，应该用脚本确保确定性。

### 5. 不要陈述显而易见的事

**错误**：
```markdown
## 介绍
本技能用于创建插件。插件是一种可移植的软件包...
```

**正确**：
直接进入工作流，假设用户知道插件是什么。

## Skill 结构模板

```markdown
---
name: my-skill
description: 技能描述。当用户要求XXX、YYY、ZZZ时使用。
license: MIT
---

## 工作流

### 步骤 1：需求分析
...

### 步骤 2：执行
...

## Gotchas

- ...
- ...

## 参考

- 详细指南：`references/detailed-guide.md`
- API 参考：`references/api-reference.md`
```

## 命名规范

- **Skill name**：小写字母+数字+连字符，max 64，不允许点号
- **Plugin name**：小写字母+数字+连字符+点，max 64
- **目录名**：与 name 完全一致

## 测试清单

发布前检查：

- [ ] `validate_skill.py` 通过
- [ ] `official/skill-creator/scripts/quick_validate.py` 通过
- [ ] description 包含触发关键词
- [ ] Gotchas section 存在且有实质内容
- [ ] 渐进式披露（详细内容在 references/）
- [ ] 脚本有 `--help`
- [ ] 无硬编码密钥
- [ ] 示例可运行

---

**相关阅读**：
- [MCP 服务器设计最佳实践](Best-Practices:-MCP-服务器设计)
- [安全审计清单](Best-Practices:-安全审计清单)
