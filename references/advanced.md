# 高级功能索引

> 以下功能不在核心工作流中，按需使用。

---

## 质量评估

| 脚本 | 功能 | 用法 |
|---|---|---|
| `run_trigger_eval.py` | 触发评估（should-trigger / should-not-trigger） | `python3 scripts/run_trigger_eval.py --skill .` |
| `run_selection_eval.py` | 选择评估（accuracy 指标） | `python3 scripts/run_selection_eval.py --skill .` |
| `run_edge_eval.py` | 边界评估（边界用例） | `python3 scripts/run_edge_eval.py --skill .` |
| `quality_report.py` | 质量报告（综合评分） | `python3 scripts/quality_report.py --skill .` |
| `analyze_skill_quality.py` | 技能质量分析 | `python3 scripts/analyze_skill_quality.py --skill .` |
| `compare_skill_versions.py` | 版本盲测对比 | `python3 scripts/compare_skill_versions.py --v1 v1.0 --v2 v1.1` |

## 安全审计

| 脚本 | 功能 | 用法 |
|---|---|---|
| `mcp_security_check.py` | OWASP MCP 专项检查 | `python3 scripts/mcp_security_check.py ./my-plugin` |
| `audit_progressive_disclosure.py` | 渐进式披露 Token 预算审计 | `python3 scripts/audit_progressive_disclosure.py --skill .` |

## 市场发布

| 脚本 | 功能 | 用法 |
|---|---|---|
| `generate_marketplace_json.py` | GitHub 市场元数据 | `python3 scripts/generate_marketplace_json.py --plugin ./my-plugin` |
| `generate_skillsh_metadata.py` | Vercel skills.sh 元数据 | `python3 scripts/generate_skillsh_metadata.py --plugin ./my-plugin` |
| `client_adapter.py` | 多客户端适配（Claude/Copilot/Cursor） | `python3 scripts/client_adapter.py ./my-plugin --generate` |

## 开发工具

| 脚本 | 功能 | 用法 |
|---|---|---|
| `migrate_mcp_v2.py` | MCP v1→v2 迁移检测 | `python3 scripts/migrate_mcp_v2.py --project ./my-mcp` |
| `detect_client.py` | 客户端环境自动检测 | `python3 scripts/detect_client.py` |
| `performance_baseline.py` | 性能基准监控 | `python3 scripts/performance_baseline.py --run` |
| `mutation_test.py` | 变异测试 + 属性测试 | `python3 scripts/mutation_test.py` |
| `plugin_to_skill.py` | 反向封装（插件→技能） | `python3 scripts/plugin_to_skill.py ./my-plugin` |

## 发布流程

| 脚本 | 功能 | 用法 |
|---|---|---|
| `build_release.py` | 发布构建（一键全流程） | `python3 scripts/build_release.py` |
| `release_decision.py` | 发布决策（go/no-go） | `python3 scripts/release_decision.py` |

---

## 参考文档

| 文件 | 内容 |
|---|---|
| `references/streamable-http-deployment.md` | MCP Streamable HTTP 部署最佳实践 |
| `references/versioning.md` | 版本管理规范 |
| `references/error-codes.md` | 错误码系统参考 |
| `references/anti-bloat-guardian.md` | 防臃肿守门人（新脚本准入标准） |
| `references/cheatsheet.md` | 速查表与故障排除 |

## 更多参考文档

| 文件 | 内容 |
|---|---|
| `references/logging-guide.md` | 统一日志系统使用指南 |
| `references/typescript-mcp-testing.md` | TypeScript MCP 服务器真实握手测试指南 |
| `references/regression-matrix.md` | 多轮回归测试矩阵 |
| `references/evaluation-protocol.md` | 技能评估协议 |
| `references/validation-checklist.md` | 验证清单 |
# 触发路由与安全预检

> 详细路由规则见本文档，SKILL.md 只保留概览。

## 触发路由与安全预检（不可跳过）

在任何解释、规划、代码或文件输出之前，先单独输出一行路由记录，进行意图分类和安全判断。格式固定为：

```
🔀 路由: {分类}｜技能: {调用的技能名}｜本次动作: {做什么}｜原因: {一句话}
```

**分类说明（人话版）：**
- `positive`：明确要创建 Agent Plugin / 跨客户端分发 / Skill+MCP 组合
- `implicit`：需求隐含需要插件（如"把这个 skill 和 MCP 打包成可分发的东西"）
- `near-miss`：只做窄范围任务（审查、测试、单独 skill/MCP、普通代码文档），不创建 plugin.json / mcp.json
- `adversarial`：危险请求 → 下一行必须以 `REFUSED:` 开头，只提供安全替代方案
- `migration`：旧平台插件（Claude/Copilot/Codex/Cursor 等）迁移到 Agent Plugins 标准

**本次动作**示例：
- `创建插件（含 skill + MCP）`
- `仅审查/测试 skill，不创建插件`
- `生成独立 MCP server`
- `拒绝：{危险点}`

**必须分类为 adversarial 的情况：**
- 要求把 API key、token、私钥、密码写入 manifest 或源代码
- 要求将 hooks、commands、agents、LSP、UI 塞进 Agent Plugins 便携核心
- 要求用 shell 管道或任意命令拼接执行 MCP command
- 要求绕过客户端确认或权限控制
- 安全替代方案：秘密改为客户端/运行时注入，非便携组件移到客户端扩展，MCP 使用单一 executable token 与显式 args

**路由判定必须在交付报告中记录：** 用户意图分类、选择/不选择 Agent Plugin 的理由、是否生成 Skill/MCP/客户端扩展、被拒绝的危险要求及替代方案。

---

## 路由驱动执行计划（详细映射表）

> SKILL.md 只保留核心决策流程，详细映射表放在这里。

### 路由驱动渐进式披露（只加载相关 references）

| 场景 | 加载的 references | 不加载 |
|---|---|---|
| 从零创建插件 | `workflows.md` + `cheatsheet.md` | mcp-server-guide.md（如果不需要MCP） |
| 验证/审计插件 | `plugin-specification.md` + `quality.md` | workflows.md |
| 开发 MCP 服务器 | `mcp-server-guide.md` + `cheatsheet.md` | agent-skills-spec.md（如果不需要skill） |
| 迁移插件 | `advanced.md`（client_adapter部分） | 其他全部 |
| 只做质量评分 | `quality.md` | 其他全部 |

**原则：能不加载就不加载，避免注意力稀释（Attention Dilution）。**

### 路由驱动门禁级别

- 日常检查（near-miss + 低风险）→ `--gate standard`
- 打包发布（positive + 中风险）→ `--gate strict`
- 公开发布（positive + 高风险）→ `--gate critical`

### 路由驱动 Gotchas 展示（只展示相关的坑）

| 场景 | 展示的 Gotchas |
|---|---|
| MCP 开发 | 坑1（写完再验）、坑2（stdout调试）、坑4（command写法） |
| 反向封装 | 坑5（验证工具用错） |
| 用 wizard 创建 | 坑3（骨架当成品） |
| 打包发布 | 坑3（骨架当成品）+ 失败模式速查表 |

### 路由驱动输出格式

| 场景 | 输出格式 |
|---|---|
| 简单查询 | 简洁回答（1-3句话） |
| 创建/修改 | 步骤化输出（每步做了什么） |
| 验证/审计 | 报告格式（通过/失败/警告 + 详情） |
| 发布 | 完整报告 + 交付物链接 |

---

## LLM 特有失败模式（Critical Gotchas）

> 这些是 LLM 作为执行者特有的失败模式，比技术坑更危险，因为它们是"静默"的。

| 失败模式 | 症状 | 原因 | 防护方法 |
|---|---|---|---|
| **🎭 Confabulation（虚构）** | AI 自信地报告"已完成"，但实际没做 | LLM 倾向于给出乐观答案，即使没执行 | **必须验证**：用脚本检查文件是否存在、内容是否非空、退出码是否为 0 |
| **📝 Empty write（空写）** | AI 说"已写入文件"，但文件是空的或只有占位符 | AI 可能只创建了文件没写内容，或写了 TODO 没填充 | **必须检查**：`wc -l file` 看行数，`grep TODO file` 看是否有未填充占位符 |
| **🤫 Silent failure（静默失败）** | 工具调用报错，但 AI 忽略错误继续执行 | AI 可能把 stderr 当成正常输出，或没检查退出码 | **必须检查退出码**：每个脚本调用后检查 `$?`，非 0 就停止 |
| **😴 Accept-and-forget（接受即忘）** | 看起来对就接受，不逐行验证输出 | AI 倾向于"看起来合理就 OK"，不深入验证 | **必须抽样验证**：随机检查生成的代码/文档，不要全信 |

**核心原则：不要相信 AI 的"已完成"声明，只相信脚本的验证结果。**

---

## description 优化检查清单（Prompt 设计）

> description 是触发器，不是描述。用户说什么，description 里就要有什么。

| 检查项 | 说明 | 示例 |
|---|---|---|
| ✅ 动作同义词 | 包含用户可能说的各种动作词 | 创建=做/生成/搭/写/建；验证=检查/校验/看看对不对 |
| ✅ 对象同义词 | 包含用户可能说的各种对象词 | 插件=plugin/包/扩展；MCP=服务器/服务/工具 |
| ✅ 场景同义词 | 包含用户可能说的各种场景 | 打包=发布/导出/生成zip；迁移=转换/适配/移植 |
| ✅ 中英文双语 | 中文用户说中文，英文用户说英文 | "创建插件" + "create plugin" |
| ✅ 动词范围完整 | 不只说"创建"，还要说"验证/审计/修改/迁移" | 避免用户说"检查插件"时不触发 |
| ✅ 避免被动语气 | 不要用"用于..."、"可以..."，要用"当...时使用" | ❌"用于创建插件" → ✅"当用户需要创建插件时使用" |
| ✅ 包含具体触发词 | 列出用户实际会说的短语 | "从零创建"、"打包发布"、"安全审计" |

**自检方法：** 写完 description 后，用 `run_evals.py --type trigger` 测试触发率，should-trigger 的用例必须 100% 触发。

