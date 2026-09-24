# Agent Plugin Creator

[![CI](https://github.com/your-username/agent-plugin-creator/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/agent-plugin-creator/actions/workflows/ci.yml)
[![Release](https://github.com/your-username/agent-plugin-creator/actions/workflows/release.yml/badge.svg)](https://github.com/your-username/agent-plugin-creator/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)](https://github.com/your-username/agent-plugin-creator/releases)

> 创建符合 [Agent Plugins 1.0.0](https://github.com/agentplugins/agent-plugins-spec) 开放规范的可移植插件包，自包含官方 Agent Skills 创建能力和官方 MCP SDK 服务器创建能力，不依赖目标平台已有这些工具。

## 功能特性

- 🛠️ **从零创建 Agent Plugin** — 交互式向导或配置文件批量生成
- 📦 **Skill + MCP 组合打包** — 将 Agent Skills 和 MCP 服务器统一打包为跨客户端插件
- 🔌 **多客户端适配** — 支持 Claude Code、Cursor、GitHub Copilot、OpenAI Codex、Google Gemini
- 🔄 **旧格式迁移** — 将厂商专属插件格式迁移到 Agent Plugins 标准
- 🛡️ **安全审计** — 硬编码密钥检测、代码注入检测、路径穿越检测
- ✅ **规范验证** — 对齐官方 skills-ref 工具和 Agent Plugins 1.0.0 规范
- 📊 **质量评估** — 8 大门禁检查、5 个评估用例、性能基准测试
- 🔄 **反向封装** — 将插件反向封装为普通 Skill，兼容不支持 Agent Plugin 的平台
- 📝 **自动文档** — 从 plugin.json + skills/ + mcp.json 生成完整 README
- 🚀 **CI/CD 就绪** — GitHub Actions 自动验证、测试、发布

## 快速开始

### 安装

```bash
# 克隆到技能目录
git clone https://github.com/your-username/agent-plugin-creator.git ~/.claude/skills/agent-plugin-creator

# 或下载发布包
curl -L https://github.com/your-username/agent-plugin-creator/releases/latest/download/agent-plugin-creator-v1.4.0.zip -o plugin.zip
unzip plugin.zip -d ~/.claude/skills/
```

详细安装步骤见 [INSTALL.md](INSTALL.md)。

### 使用交互式向导

```bash
cd agent-plugin-creator
python3 scripts/wizard.py
```

### 使用命令行

```bash
# 1. 创建 Skill 脚手架
python3 scripts/init_skill.py my-skill --path ./my-plugin/skills

# 2. 生成 MCP 服务器
python3 scripts/create_mcp_server.py generate \
  --language python --transport stdio \
  --name my-server --definition def.json \
  --output ./my-plugin/servers/my-server

# 3. 验证插件
python3 scripts/validate_plugin.py ./my-plugin

# 4. 安全审计
python3 scripts/audit_plugin.py ./my-plugin

# 5. 打包发布
python3 scripts/package_plugin.py ./my-plugin --output dist
```

## 目录结构

```
agent-plugin-creator/
├── SKILL.md                    # 主技能文件
├── README.md                   # 本文件
├── CONTRIBUTING.md             # 贡献指南
├── INSTALL.md                  # 安装指南
├── CHANGELOG.md                # 版本历史
├── LICENSE.txt                 # MIT 许可证
├── provenance.json             # 发布元数据（版本唯一来源）
├── scripts/                    # 30+ Python 脚本
│   ├── init_skill.py           # Skill 脚手架
│   ├── create_mcp_server.py    # MCP 服务器生成
│   ├── validate_plugin.py      # 插件验证
│   ├── validate_skill.py       # Skill 验证
│   ├── audit_plugin.py         # 安全审计
│   ├── security_check.py       # 安全检查自动化
│   ├── wizard.py               # 交互式向导
│   ├── plugin_to_skill.py      # 反向封装
│   ├── client_adapter.py       # 多客户端适配
│   ├── package_plugin.py       # 打包发布
│   ├── benchmark.py            # 性能基准测试
│   ├── release_audit.py        # 发布审计
│   └── common/                 # 共享模块
│       └── logger.py           # 统一日志系统
├── references/                 # 详细参考文档
├── assets/                     # 模板和资源
├── official/                   # 内嵌官方资源（Anthropic）
│   ├── skill-creator/          # 官方 skill-creator
│   └── mcp-builder/            # 官方 mcp-builder
├── evals/                      # 评估用例
├── examples/                   # 5个示例插件
└── .github/workflows/          # CI/CD 配置
```

## 支持的客户端

| 客户端 | 适配方式 | 状态 |
|--------|---------|------|
| Claude Code | `.claude-plugin/` + marketplace.json | ✅ |
| OpenAI Codex | `.codex-plugin/` | ✅ |
| GitHub Copilot | `com.github.copilot/hooks/` | ✅ |
| Cursor | `.cursor/rules/*.mdc` | ✅ |
| Google Gemini | `.gemini/` | ✅ |
| 豆包 (Doubao) | 用户技能目录 | ✅ |

## 开发

### 前置要求

- Python 3.9+（零第三方依赖）
- Node.js 18+（仅 TypeScript MCP 服务器需要）

### 运行测试

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

# 评估用例
python3 scripts/run_trigger_eval.py --skill . --output /tmp/trigger.json
```

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat(script): add new feature
fix(script): fix bug
docs: update documentation
```

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 性能基准

| 测试项 | 平均耗时 |
|--------|---------|
| validate_skill | ~50ms |
| validate_plugin | ~50ms |
| audit_plugin | ~50ms |
| init_skill | ~100ms |
| **总体平均** | **~60ms** |

评级：⭐⭐⭐⭐⭐ 优秀

## 版本管理

遵循 [Semantic Versioning](https://semver.org/)：

- **MAJOR** (x.0.0): 不兼容的 API 变更
- **MINOR** (1.x.0): 向下兼容的功能新增
- **PATCH** (1.0.x): 向下兼容的问题修正

版本号唯一来源：`provenance.json`

详见 [references/versioning.md](references/versioning.md)。

## 许可证

MIT License — 详见 [LICENSE.txt](LICENSE.txt)

### 第三方资源

本项目内嵌了 Anthropic 官方的 `skill-creator` 和 `mcp-builder` 资源（位于 `official/` 目录），这些资源遵循其各自的许可证。详见 `official/` 目录下的许可证文件。

## 致谢

- [Anthropic Skills](https://github.com/anthropics/skills) — 官方 skill-creator 和 mcp-builder
- [Agent Plugins Spec](https://github.com/agentplugins/agent-plugins-spec) — 插件规范

## 联系方式

- Issue: [GitHub Issues](https://github.com/your-username/agent-plugin-creator/issues)
- 讨论: [GitHub Discussions](https://github.com/your-username/agent-plugin-creator/discussions)
