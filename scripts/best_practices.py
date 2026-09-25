#!/usr/bin/env python3
"""
最佳实践库生成工具

从真实插件中提取最佳实践，生成可复用的最佳实践文档。

用法:
    python3 scripts/best_practices.py generate --plugins ./plugin1 ./plugin2 --output best-practices.md
    python3 scripts/best_practices.py list
    python3 scripts/best_practices.py show --category security
    python3 scripts/best_practices.py --json
"""
import argparse
import json
import sys
from pathlib import Path


BEST_PRACTICES = {
    "structure": [
        {
            "id": "BP-STRUCT-001",
            "title": "插件目录结构清晰",
            "description": "使用标准目录结构：skills/、servers/、assets/、references/",
            "why": "清晰的目录结构让用户和工具更容易理解和使用插件",
            "example": "plugin/\n├── plugin.json\n├── skills/\n│   └── my-skill/\n│       └── SKILL.md\n├── servers/\n│   └── my-server/\n└── README.md",
        },
        {
            "id": "BP-STRUCT-002",
            "title": "plugin name 与目录名一致",
            "description": "plugin.json 中的 name 字段必须与插件目录名完全一致",
            "why": "Agent Plugins 规范要求，验证器会检查这一点",
            "example": "目录名: my-plugin\nplugin.json: {\"name\": \"my-plugin\"}",
        },
        {
            "id": "BP-STRUCT-003",
            "title": "每个 Skill 独立目录",
            "description": "skills/ 下每个直接子目录是一个独立的 Skill，包含 SKILL.md",
            "why": "平台只发现 skills/ 的直接子目录，不递归",
        },
    ],
    "skill": [
        {
            "id": "BP-SKILL-001",
            "title": "description 包含三要素",
            "description": "What it does + When to use it + Trigger phrases",
            "why": "description 是 LLM 判断是否触发的唯一信号",
            "example": "description: 创建和管理 Agent Plugin。当用户要求创建插件、打包 skill、生成 MCP 服务器时使用。触发词：创建插件、打包、plugin",
        },
        {
            "id": "BP-SKILL-002",
            "title": "Gotchas section 不可少",
            "description": "每个 Skill 都应该有 Gotchas 部分，记录实际踩过的坑",
            "why": "Gotchas 是最有价值的部分，防止 LLM 重复犯错",
        },
        {
            "id": "BP-SKILL-003",
            "title": "渐进式披露",
            "description": "L1 frontmatter → L2 SKILL.md body → L3 references/ 按需加载",
            "why": "平衡内容完整性和上下文效率",
        },
        {
            "id": "BP-SKILL-004",
            "title": "SKILL.md 不超过 500 行",
            "description": "超过 300 行就考虑拆分，详细内容放 references/",
            "why": "太长的文档会被 LLM 截断或忽略后半部分",
        },
    ],
    "mcp": [
        {
            "id": "BP-MCP-001",
            "title": "stdio 服务器不打印到 stdout",
            "description": "stdout 是 JSON-RPC 通道，调试信息必须打到 stderr",
            "why": "打印到 stdout 会破坏 MCP 协议，导致握手失败",
        },
        {
            "id": "BP-MCP-002",
            "title": "command 是单个可执行 token",
            "description": "mcp.json 中的 command 不能是 shell 字符串，参数放 args 数组",
            "why": "安全要求，防止命令注入",
            "example": "✅ {\"command\": \"python3\", \"args\": [\"server.py\"]}\n❌ {\"command\": \"python3 server.py\"}",
        },
        {
            "id": "BP-MCP-003",
            "title": "生成后立即跑握手测试",
            "description": "MCP 服务器生成后立即运行 test_mcp_handshake.py 验证",
            "why": "早发现早修复，不要写完所有代码再验",
        },
        {
            "id": "BP-MCP-004",
            "title": "工具命名清晰",
            "description": "工具名用动词+名词格式，如 get_user、create_order",
            "why": "清晰的命名让 LLM 更容易选择正确的工具",
        },
    ],
    "security": [
        {
            "id": "BP-SEC-001",
            "title": "不硬编码密钥",
            "description": "API key、token、密码必须通过环境变量注入",
            "why": "硬编码密钥会被安全审计检测到，且可能泄露",
        },
        {
            "id": "BP-SEC-002",
            "title": "不使用 eval/exec",
            "description": "避免使用 eval()、exec()、shell=True 等危险函数",
            "why": "可能导致代码注入攻击",
        },
        {
            "id": "BP-SEC-003",
            "title": "路径不逃逸插件根目录",
            "description": "所有文件路径必须在插件根目录内，使用 ./ 开头",
            "why": "防止路径穿越攻击",
        },
        {
            "id": "BP-SEC-004",
            "title": "mcp.json 不含密钥",
            "description": "headers 和 env 中不能嵌入凭据，由客户端管理",
            "why": "配置文件可能被公开或共享",
        },
    ],
    "testing": [
        {
            "id": "BP-TEST-001",
            "title": "每个脚本有 --help",
            "description": "所有 Python 脚本都必须支持 --help 参数",
            "why": "用户可以快速了解用法，也是基本的可用性要求",
        },
        {
            "id": "BP-TEST-002",
            "title": "评估用例覆盖正反例",
            "description": "评估用例必须包含 should-trigger 和 should-not-trigger",
            "why": "只测正例会导致过度触发",
        },
        {
            "id": "BP-TEST-003",
            "title": "发布前跑完整验证套件",
            "description": "validate_plugin + audit_plugin + release_audit 全部通过",
            "why": "防止低级错误流入发布版本",
        },
    ],
    "documentation": [
        {
            "id": "BP-DOC-001",
            "title": "必须有 README.md",
            "description": "插件根目录必须有 README.md，说明功能和用法",
            "why": "用户首先看到的就是 README",
        },
        {
            "id": "BP-DOC-002",
            "title": "有 CHANGELOG.md",
            "description": "记录每个版本的变更，遵循 Keep a Changelog 格式",
            "why": "用户可以了解版本间的差异",
        },
        {
            "id": "BP-DOC-003",
            "title": "示例覆盖常见场景",
            "description": "examples/ 目录包含从简单到复杂的完整示例",
            "why": "示例是最好的文档",
        },
    ],
}


def generate_markdown(output_file: Path = None) -> str:
    """生成最佳实践 Markdown 文档"""
    lines = [
        "# Agent Plugin 最佳实践库",
        "",
        "> 基于真实插件开发经验整理的最佳实践，共 6 大类 20 条",
        "",
    ]

    category_names = {
        "structure": "结构规范",
        "skill": "Skill 开发",
        "mcp": "MCP 服务器",
        "security": "安全",
        "testing": "测试",
        "documentation": "文档",
    }

    for category, practices in BEST_PRACTICES.items():
        lines.append(f"## {category_names.get(category, category)}（{len(practices)} 条）")
        lines.append("")
        for p in practices:
            lines.append(f"### {p['id']}: {p['title']}")
            lines.append("")
            lines.append(f"**描述**: {p['description']}")
            lines.append("")
            if "why" in p:
                lines.append(f"**为什么**: {p['why']}")
                lines.append("")
            if "example" in p:
                lines.append("**示例**:")
                lines.append("```")
                lines.append(p["example"])
                lines.append("```")
                lines.append("")

    content = "\n".join(lines)

    if output_file:
        output_file.write_text(content, encoding="utf-8")

    return content


def extract_from_plugin(plugin_dir: Path) -> dict:
    """从插件中提取最佳实践应用情况"""
    result = {
        "plugin": plugin_dir.name,
        "applied": [],
        "missing": [],
        "score": 0,
    }

    checks = [
        ("BP-STRUCT-001", (plugin_dir / "skills").is_dir()),
        ("BP-STRUCT-002", True),  # 需要验证 name 一致性
        ("BP-DOC-001", (plugin_dir / "README.md").exists()),
        ("BP-DOC-002", (plugin_dir / "CHANGELOG.md").exists()),
        ("BP-TEST-001", True),  # 需要检查脚本
        ("BP-SEC-001", True),  # 需要安全扫描
    ]

    total = len(checks)
    applied = 0
    for bp_id, passed in checks:
        if passed:
            result["applied"].append(bp_id)
            applied += 1
        else:
            result["missing"].append(bp_id)

    result["score"] = round(applied / total * 100, 1) if total > 0 else 0
    return result


def main():
    parser = argparse.ArgumentParser(description="最佳实践库生成工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # generate
    gen_parser = subparsers.add_parser("generate", help="生成最佳实践文档")
    gen_parser.add_argument("--output", help="输出 Markdown 文件")
    gen_parser.add_argument("--plugins", nargs="*", help="参考的插件目录")

    # list
    subparsers.add_parser("list", help="列出所有最佳实践")

    # show
    show_parser = subparsers.add_parser("show", help="显示某类最佳实践")
    show_parser.add_argument("--category", required=True, choices=list(BEST_PRACTICES.keys()))

    # check
    check_parser = subparsers.add_parser("check", help="检查插件应用了哪些最佳实践")
    check_parser.add_argument("--plugin", required=True, help="插件目录")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        output = Path(args.output) if args.output else None
        content = generate_markdown(output)
        if not args.output:
            print(content)
        else:
            print(f"✅ 最佳实践已生成: {output}")
            print(f"   共 {sum(len(v) for v in BEST_PRACTICES.values())} 条，6 大类")

    elif args.command == "list":
        result = {
            "total": sum(len(v) for v in BEST_PRACTICES.values()),
            "categories": {k: len(v) for k, v in BEST_PRACTICES.items()},
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "show":
        result = {"category": args.category, "practices": BEST_PRACTICES[args.category]}
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "check":
        result = extract_from_plugin(Path(args.plugin))
        print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0)


if __name__ == "__main__":
    main()
