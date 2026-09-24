# 正式版官方合规矩阵

| 领域 | 官方要求 | 当前实现 | 证据 | 状态 |
| --- | --- | --- | --- | --- |
| Plugin root | 根目录必须有 plugin.json，包内解析路径不得逃逸 | validate_plugin.py + release_audit.py | 五个样例、负向 symlink/路径规则 | PASS（本地） |
| Manifest | plugin.json 顶层闭集、schema canonical、name 规则 | 官方 plugin schema + 语义校验 | schema validation output | PASS |
| Discovery | Skill 仅从 skills/ 直接子目录发现；MCP 仅从根 mcp.json 发现 | check_skills/check_mcp | 五个样例结构测试 | PASS |
| Skill format | SKILL.md 遵循 Agent Skills specification，name 与父目录一致 | frontmatter 校验 +官方 quick_validate | 主技能及样例通过 | PASS |
| MCP config | 根 mcp.json 闭集、版本、transport、server 隔离 | 官方 MCP schema +语义校验 | MCP fixtures、运行时样例 | PASS（本地） |
| stdio command | 单一 token，不做 placeholder expansion | command 语义校验 | shell-command fixture | PASS |
| cwd containment | ./、PLUGIN_ROOT、PLUGIN_DATA 语义和 containment | cwd 解析检查 | 逃逸 fixture | PASS（本地） |
| args/env opacity | args/env 值不得被错误解释为包路径；reserved env 禁止 | validator 已移除 args ../ 误报；保留 env 阻断 | validator regression | PASS |
| Remote MCP | absolute URL、userinfo/fragment 禁止、非 loopback HTTPS、headers 不含秘密 | URL/header 语义检查 | remote-http fixture | PASS（静态） |
| Version alignment | plugin.json/mcp.json 目标版本一致 | schema identifiers + semantic check | version mismatch fixture | PASS（需补充 fixture） |
| Failure boundaries | 单个 Skill/server 无效时其他组件继续加载 | validator 可报告组件级错误；真实客户端隔离未测 | validator output | WARNING（客户端未测） |
| Client extensions | 反向域 namespace；规范不定义扩展行为 | 主技能约束和文档 | extension guidance | PASS（未接入客户端） |
| Skill authoring | 官方 skill-creator 的访谈、触发、评估和迭代 | vendor 资源 + selection/activation eval | eval results | PASS（模型/环境限定） |
| MCP authoring | 官方 mcp-builder 的研究、实现、审查、评估四阶段 | vendor 资源 + MCP samples/evaluation.xml | local servers | PASS（本地） |
| Client conformance | 至少支持 transport；客户端加载/跳过/错误报告 | 仅有测试模板，未有第三方客户端日志 | client-conformance.md | WARNING |
| Release | 许可证、来源、构建清单、可复现包、hash | provenance、LICENSE、CHANGELOG、build_release | clean-room and SHA256 | PASS |

## 正式版判定

当前版本的“规范实现”在**包格式、组件发现、Skill/MCP 配置和本地验证器**层面基本完整；“完整遵循官方规范”不能等同于“所有客户端均已证明一致”，因为 Agent Plugins 规范还要求客户端承担发现、跳过和连接失败隔离行为。当前缺口集中在真实客户端 conformance、远程 MCP、OAuth/SSO、性能和业务 UAT，而不是根 manifest 或目录格式。
