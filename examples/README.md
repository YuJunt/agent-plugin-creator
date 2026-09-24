# Examples

本目录包含插件示例和反向封装产物。

## 插件示例（含 plugin.json，可直接 validate_plugin）

| 目录 | 场景 |
|---|---|
| `minimal-skill-only` | 纯 Skill、最小化结构、入门最快 |
| `customer-support.triage` | Skill + Python MCP + 数据 + 评估 |
| `ecommerce.refund-approval` | Skill + MCP + 合同 + 审计日志 |
| `multi-skill-ts-mcp` | 多 Skill（2个）+ TypeScript MCP |

## 反向封装产物（非 plugin，是 plugin_to_skill.py 的输出示例）

| 目录 | 说明 |
|---|---|
| `customer-support-as-skill` | 由 customer-support.triage 反向封装生成的普通 Skill |

> 注意：反向封装产物没有 plugin.json，不能用 validate_plugin 验证，应该用 validate_skill。
