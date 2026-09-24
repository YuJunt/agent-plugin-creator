# 教程：交互式向导

## 概述

`wizard.py` 是 Agent Plugin Creator 的交互式创建向导，通过问答引导用户完成插件创建。

## 启动向导

```bash
cd agent-plugin-creator
python3 scripts/wizard.py
```

## 两种模式

### 1. 交互式模式（默认）

通过问答收集信息，适合新手：

```
$ python3 scripts/wizard.py

=== Agent Plugin 创建向导 ===

插件名称: my-first-plugin
插件版本 [0.1.0]: 1.0.0
插件描述: 我的第一个插件
作者名称: Your Name
许可证 [MIT]: 
关键词 (逗号分隔): plugin, demo

是否包含 Skill? (y/n): y
Skill 名称: my-skill
Skill 描述: 示例技能

是否包含 MCP 服务器? (y/n): n

=== 插件创建完成 ===
位置: ./my-first-plugin
```

### 2. 配置文件模式

通过 JSON 配置文件批量生成，适合自动化：

```bash
python3 scripts/wizard.py --config config.json --output ./my-plugin
```

**config.json 示例**：

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "插件描述",
  "author": {"name": "作者名"},
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "components": {
    "skills": [
      {"name": "skill-name", "description": "skill 描述"}
    ],
    "mcp_servers": [
      {
        "name": "server-name",
        "language": "python",
        "transport": "stdio",
        "tools": [
          {"name": "tool_name", "description": "工具描述"}
        ]
      }
    ]
  }
}
```

### 3. 预览模式

不实际写入文件，只预览将生成的内容：

```bash
python3 scripts/wizard.py --config config.json --dry-run
```

## 生成的目录结构

```
my-plugin/
├── plugin.json              # 插件清单
├── skills/
│   └── my-skill/
│       ├── SKILL.md         # 技能文件
│       ├── scripts/         # 脚本目录
│       ├── references/      # 参考文档
│       └── assets/          # 资源文件
├── mcp.json                 # MCP 配置（如包含 MCP）
└── servers/                 # MCP 服务器代码（如包含 MCP）
    └── server-name/
```

## 后续步骤

生成插件后，建议执行：

```bash
# 1. 验证插件结构
python3 scripts/validate_plugin.py ./my-plugin

# 2. 安全审计
python3 scripts/audit_plugin.py ./my-plugin

# 3. 生成文档
python3 scripts/generate_docs.py ./my-plugin --output README.md

# 4. 多客户端适配
python3 scripts/client_adapter.py ./my-plugin --generate

# 5. 打包发布
python3 scripts/package_plugin.py ./my-plugin --output dist
```

## 常见问题

### Q: 向导生成的 Skill 是空的吗？
A: 不是。向导会生成包含基本结构的 SKILL.md，包括 frontmatter、工作流框架和 Gotchas section。你需要根据实际需求填充内容。

### Q: 可以只创建 Skill 不创建 MCP 吗？
A: 可以。在向导中选择不包含 MCP 服务器即可。纯 Skill 插件不需要 mcp.json 和 servers/ 目录。

### Q: 配置文件模式支持哪些字段？
A: 支持 name、version、description、author、license、keywords、components.skills、components.mcp_servers 等字段。详细格式参见 `wizard.py --help`。

---

**下一步**：
- [Skill 编写最佳实践](Best-Practices:-Skill-编写)
- [MCP 服务器设计最佳实践](Best-Practices:-MCP-服务器设计)
- [FAQ](FAQ)
