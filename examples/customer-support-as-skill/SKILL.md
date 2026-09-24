---
name: customer-support-as-skill
description: Triage support tickets, identify SLA risk, and recommend evidence-based routing actions.。本技能由 Agent Plugin 反向封装而来，提供以下能力：ticket-triage。可调用 MCP 服务器：support-tickets。当用户需要相关功能时使用。
metadata:
  source: agent-plugin
  plugin-version: 0.1.0
  wrapper-version: 1.0.0
---

# customer-support-as-skill（Skill 封装版）

> 本技能由 Agent Plugin v0.1.0 反向封装生成。
> 原始插件描述：Triage support tickets, identify SLA risk, and recommend evidence-based routing actions.
> 封装原理：用 AI 手动读取子技能和启动 MCP 服务器，替代平台自动加载，
> 使其可以在任何支持 Agent Skills 的平台上使用。

## 能力清单

### 子技能

- **ticket-triage**：Triage customer support tickets, identify SLA and escalation risk, and recommend routing using the support-ticket MCP server. Use for queue review, incident escalation, priority assessment, and weekly support operations reporting.
  - 位置：`skills/ticket-triage/SKILL.md`

### MCP 服务器

- **support-tickets**：transport=stdio
  - 启动命令：`python3 ${PLUGIN_ROOT}/servers/support-tickets/support_ticket_server.py`

使用 MCP 工具前，先运行 `scripts/start_mcp.py` 启动服务器，
然后通过 stdio（JSON-RPC）或 HTTP 与服务器通信调用工具。

## 使用指南

### 路由判断

根据用户请求，判断使用哪种能力：

| 用户意图 | 使用的子技能 | 操作 |
|---------|------------|------|
| 需要Triage customer supp... | ticket-triage | 读取 `skills/ticket-triage/SKILL.md` 并按其步骤执行 |

| 用户意图 | 使用的 MCP | 操作 |
|---------|-----------|------|
| 需要调用support-tickets相关工具 | support-tickets | 运行 `scripts/start_mcp.py --server support-tickets` 启动后调用 |

### 使用子技能

当需要使用某个子技能时：

1. 读取对应子技能的 `SKILL.md` 完整内容
2. 按照其中的步骤、规则和最佳实践执行
3. 如果子技能有 `scripts/`，按需运行其中的脚本
4. 如果子技能有 `references/`，按需读取参考文档

### 使用 MCP 服务器

当需要调用 MCP 工具时：

1. 运行 `scripts/start_mcp.py --list` 查看可用服务器
2. 运行 `scripts/start_mcp.py --server <名称>` 启动指定服务器
3. 通过 stdio 发送 JSON-RPC 请求（initialize → tools/list → tools/call）
4. 获取结果后，关闭服务器进程

**注意**：MCP 服务器是独立进程，使用完毕后应确保关闭，避免资源泄漏。

## 原始插件配置

- 插件元数据：`references/plugin.json`
- MCP 配置：`references/mcp.json`

如需了解原始插件的完整结构和配置，可查阅上述文件。

## 限制说明

本封装版与原生 Agent Plugin 支持的区别：

1. **子技能不会被自动发现**——需要 AI 主动读取对应子技能的 SKILL.md
2. **MCP 不会被自动启动**——需要 AI 运行 start_mcp.py 手动启动
3. **客户端扩展不可用**——原生插件的客户端专属扩展（hooks、commands 等）在封装版中不生效
4. **功能基本完整**——核心的 skills 和 MCP 能力均可正常使用，用户体验基本无缝

