/**
 * MCP Server - TypeScript Template
 *
 * 基于官方 @modelcontextprotocol/sdk 的 MCP 服务器模板。
 * 在此文件中注册你的工具，然后打包进 Agent Plugin。
 *
 * 启动方式:
 *   npx tsx src/server.ts          # 开发模式（stdio）
 *   npm run build && npm start     # 生产模式（stdio）
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// ============================================================
// 服务器配置
// ============================================================

const server = new McpServer({
  name: "mcp-server-template",
  version: "1.0.0",
});

// ============================================================
// 工具注册
// ============================================================

/**
 * 示例工具：加法计算
 *
 * 替换为你的实际工具。每个工具需要：
 * - name: 小写+下划线的唯一标识
 * - description: 描述做什么+什么时候用
 * - parameters: Zod schema，每个参数有 describe()
 * - handler: 异步函数，返回 { content: [...] }
 */
server.tool(
  "add",
  "Add two numbers together. Use when the user needs to perform basic arithmetic addition.",
  {
    a: z.number().describe("First number to add"),
    b: z.number().describe("Second number to add"),
  },
  async ({ a, b }) => {
    const result = a + b;
    return {
      content: [
        {
          type: "text",
          text: `${a} + ${b} = ${result}`,
        },
      ],
    };
  }
);

/**
 * 示例工具：获取当前时间
 *
 * 演示无参数工具和错误处理。
 */
server.tool(
  "get_current_time",
  "Get the current date and time. Use when the user asks what time it is or needs a timestamp.",
  {},
  async () => {
    try {
      const now = new Date().toISOString();
      return {
        content: [
          {
            type: "text",
            text: `Current time: ${now}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error getting current time: ${error}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ============================================================
// 在此添加更多工具...
// ============================================================

// server.tool(
//   "your_tool_name",
//   "Description of what your tool does and when to use it.",
//   {
//     param1: z.string().describe("Description of param1"),
//     param2: z.number().optional().describe("Optional param2"),
//   },
//   async ({ param1, param2 }) => {
//     // 你的业务逻辑
//     return {
//       content: [{ type: "text", text: "Result" }],
//     };
//   }
// );

// ============================================================
// 启动服务器（stdio 传输）
// ============================================================

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // 注意：日志输出到 stderr，不要写到 stdout（stdout 用于 MCP 通信）
  console.error("MCP server started (stdio transport)");
}

main().catch((error) => {
  console.error("Fatal error starting MCP server:", error);
  process.exit(1);
});
