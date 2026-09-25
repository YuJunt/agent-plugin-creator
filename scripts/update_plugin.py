#!/usr/bin/env python3
"""
插件增量更新工具

支持对已有插件的增量更新，不需要每次重新生成整个插件。

用法:
    # 添加一个 skill
    python3 scripts/update_plugin.py <插件目录> --add-skill <skill目录>

    # 删除一个 skill
    python3 scripts/update_plugin.py <插件目录> --remove-skill <skill-name>

    # 添加 MCP 工具
    python3 scripts/update_plugin.py <插件目录> --add-mcp-tool <server-name> --tool tool.json

    # 删除 MCP 工具
    python3 scripts/update_plugin.py <插件目录> --remove-mcp-tool <server-name> --tool <tool-name>

    # 更新版本号
    python3 scripts/update_plugin.py <插件目录> --bump-version patch|minor|major

    # 查看当前插件状态
    python3 scripts/update_plugin.py <插件目录> --status
"""
import argparse
import json
import shutil
import sys
from pathlib import Path


def load_plugin(plugin_dir: Path) -> dict:
    """加载 plugin.json"""
    plugin_path = plugin_dir / "plugin.json"
    if not plugin_path.exists():
        print(f"错误: 插件目录缺少 plugin.json: {plugin_path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(plugin_path.read_text(encoding="utf-8"))


def save_plugin(plugin_dir: Path, plugin: dict):
    """保存 plugin.json"""
    (plugin_dir / "plugin.json").write_text(
        json.dumps(plugin, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_mcp(plugin_dir: Path) -> dict | None:
    """加载 mcp.json（如存在）"""
    mcp_path = plugin_dir / "mcp.json"
    if not mcp_path.exists():
        return None
    return json.loads(mcp_path.read_text(encoding="utf-8"))


def save_mcp(plugin_dir: Path, mcp: dict):
    """保存 mcp.json"""
    (plugin_dir / "mcp.json").write_text(
        json.dumps(mcp, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def cmd_status(plugin_dir: Path):
    """查看插件状态"""
    plugin = load_plugin(plugin_dir)
    mcp = load_mcp(plugin_dir)

    print("=" * 50)
    print(f"插件: {plugin.get('name', 'unknown')} v{plugin.get('version', '?')}")
    print("=" * 50)

    # Skills
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
        print(f"\nSkills ({len(skills)}):")
        for s in skills:
            print(f"  - {s}")
    else:
        print("\nSkills: 无")

    # MCP 服务器
    if mcp and "mcpServers" in mcp:
        servers = mcp["mcpServers"]
        print(f"\nMCP 服务器 ({len(servers)}):")
        for name, config in servers.items():
            server_type = config.get("type", "unknown")
            if server_type == "stdio":
                cmd = config.get("command", "?")
                print(f"  - {name} (stdio: {cmd})")
            else:
                url = config.get("url", "?")
                print(f"  - {name} ({server_type}: {url})")
    else:
        print("\nMCP 服务器: 无")

    # 文件统计
    total_files = sum(1 for _ in plugin_dir.rglob("*") if _.is_file())
    print(f"\n文件总数: {total_files}")
    print("=" * 50)


def cmd_add_skill(plugin_dir: Path, skill_path: Path):
    """添加一个 skill"""
    if not skill_path.is_dir():
        print(f"错误: Skill 目录不存在: {skill_path}", file=sys.stderr)
        sys.exit(1)
    if not (skill_path / "SKILL.md").exists():
        print(f"错误: Skill 目录缺少 SKILL.md: {skill_path}", file=sys.stderr)
        sys.exit(1)

    skill_name = skill_path.name
    dest = plugin_dir / "skills" / skill_name

    if dest.exists():
        print(f"错误: Skill 已存在: {skill_name}（使用 --force 覆盖）", file=sys.stderr)
        sys.exit(1)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_path, dest)
    print(f"✅ 已添加 Skill: {skill_name}")


def cmd_remove_skill(plugin_dir: Path, skill_name: str):
    """删除一个 skill"""
    skill_dir = plugin_dir / "skills" / skill_name
    if not skill_dir.exists():
        print(f"错误: Skill 不存在: {skill_name}", file=sys.stderr)
        sys.exit(1)

    shutil.rmtree(skill_dir)
    print(f"✅ 已删除 Skill: {skill_name}")

    # 如果 skills 目录空了，删除它
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir() and not any(skills_dir.iterdir()):
        skills_dir.rmdir()


def cmd_add_mcp_tool(plugin_dir: Path, server_name: str, tool_file: Path):
    """添加 MCP 工具到服务器代码"""
    mcp = load_mcp(plugin_dir)
    if not mcp:
        print("错误: 插件没有 mcp.json", file=sys.stderr)
        sys.exit(1)

    if server_name not in mcp.get("mcpServers", {}):
        print(f"错误: MCP 服务器不存在: {server_name}", file=sys.stderr)
        sys.exit(1)

    if not tool_file.exists():
        print(f"错误: 工具定义文件不存在: {tool_file}", file=sys.stderr)
        sys.exit(1)

    tool_def = json.loads(tool_file.read_text(encoding="utf-8"))
    tool_name = tool_def.get("name", "")

    # 找到服务器目录
    server_config = mcp["mcpServers"][server_name]
    server_dir = plugin_dir / "servers" / server_name

    if not server_dir.exists():
        print(f"错误: 服务器目录不存在: {server_dir}", file=sys.stderr)
        sys.exit(1)

    # 根据语言添加工具
    py_file = server_dir / "server.py"
    ts_file = server_dir / "src" / "server.ts"

    if py_file.exists():
        _add_tool_to_python(py_file, tool_def)
        print(f"✅ 已添加 MCP 工具到 Python 服务器: {tool_name}")
    elif ts_file.exists():
        _add_tool_to_typescript(ts_file, tool_def)
        print(f"✅ 已添加 MCP 工具到 TypeScript 服务器: {tool_name}")
    else:
        print(f"⚠️  未找到服务器入口文件，请手动添加工具: {tool_name}")


def _add_tool_to_python(py_file: Path, tool_def: dict):
    """向 Python FastMCP 服务器添加工具"""
    content = py_file.read_text(encoding="utf-8")
    tool_name = tool_def["name"]
    tool_desc = tool_def.get("description", "")
    params = tool_def.get("parameters", {})

    # 生成参数签名
    param_strs = []
    for pname, pschema in params.get("properties", {}).items():
        ptype = pschema.get("type", "str")
        py_type = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}.get(ptype, "str")
        default = ""
        if pname not in params.get("required", []):
            default = " = None"
        param_strs.append(f"{pname}: {py_type}{default}")

    params_code = ", ".join(param_strs)

    tool_code = f'''

@mcp.tool()
def {tool_name}({params_code}) -> str:
    """{tool_desc}"""
    # TODO: 实现工具逻辑
    return json.dumps({{"status": "ok", "tool": "{tool_name}"}})
'''

    # 在文件末尾添加（如果有 if __name__ 则在之前）
    if 'if __name__' in content:
        content = content.replace('if __name__', tool_code + '\nif __name__')
    else:
        content += tool_code

    py_file.write_text(content, encoding="utf-8")


def _add_tool_to_typescript(ts_file: Path, tool_def: dict):
    """向 TypeScript MCP 服务器添加工具（占位实现）"""
    content = ts_file.read_text(encoding="utf-8")
    tool_name = tool_def["name"]
    tool_desc = tool_def.get("description", "")

    tool_code = f'''
server.tool("{tool_name}", "{tool_desc}", {{
  // TODO: 定义输入 schema
}}, async (params) => {{
  return {{ content: [{{ type: "text", text: JSON.stringify({{ status: "ok", tool: "{tool_name}" }}) }}] }};
}});
'''

    if 'server.listen' in content:
        content = content.replace('server.listen', tool_code + '\nserver.listen')
    else:
        content += tool_code

    ts_file.write_text(content, encoding="utf-8")


def cmd_bump_version(plugin_dir: Path, level: str):
    """升级版本号"""
    plugin = load_plugin(plugin_dir)
    current = plugin.get("version", "0.1.0")

    try:
        major, minor, patch = map(int, current.split("."))
    except (ValueError, AttributeError):
        print(f"错误: 无法解析版本号: {current}", file=sys.stderr)
        sys.exit(1)

    if level == "patch":
        patch += 1
    elif level == "minor":
        minor += 1
        patch = 0
    elif level == "major":
        major += 1
        minor = 0
        patch = 0

    new_version = f"{major}.{minor}.{patch}"
    plugin["version"] = new_version
    save_plugin(plugin_dir, plugin)
    print(f"✅ 版本号: {current} → {new_version}")


def main():
    parser = argparse.ArgumentParser(description="插件增量更新工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--status", action="store_true", help="查看插件状态")
    parser.add_argument("--add-skill", help="添加 Skill（指定 Skill 目录路径）")
    parser.add_argument("--remove-skill", help="删除 Skill（指定 Skill 名称）")
    parser.add_argument("--add-mcp-tool", help="添加 MCP 工具（指定服务器名称）")
    parser.add_argument("--remove-mcp-tool", help="删除 MCP 工具（指定服务器名称）")
    parser.add_argument("--tool", help="MCP 工具定义文件路径或工具名称")
    parser.add_argument("--bump-version", choices=["patch", "minor", "major"], help="升级版本号")
    parser.add_argument("--force", action="store_true", help="强制覆盖")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    if args.status:
        cmd_status(plugin_dir)
    elif args.add_skill:
        cmd_add_skill(plugin_dir, Path(args.add_skill).resolve())
    elif args.remove_skill:
        cmd_remove_skill(plugin_dir, args.remove_skill)
    elif args.add_mcp_tool and args.tool:
        cmd_add_mcp_tool(plugin_dir, args.add_mcp_tool, Path(args.tool).resolve())
    elif args.bump_version:
        cmd_bump_version(plugin_dir, args.bump_version)
    else:
        parser.print_help()
        print("\n提示: 使用 --status 查看当前插件状态", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
