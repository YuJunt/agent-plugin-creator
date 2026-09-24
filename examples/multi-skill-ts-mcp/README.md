# Multi Skill + TypeScript MCP Example

多 Skill + TypeScript MCP 服务器示例，展示复杂插件结构和 TS 技术栈。

## 结构

```
multi-skill-ts-mcp/
├── plugin.json                    # 插件元数据
├── mcp.json                       # MCP 服务器配置
├── README.md
├── skills/
│   ├── ci-pipeline-helper/        # Skill 1: CI 流水线助手
│   │   └── SKILL.md
│   └── deployment-manager/        # Skill 2: 部署管理器
│       └── SKILL.md
└── servers/
    └── devops-tools/              # TypeScript MCP 服务器
        ├── package.json
        ├── tsconfig.json
        └── src/
            └── server.ts          # 4 个工具：list_builds, get_build_logs, list_deployments, get_service_health
```

## 特点

- ✅ 多 Skill（2 个子技能）
- ✅ TypeScript MCP 服务器（使用官方 @modelcontextprotocol/sdk）
- ✅ stdio transport
- ✅ 4 个实用工具（构建查询、日志获取、部署列表、健康检查）
- ✅ 两个 Skill 协同工作，共享 MCP 工具
- ✅ 符合 Agent Plugins 1.0.0 规范

## 适用场景

- 学习多 Skill 插件结构
- 学习 TypeScript MCP 服务器开发
- 理解 Skill 与 MCP 服务器的协作模式
- DevOps 场景的插件参考
