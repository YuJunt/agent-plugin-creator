# 常见问题 (FAQ)

## 通用问题

### Q: Agent Plugin Creator 是什么？
A: 一个用于创建符合 Agent Plugins 1.0.0 规范的可移植插件包的工具。它自包含了官方 Agent Skills 创建能力和 MCP SDK 服务器创建能力，不依赖目标平台已有这些工具。

### Q: 支持哪些客户端？
A: 目前支持 6 个客户端：
- Claude Code
- Cursor
- GitHub Copilot
- OpenAI Codex
- Google Gemini
- 豆包 (Doubao)

### Q: 需要安装什么依赖？
A: 核心脚本**零第三方依赖**，仅需要 Python 3.9+。如果要创建 TypeScript MCP 服务器，需要 Node.js 18+。

### Q: 如何安装？
A: 参见 [INSTALL.md](https://github.com/YuJunt/agent-plugin-creator/blob/main/INSTALL.md)，支持 7 个平台的安装指南。

## 使用问题

### Q: 交互式向导和命令行有什么区别？
A:
- **交互式向导** (`wizard.py`)：通过问答引导创建，适合新手
- **命令行**：更灵活，适合高级用户和自动化脚本

### Q: 创建的插件如何验证？
A: 使用 `validate_plugin.py` 验证插件结构，使用 `audit_plugin.py` 进行安全审计。

```bash
python3 scripts/validate_plugin.py ./my-plugin
python3 scripts/audit_plugin.py ./my-plugin --severity high
```

### Q: 什么是反向封装？
A: 反向封装 (`plugin_to_skill.py`) 是将 Agent Plugin 转换为普通 Skill 的功能，用于不支持 Agent Plugin 标准的平台。转换后，子技能需要 AI 主动读取，MCP 服务器需要手动启动。

### Q: 如何打包发布？
A: 使用 `package_plugin.py`：

```bash
python3 scripts/package_plugin.py ./my-plugin --output dist --version 1.0.0
```

## 安全问题

### Q: 为什么不能在 mcp.json 中硬编码密钥？
A: mcp.json 会被分发给用户，硬编码密钥会导致密钥泄露。应该使用环境变量引用，由客户端管理密钥。

### Q: 如何报告安全漏洞？
A: 请通过 [Security Advisories](https://github.com/YuJunt/agent-plugin-creator/security/advisories) 私下报告，不要公开创建 Issue。参见 [SECURITY.md](https://github.com/YuJunt/agent-plugin-creator/blob/main/SECURITY.md)。

## 开发问题

### Q: 如何贡献代码？
A: 参见 [CONTRIBUTING.md](https://github.com/YuJunt/agent-plugin-creator/blob/main/CONTRIBUTING.md)。请先创建 Issue 讨论，再提交 PR。

### Q: 版本号如何管理？
A: 遵循 [Semantic Versioning](https://semver.org/)，版本号唯一来源是 `provenance.json`。参见 [references/versioning.md](https://github.com/YuJunt/agent-plugin-creator/blob/main/references/versioning.md)。

### Q: CI 包含哪些检查？
A: CI 包含 9 个 Job：
- Skill Validation
- Evaluation Tests
- Example Plugins Validation ×4
- Security Audit
- Official Conformance Tests
- Version Consistency

### Q: 如何运行本地测试？
A:

```bash
# 技能验证
python3 scripts/validate_skill.py .

# 官方验证
python3 official/skill-creator/scripts/quick_validate.py .

# 发布审计
python3 scripts/release_audit.py .

# 安全检查
python3 scripts/security_check.py .

# 性能基准
python3 scripts/benchmark.py --quick
```

## 故障排除

### Q: `validate_plugin.py` 报错 "缺少 plugin.json"
A: 确保在插件根目录运行命令，且目录中包含 `plugin.json` 文件。

### Q: MCP 服务器握手失败
A:
1. 检查服务器是否使用 stdio 传输
2. 确保服务器不打印调试信息到 stdout（会破坏 JSON-RPC）
3. 使用 `test_mcp_handshake.py` 测试：
   ```bash
   python3 scripts/test_mcp_handshake.py --command "python3 server.py"
   ```

### Q: `audit_plugin.py` 误报硬编码密钥
A: 安全审计脚本会检测常见的密钥模式。如果是误报（如测试用例中的假密钥），可以在代码中添加注释说明，或使用 `--severity` 参数过滤。

### Q: GitHub Pages 部署失败
A: 确保 `docs/` 目录存在且包含 `index.html`，并在仓库设置中启用 Pages，源选择 `main` 分支的 `/docs` 目录。

---

**没有找到答案？** [创建 Issue](https://github.com/YuJunt/agent-plugin-creator/issues/new/choose) 或在 [Discussions](https://github.com/YuJunt/agent-plugin-creator/discussions) 中提问。
