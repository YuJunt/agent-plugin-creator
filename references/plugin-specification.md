# Agent Plugins 1.0.0 完整规范参考

本文档是 [Agent Plugins Specification 1.0.0](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md) 的详细参考，供创建插件时查阅。规范文本具有最终权威性，本文档如有冲突以官方为准。

## 目录

1. [插件包模型](#1-插件包模型)
2. [Manifest (plugin.json)](#2-manifest-pluginjson)
3. [组件发现](#3-组件发现)
4. [组件类型：Skills](#4-组件类型skills)
5. [组件类型：MCP 服务器](#5-组件类型mcp-服务器)
6. [客户端扩展](#6-客户端扩展)
7. [环境变量与占位符展开](#7-环境变量与占位符展开)
8. [版本化](#8-版本化)
9. [客户端一致性要求](#9-客户端一致性要求)
10. [合规检查清单](#10-合规检查清单)

---

## 1. 插件包模型

### 1.1 基本要求

1. 插件是根植于单个文件系统位置的目录。
2. 插件**必须**在根目录包含 `plugin.json` manifest。
3. 客户端访问插件包内的任何文件或目录时，文件系统解析后的路径**必须**保持在插件根目录内。符号链接等可以指向插件根目录内的目标，但**必须拒绝**解析到外部的包路径。
4. 规范定义为插件相对路径的配置字段**必须**以 `./` 开头，相对于插件根目录解析，且解析后仍在插件根目录内。
5. 未定义为路径的配置值（包括命令参数和环境变量值）是不透明字符串。客户端**不得**将它们解释为包路径来执行路径包含检查。

### 1.2 路径包含失败的处理

当路径不满足包含要求时，客户端**必须**应用最窄的适用失败边界：

1. `plugin.json` 不解析在插件根目录内 → **拒绝整个插件**
2. 固定组件位置不解析在插件根目录内 → 该组件类型视为无效
3. 发现的 `SKILL.md` 不解析在插件根目录内 → 跳过该 skill
4. MCP 服务器 `command` 或 `cwd` 不满足包含 → 该服务器条目无效
5. 任何其他解析到插件根目录外的包路径 → 拒绝访问该路径

### 1.3 标准布局

```
my-plugin/
├── plugin.json
├── skills/
│   └── summarize/
│       ├── SKILL.md
│       ├── scripts/
│       │   └── analyze.sh
│       └── references/
│           └── checklist.md
├── mcp.json
├── com.example.client/
│   └── hooks/
├── LICENSE
└── CHANGELOG.md
```

---

## 2. Manifest (plugin.json)

### 2.1 位置与加载

- 客户端**必须**检查插件根目录的 `plugin.json`。
- 每个插件只有一个可移植 manifest，没有其他文件可以替代、补充或覆盖根 `plugin.json` 的核心字段。
- 客户端在发现组件或应用客户端特定行为之前，先加载并验证根 `plugin.json`。

### 2.2 Manifest 对象

manifest **必须**是 JSON，且**必须**包含顶层对象。其 schema 是**封闭的**：唯一允许的顶层字段是：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `$schema` | string | 是 | 规范版本标识 |
| `name` | string | 是 | 插件名 |
| `version` | string | 否 | 版本号（推荐语义化版本） |
| `description` | string | 否 | 简短描述 |
| `author` | object | 否 | 作者信息 |
| `homepage` | string | 否 | 文档/主页 URL |
| `repository` | string | 否 | 源码仓库 URL |
| `license` | string | 否 | 许可证标识符（推荐 SPDX） |
| `keywords` | string[] | 否 | 搜索标签 |
| `extensions` | object | 否 | 客户端专属数据 |

如果 `plugin.json` 包含任何其他顶层字段，则不符合 schema。客户端**必须**报告并忽略每个未知字段，但如果 manifest 否则满足要求，则继续加载插件。客户端**不得**为未知字段赋予语义。客户端特定的 manifest 数据属于 `extensions`。

除未知顶层字段或非对象 `extensions` 字段外的任何 schema 违规都是**致命的**：客户端**必须**拒绝插件，且**不得**发现或执行其任何组件。

### 2.3 $schema 字段

`$schema` 的值**必须**为规范标识符：
```
https://agent-plugins.org/schemas/1.0.0/plugin.schema.json
```

客户端**必须**使用可识别的 `$schema` 值来选择本地支持的 manifest 验证和解释规则。客户端**不得**在加载插件时检索 schema。如果客户端不支持声明的 Agent Plugins 版本或明确识别的兼容版本，**必须**拒绝插件并**应该**报告不支持的版本。

### 2.4 name 字段约束

- 类型：string
- 最小长度：1
- 最大长度：64
- 正则：`^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$`
- 即：小写字母、数字、连字符、点；以字母或数字开头和结尾；禁止连续连字符 `--` 或连续点 `..`

### 2.5 author 对象

`author` 对象**可以**只包含 `name`、`email`、`url` 字段，每个字段值为字符串。任何其他字段或值类型都会使 manifest 无效。

### 2.6 元数据字段验证

除规范明确声明的约束外，元数据字段仅按 JSON 类型验证。客户端**不得**仅因为以下原因拒绝 manifest：
- `version` 不是有效的语义化版本
- `homepage`、`repository` 或 `author.url` 不是可识别的 URL
- `author.email` 不是可识别的邮箱地址
- `license` 不是 SPDX 标识符

### 2.7 最小 manifest 示例

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "minimal-plugin"
}
```

### 2.8 完整 manifest 示例

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "plugin-name",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": {
    "name": "Author Name",
    "email": "author@example.com",
    "url": "https://example.com"
  },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/example/plugin",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "extensions": {
    "com.example.client": {
      "setting": true
    }
  }
}
```

---

## 3. 组件发现

### 3.1 固定位置

客户端**必须**从固定位置发现每种支持的组件类型。`plugin.json` **不能**覆盖这些位置或包含内联组件配置。

| 组件类型 | 固定位置 | 模式 |
|----------|----------|------|
| Skills | `skills/` | 包含 `SKILL.md` 的子目录 |
| MCP servers | `mcp.json` | JSON 配置 |

### 3.2 缺失位置

- 如果固定组件位置不存在，客户端**不得**将其视为错误。
- 如果固定组件位置存在但不解析为预期的文件系统类型（例如 `skills` 不是目录，或 `mcp.json` 不是常规文件），客户端**必须**将该组件类型视为无效，并继续加载其他支持的组件类型。

---

## 4. 组件类型：Skills

### 4.1 规范遵循

Agent Skills **必须**符合 [Agent Skills 规范](https://agentskills.io/specification)。该规范是 `SKILL.md` 格式、frontmatter 字段和目录布局（`scripts/`、`references/`、`assets/`）的权威来源。

Agent Plugins 规范定义的是 Agent Skills 在插件内的**发现方式**，而不是 skill 格式本身或客户端如何向用户或模型展示 skills。

### 4.2 发现规则

- 固定发现位置是 `skills/`。
- 每个包含名为 `SKILL.md` 的常规文件的**直接子目录**被视为一个 skill。
- 客户端**不得**递归搜索更深层的后代以查找额外 skills。
- 如果发现的 skill 不符合 Agent Skills 规范，客户端**必须**跳过该 skill 并继续加载其他 skills 和组件类型。客户端**应该**报告无效的 skill。

### 4.3 Skill 目录示例

```
skills/
└── deploy/
    ├── SKILL.md          # name: deploy
    ├── scripts/
    │   └── rollback.sh
    └── references/
        └── runbook.md
```

---

## 5. 组件类型：MCP 服务器

[Model Context Protocol 规范](https://modelcontextprotocol.io/specification) 定义了 MCP 线路行为和生命周期语义。Agent Plugins 定义了用于在插件中定位和连接 MCP 服务器的 `mcp.json` 配置格式。

### 5.1 发现与配置

- MCP 配置路径是插件根目录的 `mcp.json`。
- MCP 配置**不得**在 `plugin.json` 中内联声明，也**不得**从任何替代核心路径加载。
- `mcp.json` **必须**是 JSON 对象，包含必需的 `$schema` 和 `mcpServers` 字段，没有其他顶层字段。
- `mcpServers` **必须**是对象，其成员名标识服务器，成员值是服务器配置对象。空的 `mcpServers` 对象是有效的。

`mcp.json` 的 `$schema` 值**必须**为：
```
https://agent-plugins.org/schemas/1.0.0/mcp.schema.json
```

### 5.2 服务器配置通用规则

每个服务器配置**必须**包含 `type` 字段，且**必须**精确匹配以下封闭变体之一。未知字段、未知 `type` 值或属于另一个变体的字段都会使该服务器条目无效。

### 5.3 stdio 传输

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `type` | `"stdio"` | 是 | 选择 MCP stdio 传输 |
| `command` | string | 是 | 要启动的可执行 token |
| `args` | string[] | 否 | 传递给可执行文件的参数 |
| `env` | object of strings | 否 | 提供给进程的环境变量 |
| `cwd` | string | 否 | 进程的工作目录 |

#### command 规则

- `command` **必须**包含单个可执行 token，不是 shell 命令字符串。
- 它**必须**是裸可执行文件名或以 `./` 开头的插件相对路径。
- 客户端**必须**使用平台的可执行文件搜索规则解析裸名称，并相对于插件根目录解析插件相对路径。
- 客户端**不得**在 `command` 中执行占位符展开。
- 打包在插件中的可执行文件**必须**使用插件相对 `command`（如 `./bin/server`）。

#### cwd 规则

- 省略 `cwd` 时，客户端**必须**使用插件根目录作为子进程工作目录。
- 存在时，`cwd` **必须**具有以下形式之一：
  1. 以 `./` 开头的插件相对路径
  2. 精确为 `${PLUGIN_ROOT}` 或以 `${PLUGIN_ROOT}/` 开头的路径
  3. 精确为 `${PLUGIN_DATA}` 或以 `${PLUGIN_DATA}/` 开头的路径
- 客户端**必须**在解析 `cwd` 之前展开占位符。
- 插件相对或以 `${PLUGIN_ROOT}` 为根的值**必须**保持在文件系统解析的插件根目录内。
- 以 `${PLUGIN_DATA}` 为根的值**必须**保持在文件系统解析的插件数据目录内。

#### env 规则

- `args`、`env` 和 `cwd` 字段**必须**支持 `${PLUGIN_ROOT}` 和 `${PLUGIN_DATA}` 展开。
- MCP 服务器的 `env` 对象**不得**包含名为 `PLUGIN_ROOT` 或 `PLUGIN_DATA` 的条目。这样的条目会使该服务器配置无效。

### 5.4 streamable-http 和 sse 传输

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `type` | `"streamable-http"` 或 `"sse"` | 是 | 选择远程 MCP 传输 |
| `url` | string | 是 | MCP 端点 URL |
| `headers` | object of strings | 否 | 连接时发送的固定 HTTP 头 |

- `streamable-http` 选择当前的 MCP Streamable HTTP 传输。
- `sse` 选择已弃用的 HTTP+SSE 传输（由 MCP 2024-11-05 规范定义）。它不指 Streamable HTTP 中使用的 SSE 响应或流。

#### url 规则

- `url` 值**必须**是绝对 HTTP 或 HTTPS URL，且**不得**包含用户信息或 fragment。
- 非回环端点**必须**使用 HTTPS。
- 当 URL 主机精确为 `localhost` 或回环范围内的 IP 字面量时，可以使用 HTTP。

#### headers 规则

- 头名称和值**必须**是有效的 HTTP 头字段。
- 头名称不区分大小写；在不同大小写下包含相同头名称多次的条目是无效的。
- 客户端**不得**在 `url`、头名称或头值中执行占位符或环境变量展开。
- 头值是可见的包数据，不是可移植的密钥机制。插件**不得**在 `headers` 中嵌入凭据或其他密钥。
- 客户端生成的用于实现 HTTP、MCP 或授权的头优先于配置的同名（不区分大小写）头。
- 客户端**不得**在没有明确用户授权的情况下，通过重定向或旧版 SSE 端点事件将配置的头转发到不同源。

### 5.5 传输支持

- 支持 Agent Plugins MCP 服务器的客户端**必须**至少支持 `stdio` 或 `streamable-http` 之一，且**应该**同时支持两者。
- 对 `sse` 的支持是**可选的**。
- 客户端**必须**使用 `type` 声明的传输进行初始连接尝试。Agent Plugins 不定义该尝试失败时的回退行为。

### 5.6 mcp.json 完整示例

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "local-validator": {
      "type": "stdio",
      "command": "./bin/validator",
      "args": ["--data", "${PLUGIN_DATA}/validator"],
      "env": {
        "CONFIG": "${PLUGIN_ROOT}/config.json"
      },
      "cwd": "${PLUGIN_ROOT}"
    },
    "deployment-api": {
      "type": "streamable-http",
      "url": "https://deploy.example.com/mcp",
      "headers": {
        "X-Tenant": "public-tenant"
      }
    },
    "legacy-events": {
      "type": "sse",
      "url": "https://legacy.example.com/sse"
    }
  }
}
```

### 5.7 加载规则

1. 支持 MCP 服务器的客户端**必须**仅从插件根目录的 `mcp.json` 加载配置。
2. 如果 `mcp.json` 不是有效 JSON、目标是客户端不支持的 Agent Plugins 版本、目标版本与 `plugin.json` 不同、或不满足其他顶层要求，客户端**必须**禁用该插件的 MCP 并继续加载其他组件类型。
3. 如果单个服务器条目不满足要求，客户端**必须**跳过该服务器并继续加载其他服务器和组件类型。
4. 如果客户端不支持其他有效服务器条目中声明的传输，**必须**跳过该服务器并继续加载其他服务器和组件类型。
5. 如果服务器启动、连接、认证或完成 MCP 握手失败，客户端**必须**继续加载其他服务器和组件类型。

---

## 6. 客户端扩展

### 6.1 Manifest 扩展数据

`extensions` 字段包含以反向域名扩展命名空间为键的客户端特定 manifest 数据。Agent Plugins 不为命名空间对象内容赋予任何语义。

- `extensions` 的值**必须**是对象。非对象值由客户端报告并忽略，但不使插件无效。
- 客户端**必须**忽略未实现的 `extensions` 成员，且不验证其值的内容。

### 6.2 扩展目录

- 扩展目录是顶层目录，其名称精确为扩展命名空间，其内容由该命名空间的拥有客户端定义。
- 客户端从其顶层命名空间目录发现已实现的基于文件的扩展。
- 其他客户端忽略不认识的命名空间目录。

### 6.3 常见命名空间

| 命名空间 | 所属客户端 |
|----------|-----------|
| `com.github.copilot` | GitHub Copilot / VS Code |
| `com.cursor` | Cursor |
| `com.openai.codex` | OpenAI Codex |
| `com.vercel` | Vercel |
| `com.amazon` | AWS |

---

## 7. 环境变量与占位符展开

### 7.1 子进程环境

启动插件子进程（即 stdio MCP 服务器）的客户端**必须**在每个子进程环境中提供 `PLUGIN_ROOT` 和 `PLUGIN_DATA`。

| 变量 | 说明 |
|------|------|
| `PLUGIN_ROOT` | 文件系统解析的插件根目录的绝对路径 |
| `PLUGIN_DATA` | 客户端管理的、专用于该已安装插件实例的持久数据目录的绝对路径 |

- 客户端选择 `PLUGIN_DATA` 的位置。它**必须**在启动插件子进程之前创建该目录，**必须**使其对子进程可写，且**必须**在插件更新期间保留其内容。
- 客户端可以在卸载插件时删除该目录。
- `PLUGIN_DATA` 用于：已安装的依赖（node_modules、虚拟环境）、生成的代码、缓存和其他应在更新间持久化的插件状态。
- `PLUGIN_ROOT` 用于：引用随插件提供的捆绑脚本、二进制文件和配置文件。

### 7.2 占位符展开

启动插件子进程的客户端**必须**在支持的配置字段中展开 `${PLUGIN_ROOT}` 和 `${PLUGIN_DATA}`。

- 展开是对任一占位符每个精确出现位置的**单次、非递归**文本替换。替换引入的文本**不得**被扫描以查找更多占位符。
- 展开适用于：`args` 的每个字符串元素、`env` 的每个字符串值、`cwd` 字符串。
- 不适用于：`env` 键、`command`、固定组件位置。
- 未识别的类占位符文本**必须**保持字面量。客户端**不得**执行任何其他占位符或环境变量展开。

### 7.3 安全注意事项

- 配置的 `env` 值是可见的包数据，不是可移植的密钥机制。插件**不得**在 `env` 中嵌入凭据或其他密钥。
- Agent Plugins v1 不定义 OAuth 配置或可移植的凭据引用字段。授权发现、用户交互和凭据存储由客户端管理。

---

## 8. 版本化

### 8.1 规范和 schema 版本

- 第 1 节中的版本标识完整的 Agent Plugins 规范版本，包括其规范文本、plugin manifest schema 和 MCP 配置 schema。
- 每个规范版本**必须**发布与规范版本相同的两个 schema，即使 schema 的验证规则与上一版本相比没有变化。
- 插件的 `plugin.json` `$schema` 值声明包目标的 Agent Plugins 版本。
- 当存在 `mcp.json` 时，其 `$schema` 值中的版本**必须**与 `plugin.json` 声明的版本匹配。不匹配会使 MCP 配置无效，但不会使其他组件类型无效。
- 已发布的规范 schema 标识符**不得**重新分配给不同的 schema 内容。
- 现有插件可以继续目标为旧版 Agent Plugins 版本；客户端使用声明的规范标识符和任何明确的兼容性映射来确定支持。

### 8.2 插件版本

插件**应该**对 `version` 使用语义化版本。

| 段 | 含义 | 说明 |
|----|------|------|
| Major | 破坏性变更 | 不兼容的行为或 schema 变更 |
| Minor | 向后兼容的功能 | 不破坏现有客户端或用户的新行为 |
| Patch | 向后兼容的修复 | 无意造成行为破坏的纠正性变更 |

客户端可以使用 `version` 来确定是否有可用更新以及缓存是否过时。

---

## 9. 客户端一致性要求

### 9.1 最低客户端要求

符合规范的客户端**必须**满足第 1-10 节中所有适用的要求。至少它：

1. 可以从目录路径加载插件。
2. 从 `$schema` 选择本地支持的 plugin manifest schema，然后使用第 5.2 节和第 8.1 节中的非致命异常解析并验证封闭的 `plugin.json` schema。
3. 忽略 `extensions` 中未实现的成员，且不验证其值的内容。
4. 对于它支持的每种组件类型，在其固定位置发现组件。
5. 如果支持 MCP 服务器，从 `$schema` 选择本地支持的 MCP 配置 schema，并在 `mcp.json` 中至少支持 `stdio` 或 `streamable-http` 变体之一。
6. 如果客户端启动插件子进程（即 stdio MCP 服务器），提供 `PLUGIN_ROOT` 和 `PLUGIN_DATA`，并在运行时配置值（`args`、`env`、`cwd`）中展开这两个变量。
7. 对于 stdio MCP 服务器，将 `command` 解析为单个可执行 token，并使用插件根目录作为默认子进程工作目录。
8. 至少支持一种组件类型（skills 或 MCP 服务器）。

### 9.2 增量采用

客户端不需要支持每种组件类型。例如，仅支持 skills 的客户端可以在不支持 MCP 服务器的情况下符合规范，只要它满足所有适用要求。

### 9.3 不支持的组件和失败

- 客户端**必须**忽略它们不支持的组件类型。
- 独立组件失败时，客户端**必须**继续加载其他组件。

---

## 10. 合规检查清单

### 插件作者检查清单

- [ ] 插件根目录包含 `plugin.json`
- [ ] `plugin.json` 是有效 JSON 且为顶层对象
- [ ] `$schema` 精确为 `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`
- [ ] `name` 存在，符合命名规则，且与目录名一致
- [ ] `plugin.json` 不含未知顶层字段（自定义数据用 `extensions`）
- [ ] `author` 对象只含 `name`、`email`、`url`
- [ ] Skills 在 `skills/` 的直接子目录中，每个含 `SKILL.md`
- [ ] 没有嵌套过深的 skills（不递归）
- [ ] `mcp.json`（如存在）含 `$schema` 和 `mcpServers`
- [ ] `mcp.json` 的 `$schema` 版本与 `plugin.json` 一致
- [ ] 每个 MCP 服务器有 `type` 且匹配对应变体的字段
- [ ] stdio `command` 是单个 token，不是 shell 字符串
- [ ] 插件内可执行文件用 `./` 相对路径
- [ ] `cwd` 是允许的三种形式之一
- [ ] `env` 不含 `PLUGIN_ROOT` 或 `PLUGIN_DATA`
- [ ] `headers` 不含凭据/密钥
- [ ] 远程 URL 非 localhost 时用 HTTPS
- [ ] 所有插件内相对路径以 `./` 开头且不逃逸出插件根目录
- [ ] 客户端扩展使用反向域名命名空间
