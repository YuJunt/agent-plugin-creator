# Changelog

## [2.5.0] - 2026-09-27

### 专业度提升（5 大优化，全部是整合优化不是加功能）

1. **消除代码重复** 🧹
   - 新增 `scripts/_common.py` 共享模块
   - 提取 `load_plugin_json()`、`load_mcp_json()`、`print_header()`、`print_footer()`、`error_exit()`、`detect_plugin_dir()` 等通用函数
   - 3 个脚本（client_adapter/generate_docs/package_plugin）改用共享模块，减少重复代码 ~100 行

2. **统一错误处理** 🎯
   - 核心入口 `plugin.py` 改用 `errors.py` 统一错误码系统（31 个标准化错误码）
   - 验证链失败时根据失败步骤自动选择错误码（验证失败/安全审计失败/MCP握手失败/构建失败）
   - 错误输出格式统一：`[EXXXX] 错误类型: 详细描述` + `建议: 修复建议` + `调试: 具体命令`

3. **验证失败自动修复建议** 🔧
   - `validate_plugin.py` 新增 `fix` 参数，常见错误直接给出修复方法
   - 覆盖 5 类常见错误：name 不一致、缺少 $schema、缺少 name、schema 版本不一致、缺少 SKILL.md
   - 输出格式：`🔧 自动修复建议 (N 项):` + 每条错误的具体修复命令

4. **plugin.py 智能默认值** 🧠
   - 所有需要 plugin 参数的命令改为可选（`nargs="?"`）
   - 不指定路径时自动检测当前目录是否有 plugin.json
   - 检测成功显示：`📂 自动检测到插件目录: /path/to/plugin`
   - 检测失败使用统一错误码提示，不再是生硬的参数错误
   - 用户体验：在插件目录内直接运行 `plugin.py validate` 即可，不用再输路径

5. **端到端集成测试** ✅
   - 新增 `tests/test_e2e.py`，14 个集成测试用例
   - 覆盖完整工作流：创建 → 验证 → 审计 → 冒烟 → 生成文档 → 打包
   - 覆盖 plugin.py 统一入口：validate/audit/smoke/智能默认值
   - 覆盖错误处理：无效 JSON/缺少文件/name 不一致/智能默认值失败
   - 总测试数从 25 个增加到 **39 个**，全部通过

### 验证结果
- 回归测试：39/39 通过（新增 14 个集成测试）
- 质量检查：91.7 分（A+）
- SKILL.md：300 行（保持精简）
- 自动修复建议：实测正常输出
- 智能默认值：实测自动检测正常
- 统一错误码：实测格式统一

## [2.4.1] - 2026-09-27

### 做减法精简（避免无脑做加法导致臃肿）

基于用户反馈"多轮优化是不是变成了无脑做加法"，进行系统性精简：

1. **触发路由精简**（141 行 → 58 行）
   - 保留核心决策流程（5 步）、路由分类表（5 类）、风险分级表（3 级）
   - 详细映射表（渐进式披露/门禁/Gotchas/输出格式）移到 `references/advanced.md`

2. **Gotchas 合并精简**（60 行 → 25 行）
   - 保留失败模式速查表（7 项）和 3 个核心技术坑
   - LLM 特有失败模式（4 项）移到 `references/advanced.md`
   - 技术坑格式统一为 `### 坑 N：`（兼容质量检查脚本）

3. **同义词清单移走**（15 行 → 0 行）
   - description 优化检查清单（7 项）移到 `references/advanced.md`

4. **评估脚本统一入口**（4 个 → 1 个入口 + 3 个内部模块）
   - 新增 `run_evals.py --type {trigger|selection|edge|all}` 统一入口
   - 删除 `run_all_evals.py`（功能被 `--type all` 替代）
   - 保留三个内部模块（避免单文件 600+ 行臃肿）

5. **工作流程精简**（51 行 → 28 行）
   - 从"10 步"改为"3 阶段"（创建/验证+调试/发布）
   - 详细步骤本来就在 `references/workflows.md`

### 结果
- SKILL.md：456 行 → **300 行**（-34%）
- 质量分：83.3 → **91.7（A+）**
- 功能：一个都没丢，只是把文档移到该去的地方
- 回归测试：25/25 通过
- 三种评估：100% 通过

## [2.4.0] - 2026-09-27

### 基于 7 大功能深度调研的 4 大优化

1. **编排脚本加入并行执行** ⚡
   - validate 和 audit 没有依赖关系，并行执行
   - 两阶段执行：阶段1并行（validate ∥ audit）→ 阶段2串行（smoke + 额外检查）
   - 预期耗时减少 30-40%
   - 基于 DAG（有向无环图）依赖管理思想

2. **Gotchas 加入 LLM 特有失败模式** 🎭
   - Confabulation（虚构）：AI 自信报告完成但实际没做 → 必须用脚本验证
   - Empty write（空写）：AI 说写了文件但实际是空的 → 必须检查行数和 TODO
   - Silent failure（静默失败）：工具调用报错但 AI 忽略 → 必须检查退出码
   - Accept-and-forget（接受即忘）：看起来对就接受不验证 → 必须抽样验证
   - 核心原则：不要相信 AI 的"已完成"声明，只相信脚本的验证结果

3. **硬门禁加入审计记录** 📝
   - 每次验证链执行后写 `verification-audit.json`
   - 记录：时间戳、插件路径、门禁级别、各步骤详情（脚本/参数/退出码/耗时）、总耗时、结果
   - 基于业界最佳实践：每个门禁执行必须产生审计记录

4. **Prompt 设计加入同义词检查清单** 📋
   - 7 项检查：动作同义词、对象同义词、场景同义词、中英文双语、动词范围、避免被动语气、包含具体触发词
   - 自检方法：写完 description 后用 `run_trigger_eval.py` 测试触发率
   - 基于业界最佳实践：description 是触发器，用户说什么就要有什么

### 验证
- 并行执行实测正常（两阶段输出清晰）
- 审计记录实测生成（JSON 格式完整）
- 回归测试 25/25 通过
- 质量检查 91.7 分（A+）

## [2.3.0] - 2026-09-27

### 重大升级：触发路由从"分类器"升级为"编排器大脑"

基于联网深度调研（Supervisor Pattern、Context-Aware Routing、Decision Tree），触发路由不再只是简单分类，而是构建完整执行计划，串联 7 大功能模块。

**新增 4 大路由驱动能力：**

1. **路由驱动渐进式披露** 📚
   - 根据场景只加载相关 references，避免注意力稀释
   - 创建插件 → workflows.md + cheatsheet.md
   - 验证/审计 → plugin-specification.md + quality.md
   - MCP 开发 → mcp-server-guide.md + cheatsheet.md
   - 迁移 → advanced.md
   - 质量评分 → quality.md

2. **路由驱动门禁级别** 🔒
   - 日常检查（低风险）→ standard 门禁
   - 打包发布（中风险）→ strict 门禁
   - 公开发布（高风险）→ critical 门禁

3. **路由驱动 Gotchas 展示** ⚠️
   - MCP 开发 → 展示坑1、坑2、坑4
   - 反向封装 → 展示坑5
   - wizard 创建 → 展示坑3
   - 打包发布 → 坑3 + 失败模式速查表

4. **路由决策可观测性** 🔍
   - 每次执行前输出完整路由决策轨迹
   - 包含：意图、分类、置信度、风险、门禁、上下文、Gotchas、输出格式、预计步骤
   - 避免黑箱操作，出问题可回溯

**新增：上下文感知（Context-Aware Routing）**
- 路由前检查项目状态（已有 plugin.json / skills/ / mcp.json）
- 上下文影响路由决策（用户说"验证"但目录为空 → 可能需要先创建）

**路由决策流程从 4 步升级为 5 步：**
1. 意图分析 → 2. 上下文感知 → 3. 分类+置信度+风险 → 4. 构建执行计划 → 5. 透明通信

### 验证
- 质量检查 91.7 分（A+）
- 回归测试 25/25 通过
- 三级门禁实测正常
- 路由决策轨迹格式正确

## [2.2.0] - 2026-09-27

### 新功能（基于联网深度调研的 7 大功能高级用法）

1. **触发路由加入风险分级** 🟢🟡🔴
   - 低风险（只读）：自动执行，无需确认
   - 中风险（有副作用但可逆）：执行前告知，可直接执行
   - 高风险（不可逆/高影响）：必须用户明确确认
   - 高风险操作包括：--force 覆盖、公开发布、修改核心文件、可能数据丢失

2. **硬门禁升级为三级门禁** 🔒
   - Standard（标准）：validate + audit + smoke（日常开发）
   - Strict（严格）：+ 质量评分 + MCP 握手测试（发布前）
   - Critical（关键）：+ 发布审计 + 完整评估（公开发布）
   - `plugin.py package --gate {standard|strict|critical}`

3. **编排脚本加入重试机制** 🔄
   - 临时失败自动重试（指数退避：1s → 2s，最多 2 次）
   - 幂等性保证：重试不会产生重复副作用
   - 只对允许重试的步骤（质量评分、握手测试等）重试

4. **Gotchas 加入失败模式速查表** 📋
   - 8 个常见问题的 Issue | Recovery 表格
   - 快速定位问题和恢复方法
   - 与现有 5 个结构化坑互补

### 验证
- 三级门禁实测：Standard 通过，Strict 正确阻止质量不达标插件
- 重试机制实测：失败后自动重试 2 次（指数退避）
- 回归测试 25/25 通过
- 质量检查 91.7 分（A+）

## [2.1.1] - 2026-09-27

### Bug 修复
- **修复 smoke_test.py 参数错误**: plugin.py 调用 smoke_test.py 时使用了 `--plugin` 参数，但 smoke_test.py 实际是位置参数，导致通过 plugin.py smoke 命令时报错。已修复为位置参数。

### 验证
- 5 大场景端到端实测全部通过（最简纯Skill / Skill+Python MCP / 多Skill复杂插件 / 反向封装 / 边界情况）
- 回归测试 25/25 通过
- 质量检查 91.7 分（A+）

## [2.1.0] - 2026-09-27

### 重大变更
- **触发路由重大升级**: 从简单分类升级为完整的 4 步路由决策系统（意图分析 → 路由分类 → 置信度评估 → 透明通信）
- **插件模板升级**: 用本技能创建的每个插件里的 Skill，都自带"触发与路由"决策表（什么情况走什么路径）
- **7 大功能全覆盖**: 联网深度调研业界最佳实践，确认 7 大功能完整覆盖技能工作流
- **插件层面 7 大功能**: 明确区分开发时功能（硬门禁/检验脚本由技能提供）和运行时功能（渐进式披露/触发路由/Gotchas/Prompt 设计由插件自带）

### 改进
- 触发路由加入置信度评估：≥80%直接做，60-80%确认，<60%问澄清
- 中英文模板同步升级，从"触发场景"升级为"触发与路由"
- 回归测试 25/25 通过
- 质量检查 91.7 分（A+）

## [2.0.0] - 2026-09-27

### 重大变更
- **无损精简**: 脚本从 36 个精简到 22 个（-39%），砍掉 14 个可有可无的脚本
- **文档合并**: references/ 从 9 个合并到 7 个，routing.md → advanced.md，versioning.md → quality.md
- **SKILL.md 优化**: 精简到 288 行（< 300 行），完整脚本速查表透明化所有功能
- **新增质量检查**: check_skill_quality.py 自动检查 Skill 质量（4 大类 12 项）
- **新增质量评分**: score_plugin.py 插件质量自动评分（6 维度加权）
- **自动级联验证**: plugin.py package 自动先跑 validate → audit → smoke，失败就中止
- **Yes-Man 防护**: --skip-verify 时显示警告 + 必须输入 yes 二次确认
- **可观测性**: 验证链增加 Trace 记录（每步耗时+状态+总耗时）

### 砍掉的 14 个脚本（都是可有可无的）
- 功能重复: quality_report.py, release_decision.py, build_release.py, analyze_skill_quality.py
- 太高级: mutation_test.py, performance_baseline.py
- 特定平台: generate_marketplace_json.py, generate_skillsh_metadata.py
- 一次性工具: migrate_mcp_v2.py
- 内部工具: detect_client.py, workflow_state.py
- 太细分: mcp_security_check.py, audit_progressive_disclosure.py, compare_skill_versions.py

### 验证
- 质量检查 100 分（A+）
- 回归测试 25/25 通过
- 核心工作流实测通过

## [1.9.0] - 2026-09-26

### 重大变更
- **references/ 整合**: 从 19 个文件精简到 9 个（-53%），按主题分类合并
- **新增评估汇总脚本**: `run_all_evals.py` 一键运行所有评估（触发/选择/边界）
- **修复参数一致性**: `smoke_test.py` 从 `--plugin` 改为位置参数，与其他脚本统一
- **SKILL.md 优化**: 精简到 201 行，符合渐进式披露专业标准

### 改进
- 评估准确率 100%（12/12 通过）
- 发布审计 PASS（0 错误）
- 回归测试 25/25 通过

## [1.8.0] - 2026-09-26

### 重大变更
- 新增统一入口 CLI（plugin.py）
- 明确核心工作流（6 步）
- 新增防臃肿守门人（anti-bloat-guardian.md）
- SKILL.md 分层：核心工作流 + 高级功能

## [1.7.0] - 2026-09-26

### 重大变更
- **激进精简**: 脚本从 73 个 → 30 个（-59%），清理技术债
- **新增**: MCP v1→v2 迁移辅助工具
- **新增**: 错误信息三要素标准化（Failure + Cause + Next Action）
- **新增**: 提示注入专项检测（OWASP MCP01-MCP03，15 种模式）
- **新增**: Vercel skills.sh 发布元数据生成
- **新增**: 渐进式披露 Token 预算审计
- **新增**: 客户端环境自动检测与推荐
- **新增**: Streamable HTTP 部署最佳实践文档
- **新增**: 变异测试 + 属性测试框架
- **新增**: 性能基准监控工具

### 移除
- 移除 43 个冗余/重复功能脚本
- 移除过时的 security_check.py（功能已合并到 audit_plugin.py）
- 移除重复的评估脚本（judge_trigger_eval, evaluate_plugin_artifact 等）
- 移除未在核心工作流中使用的边缘功能脚本

### 修复
- 修复 generate_docs.py 的 --force 参数支持
- 修复 release_audit.py 的必需文件列表
- 修复 performance_baseline.py 的 JSON 解析 bug

### 测试
- 单元测试: 25 个用例全部通过
- 端到端测试: 17 个场景，91% 通过率
- 性能基准: JSON 解析 4ms / 文件读取 220ms / 正则匹配 5ms

[1.7.0]: https://github.com/YuJunt/agent-plugin-creator/releases/tag/v1.7.0
