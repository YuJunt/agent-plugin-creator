# Customer Support as Skill（反向封装示例）

这是一个由 Agent Plugin 反向封装为 Skill 的示例，展示 `plugin_to_skill.py` 工具的输出结果。

## 来源

原始插件：`../customer-support.triage/`

封装命令：
```bash
python3 scripts/plugin_to_skill.py ../customer-support.triage --output ./customer-support-as-skill
```

## 结构

```
customer-support-as-skill/
├── SKILL.md                    # 封装层：能力清单 + 路由判断 + 使用指南
├── skills/
│   └── ticket-triage/
│       └── SKILL.md            # 原始子技能（保留不动）
├── servers/
│   └── support_ticket_server.py # 原始 MCP 服务器代码
├── scripts/
│   └── start_mcp.py            # 自动生成的 MCP 启动管理工具
├── references/
│   ├── plugin.json             # 原始插件元数据
│   └── mcp.json                # 原始 MCP 配置
├── data/
│   └── tickets.csv             # 原始数据
└── evals/
    └── evaluation.xml          # 原始评估
```

## 封装原理

用"AI 手动执行"替代"平台自动加载"：
- 子技能不会被平台自动发现 → 封装层 SKILL.md 指导 AI 何时读取哪个子技能
- MCP 不会被平台自动启动 → 封装层指导 AI 运行 start_mcp.py 手动启动
- 换取平台兼容性 → 可以在任何支持 Agent Skills 的平台使用

## 与原生插件的区别

| 维度 | 原生 Agent Plugin | 反向封装 Skill |
|------|------------------|---------------|
| 子技能发现 | 平台自动发现 | AI 手动读取 |
| MCP 启动 | 平台自动启动 | AI 手动运行 start_mcp.py |
| 客户端扩展 | 支持 | 不支持 |
| 平台兼容性 | 仅 5 个兼容客户端 | 任何支持 Skill 的平台 |
| 功能完整性 | 100% | ~95%（核心功能完整） |

## 使用方式

将此目录作为 Skill 安装到任何支持 Agent Skills 的平台即可使用。
