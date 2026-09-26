#!/usr/bin/env python3
"""
共享 SKILL.md 模板生成器

三个脚本（init_skill.py、wizard.py、plugin_to_skill.py）都调用这个函数，
确保生成的 SKILL.md 模板质量完全一致。

模板版本：v1.1.0
变更记录：
  - v1.1.0 (2026-09-26): 新增第四大能力（对抗 LLM 不可靠性）+ Yes-Man 防护 + HITL 门控
  - v1.0.0 (2026-09-25): 初始版本，三大能力（渐进式披露 + 触发路由 + Gotchas）
"""
from typing import Optional

# 模板版本号（ SemVer ）
TEMPLATE_VERSION = "1.1.0"


def generate_skill_md_template(
    name: str,
    description: str = "",
    lang: str = "zh",
    title: Optional[str] = None,
) -> str:
    """
    生成标准 SKILL.md 模板（四大能力完整版）
    
    Args:
        name: skill 名称（小写字母+数字+连字符）
        description: skill 描述（触发器）
        lang: 语言（zh/en）
        title: 显示标题（默认从 name 转换）
    
    Returns:
        完整的 SKILL.md 内容
    """
    if title is None:
        title = name.replace("-", " ").title()
    
    if not description:
        description = f"TODO - 替换为清晰的描述，必须包含三要素：1) 这个技能做什么 2) 什么时候应该触发 3) 具体使用场景/触发关键词。这是 AI 判断是否调用这个技能的主要依据（触发器）。"
    
    if lang == "zh":
        return _template_zh(name, description, title)
    else:
        return _template_en(name, description, title)


def _template_zh(name: str, description: str, title: str) -> str:
    """中文模板（四大能力完整版）"""
    return f"""---
name: {name}
description: {description}
---

# {title}

> **模板版本**: v{TEMPLATE_VERSION}（四大能力完整版）
> **生成工具**: agent-plugin-creator

> **⚠️ AI 填充指南（生成后删除此部分）**
>
> 生成此模板后，AI 必须根据用户需求自动填充以下内容，不要留占位符：
>
> ## 质量检查（用脚本自动做，不靠记忆）
>
> **填充完后，运行自动检查：**
> ```bash
> python3 scripts/check_skill_quality.py .
> ```
>
> 脚本会自动检查所有质量项，不通过就报错。
>
> **核心原则：不要靠提示词要求自己，靠脚本强制。**
>
> ## 填充清单
> 1. **description**：三要素（做什么 + 什么时候用 + 触发关键词）
> 2. **概述**：2-3 句话说清楚解决什么问题
> 3. **工作流程**：可执行的具体步骤，写出具体命令
> 4. **关键规则**：真正的规则，包括边界情况和错误处理
> 5. **Gotchas**：至少 3 个坑，症状→修正→原因
> 6. **HITL 门控**：哪些操作需要用户确认（不可逆、高影响等）
> 7. **自动验证**：填充完运行 check_skill_quality.py 检查

## 概述
TODO - 用 2-3 句话说清楚这个技能解决什么问题

## 触发与路由

### 触发场景
- ✅ 应该触发：TODO - 具体用户提问示例
- ✅ 应该触发：TODO
- ❌ 不应该触发：TODO - 容易混淆但不触发的场景

### 路由决策（什么情况走什么路径）
| 用户需求 | 执行路径 |
|---|---|
| TODO - 场景 A | TODO - 对应步骤 |
| TODO - 场景 B | TODO - 对应步骤 |
| 不确定 | 先问澄清问题，不要猜 |

## 工作流程
1. TODO - 具体动作（包含命令）
2. TODO - 具体动作
3. TODO - 具体动作

## 关键规则
- TODO - 边界情况怎么处理？
- TODO - 错误怎么处理？
- TODO - 其他重要规则

## Gotchas（踩过的坑）
> 这是最有价值的部分，写实际踩过的坑，不要泛泛而谈。

### 坑 1：TODO - 坑的标题
- **症状**：TODO - 出现什么问题？
- **修正**：TODO - 怎么解决？
- **原因**：TODO - 为什么会出现？

### 坑 2：TODO
- **症状**：TODO
- **修正**：TODO
- **原因**：TODO

### 坑 3：TODO
- **症状**：TODO
- **修正**：TODO
- **原因**：TODO

## 参考资源
> 渐进式披露：详细内容移到这里，SKILL.md 只保留核心工作流
> 超过 100 行的文件请在开头加目录

- TODO - 详细 XX 文档参见 references/xx.md
- TODO - 详细 YY 指南参见 references/yy.md
- 可执行脚本参见 scripts/ 目录
- 输出模板参见 assets/ 目录
"""


def _template_en(name: str, description: str, title: str) -> str:
    """English template (full three capabilities)"""
    return f"""---
name: {name}
description: {description}
---

# {title}

## Overview
TODO - Briefly describe what this skill does and what problem it solves.

## Trigger & Routing

### Trigger Scenarios
- ✅ Should trigger: TODO - specific user query examples
- ✅ Should trigger: TODO
- ❌ Should NOT trigger: TODO - easily confused but shouldn't trigger

### Routing Decision (what path for what need)
| User Need | Execution Path |
|---|---|
| TODO - Scenario A | TODO - corresponding steps |
| TODO - Scenario B | TODO - corresponding steps |
| Uncertain | Ask clarifying question first, don't guess |

## Workflow
1. TODO - Specific action (with commands)
2. TODO - Specific action
3. TODO - Specific action

## Key Rules
- TODO - How to handle edge cases?
- TODO - How to handle errors?

## Gotchas
> This is the most valuable part. Write actual pitfalls you've encountered.

### Pitfall 1: TODO - Title
- **Symptom**: TODO - What goes wrong?
- **Fix**: TODO - How to fix it?
- **Cause**: TODO - Why does this happen?

### Pitfall 2: TODO
- **Symptom**: TODO
- **Fix**: TODO
- **Cause**: TODO

## Bundled Resources
> Progressive disclosure: Move detailed content here. SKILL.md should stay lean.

- TODO - See references/xx.md for detailed XX
- Executable scripts: see scripts/ directory
- Output templates: see assets/ directory
"""
