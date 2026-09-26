#!/usr/bin/env python3
"""
插件完成度检查器

检测插件中 SKILL.md 和 MCP 服务器代码的 TODO 数量，
如果超过阈值就警告用户，确保插件不是空框架。

用法:
    python3 scripts/check_completion.py <plugin_dir>
    python3 scripts/check_completion.py <plugin_dir> --threshold 5
    python3 scripts/check_completion.py <plugin_dir> --json
"""
import argparse
import json
import sys
from pathlib import Path


def count_todos_in_file(file_path: Path) -> int:
    """统计文件中的 TODO 数量"""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return content.count("TODO") + content.count("todo")
    except (OSError, UnicodeDecodeError):
        return 0


def check_completion(plugin_dir: Path, threshold: int = 5) -> dict:
    """检查插件完成度"""
    result = {
        "plugin_dir": str(plugin_dir),
        "threshold": threshold,
        "skills": [],
        "mcp_servers": [],
        "total_todos": 0,
        "passed": True,
        "warnings": [],
        "suggestions": [],
    }

    # 1. 检查 skills/ 目录下的 SKILL.md
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                todos = count_todos_in_file(skill_md)
                result["total_todos"] += todos
                skill_result = {
                    "name": skill_dir.name,
                    "skill_md": str(skill_md.relative_to(plugin_dir)),
                    "todo_count": todos,
                    "status": "pass" if todos <= threshold else "warn",
                }
                result["skills"].append(skill_result)
                if todos > threshold:
                    result["warnings"].append(
                        f"Skill '{skill_dir.name}' 有 {todos} 个 TODO（阈值 {threshold}）"
                    )
                    result["suggestions"].append(
                        f"填充 {skill_dir.name}/SKILL.md 中的 TODO 占位符，"
                        f"或参考 examples/ 目录中的高质量示例"
                    )

    # 2. 检查 servers/ 目录下的 MCP 服务器代码
    servers_dir = plugin_dir / "servers"
    if servers_dir.is_dir():
        for server_dir in sorted(servers_dir.iterdir()):
            if not server_dir.is_dir():
                continue
            server_todos = 0
            server_files = []
            for code_file in server_dir.rglob("*.py"):
                todos = count_todos_in_file(code_file)
                if todos > 0:
                    server_todos += todos
                    server_files.append({
                        "file": str(code_file.relative_to(plugin_dir)),
                        "todo_count": todos,
                    })
            for code_file in server_dir.rglob("*.ts"):
                todos = count_todos_in_file(code_file)
                if todos > 0:
                    server_todos += todos
                    server_files.append({
                        "file": str(code_file.relative_to(plugin_dir)),
                        "todo_count": todos,
                    })

            result["total_todos"] += server_todos
            server_result = {
                "name": server_dir.name,
                "todo_count": server_todos,
                "files": server_files,
                "status": "pass" if server_todos <= threshold else "warn",
            }
            result["mcp_servers"].append(server_result)
            if server_todos > threshold:
                result["warnings"].append(
                    f"MCP 服务器 '{server_dir.name}' 有 {server_todos} 个 TODO"
                )
                result["suggestions"].append(
                    f"实现 {server_dir.name} 中 MCP 工具的业务逻辑，替换 TODO 占位符"
                )

    # 3. 总体判断
    if result["total_todos"] > threshold:
        result["passed"] = False
        result["suggestions"].insert(0,
            f"插件共有 {result['total_todos']} 个 TODO，建议填充后再发布"
        )
    else:
        result["suggestions"].append(
            f"插件完成度良好（{result['total_todos']} 个 TODO，阈值 {threshold}）"
        )

    return result


def print_report(result: dict):
    """打印完成度检查报告"""
    print("=" * 60)
    print("插件完成度检查")
    print("=" * 60)
    print(f"插件目录: {result['plugin_dir']}")
    print(f"TODO 阈值: {result['threshold']}")
    print()

    if result["skills"]:
        print("Skills:")
        for skill in result["skills"]:
            icon = "✅" if skill["status"] == "pass" else "⚠️"
            print(f"  {icon} {skill['name']}: {skill['todo_count']} 个 TODO")
        print()

    if result["mcp_servers"]:
        print("MCP 服务器:")
        for server in result["mcp_servers"]:
            icon = "✅" if server["status"] == "pass" else "⚠️"
            print(f"  {icon} {server['name']}: {server['todo_count']} 个 TODO")
            for f in server.get("files", []):
                print(f"     - {f['file']}: {f['todo_count']} 个")
        print()

    print("-" * 60)
    print(f"总计: {result['total_todos']} 个 TODO")
    print()

    if result["warnings"]:
        print("⚠️  警告:")
        for w in result["warnings"]:
            print(f"  - {w}")
        print()

    if result["suggestions"]:
        print("💡 建议:")
        for s in result["suggestions"]:
            print(f"  - {s}")
        print()

    print("=" * 60)
    if result["passed"]:
        print("✅ 插件完成度检查通过")
    else:
        print("❌ 插件完成度检查未通过（TODO 数量超过阈值）")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="插件完成度检查器")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--threshold", type=int, default=5,
                        help="TODO 数量阈值（默认 5，超过则警告）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.exists():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    result = check_completion(plugin_dir, args.threshold)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result)

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
