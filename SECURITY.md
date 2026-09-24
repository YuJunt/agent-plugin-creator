# 安全策略 (Security Policy)

## 支持的版本

本项目遵循 [Semantic Versioning](https://semver.org/)，仅支持最新的 MINOR 版本接收安全更新。

| 版本 | 支持状态 |
|------|---------|
| 1.4.x | ✅ 完全支持 |
| < 1.4 | ❌ 不再支持 |

## 报告安全漏洞

如果你发现了安全漏洞，请**不要**公开创建 Issue，而是通过以下方式私下报告：

### 报告方式

1. **GitHub Security Advisory**（推荐）：
   - 前往 [Security Advisories](https://github.com/YuJunt/agent-plugin-creator/security/advisories)
   - 点击 "New draft security advisory"
   - 填写漏洞详情

2. **邮件报告**：
   - 发送邮件至项目维护者（请在 GitHub 个人主页查看联系方式）
   - 邮件标题格式：`[SECURITY] agent-plugin-creator - <漏洞简述>`

### 报告内容

请在报告中包含以下信息：

- **漏洞类型**：如硬编码密钥、代码注入、路径穿越、权限绕过等
- **影响范围**：受影响的版本号、文件、功能模块
- **复现步骤**：详细的复现步骤（POC）
- **潜在影响**：攻击者可能利用此漏洞做什么
- **修复建议**：如果你有修复建议，请一并提供
- **你的联系方式**：以便我们跟进确认

## 响应时间

| 严重程度 | 首次响应 | 修复目标 |
|---------|---------|---------|
| Critical（严重） | 24小时内 | 7天内 |
| High（高危） | 48小时内 | 14天内 |
| Medium（中危） | 7天内 | 30天内 |
| Low（低危） | 14天内 | 下一版本 |

## 安全最佳实践

本项目内置了安全审计工具，使用者应注意：

### 1. 不要硬编码密钥

- ❌ 错误：`api_key = "sk-1234567890abcdef"`
- ✅ 正确：`api_key = os.environ.get("API_KEY")`

### 2. MCP 服务器安全

- `mcp.json` 的 `headers` 和 `env` 中**不要**写入真实密钥
- 使用 `${ENV_VAR}` 引用环境变量
- stdio 服务器不要打印调试信息到 stdout（会破坏 JSON-RPC）

### 3. 插件分发前必做

```bash
# 运行安全审计
python3 scripts/audit_plugin.py ./your-plugin --severity high

# 运行自动化安全检查
python3 scripts/security_check.py ./your-plugin

# 确认无 critical/high 问题后再发布
```

### 4. 依赖安全

- 本项目核心脚本**零第三方依赖**（仅 Python 标准库）
- CI 环境使用 `pyyaml` 和 `requests`，请定期更新
- 生成的 MCP 服务器依赖 `mcp` SDK 或 `fastmcp`，请关注上游安全公告

## 安全审计功能

本技能内置多层安全防护：

| 工具 | 功能 |
|------|------|
| `audit_plugin.py` | 扫描插件代码中的危险模式和密钥 |
| `security_check.py` | 自动化安全检查（CI/CD 集成） |
| `validate_plugin.py` | 验证 mcp.json 中无硬编码密钥 |
| `release_audit.py` | 发布前安全检查清单 |
| `.pre-commit-config.yaml` | 提交前自动安全检查 |

## 致谢

感谢所有负责任地披露安全漏洞的安全研究者。你的报告帮助我们让这个项目更安全。

---

**最后更新**：2026-09-24
**策略版本**：1.0
