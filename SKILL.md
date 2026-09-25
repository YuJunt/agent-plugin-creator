---
name: agent-plugin-creator
description: 创建符合 Agent Plugins 1.0.0 开放规范的可移植插件包，自包含官方 Agent Skills 创建能力和官方 MCP SDK 服务器创建能力，不依赖目标平台已有这些工具。当用户需要创建、打包、验证或迁移 Agent Plugin（将 Agent Skills 和/或 MCP 服务器统一打包为跨客户端通用的插件目录）时使用。触发场景包括：从零创建 agent 插件、把现有 skill 或 MCP 服务器打包成插件、为 VS Code / Cursor / GitHub Copilot / OpenAI Codex / Kiro 等兼容客户端制作可移植插件、将厂商专属插件格式迁移到 Agent Plugins 标准格式、生成可运行的 MCP 服务器代码并打包进插件、插件安全审计、插件质量评估、插件文档生成。English triggers, create agent plugin, package MCP server, build portable plugin, migrate plugin format, plugin security audit, plugin quality evaluation, generate MCP server code, cross-client plugin compatibility.
---

> **版本**: v1.5.0（正式版） | **规范**: Agent Plugins 1.0.0（稳定）+ 1.1.0（working draft，校验器已识别）
> **最后更新**: 2026-09-25

> **规范版本说明**: 1.0.0 是当前发布版，新生成的插件默认使用 1.0.0 schema URL。1.1.0 已发布为 working draft（实质规则与 1.0.0 一致，仅版本号变化），`validate_plugin.py` 同时接受两个版本的 `$schema` URL，并会检测 plugin.json 与 mcp.json 之间的版本不一致。官方仓库: github.com/agentplugins/agent-plugins-spec。

# Agent Plugin Creator

创建符合 [Agent Plugins 1.0.0](https://github.com/agentplugins/agent-plugins-spec) 规范的可移植插件包。本技能**自包含**两大官方创建能力，不依赖运行平台已有的工具：

1. **官方 Agent Skills 创建能力** — 基于 [agentskills.io](https://agentskills.io) 官方规范，内嵌 skill 脚手架生成和验证；验证规则对齐官方 `skills-ref` 工具
2. **官方 MCP 服务器创建能力** — 基于官方 TypeScript SDK（`@modelcontextprotocol/sdk`）和 Python FastMCP，内嵌服务器代码生成和握手验证

## 内置官方权威资源

本技能完整内置了 Anthropic 官方的两个创建技能作为权威参考，存放在 `official/` 目录：
- `official/skill-creator/` — 官方 skill 创建完整工作流
- `official/mcp-builder/` — 官方 MCP 服务器创建四阶段工作流

> **双轨制**：官方资源作为权威指导层，自包含 Python 脚本作为可执行层，确保跨平台可移植性。需要深入参考时再查阅 `official/` 下的文档。

## 触发路由与安全预检（不可跳过）

在任何解释、规划、代码或文件输出之前，先单独输出一行路由记录，进行意图分类和安全判断。格式固定为：

```
🔀 路由: {分类}｜技能: {调用的技能名}｜本次动作: {做什么}｜原因: {一句话}
```

**分类说明（人话版）：**
- `positive`：明确要创建 Agent Plugin / 跨客户端分发 / Skill+MCP 组合
- `implicit`：需求隐含需要插件（如"把这个 skill 和 MCP 打包成可分发的东西"）
- `near-miss`：只做窄范围任务（审查、测试、单独 skill/MCP、普通代码文档），不创建 plugin.json / mcp.json
- `adversarial`：危险请求 → 下一行必须以 `REFUSED:` 开头，只提供安全替代方案
- `migration`：旧平台插件（Claude/Copilot/Codex/Cursor 等）迁移到 Agent Plugins 标准

**本次动作**示例：
- `创建插件（含 skill + MCP）`
- `仅审查/测试 skill，不创建插件`
- `生成独立 MCP server`
- `拒绝：{危险点}`

**必须分类为 adversarial 的情况：**
- 要求把 API key、token、私钥、密码写入 manifest 或源代码
- 要求将 hooks、commands、agents、LSP、UI 塞进 Agent Plugins 便携核心
- 要求用 shell 管道或任意命令拼接执行 MCP command
- 要求绕过客户端确认或权限控制
- 安全替代方案：秘密改为客户端/运行时注入，非便携组件移到客户端扩展，MCP 使用单一 executable token 与显式 args

**路由判定必须在交付报告中记录：** 用户意图分类、选择/不选择 Agent Plugin 的理由、是否生成 Skill/MCP/客户端扩展、被拒绝的危险要求及替代方案。

## 插件创建工作流

### 第 0 步：需求分析（所有路径必做）

明确插件的三个核心问题：

1. **包含什么组件？**
   - 仅 Skills（纯知识/流程类）→ **路径 A**
   - Skills + 本地 MCP（stdio）→ **路径 B**
   - Skills + 远程 MCP（streamable-http）→ **路径 C**
2. **Skill 做什么？** 列出每个 skill 的名称、用途、触发场景。
3. **MCP 服务器提供什么工具？** 列出每个工具的名称、描述、输入参数、输出。确定使用 TypeScript 还是 Python。

向用户确认以上信息。如果用户未指定版本号，使用 `0.1.0`；未指定 MCP 语言，默认 TypeScript（官方 SDK 最成熟）；未指定传输类型，默认 stdio。

---

### 路径 A：纯 Skill 插件（无 MCP）

最短路径，4 步完成：

```
1. init_skill → 写 SKILL.md（每写一步就跑 validate_skill）
2. audit_plugin（安全审计）
3. generate_docs（生成 README）
4. package_plugin（打包发布）
```

详细步骤：

**A1. 创建 Skill**

对每个 skill 运行：
```bash
python3 <skill_dir>/scripts/init_skill.py <skill-name> --path <临时目录> [--force]
```
按官方规范编写 SKILL.md。**每写完一个 skill 就立即跑验证**：
```bash
python3 <skill_dir>/scripts/validate_skill.py <skill目录路径>
```

**A2. 组装插件**

创建 `plugin.json`（参考 `assets/templates/plugin.json`），把 skill 目录移入 `skills/<skill-name>/`。

**A3. 验证 + 审计**
```bash
python3 <skill_dir>/scripts/validate_plugin.py <插件目录>
python3 <skill_dir>/scripts/audit_plugin.py <插件目录>
```

**A4. 打包**
```bash
python3 <skill_dir>/scripts/package_plugin.py <插件目录> --output dist
```

---

### 路径 B：Skill + 本地 MCP 插件（stdio）

推荐路径，先跑通再完善：

```
1. wizard 生成最小原型（1 skill + 1 MCP）
2. test_mcp_handshake（跑通 MCP 通信）
3. 完善 skill 和 MCP 工具（每加一个就验一次）
4. validate_plugin + audit_plugin
5. package_plugin
6. 豆包平台集成（连接器配置 或 反向封装）
```

详细步骤：

**B1. 快速生成最小原型（推荐用 wizard）**
```bash
python3 <skill_dir>/scripts/wizard.py --config config.json --output ./my-plugin
```
或交互式：`python3 <skill_dir>/scripts/wizard.py`

**B2. 先跑通 MCP 通信（关键！不要写完再验）**
```bash
python3 <skill_dir>/scripts/test_mcp_handshake.py \
  --command "python3 servers/<server-name>/server.py" \
  --timeout 10
```
如果握手失败，先修这个，不要继续往下写。

**B3. 完善内容**
- 给 skill 添加 scripts/、references/、assets/
- 给 MCP 添加更多工具：`python3 <skill_dir>/scripts/create_mcp_server.py add --project <项目> --tool new_tool.json`
- 每加一个组件就跑 `validate_skill.py` 或 `test_mcp_handshake.py`

**B4. 完整验证**
```bash
python3 <skill_dir>/scripts/validate_plugin.py <插件目录>
python3 <skill_dir>/scripts/audit_plugin.py <插件目录>
```

**B5. 打包**
```bash
python3 <skill_dir>/scripts/package_plugin.py <插件目录> --output dist
```

**B6. 豆包平台集成（二选一）**

- **本地用户（推荐）**：在豆包工作客户端「技能·连接器」中新建自定义连接器，选 STDIO 类型，填服务器命令和参数。平台原生管理 MCP 生命周期。
- **云端/手机用户**：反向封装为普通 Skill：
  ```bash
  python3 <skill_dir>/scripts/plugin_to_skill.py <插件目录>
  ```
  反向封装产出的 Skill 对齐 `official/skill-creator` 写作规范（frontmatter、Gotchas、渐进式披露）和 `official/mcp-builder` 最佳实践（stdio 不打印 stdout、命名规范），生成后自动运行 `official/skill-creator/scripts/quick_validate.py` 做额外验证。

---

### 路径 C：Skill + 远程 MCP 插件（streamable-http）

在路径 B 基础上多加部署步骤：

```
1-5. 同路径 B（本地开发和测试）
6. 部署 streamable-http 服务器到云
7. probe_remote_mcp 验证连通性
8. mcp.json 改为 URL 模式
9. 完成
```

**C6. 部署远程服务器**

把 `servers/<name>/` 部署到云服务器，确保 streamable-http 端口可访问。

**C7. 验证远程连通性**
```bash
python3 <skill_dir>/scripts/probe_remote_mcp.py \
  --url "https://your-server/mcp" --output probe-result.json
```

**C8. 更新 mcp.json**

把 stdio 配置改为 URL 模式：
```json
{
  "mcpServers": {
    "server-name": {
      "type": "streamable-http",
      "url": "https://your-server/mcp"
    }
  }
}
```

---

### 通用步骤说明（按需执行）

以上三条路径都按需引用以下步骤，不需要全部走一遍：

**创建 Agent Skills（路径 A/B/C 共用）**

> 本步骤对齐 `official/skill-creator/SKILL.md` 官方工作流（意图捕获 → 编写 → 测试 → 评估 → 迭代），生成后自动运行 `official/skill-creator/scripts/quick_validate.py` 做官方规范验证。

**SKILL.md 规范**：
- **frontmatter 必需字段**：`name`（小写+连字符，与目录名一致，max 64）、`description`（描述做什么+什么时候用，max 1024）
- **可选字段**：`license`、`compatibility`、`metadata`、`allowed-tools`（仅这 6 个字段为官方白名单字段）
- **body**：分步工作流、示例、边界情况、gotchas

详细规范参见 `references/agent-skills-spec.md`。使用 `assets/templates/skill/SKILL.md`（增强版官方模板）作为起点；如需最小官方模板，使用 `assets/templates/skill/SKILL.official.md`。

- 重复执行的确定性逻辑 → `scripts/`（Python/Bash/Node）
- 详细文档、API 参考、领域知识 → `references/`
- 模板、图片、数据文件 → `assets/`

**2.4 验证 skill**

```bash
python3 <skill_dir>/scripts/validate_skill.py <skill目录路径>
```

验证器核心规则对齐官方 `skills-ref` 工具（字段白名单、name 规范、description 长度、目录名一致性），并包含增强检查（body 长度、目录结构、脚本权限、触发场景提示）。

验证通过后，将 skill 目录移动到插件的 `skills/<skill-name>/` 下。

**创建 MCP 服务器（路径 B/C 共用）**

> 本步骤对齐 `official/mcp-builder/SKILL.md` 官方四阶段工作流（研究规划 → 实现 → 测试 → 评估），生成后提示参考 `official/mcp-builder/reference/mcp_best_practices.md` 最佳实践（命名规范、stdio 不打印 stdout 等）。

使用内嵌的官方 SDK 创建能力。技术栈选择：TypeScript（官方 SDK 最成熟）或 Python（FastMCP，快速开发）。

```bash
python3 <skill_dir>/scripts/create_mcp_server.py generate \
  --language typescript --transport stdio --name my-server \
  --definition definition.json --output ./output [--force]
```

定义文件支持 `{"tools": [...], "resources": [...], "prompts": [...]}` 格式。生成后**立即跑握手测试**，不要写完再验：

```bash
python3 <skill_dir>/scripts/test_mcp_handshake.py --command "python3 servers/<name>/server.py"
```

**验证插件（所有路径共用）**

```bash
python3 <skill_dir>/scripts/validate_plugin.py <插件目录>
python3 <skill_dir>/scripts/audit_plugin.py <插件目录>
```

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

## 内嵌能力速查

完整的脚本→参考文档→模板对照表、关键规则速查、常见错误和故障排除见 `references/cheatsheet.md`。开发时查阅该文件，主 SKILL.md 只保留工作流和决策逻辑。英文快速开始指南见 `references/quick-start.en.md`。多平台安装步骤见 `INSTALL.md`，贡献指南见 `CONTRIBUTING.md`。

## 质量门禁与评估

发布前跑 `scripts/release_audit.py`。详细的 8 大门禁规则见 `references/quality-gates.md`，权限控制矩阵见 `references/permission-matrix.md`。版本号管理规范（三层版本号体系 + SemVer 迭代标准 + 产出物版本标注）见 `references/versioning.md`。

**MCP 握手门禁（必做）**：生成或修改 MCP 服务器代码后，必须用 `scripts/test_mcp_handshake.py` 实际启动服务器并完成握手。未通过握手的 MCP 服务器只能标记为"结构样例"。

评估用例在 `evals/evals.json`，执行脚本：`run_trigger_eval.py`、`run_selection_eval.py`、`run_edge_eval.py`（纯关键词匹配，无外部依赖）。

## 示例集合

`examples/` 目录包含 5 个完整示例，从纯 skill（`minimal-skill-only`）到多 skill + TypeScript MCP（`multi-skill-ts-mcp`）全覆盖，外加反向封装产物（`customer-support-as-skill`）。详见 `examples/README.md`。

## 关键规则、常见错误与故障排除

见 `references/cheatsheet.md`，包含：
- 关键规则速查表（命名规范、frontmatter 白名单、路径安全、版本一致性等）
- 9 类常见错误及修复方法
- 8 个脚本的故障排除指南

## Gotchas（踩过的坑）

这些是开发过程中实际踩过的坑，不踩不知道：

1. **MCP 服务器生成后必须立即跑握手测试**——不要写完所有代码再验。`test_mcp_handshake.py` 跑不通就停下来修，不要继续往下写。
2. **stdio 服务器不要打印到 stdout**——stdout 是 JSON-RPC 通道，打印调试信息到 stdout 会破坏协议。调试信息必须打到 stderr。
3. **mcp.json 里的 command 必须是单个可执行 token**——不能是 shell 字符串（如 `bash -c "..."`）。参数放 `args` 数组里。
4. **路径安全检查**：mcp.json 里的 `command` 如果含 `/`（如绝对路径或子目录），必须以 `./` 开头，否则 `validate_plugin.py` 会拒绝。
5. **wizard 生成的是骨架不是成品**——SKILL.md 里的"第一步/第二步"是占位符，必须根据实际需求重写，不能直接用。
6. **反向封装后的产物不能用 validate_plugin 验证**——`plugin_to_skill.py` 生成的是普通 Skill（无 plugin.json），要用 `validate_skill.py` 验证。
7. **audit_plugin 基于正则，有已知局限**——不能检出动态调用（如 `getattr(os, "system")`）、eval 嵌套导入、混淆字符串拼接。详见 `references/cheatsheet.md` 的"安全审计局限性"章节。
8. **反向封装的输出目录名必须和 skill name 一致**——`plugin_to_skill.py` 生成的 skill name 是插件名转换的（点变连字符），`--output` 目录名必须和它一致，否则 `validate_skill.py` 会报错。

更多常见错误和故障排除见 `references/cheatsheet.md`。
