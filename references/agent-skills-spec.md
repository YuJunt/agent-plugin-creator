# Agent Skills 官方规范参考

本文档基于 [agentskills.io](https://agentskills.io) 官方规范，是创建插件内 Agent Skills 的权威参考。规范原文：https://agentskills.io/specification.md

## 目录

1. [什么是 Agent Skill](#什么是-agent-skill)
2. [目录结构](#目录结构)
3. [SKILL.md 格式](#skillmd-格式)
4. [Frontmatter 字段详解](#frontmatter-字段详解)
5. [Body 内容指南](#body-内容指南)
6. [可选目录约定](#可选目录约定)
7. [渐进式加载](#渐进式加载)
8. [文件引用规范](#文件引用规范)
9. [创建工作流](#创建工作流)
10. [验证清单](#验证清单)
11. [常见陷阱](#常见陷阱)

---

## 什么是 Agent Skill

Agent Skill 是一个目录，包含至少一个 `SKILL.md` 文件，用于将专业知识、工作流和代码打包成可移植、版本控制的技能目录，AI agent 按需加载。

核心设计原则：**渐进式加载**——agent 启动时只加载每个 skill 的 name 和 description（~50-100 tokens）；当任务匹配到某个 skill 时，才加载完整的 SKILL.md body；如果指令引用了支持文件，再按需加载。

## 目录结构

```
skill-name/
├── SKILL.md          # 必需：frontmatter + 指令
├── scripts/          # 可选：可执行代码
│   ├── script.py
│   └── script.sh
├── references/       # 可选：文档
│   ├── REFERENCE.md
│   └── api-errors.md
└── assets/           # 可选：模板、图片、数据
    ├── template.md
    └── lookup-table.json
```

除了必需的 `SKILL.md`，skill 目录可以包含任何文件和目录。上述三个目录是组织常见内容的推荐约定。

## SKILL.md 格式

`SKILL.md` 文件必须包含 YAML frontmatter，后跟 Markdown 内容。

### 最小示例

```markdown
---
name: skill-name
description: A description of what this skill does and when to use it.
---

# Skill Title

技能指令内容...
```

### 含可选字段的示例

```markdown
---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
license: Apache-2.0
compatibility: Requires Python 3.10+ and pdftotext
metadata:
  author: example-org
  version: "1.0"
---
```

## Frontmatter 字段详解

### 必需字段

| 字段 | 约束 | 说明 |
|------|------|------|
| `name` | 1-64 字符，小写字母+数字+连字符，不以连字符开头/结尾，不含连续连字符，必须与父目录名一致 | skill 的唯一标识符 |
| `description` | 1-1024 字符，非空 | 描述 skill 做什么**以及**什么时候使用它。承担触发匹配的全部责任 |

### name 字段

- 必须是 1-64 字符
- 只能包含 Unicode 小写字母数字字符（`a-z`, `0-9`）和连字符（`-`）
- 不能以连字符开头或结尾
- 不能包含连续连字符（`--`）
- 必须与父目录名完全一致

**有效示例**：`pdf-processing`、`data-analysis`、`code-review`

**无效示例**：
- `PDF-Processing`（不允许大写）
- `-pdf`（不能以连字符开头）
- `pdf--processing`（不允许连续连字符）
- `pdf.processing`（不允许点，这是 agentskills.io 规范与 Agent Plugins plugin name 的区别）

### description 字段

- 必须是 1-1024 字符
- 应该同时描述 skill 做什么和什么时候使用
- 应该包含帮助 agent 识别相关任务的特定关键词

**好的示例**：
```
Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.
```

**差的示例**：
```
Helps with PDFs.
```

### 可选字段

| 字段 | 约束 | 说明 |
|------|------|------|
| `license` | 短字符串 | 许可证名称或对捆绑许可证文件的引用 |
| `compatibility` | 1-500 字符（如提供） | 环境要求（目标产品、系统包、网络访问等）。大多数 skill 不需要此字段 |
| `metadata` | 字符串键到字符串值的映射 | 客户端可用于存储规范未定义的额外属性。建议键名足够独特以避免冲突 |
| `allowed-tools` | 空格分隔的工具名字符串 | 预批准可运行的工具（实验性，支持程度因实现而异） |

#### license 示例
```yaml
license: Proprietary. LICENSE.txt has complete terms
```

#### compatibility 示例
```yaml
compatibility: Designed for Claude Code (or similar products)
compatibility: Requires git, docker, jq, and access to the internet
compatibility: Requires Python 3.14+ and uv
```

#### metadata 示例
```yaml
metadata:
  author: example-org
  version: "1.0"
```

#### allowed-tools 示例
```yaml
allowed-tools: Bash(git:*) Bash(jq:*) Read
```

## Body 内容指南

frontmatter 之后的 Markdown body 包含 skill 指令。没有格式限制，写任何能帮助 agent 有效执行任务的内容。

**推荐包含的部分**：
- 分步指令
- 输入输出示例
- 常见边界情况

**写作原则**：
- 专注于 agent **没有你的 skill 就不会知道**的内容：项目特定约定、非显而易见的边界情况、该用什么工具
- 省略通用知识（什么是 PDF、HTTP 如何工作）
- 包含一个 "gotchas" 部分，列出违背合理假设的环境特定事实——这通常是许多 skill 中价值最高的内容
- 保持主 `SKILL.md` 在 500 行以内，详细参考材料移到单独文件

## 可选目录约定

### scripts/

包含 agent 可以运行的可执行代码。脚本应该：
- 自包含或清楚记录依赖
- 包含有帮助的错误消息
- 优雅处理边界情况

支持的语言取决于 agent 实现，常见选项包括 Python、Bash、JavaScript。

**常见脚本模式**：

| 用例 | 命令 | 说明 |
|------|------|------|
| Python 内联依赖 | `uv run scripts/extract.py` | 需要 uv，使用 PEP 723 语法 |
| Python pipx | `pipx run 'package==version'` | 需要 pipx |
| Node.js 包 | `npx eslint@9 --fix .` | 随 Node.js 捆绑，固定版本 |
| Deno 脚本 | `deno run scripts/extract.ts` | 自包含，用 `npm:` 引用 npm 包 |
| Bash 脚本 | `bash scripts/validate.sh` | 无依赖，保持自包含 |

### references/

包含 agent 可以按需阅读的额外文档：
- `REFERENCE.md` — 详细技术参考
- `FORMS.md` — 表单模板或结构化数据格式
- 领域特定文件（`finance.md`、`legal.md` 等）

保持单个参考文件聚焦。agent 按需加载，所以更小的文件意味着更少的上下文占用。

### assets/

包含静态资源：
- 模板（文档模板、配置模板）
- 图片（图表、示例）
- 数据文件（查找表、schema）

## 渐进式加载

Agent 渐进式加载 skills，仅在任务需要时引入更多细节：

1. **元数据**（~100 tokens）：启动时加载所有 skill 的 `name` 和 `description`
2. **指令**（推荐 < 5000 tokens）：skill 被激活时加载完整 `SKILL.md` body
3. **资源**（按需）：仅在需要时加载文件（如 `scripts/`、`references/`、`assets/` 中的文件）

## 文件引用规范

在 skill 中引用其他文件时，使用相对于 skill 根目录的相对路径：

```markdown
See [the reference guide](references/REFERENCE.md) for details.
Run the extraction script:
scripts/extract.py
```

保持文件引用距 `SKILL.md` 一层深。避免深度嵌套的引用链。

## 创建工作流

### 创建一个 skill

1. **识别领域** — 这个 skill 捕获什么专业知识或工作流？它是否足够窄以保持内聚（一个 skill = 一个工作单元）但又足够宽以可复用？
2. **收集素材** — 不要让 LLM 从零生成 skill。收集真实的专业知识：内部 runbook、API 规范、代码审查评论、版本控制历史、失败案例和解决方案。将这些输入 skill 创建过程。
3. **创建目录和 SKILL.md** — 创建 `skill-name/SKILL.md`，包含 `name` 字段（小写、连字符、与目录名匹配）和 `description` 字段（1-1024 字符，描述做什么和什么时候用），以及 Markdown body 中的分步指令。
4. **为 agent 的上下文写作** — 专注于 agent 没有你的 skill 就不会知道的内容。省略通用知识。
5. **添加 gotchas 部分** — 包含违背合理假设的环境特定事实。
6. **按需捆绑脚本** — 如果 agent 会在测试用例中重复运行相同逻辑，编写经过测试的脚本放在 `scripts/` 中，用相对路径从 `SKILL.md` 引用。
7. **测试触发** — 创建 20 个评估查询（8-10 个应触发，8-10 个不应触发），用不同的措辞、明确度和复杂度。每个查询运行 3 次，计算触发率。如果 skill 应触发时没触发，修改 `description` 字段。
8. **测试输出质量** — 运行 2-3 个测试用例，分别在有 skill 和无 skill（基线）的情况下运行。根据断言对输出评分。比较通过率和 token 使用量。根据失败迭代。

### 优化 skill description

1. **设计评估查询** — 创建 20 个现实用户提示，标记是否应触发 skill。包含近似失误（共享关键词但需要不同东西的查询）。
2. **划分训练/验证集** — ~60% 训练，~40% 验证。用训练集指导改进，用验证集检查泛化。
3. **评估当前 description** — 每个查询运行 3 次，计算触发率。应触发查询触发率 > 0.5 为通过，不应触发查询 < 0.5 为通过。
4. **识别失败** — 哪些应触发查询没触发？哪些不应触发查询误触发？
5. **修改 description** — 应触发失败则拓宽范围或添加上下文；不应触发误触发则增加特异性或澄清边界。避免过度拟合特定关键词。
6. **重复** — 在训练集上评估、修改、重复，直到所有训练查询通过或改进停滞（通常 5 次迭代）。
7. **选择最佳迭代** — 选择验证集通过率最高的描述，不一定是最后一个。
8. **验证** — 更新 `SKILL.md`，用 5-10 个新查询做 sanity check。

## 验证清单

在最终确定 skill 之前：

- [ ] `SKILL.md` 存在于 skill 目录根目录
- [ ] `name` 字段 1-64 字符，仅小写字母+数字+连字符，与父目录名一致
- [ ] `name` 不以连字符开头/结尾，不含连续连字符
- [ ] `description` 字段 1-1024 字符，非空，同时描述做什么和什么时候用
- [ ] `description` 使用祈使句式（"Use when..."）并列出特定上下文
- [ ] skill 指令专注于 agent 没有 skill 就不会知道的内容
- [ ] gotchas 部分包含违背合理假设的环境特定事实
- [ ] 脚本自包含或清楚记录依赖
- [ ] 脚本避免交互式提示，包含有帮助的错误消息
- [ ] 脚本中的相对路径正确（相对于 skill 目录根目录）
- [ ] 捆绑的脚本有 `--help` 输出记录用法
- [ ] `SKILL.md` body 在 500 行以内；详细参考材料在 `references/` 中
- [ ] skill 已在 2-3 个现实测试用例上测试
- [ ] skill 在应触发查询上触发，在不应触发查询上不触发
- [ ] 有 skill 时输出质量优于无 skill（更高通过率，可接受的 token 成本）
- [ ] `license` 字段（如提供）简短清晰
- [ ] `compatibility` 字段（如提供）记录环境要求

## 常见陷阱

- **description 没有传达什么时候使用 skill** — description 承担触发的全部责任。如果它不说什么时候有用，agent 就不知道该用它。使用祈使句式（"Use when..."），列出特定上下文，包含用户可能不会明确提及的关键词。
- **description 过度拟合特定查询** — 优化描述时，避免添加失败查询中的精确关键词。相反，泛化到这些查询代表的概念。使用训练/验证划分来检测过度拟合。
- **skill 指令太模糊** — "Handle errors appropriately" 没有帮助。要具体："If the API returns a 429 status, wait 60 seconds and retry up to 3 times." 模糊指令导致 agent 浪费轮次尝试多种方法。
- **skill 指令太全面** — 详尽的文档弊大于利。agent 难以提取相关内容，可能追求无效路径。简洁的分步指导加可用示例优于详尽的规则。
- **脚本有交互式提示** — agent 在非交互式 shell 中操作。阻塞在 TTY 提示、密码对话框或确认菜单上的脚本会无限期挂起。所有输入通过命令行标志、环境变量或 stdin 接受。
- **脚本错误消息差** — 脚本失败时，错误消息直接塑造 agent 的下一次尝试。"Error: invalid input" 浪费一轮。改为："Error: --format must be one of: json, csv, table. Received: 'xml'."
- **上下文压缩期间 skill 内容丢失** — 如果 agent 在上下文窗口填满时截断旧消息，skill 指令可能被修剪，静默降低性能。将 skill 内容标记为受保护不被修剪。
- **脚本中的相对路径解析不正确** — 脚本应从 skill 目录根目录运行。用相对路径引用捆绑文件：`scripts/extract.py`、`references/api-errors.md`。agent 自动解析这些。
- **skill 在不应处理的简单任务上触发** — agent 只在需要超出自身能力的专业知识时才咨询 skill。一个在 "read this PDF" 上触发的 skill（即使 agent 原生能做）是在浪费上下文。写强调什么时候需要专业知识的 description。
- **name 字段与目录名不匹配** — `name` 字段必须与父目录名完全匹配。`name: pdf-processing` 要求目录是 `pdf-processing/`，不是 `PDF-Processing/` 或 `pdf_processing/`。
- **name 中有连续连字符或开头/结尾连字符** — 无效：`pdf--processing`、`-pdf-processing`、`pdf-processing-`。有效：`pdf-processing`、`data-analysis`、`code-review`。
- **description 超过 1024 字符** — 描述在优化过程中容易增长。最终确定前检查字符数。
- **捆绑脚本没有声明依赖** — 如果脚本需要外部包，内联声明（Python 用 PEP 723，Deno 用 `npm:` 等）或在 `SKILL.md` 和 `compatibility` 字段中记录前置条件。
