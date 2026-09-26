# MCP 服务器创建指南（基于官方 SDK）

本文档基于 MCP 官方 SDK，指导如何创建可打包进 Agent Plugin 的 MCP 服务器。

## 目录

1. [MCP 概述](#mcp-概述)
2. [技术栈选择](#技术栈选择)
3. [传输类型选择](#传输类型选择)
4. [TypeScript 官方 SDK](#typescript-官方-sdk)
5. [Python FastMCP](#python-fastmcp)
6. [工具定义规范](#工具定义规范)
7. [打包进 Agent Plugin](#打包进-agent-plugin)
8. [验证与测试](#验证与测试)
9. [常见问题](#常见问题)

---

## MCP 概述

Model Context Protocol (MCP) 是 AI 应用连接外部工具、数据源和工作流的开放标准协议。MCP 服务器暴露三类能力：

| 能力 | 说明 | 示例 |
|------|------|------|
| **Tools** | AI 模型可调用的函数 | search_database, create_issue, run_tests |
| **Resources** | AI 模型可读取的数据源 | 文件内容、API 响应、数据库记录 |
| **Prompts** | 可复用的提示模板 | 结构化查询模板 |

在 Agent Plugin 中，最常用的是 **Tools**。

## 技术栈选择

| 语言 | 官方 SDK | 包名 | 适用场景 |
|------|---------|------|---------|
| **TypeScript** | 官方主 SDK | `@modelcontextprotocol/sdk` | 生态最成熟，示例最多，推荐默认 |
| **Python** | 官方维护 | `fastmcp`（独立包，3.x） | 数据处理、AI/ML 场景、Python 生态 |
| Kotlin | 官方 | `modelcontextprotocol-kotlin` | JVM 生态 |
| C# | 社区 | 第三方模板 | .NET 生态 |

**默认选择 TypeScript**：官方 SDK 最成熟，文档最完善，stdio 和 streamable-http 都有一等支持。

## 传输类型选择

| 传输类型 | 说明 | 适用场景 | Agent Plugin 配置 |
|---------|------|---------|------------------|
| **stdio** | 通过标准输入/输出通信的本地子进程 | 打包随插件分发的本地工具 | `type: "stdio"`, `command` 指向启动命令 |
| **streamable-http** | 通过 HTTP 端点通信的远程服务 | 已部署的远程服务、需要集中管理的工具 | `type: "streamable-http"`, `url` 指向端点 |
| **sse** | 已弃用的 HTTP+SSE 传输 | 仅兼容旧版 MCP 服务器 | `type: "sse"`（不推荐新开发） |

**默认选择 stdio**：最易打包分发，插件自包含，不依赖外部服务部署。

## TypeScript 官方 SDK

### 安装

```bash
npm install @modelcontextprotocol/sdk zod
```

### 最小服务器示例（stdio）

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// 创建服务器
const server = new McpServer({
  name: "my-server",
  version: "1.0.0",
});

// 注册工具
server.tool(
  "add",
  "Add two numbers together",
  {
    a: z.number().describe("First number"),
    b: z.number().describe("Second number"),
  },
  async ({ a, b }) => {
    return {
      content: [{ type: "text", text: String(a + b) }],
    };
  }
);

// 启动 stdio 传输
const transport = new StdioServerTransport();
await server.connect(transport);
console.error("MCP server running on stdio");
```

### 工具定义详解

```typescript
server.tool(
  "tool_name",           // 工具名：小写+下划线，唯一标识
  "工具描述",             // 描述：AI 模型据此决定何时调用
  {
    // 参数 schema：使用 Zod 定义
    param1: z.string().describe("参数描述"),
    param2: z.number().optional().describe("可选参数"),
    param3: z.enum(["option1", "option2"]).describe("枚举参数"),
  },
  async ({ param1, param2, param3 }) => {
    // 业务逻辑
    return {
      content: [
        { type: "text", text: "结果文本" }
      ],
      // 可选：结构化结果
      // structuredContent: { ... }
    };
  }
);
```

### 工具返回格式

```typescript
// 成功返回
return {
  content: [{ type: "text", text: "操作成功，结果是..." }],
};

// 错误返回（isError 标记）
return {
  content: [{ type: "text", text: "错误：无法连接到数据库" }],
  isError: true,
};

// 多段内容
return {
  content: [
    { type: "text", text: "找到以下结果：" },
    { type: "text", text: JSON.stringify(results, null, 2) },
  ],
};
```

### Streamable HTTP 服务器

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const server = new McpServer({ name: "my-server", version: "1.0.0" });

// 注册工具（同 stdio）
server.tool("hello", { name: z.string() }, async ({ name }) => ({
  content: [{ type: "text", text: `Hello, ${name}!` }],
}));

// HTTP 传输需要会话管理
const sessions = new Map();

app.post("/mcp", async (req, res) => {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: () => crypto.randomUUID(),
    onsessioncreated: (session) => sessions.set(session.id, transport),
  });
  await server.connect(transport);
  await transport.handleRequest(req, res);
});
```

### package.json 配置

```json
{
  "name": "my-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/server.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "zod": "^4.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0"
  }
}
```

## Python FastMCP

### 安装

```bash
pip install fastmcp
```

### 最小服务器示例（stdio）

```python
from fastmcp import FastMCP

# 创建服务器
mcp = FastMCP("my-server")

# 注册工具（使用装饰器）
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    return a + b

# 启动 stdio 传输
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 工具定义详解

```python
from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("my-server")

# 方式1：函数装饰器（类型注解自动生成 schema）
@mcp.tool()
def search_documents(query: str, limit: int = 10) -> list[dict]:
    """Search the knowledge base.

    Args:
        query: Search query text
        limit: Maximum number of results
    """
    # 业务逻辑
    return [{"title": "Result 1", "score": 0.95}]

# 方式2：Pydantic 模型作为参数
class DeployParams(BaseModel):
    service: str = Field(description="Service name to deploy")
    environment: str = Field(description="Target environment")
    dry_run: bool = Field(default=False, description="Preview without executing")

@mcp.tool()
def deploy_service(params: DeployParams) -> str:
    """Deploy a service to the specified environment."""
    if params.dry_run:
        return f"Would deploy {params.service} to {params.environment}"
    return f"Deployed {params.service} to {params.environment}"

# 启动
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Streamable HTTP 服务器

```python
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

### pyproject.toml 配置

```toml
[project]
name = "my-mcp-server"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "fastmcp>=3.0.0",
    "pydantic>=2.0.0",
]

[project.scripts]
my-mcp-server = "server:main"
```

## 工具定义规范

无论使用哪种语言，工具定义都应遵循以下规范：

### 工具命名

- 使用小写字母和下划线（snake_case）
- 动词开头，描述操作：`search_*`, `create_*`, `get_*`, `update_*`, `delete_*`
- 简洁但有描述性：`search_knowledge_base` 优于 `search` 或 `skb`

### 工具描述

- 一句话说明工具做什么
- 包含何时使用的上下文
- 不要超过 2-3 句

**好的描述**：
```
Search the internal knowledge base for documents matching the query. Use when the user asks about company policies, technical documentation, or past project reports.
```

**差的描述**：
```
Search stuff.
```

### 参数定义

- 每个参数都要有描述（AI 模型据此理解参数含义）
- 必需参数和可选参数明确区分
- 使用枚举限制可选值时，在描述中列出选项
- 参数名使用 snake_case

### 返回值

- 成功时返回有意义的结果文本
- 失败时设置 `isError: true` 并返回清晰的错误信息
- 大结果考虑分页或摘要，不要一次性返回过多内容
- 结构化数据用 JSON 格式返回，方便 AI 解析

## 打包进 Agent Plugin

### stdio 服务器的目录布局

```
my-plugin/
├── plugin.json
├── mcp.json
├── skills/
└── servers/
    └── my-server/              # MCP 服务器代码
        ├── package.json         # TypeScript
        ├── tsconfig.json
        ├── src/
        │   └── server.ts
        └── node_modules/        # 安装依赖后（或在安装时生成）
```

### mcp.json 配置（stdio + TypeScript）

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "my-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "tsx", "${PLUGIN_ROOT}/servers/my-server/src/server.ts"],
      "cwd": "${PLUGIN_ROOT}/servers/my-server",
      "env": {
        "NODE_ENV": "production",
        "LOG_LEVEL": "warn"
      }
    }
  }
}
```

### mcp.json 配置（stdio + Python）

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "my-server": {
      "type": "stdio",
      "command": "python3",
      "args": ["${PLUGIN_ROOT}/servers/my-server/server.py"],
      "cwd": "${PLUGIN_ROOT}/servers/my-server",
      "env": {
        "PYTHONPATH": "${PLUGIN_ROOT}/servers/my-server",
        "DATA_DIR": "${PLUGIN_DATA}/my-server"
      }
    }
  }
}
```

### mcp.json 配置（streamable-http）

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "my-server": {
      "type": "streamable-http",
      "url": "https://my-server.example.com/mcp",
      "headers": {
        "X-Service": "agent-plugin",
        "X-Plugin-Version": "1.0.0"
      }
    }
  }
}
```

### 关键打包注意事项

1. **`command` 必须是单个可执行 token**：不能是 `"npx tsx server.ts"`，要用 `command: "npx"` + `args: ["-y", "tsx", "..."]`
2. **插件内文件用 `${PLUGIN_ROOT}` 引用**：不要用绝对路径或相对路径
3. **运行时数据用 `${PLUGIN_DATA}`**：缓存、数据库、生成的文件放在这里，插件更新时保留
4. **env 中不要放密钥**：API key 等由客户端的授权机制管理
5. **headers 中不要放凭据**：同上
6. **依赖要在插件安装时可获取**：TypeScript 用 `npx` 自动安装，Python 需确保依赖已安装或在启动脚本中安装

## 验证与测试

### 1. 语法和类型检查

```bash
# TypeScript
npx tsc --noEmit

# Python
python -m py_compile server.py
```

### 2. 启动测试

```bash
# stdio 服务器启动测试（应无报错，保持运行）
node dist/server.js
# 或
python server.py
```

### 3. MCP 握手测试

使用 MCP Inspector 或手动测试：

```bash
# 安装 MCP Inspector
npx @modelcontextprotocol/inspector

# 连接到服务器
# 在 Inspector 中配置 stdio 命令或 HTTP URL
```

### 4. 工具列表测试

服务器启动后，发送 `tools/list` 请求，确认所有工具都正确注册，参数 schema 完整。

### 5. 工具调用测试

对每个工具发送测试调用，验证：
- 参数验证正确（无效参数返回错误）
- 正常输入返回预期结果
- 错误情况返回 `isError: true` 和清晰的错误信息

## 常见问题

### Q: stdio 服务器启动后没有响应？

A: 检查：
1. 服务器是否真的在 stdin/stdout 上通信（而不是打印到 stdout）
2. 日志输出要写到 stderr（`console.error`），不要写到 stdout
3. 确认传输类型正确连接（`server.connect(transport)`）

### Q: 工具没有出现在 tools/list 中？

A: 检查：
1. 工具注册代码在服务器连接之前执行
2. 工具名没有重复
3. TypeScript：确认 `server.tool()` 调用没有被条件分支跳过
4. Python：确认装饰器 `@mcp.tool()` 正确应用

### Q: 参数 schema 不正确？

A: 检查：
1. TypeScript：每个参数都有 `.describe()`，可选参数用 `.optional()`
2. Python：类型注解正确，docstring 中 Args 部分格式正确
3. 枚举类型使用 `z.enum()` 或 `Literal` 类型

### Q: 插件安装后服务器找不到依赖？

A: 检查：
1. TypeScript：`package.json` 的 dependencies 包含所有需要的包
2. 使用 `npx -y` 自动安装依赖，或在插件安装脚本中运行 `npm install`
3. Python：`requirements.txt` 或 `pyproject.toml` 声明所有依赖
4. 考虑将依赖打包进插件（`node_modules/` 或虚拟环境），但注意体积

### Q: 如何处理需要 API key 的工具？

A: 
1. 不要在 `mcp.json` 的 env 或 headers 中硬编码 key
2. 在 env 中声明变量名（如 `"API_KEY": ""`），由客户端在安装时提示用户输入
3. 或者使用客户端的 OAuth/授权机制
4. 在工具描述中说明需要什么权限

### Q: streamable-http 和 stdio 怎么选？

A:
- **stdio**：工具逻辑随插件分发，不需要外部服务，适合本地工具、文件操作、简单 API 封装
- **streamable-http**：工具逻辑在远程服务，适合需要集中管理、有状态、重计算的工具
- 默认选 stdio，除非有明确的远程部署需求
# MCP 创建与审计指南

本文件只处理 MCP server 的设计与接入决策；MCP wire protocol 与授权规范以 <https://modelcontextprotocol.io/specification> 及官方开发文档为准，Agent Plugins 规范只负责连接配置的可移植封装。

## Skill 与 MCP 的选择

| 需求特征 | 首选 | 原因 |
| --- | --- | --- |
| 方法论、检查表、写作规范、决策规则 | Agent Skill | 主要是按需加载的指令，不需要运行时外部连接。 |
| 调用 API、数据库、搜索、文件系统或企业系统 | MCP server | 需要真实工具、资源、状态或权限边界。 |
| 既要指导流程又要调用工具 | Skill + MCP | Skill 负责任务编排、输入确认和安全策略，MCP 负责窄而可审计的运行时能力。 |
| 仅想把现有远程 MCP 接入插件 | 只写 `mcp.json` | 不要为了接入而重新实现 server；确认 URL、transport、认证由客户端支持。 |

## 设计顺序

1. 先定义用户任务、外部系统、只读/写入动作、数据敏感度、身份模型和失败恢复。
2. 按最小权限拆分工具；每个工具有明确名称、输入 schema、输出结构、错误语义和幂等性说明。
3. 选择 transport。优先使用 `stdio`（随包提供本地 server）或 `streamable-http`（远程服务）；仅因旧客户端要求时使用 `sse`。
4. 将 portable connection 写入根目录 `mcp.json`，不要把 server 配置内联到 `plugin.json`。
5. 明确认证归属。Agent Plugins 1.0.0 不定义可移植 OAuth 或 credential-reference 字段；不要将 token、API key、密码写入包、URL 或 headers。
6. 对写操作增加用户确认、最小 scope、审计日志、超时、重试边界、幂等键和回滚/补偿方案。
7. 使用真实目标客户端进行连接冒烟测试，并记录客户端不支持的 transport、认证方式或能力。

## mcp.json 模板

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "local-server": {
      "type": "stdio",
      "command": "./bin/server",
      "args": ["--data", "${PLUGIN_DATA}/local-server"],
      "env": {
        "CONFIG": "${PLUGIN_ROOT}/config.json"
      },
      "cwd": "${PLUGIN_ROOT}"
    },
    "remote-server": {
      "type": "streamable-http",
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "X-Tenant": "public"
      }
    }
  }
}
```

## 安全红线

不得把 shell 管道、重定向或多段命令放进 `command`；需要复杂启动逻辑时提供包内启动器并让 `command` 指向一个可执行文件。不得使用 `../` 逃出插件根；不得把 `${PLUGIN_ROOT}` 或 `${PLUGIN_DATA}` 放在规范未定义展开的字段中。远程非 loopback URL 必须 HTTPS 且不能含 userinfo 或 fragment，headers 是可见包数据。

MCP proxy 必须防止 confused deputy；OAuth 实现需做 per-client consent、精确 redirect URI 校验、CSRF/state 校验和 token audience 校验。禁止 token passthrough，即不能未经验证地接受发给其他资源的 token 并转发给下游 API。

## 验证输出

报告至少包含 server 名称与 transport、启动命令是否为单 token、所有路径的 containment 结果、远程 URL/headers 检查、认证责任归属、工具读写风险、目标客户端测试结果，以及每项失败时的隔离边界。

---

# TypeScript MCP 测试指南
# TypeScript MCP 服务器真实握手测试指南

> 本文档说明如何对 `create_mcp_server.py` 生成的 TypeScript MCP 服务器进行真实握手测试和工具调用验证。

## 为什么需要单独说明

Python MCP 服务器（fastmcp）可以直接用 `python3 server.py` 启动，但 TypeScript MCP 服务器需要：
1. 安装 npm 依赖（`@modelcontextprotocol/sdk`、`zod`、`typescript`、`tsx`）
2. 编译 TypeScript（或用 `tsx` 直接运行）
3. 正确设置启动命令

## 环境准备

### 1. 安装 Node.js（>= 18）

```bash
# 检查版本
node --version  # 需要 >= 18.0.0
npm --version

# Ubuntu/Debian 安装
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install node
```

### 2. 安装 TypeScript 和 tsx（全局或本地）

```bash
# 全局安装（推荐）
npm install -g typescript tsx

# 验证
tsc --version
tsx --version
```

## 测试步骤

### 步骤 1：生成 TypeScript MCP 服务器

```bash
# 创建工具定义文件
cat > tools.json << 'EOF'
{
  "tools": [
    {
      "name": "add",
      "description": "两数相加",
      "parameters": {
        "type": "object",
        "properties": {
          "a": {"type": "integer"},
          "b": {"type": "integer"}
        },
        "required": ["a", "b"]
      }
    },
    {
      "name": "greet",
      "description": "问候用户",
      "parameters": {
        "type": "object",
        "properties": {
          "name": {"type": "string"}
        },
        "required": ["name"]
      }
    }
  ]
}
EOF

# 生成 TypeScript MCP 服务器
python3 scripts/create_mcp_server.py generate \
  --language typescript \
  --transport stdio \
  --name my-ts-server \
  --definition tools.json \
  --output ./my-ts-server
```

### 步骤 2：安装依赖

```bash
cd my-ts-server
npm install
```

这会安装 `package.json` 中声明的依赖，包括：
- `@modelcontextprotocol/sdk` — MCP 官方 SDK
- `zod` — 参数校验
- `typescript` — TypeScript 编译器
- `tsx` — TypeScript 直接运行器
- `@types/node` — Node.js 类型定义

### 步骤 3：编译（可选，用 tsx 可跳过）

```bash
# 编译为 JavaScript
npx tsc --noEmit  # 仅类型检查，不输出
npx tsc            # 编译到 dist/

# 如果编译报错，检查：
# - tsconfig.json 的 target 是否为 ES2022 或更高
# - 是否安装了 @types/node
```

### 步骤 4：运行握手测试

```bash
# 方式 A：用 tsx 直接运行（推荐，无需编译）
python3 scripts/test_mcp_handshake.py \
  --command "npx tsx src/server.ts" \
  --timeout 15

# 方式 B：先编译再运行
npx tsc
python3 scripts/test_mcp_handshake.py \
  --command "node dist/server.js" \
  --timeout 10
```

预期输出：
```
MCP 服务器握手测试报告
✅ 通过: initialize (初始化握手)
✅ 通过: tools/list (工具列表，发现 2 个工具)
结论: 握手测试全部通过 ✅
```

### 步骤 5：运行工具真实调用测试

```bash
# 方式 A：tsx 直接运行
python3 scripts/test_mcp_tools.py \
  --command npx \
  --args tsx src/server.ts \
  --timeout 15

# 方式 B：编译后运行
python3 scripts/test_mcp_tools.py \
  --command node \
  --args dist/server.js \
  --timeout 10
```

预期输出：
```
✅ 工具列表: 2 个工具

工具调用测试:
------------------------------------------------------------
  ✅ add (1.2ms)
  ✅ greet (1.0ms)

============================================================
汇总: 2/2 通过 (100.0%), 失败 0, 跳过 0
✅ 所有工具调用测试通过
============================================================
```

### 步骤 6：性能基准测试

```bash
python3 scripts/benchmark_mcp.py \
  --server src/server.ts \
  --command "npx tsx" \
  --tool add \
  --arguments '{"a":1,"b":2}' \
  --requests 10 \
  --concurrency 1 \
  --timeout 15 \
  --output benchmark.json
```

## 常见问题排查

### 问题 1：`npx tsx` 启动慢，握手超时

**症状**：`test_mcp_handshake.py` 报 "等待响应超时"

**原因**：`npx tsx` 首次运行需要下载和编译，启动慢

**解决**：
```bash
# 增加超时时间
python3 scripts/test_mcp_handshake.py --command "npx tsx src/server.ts" --timeout 30

# 或全局安装 tsx，避免 npx 开销
npm install -g tsx
python3 scripts/test_mcp_handshake.py --command "tsx src/server.ts" --timeout 15

# 或先编译再运行（启动更快）
npx tsc
python3 scripts/test_mcp_handshake.py --command "node dist/server.js" --timeout 10
```

### 问题 2：TypeScript 编译报错 `Cannot find module '@modelcontextprotocol/sdk'`

**原因**：依赖未安装或安装失败

**解决**：
```bash
rm -rf node_modules package-lock.json
npm install
npm ls @modelcontextprotocol/sdk  # 确认已安装
```

### 问题 3：握手失败，报 "Invalid JSON-RPC response"

**原因**：服务器在 stdout 打印了调试信息，破坏了 JSON-RPC 协议

**解决**：
- 所有 `console.log()` 改为 `console.error()`
- stdout 是 JSON-RPC 专用通道，任何额外输出都会破坏协议
- 检查生成的 `src/server.ts`，确保没有 `console.log`

### 问题 4：`tsc` 报 `Cannot find name 'process'`

**原因**：缺少 `@types/node`

**解决**：
```bash
npm install --save-dev @types/node
# 确保 tsconfig.json 中有 "types": ["node"]
```

### 问题 5：工具调用返回空结果

**原因**：工具函数没有正确返回值，或返回值格式不对

**解决**：
- 检查工具函数是否有 `return` 语句
- MCP 工具返回值应为字符串，或包含 `content` 数组的对象
- 参考生成的模板代码中的返回格式

## streamable-http 传输类型测试

如果生成的是 streamable-http 类型的服务器：

```bash
# 1. 启动服务器（监听端口）
npx tsx src/server.ts --port 3000 &

# 2. 用 probe_remote_mcp.py 探测
python3 scripts/probe_remote_mcp.py \
  --url "http://localhost:3000/mcp" \
  --output probe.json

# 3. 验证结果
cat probe.json
```

注意：streamable-http 类型的服务器需要自己实现 HTTP 监听，生成的模板可能需要补充启动代码。

## 快速验证清单

发布 TypeScript MCP 服务器前，确保以下全部通过：

- [ ] `npm install` 无错误
- [ ] `npx tsc --noEmit` 类型检查通过
- [ ] `test_mcp_handshake.py` 握手通过
- [ ] `test_mcp_tools.py` 所有工具调用通过
- [ ] stdout 无调试输出（全部用 stderr）
- [ ] `validate_plugin.py` 插件结构验证通过
- [ ] `audit_plugin.py` 无 high/critical 安全问题

---

# 日志指南
# 统一日志系统使用指南

> 本指南说明如何使用 `scripts/common/logger.py` 统一日志系统。

## 概述

`scripts/common/logger.py` 提供标准化的日志输出，适用于新建脚本和需要调试的场景。现有脚本已稳定运行，可按需迁移。

## 快速开始

```python
import sys
sys.path.insert(0, str(Path(__file__).parent))

from common.logger import setup_logging, get_logger

# 初始化（verbose 模式输出 DEBUG）
setup_logging(verbose=False)

# 获取日志器
log = get_logger("my-script")

# 使用
log.debug("调试信息")      # 仅 verbose 模式输出到 stderr
log.info("普通信息")       # 输出到 stdout
log.warning("警告信息")    # 输出到 stderr
log.error("错误信息")      # 输出到 stderr
log.success("操作成功")    # ✅ 前缀
log.fail("操作失败")       # ❌ 前缀
log.step(1, 5, "第一步")   # [1/5] 前缀
```

## 日志级别

| 级别 | 输出目标 | 颜色 | 使用场景 |
|------|---------|------|---------|
| DEBUG | stderr | 青色 | 详细调试信息，仅 verbose 模式 |
| INFO | stdout | 绿色 | 正常进度信息 |
| WARNING | stderr | 黄色 | 非致命警告 |
| ERROR | stderr | 红色 | 错误，但可继续 |
| CRITICAL | stderr | 紫色 | 致命错误，需终止 |

## 命令行集成

在 argparse 中添加 --verbose 选项：

```python
import argparse
from common.logger import setup_logging, get_logger, parse_verbose_args

def main():
    # 方法1：手动解析
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true", help="启用调试模式")
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)
    
    # 方法2：自动解析（在 argparse 之前）
    argv, verbose = parse_verbose_args(sys.argv[1:])
    setup_logging(verbose=verbose)
```

## 输出格式

```
[INFO] 14:30:25 my-script - 开始处理
[WARNING] 14:30:26 my-script - 配置文件不存在，使用默认值
[ERROR] 14:30:27 my-script - 处理失败
✅ [INFO] 14:30:28 my-script - 操作成功
```

彩色终端环境下，级别标签会有对应颜色。

## 迁移指南

现有脚本迁移到统一日志系统的步骤：

1. **添加导入**：
   ```python
   from common.logger import setup_logging, get_logger
   ```

2. **初始化**：在 main() 开头添加：
   ```python
   setup_logging(verbose=args.verbose)
   log = get_logger("script-name")
   ```

3. **替换 print**：
   - `print("信息")` → `log.info("信息")`
   - `print("错误", file=sys.stderr)` → `log.error("错误")`
   - `print("✅ 成功")` → `log.success("成功")`

4. **添加 --verbose 参数**：
   ```python
   parser.add_argument("--verbose", "-v", action="store_true", help="启用调试模式")
   ```

## 注意事项

- **零依赖**：仅使用 Python 标准库（sys, time）
- **向后兼容**：不使用日志系统的脚本不受影响
- **彩色自动检测**：非终端环境（如 CI）自动禁用彩色
- **stderr/stdout 分离**：INFO 到 stdout，WARNING/ERROR/DEBUG 到 stderr
- **性能**：DEBUG 级别在非 verbose 模式下完全不执行格式化

## 最佳实践

1. **新建脚本必须使用**统一日志系统
2. **现有脚本按需迁移**，优先迁移复杂脚本（wizard, plugin_to_skill）
3. **错误必须用 log.error**，不要用 print 到 stderr
4. **成功消息用 log.success**，保持一致性
5. **多步骤操作用 log.step**，显示进度

---

# 生产级 MCP 服务器最佳实践

> 本章节基于 AWS、Microsoft、MCPgee 等业界最佳实践整理，适用于需要部署到生产环境的 MCP 服务器。

## 目录

- [架构设计原则](#架构设计原则)
- [生产级清单](#生产级清单)
- [安全加固](#安全加固)
- [可靠性模式](#可靠性模式)
- [可观测性](#可观测性)
- [性能优化](#性能优化)

## 架构设计原则

### 1. 关注点分离（Separation of Concerns）

**错误做法**（单文件，业务逻辑与传输层耦合）：
```python
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
def query_database(sql: str) -> str:
    # 业务逻辑直接写在工具函数里
    import psycopg2
    conn = psycopg2.connect(...)
    cursor = conn.cursor()
    cursor.execute(sql)
    return str(cursor.fetchall())
```

**正确做法**（分层架构）：
```
my-server/
├── server.py          # MCP 传输层（只负责协议处理）
├── services/          # 业务逻辑层
│   ├── database.py    # 数据库查询服务
│   └── analytics.py   # 分析服务
├── models/            # 数据模型层
│   └── schemas.py     # Pydantic/Zod schema
└── tests/             # 测试层
    └── test_services.py
```

```python
# server.py - 只负责协议处理
from fastmcp import FastMCP
from services.database import DatabaseService

mcp = FastMCP("my-server")
db = DatabaseService()

@mcp.tool()
def query_database(sql: str) -> str:
    """工具处理器保持精简，委托给服务层"""
    return db.query(sql)
```

```python
# services/database.py - 业务逻辑，可独立测试
class DatabaseService:
    def __init__(self):
        self.conn = None
    
    def query(self, sql: str) -> str:
        # 输入验证
        if not self._is_safe_sql(sql):
            raise ValueError("不安全的 SQL 查询")
        # 业务逻辑
        ...
        return result
    
    def _is_safe_sql(self, sql: str) -> bool:
        # 安全检查
        ...
```

**好处**：
- 业务逻辑可以独立单元测试，不需要启动 MCP 服务器
- 可以复用业务逻辑到其他接口（REST API、CLI 等）
- 更容易做依赖注入和 Mock

### 2. 类型安全（Type Safety）

**TypeScript**：使用 Zod schema 做运行时验证
```typescript
import { z } from "zod";

const QueryParams = z.object({
  sql: z.string().min(1).max(1000),
  limit: z.number().int().min(1).max(100).default(10),
});

// MCP 工具定义时使用 Zod schema
server.tool("query_database", {
  description: "查询数据库",
  inputSchema: QueryParams,
}, async (args) => {
  // args 已经过 Zod 验证
  const { sql, limit } = QueryParams.parse(args);
  ...
});
```

**Python**：使用 Pydantic 模型做参数验证
```python
from pydantic import BaseModel, Field, field_validator

class QueryParams(BaseModel):
    sql: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    
    @field_validator("sql")
    @classmethod
    def validate_sql_safety(cls, v: str) -> str:
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]
        for keyword in dangerous_keywords:
            if keyword.upper() in v.upper():
                raise ValueError(f"不允许的 SQL 操作: {keyword}")
        return v
```

### 3. 错误边界（Error Boundaries）

每一层都应该有错误处理，不要让异常直接泄露到 MCP 协议层：

```python
# services/database.py
class DatabaseService:
    def query(self, sql: str) -> str:
        try:
            # 业务逻辑
            result = self._execute_query(sql)
            return result
        except ConnectionError as e:
            # 转换为业务异常，附带上下文
            raise DatabaseError(f"数据库连接失败: {e}") from e
        except TimeoutError as e:
            raise DatabaseError(f"查询超时（30秒）: {e}") from e

# server.py - 最外层捕获所有异常
@mcp.tool()
def query_database(sql: str) -> str:
    try:
        return db.query(sql)
    except DatabaseError as e:
        # 返回结构化错误，不泄露内部细节
        return f"错误: {e.message}"
    except Exception as e:
        # 未知异常，记录日志，返回通用错误
        log.error(f"未预期的错误: {e}", exc_info=True)
        return "错误: 服务暂时不可用，请稍后重试"
```

### 4. 工具数量控制

**业界最佳实践**：每个 MCP 服务器限制在 **5-8 个工具**。

原因：
- 每个工具定义占用 100-300 tokens 的上下文
- 工具越多，AI 选择正确工具的难度越大
- 超过 10 个工具时，建议拆分为多个服务器

**拆分策略**：
```
# 错误：一个服务器 20 个工具
big-server/
└── tools: [query, insert, update, delete, export, import, 
            analyze, report, dashboard, alert, ...]

# 正确：按领域拆分为多个服务器
database-server/    # 4 个工具：query, insert, update, delete
analytics-server/   # 3 个工具：analyze, report, dashboard
alert-server/       # 2 个工具：create_alert, list_alerts
```

## 生产级清单

发布到生产环境前，必须逐项检查：

### 必须项（100% 达标）

- [ ] **输入验证**：所有工具参数都有 schema 验证（类型、范围、长度）
- [ ] **输出清理**：返回结果中不包含密钥、密码、PII（个人身份信息）
- [ ] **认证配置**：远程 MCP 必须要求认证，禁止匿名访问
- [ ] **授权规则**：每个工具都有权限检查，遵循最小权限原则
- [ ] **单元测试**：业务逻辑层有单元测试，覆盖率 ≥ 70%
- [ ] **集成测试**：有端到端的 MCP 握手 + 工具调用测试
- [ ] **结构化日志**：所有工具调用都有日志（用户ID、工具名、参数哈希、结果状态）
- [ ] **错误处理**：所有异常都被捕获，返回友好错误信息
- [ ] **超时设置**：所有外部调用都有超时（默认 30 秒）
- [ ] **依赖锁定**：package.json / requirements.txt 版本锁定

### 推荐项（建议达标）

- [ ] **限流**：每个用户/令牌有速率限制（如 100 次/分钟）
- [ ] **审计日志**：所有工具调用记录到审计日志，保留 30 天
- [ ] **健康检查**：提供健康检查端点（`/health`）
- [ ] **监控仪表盘**：工具调用量、成功率、P95 延迟、错误率
- [ ] **告警**：错误率 > 5% 时触发告警
- [ ] **熔断**：外部依赖失败率高时自动熔断
- [ ] **降级**：关键工具有降级方案（缓存、默认值）
- [ ] **文档**：每个工具都有清晰的描述和使用示例

## 安全加固

### 1. 认证与授权

**远程 MCP（streamable-http）必须配置认证**：

```python
# 方式1：API Key 认证
from fastmcp import FastMCP
from fastmcp.transports import StreamableHTTPTransport

mcp = FastMCP("secure-server")

# 认证中间件
def auth_middleware(request):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != os.environ.get("MCP_API_KEY"):
        return {"status": 401, "body": {"error": "未授权"}}
    return request

transport = StreamableHTTPTransport(
    mcp,
    host="0.0.0.0",
    port=8000,
    middleware=[auth_middleware],
)
```

**本地 MCP（stdio）**：
- 不需要网络认证（只在本地运行）
- 但仍需检查文件系统访问权限
- 不要以 root 权限运行

### 2. 输入验证深度

不仅验证类型，还要验证业务规则：

```python
from pydantic import BaseModel, Field, field_validator

class EmailParams(BaseModel):
    to: str = Field(..., description="收件人邮箱")
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=10000)
    
    @field_validator("to")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("无效的邮箱格式")
        # 检查是否在允许的域名列表中
        allowed_domains = ["example.com", "company.com"]
        domain = v.split("@")[1]
        if domain not in allowed_domains:
            raise ValueError(f"不允许的邮箱域名: {domain}")
        return v
    
    @field_validator("body")
    @classmethod
    def sanitize_html(cls, v: str) -> str:
        # 移除潜在的 XSS 攻击代码
        import re
        return re.sub(r"<script.*?</script>", "", v, flags=re.DOTALL)
```

### 3. 输出清理

返回结果前，清理敏感信息：

```python
import re

def sanitize_output(text: str) -> str:
    """清理输出中的敏感信息"""
    # 移除 API Key
    text = re.sub(r"(sk-[A-Za-z0-9]{20,})", "[REDACTED_API_KEY]", text)
    # 移除密码
    text = re.sub(r"(password\s*[:=]\s*)\S+", r"\1[REDACTED]", text, flags=re.IGNORECASE)
    # 移除手机号
    text = re.sub(r"1[3-9]\d{9}", "[REDACTED_PHONE]", text)
    # 移除身份证号
    text = re.sub(r"\d{17}[\dXx]", "[REDACTED_ID]", text)
    return text
```

### 4. 密钥管理

**绝对禁止**：
- ❌ 硬编码密钥在代码中
- ❌ 将密钥提交到 Git 仓库
- ❌ 在日志中打印密钥
- ❌ 通过环境变量名传递密钥（如 `API_KEY=xxx python server.py`）

**正确做法**：
- ✅ 使用环境变量（在运行时注入）
- ✅ 使用密钥管理服务（AWS Secrets Manager、HashiCorp Vault）
- ✅ 使用 `.env` 文件（加入 `.gitignore`）
- ✅ 密钥轮换机制（定期更新）

## 可靠性模式

### 1. 健康检查

```python
# health.py
from fastmcp import FastMCP

mcp = FastMCP("server-with-health")

@mcp.tool()
def health_check() -> dict:
    """健康检查：返回服务器状态和依赖健康度"""
    checks = {
        "server": "ok",
        "database": check_database(),
        "cache": check_cache(),
        "external_api": check_external_api(),
    }
    all_healthy = all(v == "ok" for v in checks.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": time.time(),
    }

def check_database() -> str:
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        return "ok"
    except Exception:
        return "unhealthy"
```

### 2. 断路器（Circuit Breaker）

当外部依赖失败率高时，自动熔断，避免级联故障：

```python
import time

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise Exception("断路器已打开，跳过调用")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        self.failures = 0
        self.state = "closed"
    
    def on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"

# 使用
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

@mcp.tool()
def call_external_api(query: str) -> str:
    try:
        return breaker.call(external_api.query, query)
    except Exception as e:
        if "断路器已打开" in str(e):
            return "服务暂时不可用（断路器已打开），请稍后重试"
        raise
```

### 3. 降级策略

关键工具有降级方案：

```python
@mcp.tool()
def get_weather(city: str) -> str:
    # 优先调用实时 API
    try:
        return weather_api.get_current(city)
    except Exception as e:
        log.warning(f"实时天气 API 失败: {e}")
        # 降级1：使用缓存
        cached = cache.get(f"weather:{city}")
        if cached:
            return f"{cached}（缓存数据，可能不是最新）"
        # 降级2：返回默认值
        return f"暂时无法获取 {city} 的天气数据，请稍后重试"
```

### 4. 重试机制

对临时性错误进行重试：

```python
import time
import random

def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    """指数退避重试"""
    for attempt in range(max_retries):
        try:
            return func()
        except (ConnectionError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            log.warning(f"第 {attempt+1} 次重试，等待 {delay:.1f} 秒: {e}")
            time.sleep(delay)
```

## 可观测性

### 1. 结构化日志

```python
import json
import sys
import time

class StructuredLogger:
    def __init__(self, service_name):
        self.service_name = service_name
    
    def _log(self, level, message, **kwargs):
        entry = {
            "timestamp": time.time(),
            "service": self.service_name,
            "level": level,
            "message": message,
            **kwargs,
        }
        # 日志输出到 stderr（stdout 只用于 MCP JSON-RPC）
        print(json.dumps(entry, ensure_ascii=False), file=sys.stderr)
    
    def info(self, message, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def error(self, message, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def tool_call(self, tool_name, user_id, args_hash, duration_ms, success):
        self._log("TOOL_CALL", 
                  f"工具调用: {tool_name}",
                  tool=tool_name,
                  user_id=user_id,
                  args_hash=args_hash,
                  duration_ms=duration_ms,
                  success=success)

log = StructuredLogger("my-mcp-server")

# 使用
@mcp.tool()
def query_database(sql: str) -> str:
    start = time.time()
    try:
        result = db.query(sql)
        log.tool_call("query_database", "user-123", hash(sql), 
                      int((time.time()-start)*1000), True)
        return result
    except Exception as e:
        log.tool_call("query_database", "user-123", hash(sql),
                      int((time.time()-start)*1000), False)
        log.error("查询失败", error=str(e))
        raise
```

### 2. 监控指标

关键指标：
- **工具调用量**：每分钟/每小时调用次数
- **成功率**：成功调用 / 总调用
- **P95 延迟**：95% 的调用在多少毫秒内完成
- **错误率**：按错误类型分类统计
- **活跃用户数**：唯一用户数量

### 3. 告警规则

- 错误率 > 5% 持续 5 分钟 → PagerDuty 告警
- P95 延迟 > 5 秒持续 10 分钟 → Slack 告警
- 认证失败次数突增 → 安全告警
- 服务器重启次数 > 3 次/小时 → 告警

## 性能优化

### 1. 连接池

对数据库、HTTP 客户端使用连接池：

```python
# 数据库连接池
from psycopg2 import pool

connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host="localhost",
    database="mydb",
    user="user",
    password="password"
)

def get_connection():
    return connection_pool.getconn()

def release_connection(conn):
    connection_pool.putconn(conn)
```

### 2. 缓存

对频繁查询、变化少的数据使用缓存：

```python
from functools import lru_cache
import time

class Cache:
    def __init__(self, ttl=300):  # 5 分钟过期
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())

cache = Cache(ttl=300)

@mcp.tool()
def get_product_info(product_id: str) -> dict:
    # 先查缓存
    cached = cache.get(f"product:{product_id}")
    if cached:
        return cached
    # 缓存未命中，查询数据库
    result = db.query_product(product_id)
    cache.set(f"product:{product_id}", result)
    return result
```

### 3. 异步处理

对耗时操作使用异步：

```python
import asyncio
from fastmcp import FastMCP

mcp = FastMCP("async-server")

@mcp.tool()
async def generate_report(report_type: str) -> str:
    # 异步执行多个任务
    tasks = [
        fetch_data_async("sales"),
        fetch_data_async("inventory"),
        fetch_data_async("customers"),
    ]
    results = await asyncio.gather(*tasks)
    return process_report(results)
```

## 总结

生产级 MCP 服务器的核心原则：

1. **架构分层**：传输层 / 业务层 / 数据层分离
2. **安全第一**：认证、授权、输入验证、输出清理
3. **可靠运行**：健康检查、断路器、降级、重试
4. **可观测**：结构化日志、监控、告警
5. **性能优化**：连接池、缓存、异步
6. **工具精简**：每个服务器 5-8 个工具，按领域拆分

遵循这些原则，你的 MCP 服务器就能从"能跑"升级到"生产级可用"。
