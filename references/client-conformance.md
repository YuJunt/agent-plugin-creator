# Client Conformance Test Template

Agent Plugins v1 的客户端一致性不能由包结构验证器代替。为每个目标客户端记录真实版本、操作系统、安装方式、插件来源和完整测试日志。

| 客户端 | 版本 | OS | 安装成功 | plugin.json 加载 | Skill 发现 | MCP 发现 | MCP handshake | 单组件失败隔离 | 扩展行为 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<client>` | `<version>` | `<os>` | unknown | unknown | unknown | unknown | unknown | unknown | unknown | `<log path>` |

## 必测场景

### 基础加载

安装一个只含 plugin.json 的最小插件，确认客户端接受 canonical schema 和 name。安装包含一个 Skill 的插件，确认仅发现 `skills/` 的直接子目录。安装包含一个 MCP server 的插件，确认只从根 `mcp.json` 读取配置。

### 组件隔离

在同一个插件中放置一个有效 Skill 和一个无效 Skill；放置一个有效 MCP server 和一个无效 server。客户端应跳过无效组件并继续加载其他组件，不应把单组件失败升级为整包失败。

### 运行时失败

让 server 启动失败、握手失败、认证失败和工具调用失败，确认其他插件组件仍可用，并且客户端给出可诊断的错误。

### 版本和扩展

使 plugin.json 与 mcp.json schema 版本不一致，确认 MCP 被禁用但其他组件按规范处理。加入客户端公开的 reverse-domain extension，确认目标客户端读取；在不支持该 namespace 的客户端中，确认便携核心仍可加载。

## 证据要求

截图不能替代文本日志。每个测试应保存客户端版本、安装命令、插件 SHA256、发现列表、错误日志和结果摘要。未执行的测试必须写 `not tested`，不得写 `compatible`。
