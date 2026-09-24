# Minimal Skill Only Plugin

这是一个最小化的纯 Skill 插件示例，展示 Agent Plugins 1.0.0 规范的最简结构。

## 结构

```
minimal-skill-only/
├── plugin.json              # 插件元数据（唯一必需文件）
└── skills/
    └── code-reviewer/
        └── SKILL.md         # 代码审查技能
```

## 特点

- ✅ 纯 Skill，无 MCP 服务器
- ✅ 最小化结构，适合入门理解
- ✅ 包含一个实用的代码审查技能
- ✅ 符合 Agent Plugins 1.0.0 规范

## 适用场景

- 学习 Agent Plugins 规范的最简结构
- 只需要 Skill 能力，不需要 MCP 工具
- 快速创建轻量级插件
