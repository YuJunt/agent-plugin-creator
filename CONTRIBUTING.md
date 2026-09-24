# Contributing to Agent Plugin Creator

感谢你对 Agent Plugin Creator 的关注！本指南说明如何参与贡献。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境](#开发环境)
- [代码规范](#代码规范)
- [测试要求](#测试要求)
- [提交规范](#提交规范)
- [版本管理](#版本管理)
- [发布流程](#发布流程)

## 行为准则

本项目采用 [Contributor Covenant](https://www.contributor-covenant.org/) 行为准则。参与即表示你同意遵守。

## 如何贡献

### 报告 Bug

请在 Issue 中包含：

1. **环境信息**：操作系统、Python 版本、使用的客户端（Claude Code/Cursor/豆包等）
2. **复现步骤**：精确的命令和输入
3. **预期行为**：你期望发生什么
4. **实际行为**：实际发生了什么（包含完整错误输出）
5. **技能版本**：`provenance.json` 中的 version 字段

### 提交功能请求

请说明：

1. **使用场景**：你遇到了什么问题
2. **期望功能**：你希望如何解决
3. **替代方案**：你考虑过的其他方案

### 提交 Pull Request

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'feat: add your feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

## 开发环境

### 前置要求

- Python 3.9+
- Node.js 18+（用于 TypeScript MCP 服务器测试）
- 无外部 Python 依赖（全部使用标准库）

### 本地设置

```bash
# 克隆仓库
git clone https://github.com/your-org/agent-plugin-creator.git
cd agent-plugin-creator

# 验证环境
python3 --version  # 3.9+

# 运行全量测试
bash scripts/run_all_tests.sh  # 如存在
# 或手动运行
python3 scripts/validate_skill.py .
python3 scripts/release_audit.py .
python3 official/skill-creator/scripts/quick_validate.py .
```

### 目录结构

```
agent-plugin-creator/
├── SKILL.md                    # 主技能文件（<500行，渐进式披露）
├── plugin.json                 # 插件清单（如作为插件分发）
├── CHANGELOG.md                # 版本历史
├── LICENSE.txt                 # MIT 许可证
├── provenance.json             # 发布元数据（版本唯一来源）
├── scripts/                    # 29个 Python 脚本
│   ├── init_skill.py           # Skill 脚手架
│   ├── create_mcp_server.py    # MCP 服务器生成
│   ├── validate_plugin.py      # 插件验证
│   ├── validate_skill.py       # Skill 验证
│   ├── audit_plugin.py         # 安全审计
│   ├── wizard.py               # 交互式向导
│   ├── plugin_to_skill.py      # 反向封装
│   ├── client_adapter.py       # 多客户端适配
│   └── ...                     # 其他脚本
├── references/                 # 详细参考文档
│   ├── cheatsheet.md           # 速查表
│   ├── versioning.md           # 版本管理规范
│   ├── quick-start.en.md       # 英文快速开始
│   └── ...
├── assets/                     # 模板和资源
│   ├── templates/              # skill/mcp/plugin 模板
│   └── schemas/                # JSON Schema
├── official/                   # 内嵌官方资源
│   ├── skill-creator/          # Anthropic 官方 skill-creator
│   └── mcp-builder/            # Anthropic 官方 mcp-builder
├── evals/                      # 评估用例
│   └── evals.json              # 5个评估场景
└── examples/                   # 5个示例插件
```

## 代码规范

### Python 代码

- **风格**：PEP 8，使用 4 空格缩进
- **类型注解**：所有公共函数必须有类型注解
- **文档字符串**：所有公共函数必须有 docstring
- **错误处理**：使用 `sys.exit(code)` 而非 `raise SystemExit`
- **参数解析**：必须使用 `argparse`，所有脚本必须支持 `--help`
- **资源管理**：文件操作使用 `with`，subprocess 使用 `run()` 或 `Popen + finally`
- **无外部依赖**：仅使用 Python 标准库，不引入第三方包
- **幂等设计**：所有生成操作默认不覆盖已有文件，使用 `--force` 才覆盖

### SKILL.md 规范

- **行数**：主文件 < 500 行（渐进式披露）
- **frontmatter**：仅使用官方白名单字段（name/description/license/compatibility/metadata/allowed-tools）
- **description**：包含中英文触发词，< 1024 字符
- **Gotchas**：必须有 Gotchas section，这是最重要的部分
- **不要 railroad**：提供多条路径（路径 A/B/C），不强制单一流程
- **不要陈述显而易见的事**：聚焦于容易出错的地方

### 测试规范

- 新增脚本必须有对应的测试场景
- 修改脚本必须运行全量回归测试
- 测试必须使用临时目录，不污染用户环境
- 测试退出码：0=通过，非0=失败

## 测试要求

提交 PR 前必须通过以下测试：

```bash
# 1. 语法检查
python3 -m py_compile scripts/*.py

# 2. 技能验证
python3 scripts/validate_skill.py .

# 3. 官方验证
python3 official/skill-creator/scripts/quick_validate.py .

# 4. 发布审计
python3 scripts/release_audit.py .

# 5. 评估用例
python3 scripts/run_trigger_eval.py --skill . --output /tmp/trigger.json
python3 scripts/run_selection_eval.py --skill . --output /tmp/selection.json

# 6. 示例插件验证
for ex in examples/*/; do
  python3 scripts/validate_plugin.py "$ex"
done

# 7. 所有脚本 --help
for f in scripts/*.py; do python3 "$f" --help >/dev/null 2>&1 || echo "FAIL: $f"; done
```

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）：**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具/依赖

**范围（scope）：**
- `skill`: SKILL.md 相关
- `script`: 脚本相关
- `template`: 模板相关
- `doc`: 文档相关
- `eval`: 评估相关
- `example`: 示例相关

**示例：**
```
feat(script): add --help to 8 CLI scripts

Add argparse to build_release, evaluate_plugin_artifact,
generate_repair_plan, judge_trigger_eval, quality_report,
release_audit, release_decision, validate_tool_contract.

Closes #123
```

## 版本管理

遵循 [Semantic Versioning](https://semver.org/)：

- **MAJOR** (x.0.0): 不兼容的 API 变更
- **MINOR** (1.x.0): 向下兼容的功能新增
- **PATCH** (1.0.x): 向下兼容的问题修正

**版本号唯一来源**：`provenance.json` 的 `version` 字段

**三处必须同步更新**：
1. `SKILL.md` 头部 `> **版本**: vX.Y.Z`
2. `provenance.json` 的 `version` 字段
3. `CHANGELOG.md` 顶部新增条目

**版本一致性检查**：`release_audit.py` 会自动验证三处一致

详见 `references/versioning.md`。

## 发布流程

### 发布前检查清单

- [ ] 所有测试通过
- [ ] `release_audit.py` 返回 PASS
- [ ] 版本号三处一致
- [ ] CHANGELOG.md 已更新
- [ ] 示例插件全部验证通过
- [ ] 评估用例准确率 100%
- [ ] 无硬编码密钥
- [ ] 无 `__pycache__` 或临时文件

### 发布步骤

```bash
# 1. 运行发布审计
python3 scripts/release_audit.py .

# 2. 构建发布包
python3 scripts/build_release.py . dist/agent-plugin-creator-vX.Y.Z.zip

# 3. 发布决策
python3 scripts/release_decision.py . dist/

# 4. 打标签
git tag vX.Y.Z
git push origin vX.Y.Z
```

## 常见问题

**Q: 可以添加第三方 Python 依赖吗？**
A: 不可以。本技能设计为零依赖，所有功能必须用标准库实现。

**Q: 可以修改 official/ 目录下的文件吗？**
A: 不可以。official/ 是 Anthropic 官方资源的快照，如需更新请同步官方仓库。

**Q: 新增脚本需要做什么？**
A: 添加 argparse --help、类型注解、docstring、测试场景，并在 SKILL.md 的能力速查表中登记。

**Q: SKILL.md 超过 500 行怎么办？**
A: 将详细内容下沉到 references/，主文件只保留工作流和决策逻辑。

## 联系

- Issue: GitHub Issues
- 讨论: GitHub Discussions
