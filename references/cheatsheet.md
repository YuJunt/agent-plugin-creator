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

### P0/P1/P2 脚本常用参数速查

> 以下为最常用的参数和示例，完整参数用 `--help` 查看。

#### P0 工程效率

| 脚本 | 关键参数 | 示例 |
|------|---------|------|
| `test_mcp_tools.py` | `--command` `--args` `--timeout` `--skip-tools` `--json` | `python3 test_mcp_tools.py --command python3 --args server.py --timeout 10` |
| `update_plugin.py` | `plugin_dir` `--bump-version {patch,minor,major}` `--add-skill` `--remove-skill` `--add-mcp-tool` `--force` | `python3 update_plugin.py ./my-plugin --bump-version minor --force` |
| `reverse_engineer.py` | `server_dir` `--output` `--name` `--force` | `python3 reverse_engineer.py ./existing-server --output ./my-plugin --name my-plugin` |
| `score_plugin.py` | `plugin_dir` `--json` `--threshold` | `python3 score_plugin.py ./my-plugin --threshold 80` |
| `manage_deps.py` | `server_dir` `--check` `--generate` `--language {python,typescript,auto}` `--name` | `python3 manage_deps.py ./servers/api --check` |
| `auto_fix.py` | `plugin_dir` `--max-attempts` `--dry-run` `--force` | `python3 auto_fix.py ./my-plugin --max-attempts 3` |
| `build_all.py` | `--config` `--output` `--name` `--clients` `--skip-tests` `--skip-audit` `--json` | `python3 build_all.py --config config.json --output ./dist --name my-plugin` |
| `progress.py` | （作为模块导入使用） | `from progress import ProgressBar` |
| `export_config.py` | `plugin_dir` `--output` `--format {json,yaml}` | `python3 export_config.py ./my-plugin --output config.json` |

#### P1 质量与生态

| 脚本 | 关键参数 | 示例 |
|------|---------|------|
| `check_coverage.py` | `--threshold` `--output` `--json` | `python3 check_coverage.py --threshold 60` |
| `fuzz_test.py` | `--target` `--iterations` `--output` `--seed` | `python3 fuzz_test.py --target validate_plugin --iterations 50` |
| `benchmark_monitor.py` | `--baseline` `--compare` `--output` `--threshold` | `python3 benchmark_monitor.py --baseline` |
| `errors.py` | `--list` `--lookup CODE` `--category CAT` `--json` | `python3 errors.py --list` |
| `dockerize.py` | `plugin_dir` `--output` `--server` `--port` `--all` `--force` | `python3 dockerize.py ./my-plugin --output ./docker --all --force` |
| `publish_config.py` | `server_dir` `--type {pypi,npm}` `--output` `--version` `--github-actions` `--force` | `python3 publish_config.py ./servers/api --type pypi --version 1.0.0` |
| `vscode_extension.py` | `plugin_dir` `--output` `--publisher` `--force` | `python3 vscode_extension.py ./my-plugin --output ./vscode-ext --force` |
| `mcp_marketplace.py` | `plugin_dir` `--output` `--category` `--tags` `--force` | `python3 mcp_marketplace.py ./my-plugin --output marketplace.json` |
| `type_check.py` | `--strict` `--output` `--threshold` `--json` | `python3 type_check.py --strict --threshold 70` |

#### P2 安全与高级

| 脚本 | 关键参数 | 示例 |
|------|---------|------|
| `supply_chain_scan.py` | `plugin_dir` `--severity {low,medium,high,critical}` `--output` `--json` | `python3 supply_chain_scan.py ./my-plugin --severity high` |
| `generate_sbom.py` | `plugin_dir` `--format {cyclonedx,spdx,both}` `--output` `--force` | `python3 generate_sbom.py ./my-plugin --format both --output sbom.json` |
| `sign_plugin.py` | `plugin_dir` `--sign` `--verify` `--key` `--output` | `python3 sign_plugin.py ./my-plugin --sign --key my-secret` |
| `analyze_plugin.py` | `plugin_dir` `--output` `--json` `--depth {quick,deep}` | `python3 analyze_plugin.py ./my-plugin --depth deep` |
| `combine_plugins.py` | `plugin1 plugin2 ...` `--output` `--name` `--version` `--force` `--json` | `python3 combine_plugins.py ./p1 ./p2 --output ./combined --name super-plugin` |
| `migrate_version.py` | `plugin_dir` `--to {1.0.0,1.1.0}` `--dry-run` `--force` | `python3 migrate_version.py ./my-plugin --to 1.1.0` |
| `eval_driven_dev.py` | `generate-evals\|run\|report` `--plugin` `--evals` `--output` | `python3 eval_driven_dev.py run --plugin ./my-plugin --evals evals.json` |
| `best_practices.py` | `list\|check\|apply` `--plugin` `--category` `--json` | `python3 best_practices.py check --plugin ./my-plugin` |
| `i18n_helper.py` | `init\|extract\|validate` `--plugin` `--locales` `--output` | `python3 i18n_helper.py init --plugin ./my-plugin --locales en,zh,ja` |
| `health_check.py` | `plugin_dir` `--output` `--json` `--threshold` | `python3 health_check.py ./my-plugin --threshold 80` |

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

---

# Gotchas（踩过的坑）
# Gotchas（踩过的坑）

> 这些是开发过程中实际踩过的坑，每个都有症状→修正→原因。遇到对应情况必须按修正做。

## Gotchas（踩过的坑，最高优先级）

> 这些是开发过程中实际踩过的坑，每个都有**症状→修正→原因**。遇到对应情况必须按修正做。

### 1. MCP 服务器写完再验，结果全是错
- **症状**：写完所有 MCP 工具代码后运行，握手失败、工具不响应、协议解析错误，不知道哪里出问题
- **修正**：生成 MCP 服务器后**立即跑 `test_mcp_handshake.py`**，跑不通就停下来修，不要继续往下写。每加一个工具就验一次。
- **原因**：MCP 协议对 stdout/stderr 分离、JSON-RPC 格式要求严格，早期错误会被后续代码掩盖，越早发现越容易定位。

### 2. stdio 服务器打印调试信息到 stdout
- **症状**：MCP 握手失败，报 "Invalid JSON-RPC response" 或 "Unexpected token"，但代码看起来没问题
- **修正**：所有调试信息必须打到 `stderr`（`print(..., file=sys.stderr)`），stdout 是 JSON-RPC 专用通道，不能有任何额外输出。
- **原因**：stdio 传输模式下，stdout 的每一行都会被客户端当作 JSON-RPC 响应解析，调试信息会破坏协议格式。

### 3. mcp.json 的 command 写成 shell 字符串
- **症状**：`validate_plugin.py` 报错 "command must be a single executable token"，或客户端启动服务器失败
- **修正**：`command` 必须是单个可执行文件名（如 `python3`、`node`），参数放在 `args` 数组里。禁止 `bash -c "..."` 或带空格的命令。
- **原因**：Agent Plugins 规范要求 command 是单一可执行 token，防止 shell 注入和跨平台兼容性问题。

### 4. mcp.json 里的路径不以 ./ 开头
- **症状**：`validate_plugin.py` 报路径安全错误，或客户端找不到服务器文件
- **修正**：`command` 如果含 `/`（绝对路径或子目录），必须以 `./` 开头（如 `./bin/server`）。插件内所有相对路径都以 `./` 开头。
- **原因**：路径安全检查防止路径穿越攻击，`./` 前缀明确表示"插件根目录内"，避免被解析为系统路径。

### 5. wizard 生成的骨架直接当成品用
- **症状**：生成的插件 SKILL.md 里全是"第一步/第二步"占位符，description 没有触发词，技能永远不触发
- **修正**：wizard 生成的是**骨架不是成品**。必须重写 SKILL.md 的 description（含三要素：做什么+什么时候用+触发词）、工作流步骤、Gotchas。
- **原因**：wizard 只负责生成目录结构和占位内容，业务逻辑和触发场景只有用户知道，无法自动生成。

### 6. 反向封装后用 validate_plugin 验证
- **症状**：`plugin_to_skill.py` 生成的产物用 `validate_plugin.py` 验证，报"缺少 plugin.json"
- **修正**：反向封装生成的是**普通 Skill**（无 plugin.json），要用 `validate_skill.py` 验证，不是 `validate_plugin.py`。
- **原因**：反向封装的目的就是把 Plugin 转成不支持 Plugin 的平台也能用的 Skill，结构自然不同。

### 7. audit_plugin 没检出动态调用的危险代码
- **症状**：代码里有 `getattr(os, "system")(cmd)` 或 `eval(__import__('base64').b64decode(...))`，但 audit_plugin 没报
- **修正**：audit_plugin 基于正则，**不能检出动态调用、混淆字符串、嵌套导入**。高危插件需要人工代码审查，不能只依赖自动化审计。
- **原因**：静态正则分析无法处理运行时动态解析的代码，这是所有静态分析工具的共同局限。

### 8. 反向封装的输出目录名与 skill name 不一致
- **症状**：`plugin_to_skill.py --output ./my-skill` 生成后，`validate_skill.py` 报"目录名与 skill name 不一致"
- **修正**：`--output` 目录名必须和生成的 skill name 一致（插件名中的点会转成连字符）。用 `--json` 输出查看生成的 skill_name，再指定对应目录名。
- **原因**：agentskills.io 规范要求 skill 目录名与 frontmatter 的 name 字段完全一致，这是平台发现技能的依据。

### 9. 插件包含 hooks/commands/agents 等非便携组件
- **症状**：把旧客户端插件的 hooks、commands、自定义 agent 塞进 plugin.json，`validate_plugin.py` 报"未知顶层字段"
- **修正**：便携核心只包含 skills/ + mcp.json + servers/。hooks、commands、agents、LSP、UI 等客户端专属组件放在 `com.<client>/` 扩展目录里，或用 `client_adapter.py` 生成。
- **原因**：Agent Plugins 规范的便携核心刻意限制了组件类型，确保跨客户端可移植；客户端专属能力通过扩展机制提供。


---

# 错误码手册
# 错误码系统参考手册

> 本文档列出 agent-plugin-creator 所有标准化错误码（共 31 个），按类别分组。
> 运行 `python3 scripts/errors.py --list` 获取最新列表，`python3 scripts/errors.py --lookup E1001` 查询单个错误码。

## 错误码命名规则

- 格式：`E` + 4位数字（如 `E1001`）
- 千位表示类别：
  - `1xxx`：输入/参数错误
  - `2xxx`：规范/验证错误
  - `3xxx`：安全错误
  - `4xxx`：MCP 错误
  - `5xxx`：构建/发布错误
  - `6xxx`：外部依赖/环境错误
  - `9xxx`：内部/未知错误

---

## 1xxx — 输入/参数错误（7 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E1001 | 无效参数 | 检查命令行参数是否正确，用 `--help` 查看用法 |
| E1002 | 缺少必需参数 | 查看 `--help` 获取完整参数列表，补充缺失参数 |
| E1003 | 路径无效 | 检查文件/目录路径是否存在且可访问 |
| E1004 | 文件不存在 | 确认文件路径正确，或先创建该文件 |
| E1005 | 目录不存在 | 确认目录路径正确，或先创建该目录 |
| E1006 | JSON 格式无效 | 检查 JSON 语法，使用 `python3 -m json.tool` 或 jsonlint 验证 |
| E1007 | 名称不符合规范 | 名称只能包含 Unicode 小写字母、数字、连字符（不允许点/大写/特殊字符） |

## 2xxx — 规范/验证错误（6 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E2001 | 验证失败 | 运行 `python3 scripts/validate_plugin.py <插件目录>` 查看详细错误 |
| E2002 | Schema 版本不匹配 | 确保 plugin.json 和 mcp.json 的 `$schema` 版本一致（都为 1.0.0 或都为 1.1.0） |
| E2003 | 缺少必需字段 | 检查规范文档，补充 plugin.json 的 `name`、`$schema` 等必需字段 |
| E2004 | 未知字段 | plugin.json 只允许规范定义的字段，自定义字段移到 `extensions` 下或客户端扩展目录 |
| E2005 | 名称与目录不一致 | plugin name 必须与插件目录名完全一致；skill name 必须与 skill 目录名一致 |
| E2006 | 路径不安全 | 插件内所有相对路径必须以 `./` 开头，不能包含 `../` 逃逸出插件根目录 |

## 3xxx — 安全错误（4 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E3001 | 安全审计失败 | 运行 `python3 scripts/audit_plugin.py <插件目录> --severity high` 查看详细问题 |
| E3002 | 检测到硬编码密钥 | 将 API key、密码、token 移到环境变量或客户端配置中，不要写在代码里 |
| E3003 | 检测到危险代码 | 移除 `eval()`、`exec()`、`shell=True`、`os.system()`、`pickle.loads()` 等危险调用 |
| E3004 | 路径穿越风险 | 检查文件操作路径，防止用户输入构造 `../` 逃逸出预期目录 |

## 4xxx — MCP 错误（4 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E4001 | MCP 握手失败 | 检查服务器启动命令和参数，确保 stdio 传输正确，调试信息打到 stderr 而非 stdout |
| E4002 | MCP 工具调用失败 | 检查工具名称和参数是否正确，用 `test_mcp_tools.py` 逐个验证工具 |
| E4003 | MCP 服务器不存在 | 检查 mcp.json 中的服务器配置，确认 command/args 路径正确 |
| E4004 | 无效的 MCP 传输类型 | 支持 `stdio`（本地子进程）和 `streamable-http`（远程 HTTP），不支持其他类型 |

## 5xxx — 构建/发布错误（4 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E5001 | 构建失败 | 检查构建日志，修复编译/类型错误后重试 |
| E5002 | 打包失败 | 检查插件结构，确保 plugin.json 等必需文件存在，用 `validate_plugin.py` 验证 |
| E5003 | 缺少依赖 | 运行 `python3 scripts/manage_deps.py <server_dir> --check` 检查并安装缺失依赖 |
| E5004 | 版本冲突 | 检查 plugin.json、CHANGELOG.md、provenance.json 的版本号是否一致 |

## 6xxx — 外部依赖/环境错误（4 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E6001 | 外部工具执行失败 | 检查外部工具（如 docker、npm、git）是否安装且可执行 |
| E6002 | Git 操作失败 | 检查 Git 状态、权限和远程仓库配置，确保有推送权限 |
| E6003 | 网络错误 | 检查网络连接和代理设置，确认目标地址可访问 |
| E6004 | 操作超时 | 增加 `--timeout` 参数，或检查目标服务是否响应 |

## 9xxx — 内部/未知错误（2 个）

| 错误码 | 名称 | 修复建议 |
|--------|------|---------|
| E9001 | 内部错误 | 这可能是技能本身的 bug，请在 GitHub 提交 issue 并附上复现步骤 |
| E9999 | 未知错误 | 查看详细错误信息和堆栈跟踪，根据具体内容排查 |

---

## 使用示例

```bash
# 列出所有错误码
python3 scripts/errors.py --list

# 查询单个错误码
python3 scripts/errors.py --lookup E3002

# 按类别筛选
python3 scripts/errors.py --category security

# JSON 格式输出（便于脚本解析）
python3 scripts/errors.py --list --json
```

## 错误码与脚本对应关系

| 脚本 | 主要可能触发的错误码 |
|------|---------------------|
| `validate_plugin.py` | E2001-E2006, E1006 |
| `validate_skill.py` | E2001, E2005, E1007 |
| `audit_plugin.py` | E3001-E3004 |
| `test_mcp_handshake.py` | E4001, E4003, E6004 |
| `test_mcp_tools.py` | E4002, E4001 |
| `benchmark_mcp.py` | E4001, E4002, E6004 |
| `package_plugin.py` | E5002, E2001 |
| `build_release.py` | E5001, E5002 |
| `create_mcp_server.py` | E1001, E1006, E5003 |
| `wizard.py` | E1001-E1007, E2001 |
| `dockerize.py` | E6001, E5001 |
| `manage_deps.py` | E5003, E1003 |
