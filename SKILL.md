---
name: agent-plugin-creator
description: 创建符合 Agent Plugins 1.0.0 开放规范的可移植插件包，自包含官方 Agent Skills 创建能力和官方 MCP SDK 服务器创建能力，不依赖目标平台已有这些工具。当用户需要创建、打包、验证或迁移 Agent Plugin（将 Agent Skills 和/或 MCP 服务器统一打包为跨客户端通用的插件目录）时使用。触发场景包括：从零创建 agent 插件、把现有 skill 或 MCP 服务器打包成插件、为 VS Code / Cursor / GitHub Copilot / OpenAI Codex / Kiro 等兼容客户端制作可移植插件、将厂商专属插件格式迁移到 Agent Plugins 标准格式、生成可运行的 MCP 服务器代码并打包进插件、插件安全审计、插件质量评估、插件文档生成。English triggers, create agent plugin, package MCP server, build portable plugin, migrate plugin format, plugin security audit, plugin quality evaluation, generate MCP server code, cross-client plugin compatibility.
---
> **版本**: v2.5.0（正式版） | **规范**: Agent Plugins 1.0.0（稳定）+ 1.1.0（working draft，校验器已识别）
> **最后更新**: 2026-09-27
> **规范版本说明**: 1.0.0 是当前发布版，新生成的插件默认使用 1.0.0 schema URL。1.1.0 已发布为 working draft（实质规则与 1.0.0 一致，仅版本号变化），`validate_plugin.py` 同时接受两个版本的 `$schema` URL，并会检测 plugin.json 与 mcp.json 之间的版本不一致。官方仓库: github.com/agentplugins/agent-plugins-spec。

# Agent Plugin Creator
## 概述

创建符合 Agent Plugins 1.0.0 规范的可移植插件包，自包含官方 Skill 创建和 MCP 服务器创建能力，不依赖目标平台。支持从零创建、打包、验证、审计、迁移插件。

## 快速开始

> **🚀 快速开始（第一次用？看这里）**
>
> **我想做什么？** → **我该怎么做？**
>
> | 我想做什么 | 运行什么命令 |
> |---|---|
> | 从零创建一个插件 | `plugin.py new` |
> | 创建一个带 skill 的插件 | `plugin.py skill my-skill --lang zh` |
> | 创建一个带 MCP 服务器的插件 | `plugin.py mcp` |
> | 验证我写的插件对不对 | `plugin.py validate ./my-plugin` |
> | 检查我的插件安全吗 | `plugin.py audit ./my-plugin` |
> | 打包发布我的插件 | `plugin.py package ./my-plugin` |
>
> **📖 完整教程：** 参见 `references/workflows.md`（从零创建插件的 5 步指南）

创建符合 [Agent Plugins 1.0.0](https://github.com/agentplugins/agent-plugins-spec) 规范的可移植插件包。本技能**自包含**两大官方创建能力，不依赖运行平台已有的工具：

1. **官方 Agent Skills 创建能力** — 基于 [agentskills.io](https://agentskills.io) 官方规范，内嵌 skill 脚手架生成和验证；验证规则对齐官方 `skills-ref` 工具
2. **官方 MCP 服务器创建能力** — 基于官方 TypeScript SDK（`@modelcontextprotocol/sdk`）和 Python FastMCP，内嵌服务器代码生成和握手验证

## 内置官方权威资源

本技能完整内置了 Anthropic 官方的两个创建技能作为权威参考，存放在 `official/` 目录：
- `official/skill-creator/` — 官方 skill 创建完整工作流
- `official/mcp-builder/` — 官方 MCP 服务器创建四阶段工作流

> **双轨制**：官方资源作为权威指导层，自包含 Python 脚本作为可执行层，确保跨平台可移植性。

### 如何使用内置官方资源

**创建 Skill 时：**
1. 先读 `official/skill-creator/SKILL.md` 的工作流
2. 用 `official/skill-creator/scripts/quick_validate.py` 验证规范
3. 用 `official/skill-creator/scripts/improve_description.py` 优化触发率
4. 参考 `official/skill-creator/agents/grader.md` 的评估标准

**创建 MCP 服务器时：**
1. 先读 `official/mcp-builder/SKILL.md` 的四阶段工作流
2. 遵循 `official/mcp-builder/reference/mcp_best_practices.md` 的最佳实践
3. 参考 `official/mcp-builder/reference/python_mcp_server.md` 或 `node_mcp_server.md`
4. 用 `official/mcp-builder/scripts/evaluation.py` 评估质量

**⚠️ 不要跳过官方资源直接写代码！** 官方资源已经过 Anthropic 工程师验证，遵循它们可以避免常见坑。

> **⚠️ MCP 2026-07-28 新规范弃用警告**：以下三个功能在 MCP 2026-07-28 规范中已被弃用，新生成的服务器**不再包含**这些功能：
> - **Roots（根目录）** → 替代方案：用工具参数、资源 URI 或服务器配置
> - **Sampling（采样）** → 替代方案：直接集成 LLM 提供商 API
> - **Logging（日志）** → 替代方案：stdio 用 stderr，结构化观测用 OpenTelemetry
>
> 如需从旧版 MCP v1 迁移到 v2（无状态模式），使用官方 codemod：`npx @modelcontextprotocol/codemod@beta v1-to-v2 .`

## 工作流程（3 阶段）

> **详细步骤见 `references/workflows.md`**，包含三条路径（纯 Skill / Skill+本地 MCP / Skill+远程 MCP）。

### 阶段 1：创建
```bash
plugin.py new          # 交互式创建插件骨架（推荐）
plugin.py skill        # 单独初始化 skill 骨架
plugin.py mcp          # 单独生成 MCP 服务器
```

### 阶段 2：验证 + 调试
```bash
plugin.py validate     # 验证插件结构
plugin.py audit        # 安全审计
plugin.py test         # 完整插件测试（验证链+冒烟+质量评分+MCP握手，三级门禁）
plugin.py mcp-test     # MCP 握手测试（单独测试 MCP 服务器）
plugin.py smoke        # 冒烟测试
plugin.py score        # 质量评分（目标 ≥80 分）
```
**完成标准：** 验证 0 错误 + 审计 0 critical/high + 测试 0 失败

### 阶段 3：发布
```bash
plugin.py docs         # 生成文档
plugin.py package      # 打包发布
plugin.py release-audit # 发布前审计
```

> 本流程对齐 `official/skill-creator` 和 `official/mcp-builder`，创建前应先读对应官方资源。高级功能见 `references/advanced.md`。

## 触发路由（编排器大脑）

> **详细路由规则和映射表见 `references/advanced.md`**
>
> **核心原则：路由不只是分类，而是构建完整执行计划——决定加载什么上下文、用什么门禁、走什么路径、输出什么格式。**

### 路由决策流程（5 步）

```
用户请求 → 意图分析 → 上下文感知 → 分类+置信度+风险 → 构建执行计划 → 透明通信 → 执行
```

### 路由分类

| 分类 | 识别特征 | 执行路径 |
|---|---|---|
| `positive` | 明确说"创建插件"、"打包"、"生成 MCP" | 直接走完整创建工作流 |
| `implicit` | 说"把这个 skill 分发出去"、"做个可移植的包" | 先确认需求，再走创建工作流 |
| `near-miss` | 只说"验证这个 skill"、"检查安全" | 只做对应窄范围任务，不创建插件 |
| `adversarial` | 要求写 API key、绕过权限、塞非便携组件 | 拒绝，给出安全替代方案 |
| `migration` | 说"从 Claude 插件迁移"、"转成标准格式" | 走迁移路径，用 client_adapter |

### 置信度 + 风险分级

**置信度：** ≥80% 直接执行 / 60-80% 先确认 / <60% 问澄清问题

**风险分级（决定门禁级别）：**

| 风险 | 操作类型 | 门禁 | 处理方式 |
|---|---|---|---|
| 🟢 低 | 只读：验证、审计、查看、评分 | standard | 自动执行 |
| 🟡 中 | 有副作用但可逆：创建、打包 | strict | 执行前告知 |
| 🔴 高 | 不可逆：覆盖、删除、公开发布 | critical | 必须用户确认 |

### 构建执行计划（路由驱动一切）

路由结果决定：
- **上下文加载**：只加载相关 references（避免注意力稀释）
- **门禁级别**：根据风险选择 standard/strict/critical
- **Gotchas 展示**：只展示相关的坑
- **输出格式**：简洁/步骤化/报告

> **详细映射表见 `references/advanced.md`**（5 种场景的 references 加载、4 种场景的 Gotchas 展示、4 种输出格式）

### 透明通信（路由决策可观测性）

执行前输出路由决策轨迹：

```
🔀 路由决策
意图：创建插件（含 Skill + MCP）
分类：positive | 置信度：90% | 风险：🟡中 | 门禁：strict
上下文：workflows.md + mcp-server-guide.md + cheatsheet.md
预计：5 步
```

危险请求（必须拒绝）：写 API key / 绕过权限 / 把非便携组件塞进核心

## 插件创建工作流

> **详细工作流见 `references/workflows.md`**，包含三条路径（纯 Skill / Skill+本地 MCP / Skill+远程 MCP）的详细步骤。

**快速概览：**
- **路径 A**：纯 Skill 插件（最短，4 步）
- **路径 B**：Skill + 本地 MCP（推荐，先跑通再完善）
- **路径 C**：Skill + 远程 MCP（在路径 B 基础上加部署）

**通用步骤：**
1. 创建 Skill / MCP
2. 验证 + 审计
3. 打包发布

## 快速入口：交互式创建向导

对于从零创建插件的场景，可使用交互式向导，通过问答自动生成完整插件结构：

```bash
# 交互式创建
python3 <skill_dir>/scripts/wizard.py

# 从配置文件创建（非交互式）
python3 <skill_dir>/scripts/wizard.py --config config.json --output ./my-plugin

# 预览模式
python3 <skill_dir>/scripts/wizard.py --config config.json --dry-run
```

向导自动生成：plugin.json、skills/（含 SKILL.md + scripts/references/assets 目录）、mcp.json、servers/（TypeScript 或 Python 完整模板）、README.md、.gitignore。

## 内嵌能力速查（完整脚本清单）

> **所有脚本都在 `scripts/` 目录下，统一入口是 `plugin.py`。**
>
> 大部分日常操作用 `plugin.py <命令>` 就行，下面是完整清单供需要高级功能时查阅。

### 创建类

| 脚本 | 功能 | 命令 |
|---|---|---|
| `wizard.py` | 交互式创建插件（推荐） | `plugin.py new` |
| `init_skill.py` | 初始化 Skill 脚手架 | `plugin.py skill` |
| `create_mcp_server.py` | 生成 MCP 服务器代码 | `plugin.py mcp` |
| `plugin_to_skill.py` | 反向封装：插件→普通 Skill | 高级 |

### 验证与质量类

| 脚本 | 功能 | 命令 |
|---|---|---|
| `validate_plugin.py` | 验证插件结构 | `plugin.py validate` |
| `validate_skill.py` | 验证单个 Skill | 高级 |
| `audit_plugin.py` | 安全审计 | `plugin.py audit` |
| `smoke_test.py` | 冒烟测试 | `plugin.py smoke` |
| `test_mcp_handshake.py` | MCP 握手测试 | `plugin.py mcp-test` |
| （验证链组合） | 完整插件测试（三级门禁） | `plugin.py test` |
| `check_skill_quality.py` | Skill 质量自动检查 | `python3 scripts/check_skill_quality.py .` |
| `score_plugin.py` | 插件质量评分 | `plugin.py score` |
| `release_audit.py` | 发布前审计 | `plugin.py release-audit` |

### 评估类

| 脚本 | 功能 |
|---|---|
| `run_evals.py` | 统一评估入口（`--type trigger/selection/edge/all`） |

### 打包与发布类

| 脚本 | 功能 | 命令 |
|---|---|---|
| `package_plugin.py` | 打包插件 | `plugin.py package` |
| `generate_docs.py` | 生成文档 | `plugin.py docs` |
| `client_adapter.py` | 多客户端适配 | 高级 |

### 其他工具

| 脚本 | 功能 |
|---|---|
| `skill_template.py` | 共享模板生成器（内部用） |
| `errors.py` | 统一错误码（内部用） |

> **详细的脚本→参考文档→模板对照表、关键规则速查、常见错误和故障排除见 `references/cheatsheet.md`。**
>
> 多平台安装步骤见 `INSTALL.md`，贡献指南见 `CONTRIBUTING.md`。

## 质量门禁与评估

发布前跑 `scripts/release_audit.py`。详细的质量门禁规则、验证清单、评估协议、回归矩阵和版本号管理规范见 `references/quality.md`。触发路由规则和高级功能索引见 `references/advanced.md`。

### 规范参考文档

| 文档 | 内容 | 什么时候读 |
|---|---|---|
| `references/plugin-specification.md` | Agent Plugins 1.0.0 完整规范 | 不确定插件格式时 |
| `references/agent-skills-spec.md` | Agent Skills 官方规范 | 不确定 Skill 格式时 |
| `references/mcp-server-guide.md` | MCP 服务器完整开发指南 | 开发 MCP 服务器时 |

**MCP 握手门禁（必做）**：生成或修改 MCP 服务器代码后，必须用 `scripts/test_mcp_handshake.py` 实际启动服务器并完成握手。未通过握手的 MCP 服务器只能标记为"结构样例"。

> **双时代协议支持**：test_mcp_handshake.py 同时支持旧版（2024-11-05，有状态握手）和新版（2026-07-28，无状态模式）协议。默认 `--mode auto` 自动检测，先试旧版握手，失败则自动切换新版无状态模式。也可以用 `--mode legacy` 或 `--mode stateless` 强制指定。

评估用例在 `evals/evals.json`，执行脚本：`run_evals.py --type {trigger|selection|edge|all}`（纯关键词匹配，无外部依赖）。

> **description 优化检查清单**（7 项同义词/动词范围/被动语气检查）见 `references/advanced.md`。

## 示例集合

`examples/` 目录包含 5 个完整示例，从纯 skill（`minimal-skill-only`）到多 skill + TypeScript MCP（`multi-skill-ts-mcp`）全覆盖，外加反向封装产物（`customer-support-as-skill`）。详见 `examples/README.md`。

## 关键规则、常见错误与故障排除

见 `references/cheatsheet.md`，包含：
- 关键规则速查表（命名规范、frontmatter 白名单、路径安全、版本一致性等）
- 9 类常见错误及修复方法
- 8 个脚本的故障排除指南

**质量检查清单**：发布前对照 `references/quality.md` 逐项检查，三层分类（必备层×2 / 推荐层×1 / 可选层×0.5），必备层必须100%达标才能发布。

## Gotchas（踩过的坑）

> **详细 Gotchas 见 `references/cheatsheet.md`**，**LLM 特有失败模式**见 `references/advanced.md`。

### 失败模式速查表

| Issue | Recovery |
|---|---|
| MCP 握手失败 | 检查 stdout 调试信息 → 改 stderr；检查协议版本（`--mode auto`） |
| 验证报错 name 不一致 | plugin.json 的 name 与目录名完全一致 |
| 安全审计报硬编码密钥 | 改用环境变量，不要在代码里写 API key |
| 打包后插件不能用 | 重新跑验证链，不要用 `--skip-verify` |
| 反向封装后验证报错 | 用 `validate_skill.py` 不是 `validate_plugin.py` |
| wizard 骨架直接发布 | 必须填充 TODO，重写 SKILL.md，跑完整验证 |
| mcp.json command 报错 | command 是单个可执行文件，参数放 `args` 数组 |

### 坑 1：MCP 服务器写完再验，结果全是错
生成后立即跑 `test_mcp_handshake.py`，不要写完直接打包。

### 坑 2：stdio 服务器打印调试信息到 stdout
stdout 是 JSON-RPC 协议通道，调试信息必须打到 stderr。

### 坑 3：wizard 生成的骨架直接当成品用
骨架不是成品，必须重写 SKILL.md、填充 Gotchas、跑完整验证。

更多坑见 `references/cheatsheet.md` 和 `references/advanced.md`。
