# Agent Plugin 质量检查清单（三层分类）

> 基于 Agent Plugins 1.0.0 规范 + 实战经验整理
> 每项评分：✅达标 / ⚠️部分达标 / ❌未达标
> 权重：必备层×2 / 推荐层×1 / 可选层×0.5
> 总分 = 必备层得分×2 + 推荐层得分×1 + 可选层得分×0.5
> 发布标准：必备层 100% 达标，推荐层 ≥80% 达标

---

## 第一层：必备层（12项，权重×2，必须100%达标）

> 任何一项未达标都不能发布。

### 规范合规（4项）

#### 1. plugin.json 规范
- ✅ `$schema` 字段存在且 URL 正确
- ✅ `name` 小写字母+数字+连字符+点，与目录名一致
- ✅ 仅使用规范允许的顶层字段
- ✅ 无未知字段（客户端专属数据放 `extensions` 下）

#### 2. Skill 规范
- ✅ 每个 skill 目录含 `SKILL.md`
- ✅ frontmatter 仅使用 6 个白名单字段
- ✅ `name` 与目录名一致，≤64字符
- ✅ `description` 非空，≤1024字符，含触发场景

#### 3. mcp.json 规范（如存在）
- ✅ `$schema` 与 plugin.json 版本一致
- ✅ `command` 是单个可执行 token，非 shell 字符串
- ✅ `env` 不含保留变量名 `PLUGIN_ROOT`/`PLUGIN_DATA`
- ✅ `headers` 不含硬编码密钥

#### 4. 路径安全
- ✅ 插件内相对路径以 `./` 开头
- ✅ 无路径穿越（`../` 逃逸出插件根目录）
- ✅ 无符号链接（symlink）
- ✅ servers/ 代码不含危险文件操作

### 安全审计（3项）

#### 5. 无硬编码密钥
- ✅ 代码中无 API key/token/password/secret
- ✅ mcp.json 的 headers/env 无凭据
- ✅ 无私钥文件（.pem/.key）

#### 6. 无危险代码
- ✅ 无 `eval()`/`exec()` 动态执行
- ✅ 无 `shell=True` 子进程调用
- ✅ 无 `os.system()` 调用用户输入
- ✅ 无危险的反序列化（pickle/yaml.load）

#### 7. 安全审计通过
- ✅ `audit_plugin.py` 0 critical / 0 high
- ✅ `security_check.py` 0 critical / 0 high
- ✅ 人工审查动态调用和混淆代码

### 可运行性（3项）

#### 8. MCP 握手通过（如有 MCP）
- ✅ `test_mcp_handshake.py` 全部通过
- ✅ tools/list 返回预期工具列表
- ✅ stdio 服务器不打印到 stdout

#### 9. 验证脚本通过
- ✅ `validate_plugin.py` 退出码 0
- ✅ `validate_skill.py` 对每个 skill 通过
- ✅ `release_audit.py` 状态 PASS

#### 10. 版本一致性
- ✅ plugin.json version 与发布版本一致
- ✅ CHANGELOG 最新条目与版本一致
- ✅ 无版本号硬编码不一致

### 文档完整性（2项）

#### 11. README 存在
- ✅ 插件根目录有 README.md
- ✅ 包含功能说明、安装步骤、使用方法
- ✅ 列出所有 Skill 和 MCP 工具

#### 12. 许可证存在
- ✅ 根目录有 LICENSE 文件
- ✅ plugin.json 的 license 字段与文件一致

---

## 第二层：推荐层（8项，权重×1，建议≥80%达标）

### 质量保障（3项）

#### 13. 评估用例
- ✅ 有 evals/ 目录，含至少 3 个评估用例
- ✅ 覆盖正常场景和边界场景
- ✅ 每个用例有预期输出

#### 14. 示例插件
- ✅ 有 examples/ 目录，含至少 1 个完整示例
- ✅ 示例可直接运行验证
- ✅ 示例覆盖典型使用场景

#### 15. 单元测试
- ✅ 核心脚本有单元测试
- ✅ 测试覆盖正常路径和错误路径
- ✅ CI 中自动运行测试

### 工程化（3项）

#### 16. CI/CD 配置
- ✅ 有 GitHub Actions 或类似 CI
- ✅ PR 自动运行验证和测试
- ✅ 发布流程自动化

#### 17. 代码质量
- ✅ 脚本有 --help 支持
- ✅ 错误信息清晰可操作
- ✅ 无明显的代码重复

#### 18. 依赖管理
- ✅ Python 依赖在 requirements.txt 或 pyproject.toml
- ✅ TypeScript 依赖在 package.json
- ✅ 无未使用的依赖

### 多客户端（2项）

#### 19. 客户端适配
- ✅ 至少适配 2 个客户端（Claude/Cursor/Codex等）
- ✅ `client_adapter.py --check` 无错误
- ✅ 客户端扩展不修改插件核心

#### 20. 反向封装支持
- ✅ 可通过 `plugin_to_skill.py` 反向封装
- ✅ 封装后的 Skill 通过 `validate_skill.py`
- ✅ 封装后 MCP 启动脚本可用

---

## 第三层：可选层（6项，权重×0.5，根据需求评估）

#### 21. 高级安全
- ⬜ CodeQL 或类似静态分析
- ⬜ Secret scanning + push protection
- ⬜ 依赖漏洞扫描（Dependabot等）

#### 22. 性能基准
- ⬜ 有性能基准测试
- ⬜ 关键操作 <100ms
- ⬜ 性能回归监控

#### 23. 国际化
- ⬜ 支持英文输出（--json 或 --lang）
- ⬜ 文档有英文版
- ⬜ 错误信息支持多语言

#### 24. 社区标准
- ⬜ CONTRIBUTING.md
- ⬜ SECURITY.md
- ⬜ CODE_OF_CONDUCT.md
- ⬜ Issue/PR 模板

#### 25. 高级功能
- ⬜ 交互式向导（wizard）
- ⬜ 文档自动生成（generate_docs）
- ⬜ 多 MCP 服务器支持
- ⬜ streamable-http 远程 MCP

#### 26. 可观测性
- ⬜ 结构化日志
- ⬜ 性能指标收集
- ⬜ 使用统计和反馈机制

---

## 评分计算

```
必备层得分 = (达标项数 / 12) × 100
推荐层得分 = (达标项数 / 8) × 100
可选层得分 = (达标项数 / 6) × 100

总分 = 必备层得分 × 0.5 + 推荐层得分 × 0.3 + 可选层得分 × 0.2
```

### 评级标准

| 总分 | 评级 | 说明 |
|------|------|------|
| ≥95 | 🏆 卓越 | 可作为标杆插件 |
| 85-94 | ✅ 优秀 | 可大规模分发 |
| 70-84 | ⚠️ 良好 | 可发布但建议优化 |
| 60-69 | ⚠️ 合格 | 基本可用，有明显改进空间 |
| <60 | ❌ 不合格 | 必须修复后才能发布 |

### 发布门禁

- **必备层未100%达标** → ❌ 不能发布
- **推荐层 <80% 达标** → ⚠️ 可发布但建议优化
- **总分 <70** → ❌ 不建议发布

---

## 使用方法

```bash
# 自动化检查（必备层大部分可自动检测）
python3 scripts/validate_plugin.py <插件目录>
python3 scripts/audit_plugin.py <插件目录>
python3 scripts/security_check.py <插件目录>
python3 scripts/release_audit.py <插件目录>

# 手动检查（推荐层和可选层需要人工评估）
# 对照本清单逐项确认
```
