# 安装指南

> 本指南说明如何在不同平台安装和使用 Agent Plugin Creator 技能。

## 目录

- [系统要求](#系统要求)
- [安装方式概览](#安装方式概览)
- [豆包（Doubao）](#豆包doubao)
- [Claude Code](#claude-code)
- [Cursor](#cursor)
- [OpenAI Codex](#openai-codex)
- [GitHub Copilot](#github-copilot)
- [Google Gemini](#google-gemini)
- [通用手动安装](#通用手动安装)
- [验证安装](#验证安装)
- [卸载](#卸载)
- [升级](#升级)

## 系统要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.9+ | 所有脚本使用标准库，无第三方依赖 |
| Node.js | 18+ | 仅 TypeScript MCP 服务器需要 |
| 磁盘空间 | 5MB | 技能本身约 300KB，含官方资源约 5MB |
| 操作系统 | Linux/macOS/Windows | 跨平台支持 |

## 安装方式概览

| 平台 | 安装方式 | 难度 |
|------|---------|------|
| 豆包 | 上传 zip 到用户技能目录 | ⭐ |
| Claude Code | 解压到 `~/.claude/skills/` | ⭐ |
| Cursor | 解压到 `.cursor/skills/` | ⭐ |
| Codex | 解压到 `.codex/skills/` | ⭐ |
| Copilot | 通过 client_adapter 生成适配 | ⭐⭐ |
| Gemini | 通过 client_adapter 生成适配 | ⭐⭐ |

## 豆包（Doubao）

### 方式一：用户技能目录（推荐）

1. 下载 `agent-plugin-creator-vX.Y.Z.zip`
2. 解压到豆包工作区的用户技能目录：
   ```
   /home/user/.doubao/agent_mode/workspace/.user_skills/agent-plugin-creator/
   ```
3. 重启豆包会话或刷新技能列表
4. 在对话中输入"创建 agent 插件"触发技能

### 方式二：项目级技能

1. 下载并解压到项目根目录的 `.skills/` 文件夹
2. 在项目设置中启用该技能

### 验证

```bash
ls /home/user/.doubao/agent_mode/workspace/.user_skills/agent-plugin-creator/SKILL.md
# 应输出文件路径
```

## Claude Code

### 全局安装

```bash
# 创建技能目录（如不存在）
mkdir -p ~/.claude/skills

# 解压
unzip agent-plugin-creator-vX.Y.Z.zip -d ~/.claude/skills/

# 验证
ls ~/.claude/skills/agent-plugin-creator/SKILL.md
```

### 项目级安装

```bash
mkdir -p .claude/skills
unzip agent-plugin-creator-vX.Y.Z.zip -d .claude/skills/
```

### 使用

在 Claude Code 中输入：
```
@agent-plugin-creator 创建一个包含 MCP 服务器的插件
```

## Cursor

### 全局安装

```bash
mkdir -p ~/.cursor/skills
unzip agent-plugin-creator-vX.Y.Z.zip -d ~/.cursor/skills/
```

### 项目级安装

```bash
mkdir -p .cursor/skills
unzip agent-plugin-creator-vX.Y.Z.zip -d .cursor/skills/
```

### 使用

在 Cursor 的 AI 对话中引用技能：
```
使用 agent-plugin-creator 创建一个纯 Skill 插件
```

## OpenAI Codex

### 安装

```bash
mkdir -p ~/.codex/skills
unzip agent-plugin-creator-vX.Y.Z.zip -d ~/.codex/skills/
```

### 使用

在 Codex CLI 中：
```
/skills list  # 确认技能已加载
使用 agent-plugin-creator 生成插件
```

## GitHub Copilot

Copilot 不原生支持 Agent Skills，需要通过 client_adapter 生成适配：

```bash
# 1. 先将技能作为插件安装
# 2. 生成 Copilot 适配
python3 scripts/client_adapter.py ./agent-plugin-creator --generate --clients copilot

# 3. 将生成的 com.github.copilot/ 目录复制到项目根目录
cp -r ./agent-plugin-creator/com.github.copilot/ ./
```

## Google Gemini

Gemini 通过 `.gemini/` 目录适配：

```bash
python3 scripts/client_adapter.py ./agent-plugin-creator --generate --clients gemini
cp -r ./agent-plugin-creator/.gemini/ ./
```

## 通用手动安装

适用于任何支持 Agent Skills 规范的平台：

```bash
# 1. 找到平台的技能目录
#    通常是 ~/.config/<platform>/skills/ 或 ./.skills/

# 2. 解压
SKILL_DIR="/path/to/skills/dir"
mkdir -p "$SKILL_DIR"
unzip agent-plugin-creator-vX.Y.Z.zip -d "$SKILL_DIR/"

# 3. 确认目录结构
tree "$SKILL_DIR/agent-plugin-creator/" -L 1
# 应包含: SKILL.md, scripts/, references/, assets/, official/, evals/, examples/
```

## 验证安装

安装完成后，运行以下验证：

```bash
cd /path/to/agent-plugin-creator

# 1. 技能结构验证
python3 scripts/validate_skill.py .
# 预期: 结论: Skill 验证通过

# 2. 官方规范验证
python3 official/skill-creator/scripts/quick_validate.py .
# 预期: Skill is valid!

# 3. 发布审计
python3 scripts/release_audit.py .
# 预期: "status": "PASS"

# 4. 脚本可用性
python3 scripts/init_skill.py --help
python3 scripts/create_mcp_server.py --help
python3 scripts/validate_plugin.py --help
# 全部应输出帮助信息

# 5. 示例插件验证
python3 scripts/validate_plugin.py examples/minimal-skill-only
# 预期: 结论: 插件符合 Agent Plugins 1.0.0 规范
```

全部通过即表示安装成功。

## 卸载

```bash
# 删除技能目录
rm -rf /path/to/skills/agent-plugin-creator/

# 清理可能的缓存（如平台有）
rm -rf /path/to/cache/agent-plugin-creator/
```

## 升级

### 方式一：覆盖安装（推荐）

```bash
# 备份配置（如有自定义）
cp -r /path/to/skills/agent-plugin-creator /tmp/agent-plugin-creator-backup

# 删除旧版本
rm -rf /path/to/skills/agent-plugin-creator

# 安装新版本
unzip agent-plugin-creator-vNEW.zip -d /path/to/skills/

# 验证
python3 /path/to/skills/agent-plugin-creator/scripts/validate_skill.py /path/to/skills/agent-plugin-creator
```

### 方式二：Git 更新（如果通过 git 安装）

```bash
cd /path/to/skills/agent-plugin-creator
git pull origin main
```

### 版本检查

```bash
# 查看当前版本
grep "版本" /path/to/skills/agent-plugin-creator/SKILL.md
# 或
python3 -c "import json; print(json.load(open('/path/to/skills/agent-plugin-creator/provenance.json'))['version'])"
```

### 升级注意事项

- 升级前备份自定义的评估用例（`evals/`）和示例（`examples/`）
- 升级后运行全量验证
- 查看 `CHANGELOG.md` 了解破坏性变更
- MAJOR 版本升级可能需要迁移配置

## 常见问题

**Q: 安装后技能不触发？**
A: 检查 SKILL.md 的 description 是否包含触发词，确认技能目录在平台的搜索路径中。

**Q: 脚本报错 "No module named 'xxx'"？**
A: 本技能零依赖，所有脚本使用 Python 标准库。确认 Python 版本 ≥ 3.9。

**Q: Windows 上路径问题？**
A: 所有脚本使用 `pathlib.Path`，跨平台兼容。如遇问题，使用正斜杠 `/`。

**Q: MCP 服务器无法启动？**
A: 检查 `mcp.json` 中的 command 路径是否正确，stdio 服务器不要打印到 stdout。

**Q: 如何确认版本？**
A: `provenance.json` 是版本唯一来源，SKILL.md 和 CHANGELOG.md 应与其一致。
