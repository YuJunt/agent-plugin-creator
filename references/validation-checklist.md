# Agent Plugin 1.0.0 验证清单

## 包结构与安全

- [ ] 根目录有普通文件 `plugin.json`。
- [ ] 所有 `skills/` 直接子目录中的 `SKILL.md` 都是普通文件。
- [ ] 包内引用路径存在且没有解析到插件根外部。
- [ ] 没有逃逸根目录的 symlink/junction/reparse point。
- [ ] 没有 API key、token、密码、私钥或其他秘密。

## Manifest

- [ ] `$schema` 使用 Agent Plugins 1.0.0 canonical URL。
- [ ] `name` 满足长度、字符、首尾和重复分隔符规则。
- [ ] 顶层只含规范字段。
- [ ] `extensions` 的每个值为对象，namespace 由目标客户端定义。
- [ ] 可选字段类型正确；manifest 是 JSON 对象。

## Skills

- [ ] 每个 Skill 是 `skills/<name>/SKILL.md`，不依赖递归发现。
- [ ] frontmatter 有 `name` 与 `description`。
- [ ] frontmatter `name` 与父目录相同且满足 Agent Skills 规范。
- [ ] description 同时说明能力与触发场景。
- [ ] `scripts/`、`references/`、`assets/` 的引用都存在。
- [ ] 每个 Skill 可独立验证；一个坏 Skill 不应使其他 Skill 无法加载。

## MCP（如存在）

- [ ] 根 `mcp.json` 的 schema 与 manifest 均为 1.0.0。
- [ ] 顶层仅有 `$schema` 和 `mcpServers`。
- [ ] 每个 server 只声明一种 transport。
- [ ] stdio `command` 是单 token，不是 shell 命令行。
- [ ] 插件相对路径以 `./` 开头且不逃逸根目录。
- [ ] `${PLUGIN_ROOT}`、`${PLUGIN_DATA}` 只出现在允许展开的字段。
- [ ] 远程非 loopback 地址使用 HTTPS、无 userinfo/fragment，headers 无秘密。
- [ ] 认证由客户端管理，写操作有确认和最小权限方案。

## 交付与兼容性

- [ ] 每个原始 artifact 都映射到 portable core、client extension、compatibility layer、distribution metadata 或 removal。
- [ ] 目标客户端逐一测试，记录不支持的能力。
- [ ] 安装、更新、回滚、失败隔离和人工步骤已说明。
- [ ] 交付报告不把 hooks、agents、commands、LSP、UI 或 marketplace 元数据宣称为便携 v1 组件。
