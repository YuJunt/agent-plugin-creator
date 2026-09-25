# Agent Plugin Creator 速查表与故障排除

> 本文件从 SKILL.md 拆出，供开发时快速查阅。主工作流见 SKILL.md。

## 目录
- [内嵌能力速查](#内嵌能力速查)
- [关键规则速查](#关键规则速查)
- [常见错误](#常见错误)
- [脚本故障排除](#脚本故障排除)
- [安全审计局限性](#安全审计局限性)

## 内嵌能力速查

| 能力 | 脚本 | 参考文档 | 模板 |
|------|------|---------|------|
| Skill 脚手架 | `scripts/init_skill.py` | `references/agent-skills-spec.md` | `assets/templates/skill/SKILL.md` |
| Skill 验证（对齐 skills-ref） | `scripts/validate_skill.py` | `references/agent-skills-spec.md` | — |
| MCP 服务器生成（tools/resources/prompts + add/list） | `scripts/create_mcp_server.py` | `references/mcp-server-guide.md` | `assets/templates/mcp-server/{typescript,python}/` |
| MCP 握手测试 | `scripts/test_mcp_handshake.py` | — | — |
| 插件组装验证 | `scripts/validate_plugin.py` | `references/plugin-specification.md` | `assets/templates/{plugin.json,mcp.json}` |
| Skill 质量评估 | `scripts/eval_skill.py` | `official/skill-creator/references/schemas.md` | — |
| 安全审计 | `scripts/audit_plugin.py` | — | — |
| 多客户端适配（检查/生成/编译） | `scripts/client_adapter.py` | — | — |
| 文档自动生成 | `scripts/generate_docs.py` | — | — |
| 打包发布 | `scripts/package_plugin.py` | — | — |
| 交互式创建向导 | `scripts/wizard.py` | — | — |
| 反向封装为 Skill | `scripts/plugin_to_skill.py` | — | — |
| 官方 skill-creator 工作流 | — | `official/skill-creator/SKILL.md` | — |
| 官方 mcp-builder 工作流 | — | `official/mcp-builder/SKILL.md` | — |
| 工具契约验证 | `scripts/validate_tool_contract.py` | `references/mcp-tool-contract.json` | — |
| 触发评估 | `scripts/run_trigger_eval.py` | `evals/evals.json` | — |
| 选择评估 | `scripts/run_selection_eval.py` | `references/evaluation-protocol.md` | — |
| 边界评估 | `scripts/run_edge_eval.py` | `references/evaluation-protocol.md` | — |
| 产物评估 | `scripts/evaluate_plugin_artifact.py` | `references/quality-gates.md` | — |
| 客户端一致性测试 | `scripts/run_client_conformance.py` | `references/client-conformance.md` | — |
| 失败边界测试 | `scripts/test_failure_boundaries.py` | `references/regression-matrix.md` | — |
| 官方语义测试 | `scripts/test_official_semantics.py` | `references/official-conformance-matrix.md` | — |
| 发现模拟 | `scripts/simulate_discovery.py` | — | — |
| 发布审计 | `scripts/release_audit.py` | `references/quality-gates.md` | — |
| 发布决策 | `scripts/release_decision.py` | `references/quality-gates.md` | — |
| 发布构建 | `scripts/build_release.py` | — | — |
| 修复计划生成 | `scripts/generate_repair_plan.py` | — | — |
| 质量报告 | `scripts/quality_report.py` | `references/quality-gates.md` | — |
| 远程 MCP 探测 | `scripts/probe_remote_mcp.py` | — | — |
| MCP 基准测试 | `scripts/benchmark_mcp.py` | — | — |
| 端到端示例 | — | `references/examples.md` | `examples/` |
| 官方 JSON Schema | — | `assets/schemas/1.0.0/` | — |

### P0 新增（工程效率）

| 能力 | 脚本 | 说明 |
|------|------|------|
| MCP 工具真实调用测试 | `scripts/test_mcp_tools.py` | 参数验证+返回结构+错误处理 |
| 插件增量更新 | `scripts/update_plugin.py` | 版本号+依赖+配置自动更新 |
| 从 MCP 代码反推插件 | `scripts/reverse_engineer.py` | 已有服务器代码→插件结构 |
| 插件质量评分器 | `scripts/score_plugin.py` | 6维度加权评分 |
| MCP 依赖管理 | `scripts/manage_deps.py` | 安装/更新/审计/锁定 |
| 验证失败自动修复 | `scripts/auto_fix.py` | 6类常见错误自动修复 |
| 一键全流程构建 | `scripts/build_all.py` | 验证→审计→打包→签名→发布 |
| 进度可视化模块 | `scripts/progress.py` | 可复用进度条 |
| 配置热加载 | `scripts/export_config.py` | 配置文件导出/导入 |

### P1 新增（质量与生态）

| 能力 | 脚本 | 说明 |
|------|------|------|
| 代码覆盖率报告 | `scripts/check_coverage.py` | pytest-cov+60%门禁 |
| 模糊测试 | `scripts/fuzz_test.py` | 12种畸形输入 |
| 性能基准监控 | `scripts/benchmark_monitor.py` | 历史对比+退化检测 |
| 统一错误码系统 | `scripts/errors.py` | 31个标准化错误码 |
| Docker 镜像生成 | `scripts/dockerize.py` | Dockerfile+compose |
| npm/pypi 发布配置 | `scripts/publish_config.py` | 包管理配置 |
| VS Code 扩展生成 | `scripts/vscode_extension.py` | 完整扩展骨架 |
| MCP 市场元数据 | `scripts/mcp_marketplace.py` | 自动分类+标签 |
| 类型注解检查 | `scripts/type_check.py` | mypy配置+覆盖率 |

### P2 新增（安全与高级）

| 能力 | 脚本 | 说明 |
|------|------|------|
| 供应链安全扫描 | `scripts/supply_chain_scan.py` | 25个已知漏洞包检测 |
| SBOM 生成 | `scripts/generate_sbom.py` | CycloneDX+SPDX双格式 |
| 插件数字签名 | `scripts/sign_plugin.py` | HMAC-SHA256签名+验证 |
| 插件深度分析器 | `scripts/analyze_plugin.py` | 4维度分析+改进建议 |
| 插件组合器 | `scripts/combine_plugins.py` | 多插件合并+冲突处理 |
| 版本迁移工具 | `scripts/migrate_version.py` | 1.0.0→1.1.0自动迁移 |
| 评估驱动开发 | `scripts/eval_driven_dev.py` | 先写评估再开发 |
| 最佳实践库 | `scripts/best_practices.py` | 6大类21条最佳实践 |
| 国际化框架 | `scripts/i18n_helper.py` | 多语言支持+翻译提取 |
| 插件健康诊断 | `scripts/health_check.py` | 4维度加权评分+体检 |

## 关键规则速查

| 规则 | 说明 |
|------|------|
| 唯一必需文件 | `plugin.json` |
| 幂等设计 | 所有生成操作默认不覆盖已有文件，使用 `--force` 才覆盖 |
| Skill name 规范 | 小写字母+数字+连字符（支持 Unicode 字母），max 64，与目录名一致（**不允许点**） |
| Plugin name 规范 | 小写字母+数字+连字符+点，max 64，与目录名一致 |
| Skill frontmatter 白名单 | 仅 `name`、`description`、`license`、`compatibility`、`metadata`、`allowed-tools` 6 个字段 |
| Skill 发现 | 仅 `skills/` 直接子目录，不递归，每个须含 `SKILL.md` |
| MCP 配置 | 独立的 `mcp.json`，不能内联到 plugin.json |
| 版本一致 | plugin.json 与 mcp.json 的 `$schema` 版本必须相同（1.0.0 或 1.1.0） |
| 无密钥 | mcp.json 的 headers 和 env 中不能嵌入凭据 |
| 路径安全 | 插件内相对路径以 `./` 开头，不逃逸出插件根目录 |
| 安全审计 | 发布前必须通过 audit_plugin.py，无 critical/high 问题 |
| MCP 握手 | 生成 MCP 服务器后必须用 test_mcp_handshake.py 实际验证 |

## 常见错误

1. **Skill name 用了点或大写** — agentskills.io 官方规范只允许小写字母+数字+连字符
2. **Skill frontmatter 含非白名单字段** — skills-ref 只允许 6 个字段，额外字段会报错
3. **MCP command 是 shell 字符串** — 必须是单个可执行 token，参数放 `args`
4. **mcp.json 版本不匹配** — 两个文件的 `$schema` 必须指向同一版本
5. **headers 中放 API key** — 凭据由客户端管理，不能写在配置里
6. **env 中设置 PLUGIN_ROOT/PLUGIN_DATA** — 这两个由客户端注入
7. **硬编码密钥在代码中** — audit_plugin.py 会检测到，必须使用环境变量
8. **使用 eval/exec 或 shell=True** — 安全审计会标记为 high/critical，必须避免
9. **parameters 格式错误** — 支持标准 JSON Schema（`{"type":"object","properties":{...}}`）和扁平格式，参数定义必须是对象

## 故障排除

### init_skill.py 失败
- **名称不合法**：确保 name 只含小写字母、数字、连字符，不以连字符开头/结尾，max 64 字符
- **目录已存在**：默认不覆盖，使用 `--force` 覆盖，或选择其他名称

### create_mcp_server.py 生成的代码编译失败
- **TypeScript**：确保已安装依赖 `npm install`，运行 `npx tsc --noEmit` 检查类型错误
- **Python**：确保已安装 `pip install fastmcp`，运行 `python -c "import fastmcp"` 验证
- **工具参数**：检查定义文件中的 parameters 是否为有效 JSON Schema（`{"type":"object","properties":{...}}`）

### test_mcp_handshake.py 握手失败
- **命令错误**：确保 `--command` 指向正确的可执行文件，TypeScript 需先编译
- **超时**：服务器启动慢时增加 `--timeout`（默认 10 秒）
- **stdio 问题**：确保服务器使用 stdio 传输，不要打印调试信息到 stdout（用 stderr）

### validate_plugin.py 报错
- **路径错误**：确保 mcp.json 中的 command/args 路径相对于插件根目录，以 `./` 开头
- **版本不匹配**：plugin.json 和 mcp.json 的 `$schema` 必须指向同一版本
- **缺少 SKILL.md**：skills/ 下每个子目录必须包含 SKILL.md

### validate_skill.py 报错
- **frontmatter 字段**：仅允许 name、description、license、compatibility、metadata、allowed-tools
- **name 与目录名不一致**：frontmatter 的 name 必须与 skill 目录名完全一致
- **description 为空**：description 必须非空，max 1024 字符

### client_adapter.py 问题
- **--build 输出目录已存在**：使用 `--force` 覆盖，或选择其他 `--output`
- **cursor 规则未生成**：确保插件有 skills/ 目录且每个 skill 含 SKILL.md
- **不支持的客户端**：使用 `--list-targets` 查看支持的平台列表

### package_plugin.py 问题
- **缺少 plugin.json**：插件根目录必须有 plugin.json
- **zip 包含不必要文件**：脚本自动排除 __pycache__、node_modules、.git 等
- **版本号**：使用 `--version` 指定，默认从 plugin.json 读取

### wizard.py 问题
- **交互式输入中断**：按 Ctrl+C 取消，不会生成部分文件
- **配置文件格式错误**：确保 JSON 有效，参考技能文档中的配置示例
- **输出目录已存在**：wizard 默认不覆盖，选择其他目录或手动删除

## 安全审计局限性

audit_plugin.py 基于正则匹配，能检出常见漏洞模式，但**不能检出**以下间接调用：

- `getattr(os, "system")("ls")` — 动态属性访问
- `eval("__import__('os').system('ls')")` — eval 嵌套导入
- `importlib.import_module("os").system("ls")` — 动态导入
- 混淆字符串拼接的命令（如 `"sys" + "tem"`）

## 修改已有插件

常见修改场景：

### 加一个新 Skill
1. `init_skill.py <新skill名> --path <临时目录>`
2. 写 SKILL.md，跑 `validate_skill.py`
3. 把目录移入 `skills/<新skill名>/`
4. 跑 `validate_plugin.py` 确认整体结构正确

### 加一个新 MCP 工具
1. `create_mcp_server.py add --project <servers/下的项目> --tool <工具定义JSON>`
2. 跑 `test_mcp_handshake.py` 确认新工具可用
3. 跑 `validate_plugin.py`

### 改 MCP 传输类型（stdio → streamable-http）
1. 修改 `servers/<name>/` 下的服务器代码（参考 `references/mcp-server-guide.md`）
2. 修改 `mcp.json`：删 command/args，加 url
3. 跑 `validate_plugin.py` 确认配置正确
4. 部署服务器后跑 `probe_remote_mcp.py` 验证连通性

## 调试 MCP 连接问题

按顺序排查：

1. **服务器能不能启动？**
   ```bash
   python3 servers/<name>/server.py
   ```
   如果立即退出，看 stderr 输出。

2. **握手能不能通？**
   ```bash
   python3 scripts/test_mcp_handshake.py --command "python3 servers/<name>/server.py"
   ```
   - 超时 → 服务器启动慢，增加 `--timeout`
   - BrokenPipeError → 服务器启动后立即退出，检查依赖

3. **工具能不能调用？**
   ```bash
   python3 scripts/benchmark_mcp.py --server servers/<name>/server.py --tool <工具名> --arguments '{}' --requests 1
   ```

4. **远程服务器能不能访问？**
   ```bash
   python3 scripts/probe_remote_mcp.py --url "https://your-server/mcp" --output probe.json
   ```

**建议**：安全审计是第一道防线，关键插件仍需人工审查代码，或使用专业 SAST 工具做深度分析。
