#!/usr/bin/env python3
"""
插件组合器

将多个插件合并成一个超级插件，自动处理 Skill 和 MCP 服务器冲突。

用法:
    python3 scripts/combine_plugins.py <plugin1> <plugin2> ... --output <合并目录>
    python3 scripts/combine_plugins.py ./plugin-a ./plugin-b --output ./super-plugin
    python3 scripts/combine_plugins.py ./p1 ./p2 --name super-plugin --json
"""
import argparse
import json
import shutil
import sys
from pathlib import Path


def load_plugin(plugin_dir: Path) -> dict:
    """加载插件配置"""
    plugin_json = plugin_dir / "plugin.json"
    if not plugin_json.exists():
        print(f"错误: 缺少 plugin.json: {plugin_dir}", file=sys.stderr)
        sys.exit(1)
    return json.loads(plugin_json.read_text(encoding="utf-8"))


def load_mcp(plugin_dir: Path) -> dict | None:
    """加载 MCP 配置"""
    mcp_json = plugin_dir / "mcp.json"
    if mcp_json.exists():
        return json.loads(mcp_json.read_text(encoding="utf-8"))
    return None


def combine_plugins(plugin_dirs: list, output_dir: Path, name: str, version: str) -> dict:
    """合并多个插件"""
    result = {
        "name": name,
        "version": version,
        "skills": [],
        "mcp_servers": {},
        "conflicts": [],
        "merged_from": [],
    }

    # 创建输出目录结构
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "skills").mkdir(exist_ok=True)
    (output_dir / "servers").mkdir(exist_ok=True)

    all_skills = set()
    all_mcp_servers = {}

    for i, plugin_dir in enumerate(plugin_dirs):
        plugin_dir = Path(plugin_dir).resolve()
        plugin = load_plugin(plugin_dir)
        plugin_name = plugin.get("name", f"plugin-{i}")
        result["merged_from"].append(plugin_name)

        # 合并 Skills
        skills_dir = plugin_dir / "skills"
        if skills_dir.is_dir():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_name = skill_dir.name

                # 处理冲突
                if skill_name in all_skills:
                    new_name = f"{plugin_name}-{skill_name}"
                    result["conflicts"].append({
                        "type": "skill",
                        "original": skill_name,
                        "renamed_to": new_name,
                        "from": plugin_name,
                    })
                    skill_name = new_name

                # 复制 Skill
                dest = output_dir / "skills" / skill_name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(skill_dir, dest)
                all_skills.add(skill_name)
                result["skills"].append(skill_name)

        # 合并 MCP 服务器
        mcp = load_mcp(plugin_dir)
        if mcp:
            for server_name, server_config in mcp.get("mcpServers", {}).items():
                # 处理冲突
                if server_name in all_mcp_servers:
                    new_name = f"{plugin_name}-{server_name}"
                    result["conflicts"].append({
                        "type": "mcp_server",
                        "original": server_name,
                        "renamed_to": new_name,
                        "from": plugin_name,
                    })
                    server_name = new_name

                all_mcp_servers[server_name] = server_config

                # 复制服务器代码
                server_dir = plugin_dir / "servers" / server_name
                if server_dir.exists():
                    dest = output_dir / "servers" / server_name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(server_dir, dest)

    # 生成 plugin.json
    plugin_json = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": name,
        "version": version,
        "description": f"Combined plugin from: {', '.join(result['merged_from'])}",
        "extensions": {
            "agent-plugin-creator": {
                "combined_from": result["merged_from"],
                "conflicts_resolved": len(result["conflicts"]),
            }
        }
    }
    (output_dir / "plugin.json").write_text(
        json.dumps(plugin_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 生成 mcp.json
    if all_mcp_servers:
        mcp_json = {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": all_mcp_servers,
        }
        (output_dir / "mcp.json").write_text(
            json.dumps(mcp_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        result["mcp_servers"] = list(all_mcp_servers.keys())

    return result


def main():
    parser = argparse.ArgumentParser(description="插件组合器")
    parser.add_argument("plugins", nargs="+", help="要合并的插件目录列表")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--name", help="合并后插件名称（默认 super-plugin）")
    parser.add_argument("--version", default="1.0.0", help="合并后版本号")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--force", action="store_true", help="覆盖已有输出目录")
    args = parser.parse_args()

    if len(args.plugins) < 2:
        print("错误: 至少需要 2 个插件才能合并", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output).resolve()
    if output_dir.exists():
        if not args.force:
            print(f"错误: 输出目录已存在: {output_dir}（使用 --force 覆盖）", file=sys.stderr)
            sys.exit(1)
        shutil.rmtree(output_dir)

    name = args.name or "super-plugin"
    # 确保 plugin name 与目录名一致（Agent Plugins 规范要求）
    if output_dir.name != name:
        print(f"⚠️  注意: 输出目录名 '{output_dir.name}' 与 name '{name}' 不一致")
        print(f"   已自动将 plugin name 更新为 '{output_dir.name}'（符合 Agent Plugins 规范要求）")
        name = output_dir.name
    result = combine_plugins(args.plugins, output_dir, name, args.version)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("插件合并完成")
        print("=" * 50)
        print(f"合并插件: {len(args.plugins)} 个")
        print(f"  来源: {', '.join(result['merged_from'])}")
        print(f"输出: {output_dir}")
        print(f"名称: {name} v{args.version}")
        print()
        print(f"合并结果:")
        print(f"  Skills: {len(result['skills'])} 个")
        for s in result["skills"]:
            print(f"    - {s}")
        print(f"  MCP 服务器: {len(result['mcp_servers'])} 个")
        for s in result["mcp_servers"]:
            print(f"    - {s}")
        print()
        if result["conflicts"]:
            print(f"冲突解决: {len(result['conflicts'])} 个")
            for c in result["conflicts"]:
                print(f"  [{c['type']}] {c['original']} → {c['renamed_to']} (来自 {c['from']})")
        else:
            print("无冲突")
        print("=" * 50)

    sys.exit(0)


if __name__ == "__main__":
    main()
