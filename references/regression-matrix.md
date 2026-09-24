# Agent Plugin Creator 多轮回归测试矩阵

## 官方基线

| 领域 | 基线要求 | 测试方法 |
| --- | --- | --- |
| plugin.json | canonical `$schema`、必填 name、闭集字段、name 约束 | JSON Schema + 自定义语义检查 |
| mcp.json | canonical `$schema`、stdio/streamable-http/sse oneOf、env 保留变量保护、cwd 前缀 | JSON Schema + 路径/URL/秘密审计 |
| Agent Skill | frontmatter、name 与目录一致、description 触发性、资源引用 | 官方 Skill validator + 触发评估 |
| 包边界 | 所有解析路径保持在插件根内，拒绝 symlink 逃逸 | 正向/负向路径 fixture |
| MCP runtime | server 初始化、工具发现、代表性调用、错误可恢复 | 官方 MCP client/Inspector |
| 专业质量 | 业务契约、证据化输出、权限、评估、兼容矩阵 | quality-gates.md 逐项判定 |

## 真实业务场景

| 场景 | 组件 | 关键验收 |
| --- | --- | --- |
| 销售收入管道审查 | Skill + stdio MCP | 管道汇总、加权预测、风险商机、10 个只读评估问题 |
| 客服工单分流 | Skill + stdio MCP | SLA 风险识别、优先级建议、禁止未经确认修改工单 |
| 采购合规审查 | Skill + streamable HTTP 配置 | 供应商风险证据、权限与秘密不入包、远程 HTTPS |
| 财务月结检查 | Skill-only | 仅使用本地文档流程时不生成不必要的 mcp.json |
| 旧平台插件迁移 | Skill + MCP + client extension | hooks/commands/agents 不误放入 portable core |
| 多 Skill 插件 | 多个 immediate-child Skills | 一个坏 Skill 不阻断其他 Skill 的结构验证 |

## 负向场景

应让验证器拒绝或警告以下输入：未知 manifest 顶层字段、非法插件名、非法 Skill 名、缺失 frontmatter、Skill name 与目录不一致、mcp command 含 shell 运算符、`../` 逃逸、远程 HTTP 非 loopback、URL userinfo/fragment、保留环境变量覆盖、明文 API key、错误 transport、坏 JSON、skills 非目录、mcp.json 顶层非法字段和越权 symlink。

## 迭代规则

每一轮修改都必须重新执行官方技能验证、脚手架正向测试、所有业务场景静态验证、负向 fixture、至少一个 MCP 端到端测试和回归报告。任何新增规则都必须有一个正向 fixture 与一个负向 fixture，避免只增加文档而没有可执行证明。
