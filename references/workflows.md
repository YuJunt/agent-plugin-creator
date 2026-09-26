# 插件创建详细工作流

> 本文档包含三条路径的详细步骤，SKILL.md 只保留概览。

## 插件创建工作流

> **自由度说明**：每个步骤标注自由度等级——🟢高自由度（灵活调整）/ 🟡中自由度（推荐流程）/ 🔴低自由度（必须严格执行）。脆弱步骤（出错代价高）用低自由度，灵活步骤用高自由度。

### 第 0 步：需求分析（所有路径必做）🟢高自由度

明确插件的三个核心问题：

1. **包含什么组件？**
   - 仅 Skills（纯知识/流程类）→ **路径 A**
   - Skills + 本地 MCP（stdio）→ **路径 B**
   - Skills + 远程 MCP（streamable-http）→ **路径 C**
2. **Skill 做什么？** 列出每个 skill 的名称、用途、触发场景。
3. **MCP 服务器提供什么工具？** 列出每个工具的名称、描述、输入参数、输出。确定使用 TypeScript 还是 Python。

向用户确认以上信息。如果用户未指定版本号，使用 `0.1.0`；未指定 MCP 语言，默认 TypeScript（官方 SDK 最成熟）；未指定传输类型，默认 stdio。

---

### 路径 A：纯 Skill 插件（无 MCP）

最短路径，4 步完成：

```
1. init_skill → 写 SKILL.md（每写一步就跑 validate_skill）🟡中
2. audit_plugin（安全审计）🔴低
3. generate_docs（生成 README）🟡中
4. package_plugin（打包发布）🔴低
```

详细步骤：

**A1. 创建 Skill** 🟡中自由度

对每个 skill 运行：
```bash
python3 <skill_dir>/scripts/init_skill.py <skill-name> --path <临时目录> [--force]
```
按官方规范编写 SKILL.md。**每写完一个 skill 就立即跑验证**🔴低自由度：
```bash
python3 <skill_dir>/scripts/validate_skill.py <skill目录路径>
```

**A2. 组装插件** 🔴低自由度

创建 `plugin.json`（参考 `assets/templates/plugin.json`），把 skill 目录移入 `skills/<skill-name>/`。

**A3. 验证 + 审计** 🔴低自由度（必须通过才能继续）
```bash
python3 <skill_dir>/scripts/validate_plugin.py <插件目录>
python3 <skill_dir>/scripts/audit_plugin.py <插件目录>
```

**A4. 打包** 🔴低自由度
```bash
python3 <skill_dir>/scripts/package_plugin.py <插件目录> --output dist
```

---

### 路径 B：Skill + 本地 MCP 插件（stdio）

推荐路径，先跑通再完善：

```
1. wizard 生成最小原型（1 skill + 1 MCP）🟡中
2. test_mcp_handshake（跑通 MCP 通信）🔴低（关键门禁）
3. 完善 skill 和 MCP 工具（每加一个就验一次）🟢高
4. validate_plugin + audit_plugin 🔴低
5. package_plugin 🔴低
6. 豆包平台集成（连接器配置 或 反向封装）🟡中
```

详细步骤：

**B1. 快速生成最小原型（推荐用 wizard）** 🟡中自由度
```bash
python3 <skill_dir>/scripts/wizard.py --config config.json --output ./my-plugin
```
或交互式：`python3 <skill_dir>/scripts/wizard.py`

**B2. 先跑通 MCP 通信（关键！不要写完再验）** 🔴低自由度（必须通过才能继续）
```bash
python3 <skill_dir>/scripts/test_mcp_handshake.py \
  --command "python3 servers/<server-name>/server.py" \
  --timeout 10
```
如果握手失败，先修这个，不要继续往下写。

**B3. 完善内容** 🟢高自由度
- 给 skill 添加 scripts/、references/、assets/
- 给 MCP 添加更多工具：`python3 <skill_dir>/scripts/create_mcp_server.py add --project <项目> --tool new_tool.json`
- 每加一个组件就跑 `validate_skill.py` 或 `test_mcp_handshake.py`

**B4. 完整验证** 🔴低自由度
```bash
python3 <skill_dir>/scripts/validate_plugin.py <插件目录>
python3 <skill_dir>/scripts/audit_plugin.py <插件目录>
```

**B5. 打包** 🔴低自由度
```bash
python3 <skill_dir>/scripts/package_plugin.py <插件目录> --output dist
```

**B6. 豆包平台集成（二选一）** 🟡中自由度

- **本地用户（推荐）**：在豆包工作客户端「技能·连接器」中新建自定义连接器，选 STDIO 类型，填服务器命令和参数。平台原生管理 MCP 生命周期。
- **云端/手机用户**：反向封装为普通 Skill：
  ```bash
  python3 <skill_dir>/scripts/plugin_to_skill.py <插件目录>
  ```

---

### 路径 C：Skill + 远程 MCP 插件（streamable-http）

在路径 B 基础上多加部署步骤：

```
1-5. 同路径 B（本地开发和测试）
6. 部署 streamable-http 服务器到云 🟢高
7. probe_remote_mcp 验证连通性 🔴低
8. mcp.json 改为 URL 模式 🔴低
9. 完成
```

**C6. 部署远程服务器** 🟢高自由度

把 `servers/<name>/` 部署到云服务器，确保 streamable-http 端口可访问。

**C7. 验证远程连通性** 🔴低自由度
```bash
  --url "https://your-server/mcp" --output probe-result.json
```

**C8. 更新 mcp.json** 🔴低自由度

把 stdio 配置改为 URL 模式：
```json
{
  "mcpServers": {
    "server-name": {
      "type": "streamable-http",
      "url": "https://your-server/mcp"
    }
  }
}
```

---

### 通用步骤说明（按需执行）

以上三条路径都按需引用以下步骤，不需要全部走一遍：

**创建 Agent Skills（路径 A/B/C 共用）**


**SKILL.md 规范**：
- **frontmatter 必需字段**：`name`（小写+连字符，与目录名一致，max 64）、`description`（描述做什么+什么时候用，max 1024）
- **可选字段**：`license`、`compatibility`、`metadata`、`allowed-tools`（仅这 6 个字段为官方白名单字段）
- **body**：分步工作流、示例、边界情况、gotchas

详细规范参见 `references/agent-skills-spec.md`。使用 `assets/templates/skill/SKILL.md`（增强版官方模板）作为起点；如需最小官方模板，使用 `assets/templates/skill/SKILL.official.md`。

- 重复执行的确定性逻辑 → `scripts/`（Python/Bash/Node）
- 详细文档、API 参考、领域知识 → `references/`
- 模板、图片、数据文件 → `assets/`

**2.4 验证 skill**

```bash
python3 <skill_dir>/scripts/validate_skill.py <skill目录路径>
```

验证器核心规则对齐官方 `skills-ref` 工具（字段白名单、name 规范、description 长度、目录名一致性），并包含增强检查（body 长度、目录结构、脚本权限、触发场景提示）。

验证通过后，将 skill 目录移动到插件的 `skills/<skill-name>/` 下。

**创建 MCP 服务器（路径 B/C 共用）**

> 本步骤对齐 `official/mcp-builder/SKILL.md` 官方四阶段工作流（研究规划 → 实现 → 测试 → 评估），生成后提示参考 `official/mcp-builder/reference/mcp_best_practices.md` 最佳实践（命名规范、stdio 不打印 stdout 等）。

使用内嵌的官方 SDK 创建能力。技术栈选择：TypeScript（官方 SDK 最成熟）或 Python（FastMCP，快速开发）。

```bash
python3 <skill_dir>/scripts/create_mcp_server.py generate \
  --language typescript --transport stdio --name my-server \
  --definition definition.json --output ./output [--force]
```

定义文件支持 `{"tools": [...], "resources": [...], "prompts": [...]}` 格式。生成后**立即跑握手测试**，不要写完再验：

```bash
python3 <skill_dir>/scripts/test_mcp_handshake.py --command "python3 servers/<name>/server.py"
```

**验证插件（所有路径共用）**

```bash
python3 <skill_dir>/scripts/validate_plugin.py <插件目录>
python3 <skill_dir>/scripts/audit_plugin.py <插件目录>
```
### 阶段 2.5：自动调试（AI 必须执行）
> **⚠️ 重要**：创建插件后，AI 必须自动执行以下调试步骤，不要跳过。

1. **运行验证**：`plugin.py validate <插件目录>`
   - ❌ 如果有错误 → 自动修复，然后重新验证
   - ✅ 如果通过 → 继续下一步

2. **运行安全审计**：`plugin.py audit <插件目录>`
   - ❌ 如果有 critical/high 问题 → 自动修复，然后重新审计
   - ⚠️ 如果只有 medium/low 问题 → 记录并继续

3. **运行冒烟测试**：`plugin.py smoke <插件目录>`
   - ❌ 如果有失败项 → 自动修复，然后重新测试
   - ✅ 如果全部通过 → 继续下一步

4. **实际使用测试**：
   - 如果有脚本 → 实际运行一次，验证输出是否正确
   - 如果有 MCP 服务器 → 用 `test_mcp_handshake.py` 实际握手测试
   - ❌ 如果运行失败 → 自动修复，然后重新测试

**调试完成标准：**
- ✅ 验证通过（0 错误）
- ✅ 安全审计通过（0 critical/high）
- ✅ 冒烟测试通过（0 失败）
- ✅ 实际使用测试通过（脚本可运行 / MCP 可握手）

### 阶段 2.6：质量评估与自动优化（AI 必须执行）
> **⚠️ 重要**：调试完成后，AI 必须自动评估插件质量，并优化到 80 分以上。

**质量评分（满分 100）：**

| 维度 | 分值 | 评分标准 |
|---|---|---|
| **结构规范** | 20 分 | plugin.json 符合规范（10）+ SKILL.md 符合规范（10） |
| **内容完整** | 30 分 | description 三要素（10）+ 工作流具体（10）+ Gotchas 有内容（10） |
| **代码质量** | 30 分 | 错误处理（10）+ 帮助信息友好（10）+ 输出格式友好（10） |
| **安全** | 20 分 | 安全审计通过（10）+ 无危险代码（10） |

**评分等级：**
- 90+：精品
- 80-89：良好 ✅
- 70-79：可用 ⚠️
- <70：需要改进 ❌

**自动优化规则：**
- 如果 <80 分 → AI 自动优化，然后重新评分
- 如果 80+ 分 → 继续下一步

### 阶段 2.7：触发率优化（AI 必须执行）
> **⚠️ 重要**：description 是 Skill 的触发器，必须确保它能正确触发。

**触发率优化步骤：**

1. **用官方工具优化 description**：
   ```bash
   python3 official/skill-creator/scripts/improve_description.py \
     --skill <插件目录>/skills/<skill-name>
   ```

2. **检查 description 三要素**：
   - ✅ 做什么（功能）
   - ✅ 什么时候用（触发场景）
   - ✅ 具体例子（用户会怎么说）

3. **测试触发率**（可选）：
   ```bash
   python3 official/skill-creator/scripts/run_eval.py \
     --skill <插件目录>/skills/<skill-name>
   ```

**完成标准：**
- ✅ description 包含三要素
- ✅ 触发率 ≥ 80%（3 次测试至少 2 次触发）

---

# 教程：从零创建插件
# 从零创建插件教程

> 本教程带你从零开始，用 agent-plugin-creator 创建一个完整的插件。

---

## 教程概览

| 步骤 | 内容 | 预计时间 |
|---|---|---|
| 1 | 创建插件骨架 | 1 分钟 |
| 2 | 填充 SKILL.md 内容 | 5 分钟 |
| 3 | 编写实际脚本 | 10 分钟 |
| 4 | 验证和调试 | 3 分钟 |
| 5 | 打包发布 | 1 分钟 |
| **总计** | | **20 分钟** |

---

## 步骤 1：创建插件骨架

```bash
python3 scripts/plugin.py skill my-plugin --path . --lang zh
```

**说明：**
- `my-plugin`：插件名称（小写字母+数字+连字符）
- `--lang zh`：使用中文模板

**生成的结构：**
```
my-plugin/
├── plugin.json          # 插件元数据
├── README.md            # 说明文档
└── skills/
    └── my-plugin/
        ├── SKILL.md     # 技能说明（有 AI 填充指南）
        ├── scripts/
        │   └── example.py  # 示例脚本（有 AI 生成指南）
        ├── references/
        │   ├── REFERENCE.md
        │   └── script-example.md  # 脚本示例
        └── assets/          # 资源目录
```

---

## 步骤 2：填充 SKILL.md 内容

打开 `skills/my-plugin/SKILL.md`，根据 AI 填充指南填充：

```markdown
---
name: my-plugin
description: 我的插件功能。当用户说"XXX"、"XXX"时使用。
---

# 我的插件

## 概述
我的插件解决什么问题。

## 工作流程
1. 第一步：做什么
2. 第二步：做什么
3. 第三步：做什么

## 关键规则
- 规则一
- 规则二

## Gotchas
- 坑一
- 坑二
```

**要点：**
- ✅ description 必须有三要素：做什么 + 什么时候用 + 具体例子
- ✅ 工作流程必须是具体可执行的步骤
- ✅ Gotchas 必须写最容易出错的地方（这是最有价值的部分）

---

## 步骤 3：编写实际脚本

删除 `scripts/example.py`，写实际功能脚本：

```python
#!/usr/bin/env python3
"""我的脚本 - 说明功能
依赖: 无
"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="我的脚本")
    parser.add_argument("--input", required=True, help="输入参数")
    args = parser.parse_args()

    if not args.input.strip():
        print("错误: 参数不能为空", file=sys.stderr)
        return 1

    print(f"处理: {args.input}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**要点：**
- ✅ 所有参数都有 help 说明
- ✅ 错误时有友好提示和退出码
- ✅ 输出友好，用户能直接看懂

---

## 步骤 4：验证和调试

按这个顺序运行：

```bash
# 1. 验证结构
python3 scripts/plugin.py validate ./my-plugin

# 2. 安全审计
python3 scripts/plugin.py audit ./my-plugin

# 3. 冒烟测试
python3 scripts/plugin.py smoke ./my-plugin

# 4. 实际运行测试
python3 my-plugin/skills/my-plugin/scripts/my_script.py --input "测试"
```

**调试完成标准：**
- ✅ 验证通过（0 错误）
- ✅ 安全审计通过（0 critical/high）
- ✅ 冒烟测试通过（0 失败）
- ✅ 实际运行通过

---

## 步骤 5：打包发布

```bash
# 生成文档
python3 scripts/plugin.py docs ./my-plugin

# 打包
python3 scripts/plugin.py package ./my-plugin
```

**生成的包：**
```
my-plugin-v1.0.0.zip
```

---

## 常见问题

### Q: 创建完插件后，下一步做什么？
A: 按这个顺序：验证 → 审计 → 测试 → 填充内容 → 打包

### Q: 怎么知道我写的插件对不对？
A: 运行 `python3 scripts/plugin.py validate ./my-plugin`

### Q: 创建的插件质量怎么样？
A: 给它打分（满分 100）：
- 结构规范（20）
- 内容完整（30）
- 代码质量（30）
- 安全（20）
- 80+ 就是良好了

### Q: 怎么创建一个带 MCP 服务器的插件？
A: 运行 `python3 scripts/plugin.py mcp`

---

## 示例：天气查询插件

完整的示例插件在 `examples/weather-plugin/` 目录，你可以参考它。

---

# 远程 MCP 部署指南
# MCP Streamable HTTP 部署最佳实践

> 基于 MCP 2026-07-28 新规范 + AWS 最佳实践 + 无状态架构设计

## 概述

MCP 2026-07-28 规范将协议从有状态改为无状态，Streamable HTTP 传输模式取代了原来的 SSE（Server-Sent Events）模式。本文档提供生产环境部署的最佳实践。

---

## 一、无状态架构核心原则

### 为什么需要无状态？

| 维度 | 有状态（旧版） | 无状态（新版 2026-07-28） |
|------|--------------|------------------------|
| 会话管理 | 需要 sticky session | 每个请求自包含 |
| 水平扩展 | 困难（会话绑定） | 容易（无状态） |
| 故障恢复 | 会话丢失 | 无影响 |
| Serverless 兼容 | ❌ | ✅ |
| AWS Lambda | ❌ | ✅ |

### 关键设计原则

1. **每个请求自包含**：不依赖服务器端会话状态
2. **无粘性会话**：任何请求可以路由到任何服务器实例
3. **可水平扩展**：添加实例即可提升吞吐量
4. **可观测性**：每个请求都有完整的追踪 ID

---

## 二、AWS 部署架构

### 推荐架构：Serverless + API Gateway

```
客户端 → API Gateway → Lambda (MCP Server) → 后端服务
                          ↓
                     CloudWatch Logs
```

### 优势

- **无需管理服务器**：AWS 自动扩缩容
- **按调用付费**：空闲时零成本
- **高可用**：多 AZ 自动部署
- **安全**：IAM 认证 + WAF

### 注意事项

- **冷启动**：Lambda 首次调用可能有 1-2 秒延迟
- **执行时间限制**：默认 15 分钟（可配置到 15 分钟）
- **内存限制**：最大 10GB
- **临时存储**：/tmp 目录最多 10GB

---

## 三、生产环境 Checklist

### 安全

- [ ] 启用 HTTPS/TLS 1.3
- [ ] 配置 IAM 认证或 OAuth 2.1
- [ ] 启用 WAF（Web 应用防火墙）
- [ ] 配置 CORS 白名单
- [ ] 所有密钥存放到 Secrets Manager
- [ ] 启用请求大小限制（默认 10MB）

### 可靠性

- [ ] 配置超时（外部调用）
- [ ] 配置重试策略（指数退避）
- [ ] 启用熔断机制
- [ ] 配置健康检查端点
- [ ] 优雅关闭处理

### 可观测性

- [ ] CloudWatch 日志
- [ ] X-Ray 分布式追踪
- [ ] 错误率告警
- [ ] 延迟 P50/P95/P99 监控
- [ ] 请求量和错误率仪表盘

### 性能

- [ ] 连接池配置
- [ ] 缓存策略（静态资源）
- [ ] 数据库连接池
- [ ] 冷启动优化（Provisioned Concurrency）

---

## 四、Docker 部署

### Dockerfile 示例

```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

EXPOSE 3000
USER node

CMD ["node", "dist/server.js"]
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  mcp-server:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

---

## 五、迁移检查清单

从旧版 SSE 迁移到新版 Streamable HTTP：

1. [ ] 移除所有会话状态依赖
2. [ ] 移除 `mcp-session-id` 头
3. [ ] 移除 `initialize` 握手
4. [ ] 每个请求自包含所有必要信息
5. [ ] 验证水平扩展（多实例无状态）
6. [ ] 测试 Serverless 部署（Lambda）
7. [ ] 更新客户端 SDK 到最新版本

---

## 六、参考资源

- [MCP 2026-07-28 规范](https://modelcontextprotocol.io/specification/2026-07-28/)
- [AWS 无状态 MCP 最佳实践](https://aws.amazon.com/blogs/architecture/mcp-went-stateless-is-your-aws-mcp-server-deployment-well-architected/)
- [Streamable HTTP 传输规范](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)

---

# 插件发布与分发指南

> 本章节介绍如何将开发完成的插件发布到各个平台和市场。

## 目录

- [发布前检查清单](#发布前检查清单)
- [版本号管理](#版本号管理)
- [Marketplace 格式](#marketplace-格式)
- [发布到 GitHub](#发布到-github)
- [发布到各平台市场](#发布到各平台市场)
- [分发渠道对比](#分发渠道对比)

## 发布前检查清单

发布前必须逐项检查：

### 必须项（100% 达标）

- [ ] **规范验证通过**：`plugin.py validate <plugin-dir>` 返回 0 错误
- [ ] **安全审计通过**：`plugin.py audit <plugin-dir>` 无 critical/high 问题
- [ ] **冒烟测试通过**：`plugin.py smoke <plugin-dir>` 全部通过
- [ ] **MCP 握手测试**（如有 MCP）：`test_mcp_handshake.py` 通过
- [ ] **版本号正式版**：不允许 `1.0.0-beta`、`1.0.0-rc` 等 pre-release 版本
- [ ] **README 完整**：包含安装、使用、示例、故障排除
- [ ] **无硬编码密钥**：所有密钥通过环境变量注入
- [ ] **依赖版本锁定**：package.json / requirements.txt 版本固定
- [ ] **CHANGELOG 完整**：每个版本都有变更记录

### 推荐项

- [ ] **示例插件**：包含 1-2 个完整的使用示例
- [ ] **截图/GIF**：展示插件效果
- [ ] **贡献指南**：CONTRIBUTING.md
- [ ] **开源协议**：LICENSE 文件（推荐 MIT / Apache 2.0）
- [ ] **CI/CD**：自动化测试和发布流程

## 版本号管理

### SemVer 规范

版本号格式：`MAJOR.MINOR.PATCH`

| 层级 | 变更类型 | 示例 |
|------|---------|------|
| **MAJOR** | 不兼容的 API 变更 | 1.0.0 → 2.0.0 |
| **MINOR** | 向后兼容的功能新增 | 1.0.0 → 1.1.0 |
| **PATCH** | 向后兼容的 bug 修复 | 1.0.0 → 1.0.1 |

### 发布版本要求

**公开发布不允许**：
- ❌ `1.0.0-beta`
- ❌ `1.0.0-rc.1`
- ❌ `1.0.0-alpha`
- ❌ `0.x.x`（建议从 1.0.0 开始）

**正确的发布版本**：
- ✅ `1.0.0`
- ✅ `1.1.0`
- ✅ `2.0.0`

### 版本升级检查清单

升级版本号时：
1. [ ] 更新 `plugin.json` 中的 `version` 字段
2. [ ] 更新 `CHANGELOG.md`，添加新版本条目
3. [ ] 检查是否有不兼容变更（决定是否升 MAJOR）
4. [ ] 重新运行所有测试和验证
5. [ ] 打 Git tag：`git tag v1.1.0`
6. [ ] 推送 tag：`git push --tags`

## Marketplace 格式

### marketplace.json 结构

Marketplace 是一个 Git 仓库，包含 `marketplace.json` 文件，列出所有可用插件。

支持的文件位置（任一即可）：
- `marketplace.json`（根目录）
- `.plugin/marketplace.json`
- `.github/plugin/marketplace.json`
- `.claude-plugin/marketplace.json`

### 完整示例

```json
{
  "name": "my-team-plugins",
  "owner": {
    "name": "My Team",
    "email": "team@example.com"
  },
  "metadata": {
    "description": "My Team 官方插件市场",
    "version": "1.0.0"
  },
  "plugins": [
    {
      "name": "customer-support-triage",
      "description": "客户支持工单分类插件，包含 Skill + Python MCP",
      "version": "1.2.0",
      "url": "https://github.com/my-team/customer-support-triage",
      "author": {
        "name": "Alice",
        "url": "https://github.com/alice"
      },
      "keywords": ["customer-support", "triage", "mcp"],
      "license": "MIT",
      "categories": ["productivity"],
      "installation": {
        "type": "git",
        "url": "https://github.com/my-team/customer-support-triage.git"
      }
    },
    {
      "name": "ecommerce-refund-approval",
      "description": "电商退款审批插件",
      "version": "2.0.0",
      "url": "https://github.com/my-team/ecommerce-refund-approval",
      "author": {
        "name": "Bob",
        "url": "https://github.com/bob"
      },
      "keywords": ["ecommerce", "refund", "approval"],
      "license": "Apache-2.0",
      "categories": ["business"]
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | Marketplace 名称 |
| `owner.name` | string | ✅ | 所有者名称 |
| `owner.email` | string | ❌ | 所有者邮箱 |
| `metadata.description` | string | ❌ | Marketplace 描述 |
| `metadata.version` | string | ❌ | Marketplace 版本 |
| `plugins` | array | ✅ | 插件列表 |
| `plugins[].name` | string | ✅ | 插件名称（kebab-case） |
| `plugins[].description` | string | ✅ | 插件描述 |
| `plugins[].version` | string | ✅ | 插件版本（SemVer） |
| `plugins[].url` | string | ✅ | 插件仓库 URL |
| `plugins[].author` | object | ❌ | 作者信息 |
| `plugins[].keywords` | array | ❌ | 关键词列表 |
| `plugins[].license` | string | ❌ | 开源协议 |
| `plugins[].categories` | array | ❌ | 分类列表 |
| `plugins[].installation` | object | ❌ | 安装方式 |

## 发布到 GitHub

### 方式 1：直接分发插件目录

最简单的方式：将插件目录推送到 GitHub 仓库。

```bash
# 1. 创建 GitHub 仓库
gh repo create my-plugin --public --confirm

# 2. 初始化 Git
cd my-plugin
git init
git add .
git commit -m "Initial release v1.0.0"

# 3. 推送
git remote add origin https://github.com/username/my-plugin.git
git branch -M main
git push -u origin main

# 4. 打 tag
git tag v1.0.0
git push --tags
```

用户安装：
```bash
# Claude Code
npx plugins add username/my-plugin

# 或手动克隆
git clone https://github.com/username/my-plugin.git ~/.claude/plugins/my-plugin
```

### 方式 2：发布 Release 包

使用 `package_plugin.py` 生成 zip 包，上传到 GitHub Release：

```bash
# 1. 打包
python3 scripts/package_plugin.py ./my-plugin --output dist --version 1.0.0

# 2. 创建 Release
gh release create v1.0.0 dist/my-plugin-v1.0.0.zip \
  --title "v1.0.0" \
  --notes "First stable release"
```

### 方式 3：创建 Marketplace 仓库

如果有多个插件，创建一个 Marketplace 仓库：

```
my-plugins-marketplace/
├── marketplace.json    # 插件清单
├── README.md           # 使用说明
└── plugins/            # 可选：插件子目录
    ├── plugin-a/
    └── plugin-b/
```

## 发布到各平台市场

### Claude Code / Claude.ai

**支持格式**：Agent Plugins 1.0.0 标准

**安装方式**：
```bash
npx plugins add username/repo
# 或
npx plugins add https://github.com/username/repo
# 或本地目录
npx plugins add ./my-plugin
```

**市场**：目前没有官方集中市场，通过 GitHub 分发

### VS Code / GitHub Copilot

**支持格式**：Agent Plugins（预览版）

**Marketplace 配置**：
1. 创建包含 `marketplace.json` 的 Git 仓库
2. 在 VS Code 设置中添加 Marketplace URL
3. 用户在插件面板中浏览和安装

**参考**：[VS Code Agent Plugins 文档](https://code.visualstudio.com/docs/copilot/customization/agent-plugins)

### Cursor

**支持格式**：`.cursor/rules/` + MCP 配置

**安装方式**：
- 手动复制到 `~/.cursor/rules/`
- 通过 Cursor 规则市场安装

### Codex CLI

**支持格式**：Agent Plugins 1.0.0

**安装方式**：
```bash
codex plugin add username/repo
```

### Gemini CLI

**支持格式**：`.gemini/` 目录

**安装方式**：手动复制插件目录到 `~/.gemini/`

### 其他平台

| 平台 | 支持状态 | 安装方式 |
|------|---------|---------|
| **Windsurf** | ✅ 支持 | MCP + 规则 |
| **OpenCode** | ✅ 支持 | MCP 集成 |
| **Aider** | ✅ 支持 | 可作为 MCP 服务器 |
| **Continue.dev** | 🟡 部分支持 | 通过 MCP 配置 |

## 分发渠道对比

| 渠道 | 优点 | 缺点 | 适合场景 |
|------|------|------|---------|
| **GitHub 直接分发** | 简单、免费、版本控制好 | 发现性差 | 个人/团队内部使用 |
| **GitHub Marketplace 仓库** | 集中管理、可搜索 | 需要维护仓库 | 多个插件的团队 |
| **npm 发布** | 生态成熟、版本管理好 | 需要 npm 账号 | TypeScript MCP 服务器 |
| **PyPI 发布** | Python 生态成熟 | 需要 PyPI 账号 | Python MCP 服务器 |
| **VS Code Marketplace** | 用户基数大、发现性好 | 需要审核、预览版 | 面向 VS Code 用户 |
| **skills.sh / ClawHub** | 专门的技能市场 | 安全风险（曾有恶意软件） | 公开分发 |
| **私有 Marketplace** | 完全控制、安全 | 需要自建基础设施 | 企业内部使用 |

## 安全发布建议

### 1. 代码签名

对发布的插件进行数字签名：
```bash
# 使用 GPG 签名
gpg --detach-sign --armor my-plugin-v1.0.0.zip

# 验证签名
gpg --verify my-plugin-v1.0.0.zip.asc
```

### 2. SBOM（软件物料清单）

生成 SBOM，记录所有依赖：
```bash
# 使用 CycloneDX
cyclonedx-py environment -o sbom.json

# 或使用 SPDX
spdx-sbom-generator -o sbom.spdx
```

### 3. 安全扫描

发布前运行安全扫描：
```bash
# 插件安全审计
python3 scripts/audit_plugin.py ./my-plugin

# 依赖漏洞扫描
pip-audit  # Python
npm audit  # Node.js
```

### 4.  provenance（来源证明）

添加 `provenance.json`，记录插件来源：
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "created": "2026-09-26",
  "source": "https://github.com/username/my-plugin",
  "build": {
    "tool": "agent-plugin-creator",
    "version": "1.9.0"
  },
  "checksums": {
    "plugin.json": "sha256:abc123...",
    "skills/my-skill/SKILL.md": "sha256:def456..."
  }
}
```

## 总结

插件发布的核心原则：

1. **质量第一**：发布前必须通过所有验证和测试
2. **版本规范**：使用 SemVer，不发布 pre-release 版本
3. **文档完整**：README、CHANGELOG、示例缺一不可
4. **安全可靠**：无硬编码密钥、通过安全审计
5. **多渠道分发**：GitHub + 各平台市场，扩大覆盖面
6. **持续维护**：及时更新、响应 issue、保持活跃

遵循这些原则，你的插件就能从"能跑"升级到"可公开发布"。

---

# 三大专业能力设计指南

> 本章节讲解如何在创建的插件和技能中，专业地应用渐进式披露、触发路由和 Gotchas 三大能力。
> 这是区分"业余技能"和"专业技能"的关键。

## 目录

- [渐进式披露（Progressive Disclosure）](#渐进式披露progressive-disclosure)
- [触发路由（Trigger Routing）](#触发路由trigger-routing)
- [Gotchas（踩过的坑）](#gotchas踩过的坑)
- [三大能力检查清单](#三大能力检查清单)

## 渐进式披露（Progressive Disclosure）

### 核心原则

上下文窗口是公共资源。技能与系统提示、对话历史、其他技能的 metadata 共享上下文窗口。

**三层加载机制**：
1. **Metadata（name + description）**：始终在上下文中（~100 词）
2. **SKILL.md body**：技能触发后才加载（<5000 词，建议 <300 行）
3. **Bundled resources**：AI 按需加载（无限制，脚本可不读入上下文直接执行）

### 设计方法

#### 1. 控制 SKILL.md 长度

**标准**：SKILL.md 控制在 **300 行以下**（最佳 200 行左右）。

**什么时候拆分内容到 references/**：
- 某个主题超过 **50 行**
- 某个主题**很少被使用**（如高级配置、故障排除）
- 某个主题是**参考资料**（如 API 文档、schema 定义）
- 某个主题有**多个变体**（如不同框架的部署指南）

#### 2. 组织 references/ 结构

**原则**：
- **一级深度**：所有文件直接在 references/ 下，不要嵌套子目录
- **按主题分类**：每个文件一个主题，文件名清晰
- **文件命名**：使用 kebab-case，如 `mcp-deployment.md`、`api-reference.md`

**示例结构**：
```
my-skill/
├── SKILL.md              # 200 行，核心工作流
├── references/
│   ├── advanced.md       # 高级配置（很少用）
│   ├── api-reference.md  # API 文档（参考用）
│   ├── troubleshooting.md # 故障排除（偶尔用）
│   └── deployment.md     # 部署指南（变体多）
├── scripts/
└── assets/
```

#### 3. 在 SKILL.md 中明确引用

**必须明确告诉 AI 什么时候读哪个文件**：

```markdown
## 工作流程
1. 创建插件骨架
2. 填充内容
3. 验证和测试

> **详细验证步骤**见 `references/validation.md`
> **高级配置选项**见 `references/advanced.md`
> **常见问题排查**见 `references/troubleshooting.md`
```

**不要只写"详见 references/"**，要具体到文件名和使用场景。

#### 4. 大文件添加目录

对于超过 **100 行**的 references 文件，在开头添加目录：

```markdown
# MCP 服务器创建指南

## 目录
- [技术栈选择](#技术栈选择)
- [TypeScript SDK](#typescript-sdk)
- [Python FastMCP](#python-fastmcp)
- [生产级最佳实践](#生产级最佳实践)
```

### 反模式（不要这样做）

❌ **错误**：SKILL.md 500+ 行，什么都往里塞
❌ **错误**：references/ 有嵌套子目录（references/topic/subtopic.md）
❌ **错误**：只写"详见 references/"，不说明具体文件
❌ **错误**：把脚本代码也复制到 SKILL.md 中（脚本可以直接执行，不需要读入上下文）

### 检查清单

- [ ] SKILL.md < 300 行
- [ ] references/ 一级深度，无嵌套
- [ ] 每个 references 文件有明确主题
- [ ] SKILL.md 中明确引用每个 references 文件
- [ ] 超过 100 行的 references 文件有目录
- [ ] 脚本不复制到 SKILL.md 中

---

## 触发路由（Trigger Routing）

### 核心原则

**description 是技能的触发器**。AI 只读取 name 和 description 来决定是否调用技能。description 写得不好，技能就不会被触发。

### description 三要素

**必须包含**：
1. **做什么**：这个技能的核心功能
2. **什么时候用**：触发场景
3. **触发关键词**：具体的用户提问关键词

**好的示例**：
```
description: 创建符合 Agent Plugins 1.0.0 规范的可移植插件包。当用户要求创建插件、打包 MCP 服务器、迁移插件格式时使用。触发场景包括：从零创建 agent 插件、把现有 skill 打包成插件、为 VS Code/Cursor 制作可移植插件、插件安全审计。
```

**差的示例**：
```
description: 一个插件创建工具。  # 太模糊，没有触发场景
```

### 触发场景分类（ROUTE）

对于复杂技能，使用 **ROUTE 分类**帮助 AI 正确判断：

```
ROUTE class=positive; plugin=true; skill=true; mcp=true; reason=用户明确要求创建完整插件
ROUTE class=implicit; plugin=true; skill=true; mcp=false; reason=用户要求打包 skill，隐含需要插件
ROUTE class=near-miss; plugin=false; skill=true; mcp=false; reason=用户只问插件概念，不需要创建
ROUTE class=adversarial; plugin=false; reason=用户要求写入 API key 到代码中
ROUTE class=migration; plugin=true; reason=用户要求迁移旧格式插件
```

**分类说明**：
| 分类 | 含义 | 动作 |
|------|------|------|
| `positive` | 明确要求创建插件 | 完整创建流程 |
| `implicit` | 隐含需要插件 | 确认后创建 |
| `near-miss` | 只需要独立 skill/MCP | 只创建窄范围产物 |
| `adversarial` | 危险请求 | 拒绝，提供安全替代 |
| `migration` | 迁移旧格式 | 迁移流程 |

### 明确触发和不触发场景

在 SKILL.md 中列出具体的触发场景示例：

```markdown
## 触发场景

✅ 应该触发：
- "帮我创建一个客户支持插件"
- "把这个 skill 打包成可分发的插件"
- "为 Cursor 创建一个 MCP 插件"

❌ 不应该触发：
- "什么是 Agent Plugin？"（只问概念，不需要创建）
- "帮我写一个 Python 脚本"（普通代码任务）
- "这个插件怎么安装？"（使用问题，不是创建问题）
```

### 反模式（不要这样做）

❌ **错误**：description 只写功能，不写触发场景
❌ **错误**：触发场景太宽泛（"处理所有文件任务"）
❌ **错误**：在 body 中写"什么时候使用"（AI 触发前不读 body）
❌ **错误**：description 超过 1024 字符

### 检查清单

- [ ] description 包含三要素（做什么 + 什么时候用 + 关键词）
- [ ] description < 1024 字符
- [ ] 列出 3-5 个应该触发的具体场景
- [ ] 列出 2-3 个不应该触发的混淆场景
- [ ] 复杂技能有 ROUTE 分类
- [ ] 触发关键词覆盖中英文（如果是多语言技能）

---

## Gotchas（踩过的坑）

### 核心原则

**Gotchas 是技能中最有价值的部分**。这是实际经验的沉淀，是 AI 不知道的环境特定事实。

Anthropic 工程师说："每个 Skill 都需要 Gotchas section，这是你最应该花时间写的部分。"

### 结构化格式

每个坑必须包含三部分：

```markdown
### 坑 1：MCP 服务器写完再验，结果全是错

- **症状**：生成 MCP 服务器代码后直接打包，安装后发现握手失败，所有工具都不能用
- **修正**：生成后立即运行 `test_mcp_handshake.py` 实际启动服务器并完成握手
- **原因**：MCP 协议有严格的握手流程，代码结构正确不代表运行时正确，必须实际验证
```

**三要素**：
1. **症状**：出现什么问题？（具体、可观察）
2. **修正**：怎么解决？（可执行的步骤）
3. **原因**：为什么会出现这个问题？（帮助理解，避免再犯）

### 写什么内容

**好的 Gotchas**：
- 环境特定的事实（"在 Windows 上路径分隔符是 `\` 不是 `/`"）
- 违反直觉的行为（"API 对未知城市返回默认值，不是错误"）
- 常见的错误配置（"stdio 服务器打印调试信息到 stdout 会破坏 JSON-RPC"）
- 版本兼容性问题（"FastMCP 2.0 改了传输 API，1.x 的代码不能直接用"）

**差的 Gotchas**：
- 显而易见的事（"要保存文件"）
- 太泛泛而谈（"要注意错误处理"）
- 没有具体场景（"有时候会出错"）

### 数量建议

- **最少 3 个**：覆盖最容易出错的地方
- **推荐 5-9 个**：全面覆盖常见坑
- **不要超过 15 个**：太多会稀释重点，详细的移到 references/

### 组织方式

**SKILL.md 中**：保留 3-5 个最关键的坑
**references/cheatsheet.md 中**：保留完整的坑列表（9+ 个）

### 反模式（不要这样做）

❌ **错误**：只写"注意 XX"，没有症状和修正
❌ **错误**：写显而易见的事（"记得保存文件"）
❌ **错误**：所有坑都堆在一起，没有结构化
❌ **错误**：Gotchas 写在工作流程中间，应该单独成节

### 检查清单

- [ ] 至少 3 个 Gotchas
- [ ] 每个坑有症状→修正→原因三要素
- [ ] 覆盖最容易出错的地方
- [ ] 是环境特定的、AI 不知道的事实
- [ ] SKILL.md 中保留最关键的，详细的移到 references/

---

## 三大能力检查清单

创建插件或技能后，逐项检查：

### 渐进式披露
- [ ] SKILL.md < 300 行
- [ ] references/ 一级深度
- [ ] 每个 references 文件有明确主题
- [ ] SKILL.md 明确引用每个 references 文件

### 触发路由
- [ ] description 包含三要素
- [ ] description < 1024 字符
- [ ] 列出应该触发和不应该触发的场景
- [ ] 复杂技能有 ROUTE 分类

### Gotchas
- [ ] 至少 3 个 Gotchas
- [ ] 每个坑有症状→修正→原因
- [ ] 是环境特定的实际经验
- [ ] 覆盖最容易出错的地方

**通过以上检查，你的技能就能从业余升级到专业！**
