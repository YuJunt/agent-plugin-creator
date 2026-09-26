# Changelog

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
