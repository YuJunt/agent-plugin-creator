#!/usr/bin/env python3
"""
MCP v1 → v2 迁移辅助工具

帮助用户从旧版 MCP v1（有状态模式）迁移到 v2（2026-07-28 无状态模式）。
自动检测旧版代码中的模式，并提供迁移指导。

用法:
    python3 scripts/migrate_mcp_v2.py --project ./my-mcp-server
    python3 scripts/migrate_mcp_v2.py --project ./my-mcp-server --dry-run
"""
import argparse
import json
import re
import sys
from pathlib import Path


# v1 → v2 迁移规则
MIGRATION_RULES = [
    {
        "id": "INITIALIZE_REMOVAL",
        "name": "移除 initialize 握手",
        "v1_pattern": r"server\.tool\(|new McpServer\(|await server\.connect\(",
        "v2_pattern": "直接注册工具，无需 initialize",
        "description": "v2 无状态模式移除了 initialize 握手，客户端直接发送 tools/list",
        "severity": "high",
        "auto_fix": False,
    },
    {
        "id": "SESSION_ID_REMOVAL",
        "name": "移除 mcp-session-id",
        "v1_pattern": r"mcp-session-id|McpSessionId|sessionId",
        "v2_pattern": "每个请求自包含，无需 session id",
        "description": "v2 移除了会话 ID，所有请求自包含",
        "severity": "high",
        "auto_fix": False,
    },
    {
        "id": "ROOTS_DEPRECATED",
        "name": "Roots 功能弃用",
        "v1_pattern": r"setRequestHandler\(.*roots|roots/list|listRoots",
        "v2_replacement": "用工具参数、资源 URI 或服务器配置",
        "description": "Roots 在 v2 中已弃用，用工具参数替代",
        "severity": "medium",
        "auto_fix": False,
    },
    {
        "id": "SAMPLING_DEPRECATED",
        "name": "Sampling 功能弃用",
        "v1_pattern": r"createMessage|sampling/create|requestSampling",
        "v2_replacement": "直接集成 LLM 提供商 API",
        "description": "Sampling 在 v2 中已弃用，直接调用 LLM API",
        "severity": "medium",
        "auto_fix": False,
    },
    {
        "id": "LOGGING_DEPRECATED",
        "name": "Logging 功能弃用",
        "v1_pattern": r"setLoggingLevel|logging/setLevel|sendLoggingMessage",
        "v2_replacement": "stdio 用 stderr，结构化观测用 OpenTelemetry",
        "description": "Logging 在 v2 中已弃用，用 stderr 或 OpenTelemetry",
        "severity": "low",
        "auto_fix": False,
    },
    {
        "id": "TOOL_METHOD_RENAME",
        "name": ".tool() → registerTool()",
        "v1_pattern": r"server\.tool\(",
        "v2_replacement": "server.registerTool()",
        "description": "TypeScript SDK v2 中 .tool() 重命名为 registerTool()",
        "severity": "low",
        "auto_fix": True,
        "codemod": "npx @modelcontextprotocol/codemod@beta v1-to-v2 .",
    },
]


def analyze_project(project_dir: Path) -> dict:
    """分析项目中需要迁移的代码"""
    results = {
        "project": str(project_dir),
        "language": "unknown",
        "files_scanned": 0,
        "findings": [],
        "summary": {"high": 0, "medium": 0, "low": 0, "auto_fixable": 0},
    }

    # 检测语言
    if (project_dir / "package.json").exists():
        results["language"] = "typescript"
        code_files = list(project_dir.rglob("*.ts")) + list(project_dir.rglob("*.js"))
    elif (project_dir / "pyproject.toml").exists() or (project_dir / "server.py").exists():
        results["language"] = "python"
        code_files = list(project_dir.rglob("*.py"))
    else:
        code_files = []

    # 过滤排除目录
    exclude_dirs = {"node_modules", "__pycache__", ".git", "dist", "build"}
    code_files = [f for f in code_files if not any(d in str(f) for d in exclude_dirs)]

    results["files_scanned"] = len(code_files)

    # 扫描每个文件
    for f in code_files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for rule in MIGRATION_RULES:
            matches = list(re.finditer(rule["v1_pattern"], content, re.IGNORECASE))
            if matches:
                results["findings"].append({
                    "file": str(f.relative_to(project_dir)),
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "severity": rule["severity"],
                    "match_count": len(matches),
                    "description": rule["description"],
                    "replacement": rule.get("v2_replacement", rule.get("v2_pattern", "")),
                    "auto_fixable": rule["auto_fix"],
                    "line_numbers": [content[:m.start()].count("\n") + 1 for m in matches[:5]],
                })
                results["summary"][rule["severity"]] += 1
                if rule["auto_fix"]:
                    results["summary"]["auto_fixable"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="MCP v1 → v2 迁移辅助工具")
    parser.add_argument("--project", required=True, help="MCP 服务器项目目录")
    parser.add_argument("--dry-run", action="store_true", help="只检测不修复")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    project_dir = Path(args.project).resolve()
    if not project_dir.exists():
        print(f"错误: 项目目录不存在: {project_dir}", file=sys.stderr)
        sys.exit(1)

    results = analyze_project(project_dir)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("=" * 70)
        print("MCP v1 → v2 迁移分析报告")
        print("=" * 70)
        print(f"\n项目: {results['project']}")
        print(f"语言: {results['language']}")
        print(f"扫描文件: {results['files_scanned']}")

        print(f"\n发现问题:")
        print(f"  高: {results['summary']['high']}")
        print(f"  中: {results['summary']['medium']}")
        print(f"  低: {results['summary']['low']}")
        print(f"  可自动修复: {results['summary']['auto_fixable']}")

        if results["findings"]:
            print(f"\n详细发现:")
            for f in results["findings"]:
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[f["severity"]]
                fix_icon = "🔧" if f["auto_fixable"] else "  "
                print(f"\n  {icon}{fix_icon} [{f['rule_id']}] {f['rule_name']}")
                print(f"     文件: {f['file']}:{f['line_numbers']}")
                print(f"     说明: {f['description']}")
                print(f"     替代: {f['replacement']}")

        # 迁移建议
        print(f"\n{'=' * 70}")
        if results["summary"]["high"] > 0:
            print("⚠️  发现高优先级迁移项，建议尽快迁移")
        else:
            print("✅ 未发现高优先级迁移项")

        if results["summary"]["auto_fixable"] > 0:
            print("\n💡 可自动修复的项，使用官方 codemod:")
            print("   npx @modelcontextprotocol/codemod@beta v1-to-v2 .")

        print("=" * 70)

    sys.exit(0 if results["summary"]["high"] == 0 else 1)


if __name__ == "__main__":
    main()
