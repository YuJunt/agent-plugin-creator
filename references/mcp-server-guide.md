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
