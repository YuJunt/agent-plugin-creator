#!/usr/bin/env npx tsx
/**
 * DevOps Tools MCP Server
 * 提供 CI/CD 相关工具的 MCP 服务器示例（TypeScript 实现）
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// 模拟构建数据
const mockBuilds = [
  { id: 1, status: "success", branch: "main", duration: 120, commit: "abc123" },
  { id: 2, status: "failed", branch: "feature/login", duration: 45, commit: "def456" },
  { id: 3, status: "running", branch: "main", duration: 30, commit: "ghi789" },
];

// 模拟部署数据
const mockDeployments = [
  { id: 1, service: "api-server", environment: "production", status: "healthy", version: "v2.1.0" },
  { id: 2, service: "web-app", environment: "staging", status: "healthy", version: "v2.2.0-rc1" },
];

const server = new Server(
  { name: "devops-tools", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// 列出可用工具
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_builds",
      description: "列出最近的 CI 构建记录",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "返回数量，默认 10" },
          status: { type: "string", description: "按状态筛选：success/failed/running" },
        },
      },
    },
    {
      name: "get_build_logs",
      description: "获取指定构建的日志",
      inputSchema: {
        type: "object",
        properties: {
          build_id: { type: "number", description: "构建 ID" },
        },
        required: ["build_id"],
      },
    },
    {
      name: "list_deployments",
      description: "列出应用部署记录和状态",
      inputSchema: {
        type: "object",
        properties: {
          environment: { type: "string", description: "按环境筛选：production/staging" },
        },
      },
    },
    {
      name: "get_service_health",
      description: "获取服务健康状态",
      inputSchema: {
        type: "object",
        properties: {
          service: { type: "string", description: "服务名称" },
        },
        required: ["service"],
      },
    },
  ],
}));

// 处理工具调用
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "list_builds": {
      let builds = [...mockBuilds];
      if (args?.status) {
        builds = builds.filter((b) => b.status === args.status);
      }
      const limit = args?.limit || 10;
      return {
        content: [{ type: "text", text: JSON.stringify(builds.slice(0, limit), null, 2) }],
      };
    }

    case "get_build_logs": {
      const build = mockBuilds.find((b) => b.id === args?.build_id);
      if (!build) {
        return { content: [{ type: "text", text: `构建 #${args?.build_id} 不存在` }], isError: true };
      }
      return {
        content: [
          {
            type: "text",
            text: `构建 #${build.id} (${build.status})\n分支: ${build.branch}\n提交: ${build.commit}\n耗时: ${build.duration}s\n\n[示例日志]\n$ npm ci\n$ npm run build\n$ npm test\n\n测试通过: 128/128`,
          },
        ],
      };
    }

    case "list_deployments": {
      let deployments = [...mockDeployments];
      if (args?.environment) {
        deployments = deployments.filter((d) => d.environment === args.environment);
      }
      return {
        content: [{ type: "text", text: JSON.stringify(deployments, null, 2) }],
      };
    }

    case "get_service_health": {
      const deployment = mockDeployments.find((d) => d.service === args?.service);
      if (!deployment) {
        return { content: [{ type: "text", text: `服务 ${args?.service} 不存在` }], isError: true };
      }
      return {
        content: [
          {
            type: "text",
            text: `服务: ${deployment.service}\n环境: ${deployment.environment}\n状态: ${deployment.status}\n版本: ${deployment.version}\n健康检查: 通过\n响应时间: 45ms\n错误率: 0.02%`,
          },
        ],
      };
    }

    default:
      return { content: [{ type: "text", text: `未知工具: ${name}` }], isError: true };
  }
});

// 启动服务器
const transport = new StdioServerTransport();
await server.connect(transport);
console.error("DevOps Tools MCP Server 已启动", { file: "stderr" });
