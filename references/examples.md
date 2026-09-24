# Agent Plugin 示例集合

本文档提供三种典型 Agent Plugin 的完整示例，供创建插件时参考。

## 目录

1. [示例一：仅 Skills 的插件](#示例一仅-skills-的插件)
2. [示例二：仅 MCP 服务器的插件](#示例二仅-mcp-服务器的插件)
3. [示例三：Skills + MCP 完整插件](#示例三skills--mcp-完整插件)
4. [带客户端扩展的插件](#带客户端扩展的插件)

---

## 示例一：仅 Skills 的插件

适用于纯指令/知识类插件，不依赖外部工具连接。

### 场景

一个帮助开发者编写更好的 commit message 的插件，包含两个 skill：一个用于生成常规 commit message，一个用于生成紧急修复的 commit message。

### 目录结构

```
commit-helper/
├── plugin.json
└── skills/
    ├── commit-message/
    │   ├── SKILL.md
    │   └── references/
    │       └── conventional-commits.md
    └── hotfix-message/
        └── SKILL.md
```

### plugin.json

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "commit-helper",
  "version": "1.0.0",
  "description": "帮助开发者编写符合 Conventional Commits 规范的 commit message",
  "author": {
    "name": "Dev Tools Team",
    "email": "devtools@example.com"
  },
  "license": "MIT",
  "keywords": ["git", "commit", "conventional-commits", "code-quality"]
}
```

### skills/commit-message/SKILL.md

```markdown
---
name: commit-message
description: 根据代码变更生成符合 Conventional Commits 规范的 commit message。当用户需要写 commit message、描述代码变更、或要求生成提交信息时使用。
---

# Commit Message Generator

根据暂存区的代码变更生成符合 Conventional Commits 规范的 commit message。

## 工作流程

1. 运行 `git diff --cached` 获取暂存区变更
2. 分析变更类型（feat / fix / docs / style / refactor / test / chore）
3. 识别影响范围（scope）
4. 生成简短的 subject（不超过 50 字符）
5. 如有必要，添加 body 说明变更原因和细节
6. 如有破坏性变更，添加 BREAKING CHANGE 脚注

## 格式规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

## 类型说明

| 类型 | 说明 |
|------|------|
| feat | 新功能 |
| fix | 修复 bug |
| docs | 文档变更 |
| style | 代码格式（不影响功能） |
| refactor | 重构（既不修复 bug 也不添加功能） |
| test | 测试相关 |
| chore | 构建过程或辅助工具的变动 |

详细规范参见 `references/conventional-commits.md`。
```

### skills/hotfix-message/SKILL.md

```markdown
---
name: hotfix-message
description: 为紧急生产修复生成标准化的 hotfix commit message，包含问题编号、影响范围和回滚方案。当用户需要为线上问题、紧急修复、hotfix 分支编写 commit message 时使用。
---

# Hotfix Commit Message Generator

为紧急生产修复生成包含完整上下文的 commit message。

## 必需元素

1. **问题追踪编号**：从分支名或用户输入提取（如 `PROJ-1234`）
2. **影响范围**：明确哪些服务/模块受影响
3. **根本原因**：一句话说明问题原因
4. **修复方案**：说明做了什么变更
5. **回滚方案**：如何回滚此修复

## 输出格式

```
fix(hotfix): <简短描述> [PROJ-1234]

## 影响范围
<受影响的服务/模块>

## 根本原因
<问题原因>

## 修复方案
<做了什么>

## 回滚方案
<revert commit hash 或操作步骤>
```
```

---

## 示例二：仅 MCP 服务器的插件

适用于工具/数据连接类插件，不包含 procedural knowledge。

### 场景

一个连接到公司内部知识库的插件，通过 MCP 服务器提供文档搜索和检索能力。

### 目录结构

```
knowledge-base/
├── plugin.json
├── mcp.json
└── bin/
    └── kb-mcp-server       # 打包的 MCP 服务器可执行文件
```

### plugin.json

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "knowledge-base",
  "version": "2.1.0",
  "description": "连接公司内部知识库，提供文档搜索和内容检索能力",
  "author": {
    "name": "Knowledge Platform Team",
    "url": "https://wiki.example.com/team/kb"
  },
  "homepage": "https://wiki.example.com/kb/mcp",
  "repository": "https://git.example.com/knowledge/mcp-server",
  "license": "UNLICENSED",
  "keywords": ["knowledge-base", "search", "documentation", "internal-tools"]
}
```

### mcp.json

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "kb-local": {
      "type": "stdio",
      "command": "./bin/kb-mcp-server",
      "args": ["--config", "${PLUGIN_ROOT}/config/server.json"],
      "env": {
        "KB_DATA_DIR": "${PLUGIN_DATA}/index",
        "KB_LOG_LEVEL": "warn"
      },
      "cwd": "${PLUGIN_ROOT}"
    },
    "kb-remote": {
      "type": "streamable-http",
      "url": "https://kb-mcp.internal.example.com/mcp",
      "headers": {
        "X-Service": "agent-plugin",
        "X-Plugin-Version": "2.1.0"
      }
    }
  }
}
```

### 说明

- `kb-local`：使用插件内打包的可执行文件，通过 stdio 启动本地服务器
- `kb-remote`：连接到公司内部部署的远程 MCP 服务
- 两个服务器提供相同的工具，客户端可根据网络环境选择使用哪个
- `PLUGIN_DATA` 用于存储本地索引缓存，更新插件时保留
- `headers` 中只放非敏感的服务标识，不放 API key（密钥由客户端管理）

---

## 示例三：Skills + MCP 完整插件

适用于技能 + 配套工具的完整插件，也是最常见的插件形态。

### 场景

一个部署助手插件，包含：
- 一个 skill：指导如何安全地部署服务、检查健康状态、执行回滚
- 一个 MCP 服务器：连接到部署平台，提供部署状态查询和操作工具

### 目录结构

```
deployment-assistant/
├── plugin.json
├── skills/
│   └── deploy-service/
│       ├── SKILL.md
│       ├── scripts/
│       │   └── health-check.sh
│       └── references/
│           └── runbook.md
├── mcp.json
└── com.github.copilot/
    └── hooks/
        └── hooks.json
```

### plugin.json

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "deployment-assistant",
  "version": "1.2.0",
  "description": "安全部署服务的完整助手：包含部署流程指导和部署平台工具连接",
  "author": {
    "name": "SRE Team",
    "email": "sre@example.com",
    "url": "https://sre.example.com"
  },
  "homepage": "https://docs.example.com/deployment-assistant",
  "repository": "https://github.com/example/deployment-assistant",
  "license": "Apache-2.0",
  "keywords": ["deployment", "sre", "devops", "release", "rollback"],
  "extensions": {
    "com.github.copilot": {
      "category": "devops",
      "rating": "trusted"
    }
  }
}
```

### skills/deploy-service/SKILL.md

```markdown
---
name: deploy-service
description: 指导安全部署服务的完整流程，包括预检查、灰度发布、健康检查和回滚方案。当用户需要部署服务、发布新版本、检查部署状态、或执行回滚时使用。需要配合 deployment-api MCP 服务器使用。
---

# Deployment Service Assistant

指导用户安全地完成服务部署，使用 deployment-api MCP 服务器与部署平台交互。

## 部署前检查

1. 确认当前分支是 `main` 且工作区干净
2. 检查 CI 状态：调用 `get_pipeline_status` 工具
3. 确认没有正在进行的部署：调用 `list_active_deployments` 工具
4. 检查依赖服务健康状态：运行 `scripts/health-check.sh`

## 执行部署

1. 创建发布单：调用 `create_release` 工具，传入版本号和变更说明
2. 启动灰度部署（10% 流量）：调用 `start_canary_deployment` 工具
3. 等待 5 分钟，观察错误率和延迟指标
4. 如果指标正常，逐步扩大流量（50% → 100%）
5. 如果指标异常，立即执行回滚（见下文）

## 健康检查标准

| 指标 | 阈值 | 动作 |
|------|------|------|
| 错误率 | < 0.1% | 超过则回滚 |
| P99 延迟 | < 基线的 120% | 超过则暂停 |
| CPU 使用率 | < 80% | 超过则暂停 |

详细 runbook 参见 `references/runbook.md`。

## 回滚流程

1. 立即调用 `rollback_deployment` 工具，传入发布单 ID
2. 确认回滚完成：调用 `get_deployment_status` 工具
3. 运行健康检查脚本确认服务恢复
4. 创建事件记录：调用 `create_incident` 工具
5. 通知团队：在部署频道发送回滚通知
```

### mcp.json

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "deployment-api": {
      "type": "streamable-http",
      "url": "https://deploy-api.example.com/mcp",
      "headers": {
        "X-Plugin": "deployment-assistant",
        "X-Plugin-Version": "1.2.0"
      }
    }
  }
}
```

### com.github.copilot/hooks/hooks.json

```json
{
  "preToolUse": [
    {
      "tool": "start_canary_deployment",
      "prompt": "即将启动灰度部署，请确认已完成所有预检查。是否继续？"
    }
  ],
  "postToolUse": [
    {
      "tool": "rollback_deployment",
      "action": "notify_channel",
      "channel": "#deployments"
    }
  ]
}
```

### 说明

- Skill 提供部署的 procedural knowledge（什么时候做什么、判断标准、回滚流程）
- MCP 服务器提供实际的部署平台操作工具
- 两者配合：skill 指导流程，MCP 执行操作
- `com.github.copilot/` 目录包含 Copilot 专属的 hooks 配置，其他客户端会忽略
- `extensions` 字段包含 Copilot 专属的 manifest 元数据

---

## 带客户端扩展的插件

展示如何在一个插件中同时支持多个客户端的专属功能。

### 目录结构

```
multi-client-plugin/
├── plugin.json
├── skills/
│   └── my-skill/
│       └── SKILL.md
├── mcp.json
├── com.github.copilot/
│   └── hooks/
│       └── hooks.json
├── com.cursor/
│   └── rules/
│       └── custom-rules.md
└── com.openai.codex/
    └── commands/
        └── slash-commands.json
```

### plugin.json（含多客户端 extensions）

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "multi-client-plugin",
  "version": "1.0.0",
  "description": "演示多客户端扩展的插件示例",
  "extensions": {
    "com.github.copilot": {
      "displayName": "Multi Client Plugin",
      "icon": "rocket"
    },
    "com.cursor": {
      "priority": "high"
    },
    "com.openai.codex": {
      "marketplace": "verified"
    }
  }
}
```

### 说明

- 可移植部分（`plugin.json`、`skills/`、`mcp.json`）在所有兼容客户端中通用
- 每个客户端专属目录和 `extensions` 命名空间只被对应客户端识别
- 不认识的命名空间被安全忽略，不影响插件加载
- 这种设计让插件作者可以"一次编写，处处运行"，同时为各客户端提供增强体验
