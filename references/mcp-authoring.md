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
