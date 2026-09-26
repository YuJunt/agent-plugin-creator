#!/usr/bin/env python3
"""
Plugin Marketplace 元数据生成器

生成符合 GitHub Copilot Marketplace 格式的 marketplace.json，
用于将插件发布到插件市场。

格式参考：
  - .github/plugin/marketplace.json（GitHub Copilot）
  - https://chris-ayers.com/posts/agent-skills-plugins-marketplace/

用法:
    python3 scripts/generate_markplace_json.py --plugin ./my-plugin
    python3 scripts/generate_markplace_json.py --plugin ./my-plugin --owner "My Team" --email team@example.com
"""
import argparse
import json
import sys
from pathlib import Path


def generate_marketplace_json(plugin_dir: Path, owner_name: str = None,
                              owner_email: str = None) -> dict:
    """生成 marketplace.json 内容"""
    plugin_json_path = plugin_dir / "plugin.json"
    if not plugin_json_path.exists():
        print(f"错误: plugin.json 不存在: {plugin_json_path}", file=sys.stderr)
        sys.exit(1)

    plugin = json.loads(plugin_json_path.read_text(encoding="utf-8"))

    # 收集 skills
    skills = []
    skills_dir = plugin_dir / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            # 简单解析 frontmatter
            content = skill_md.read_text(encoding="utf-8", errors="ignore")
            name = skill_dir.name
            desc = ""
            for line in content.split("\n"):
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                    break
            skills.append({
                "name": name,
                "description": desc,
                "path": f"skills/{name}",
            })

    # 收集 MCP servers
    mcp_servers = []
    mcp_json_path = plugin_dir / "mcp.json"
    if mcp_json_path.exists():
        mcp = json.loads(mcp_json_path.read_text(encoding="utf-8"))
        for server_name in mcp.get("mcpServers", {}):
            mcp_servers.append(server_name)

    # 构建 marketplace entry
    entry = {
        "name": plugin["name"],
        "version": plugin["version"],
        "description": plugin.get("description", ""),
        "author": plugin.get("author", {}),
        "license": plugin.get("license", "MIT"),
        "category": plugin.get("category", "other"),
        "tags": plugin.get("keywords", plugin.get("tags", [])),
        "homepage": plugin.get("homepage", ""),
        "repository": plugin.get("repository", ""),
    }

    if skills:
        entry["skills"] = skills
    if mcp_servers:
        entry["mcpServers"] = mcp_servers

    # 完整 marketplace.json 结构
    marketplace = {
        "name": f"{plugin['name']}-marketplace",
        "owner": {
            "name": owner_name or plugin.get("author", {}).get("name", "Unknown"),
            "email": owner_email or plugin.get("author", {}).get("email", ""),
        },
        "metadata": {
            "description": f"Marketplace for {plugin['name']}",
            "version": "1.0.0",
        },
        "plugins": [entry],
    }

    return marketplace


def main():
    parser = argparse.ArgumentParser(description="Plugin Marketplace 元数据生成器")
    parser.add_argument("--plugin", required=True, help="插件目录路径")
    parser.add_argument("--owner-name", help="市场所有者名称")
    parser.add_argument("--owner-email", help="市场所有者邮箱")
    parser.add_argument("--output", help="输出文件路径（默认写到插件目录）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出到 stdout")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin).resolve()
    if not plugin_dir.exists():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    marketplace = generate_marketplace_json(
        plugin_dir, owner_name=args.owner_name, owner_email=args.owner_email
    )

    if args.json:
        print(json.dumps(marketplace, ensure_ascii=False, indent=2))
    else:
        output_path = Path(args.output) if args.output else (plugin_dir / "marketplace.json")
        output_path.write_text(json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(f"✅ marketplace.json 已生成: {output_path}")
        print(f"   插件数: {len(marketplace['plugins'])}")
        print(f"   Skills: {len(marketplace['plugins'][0].get('skills', []))}")
        print(f"   MCP Servers: {len(marketplace['plugins'][0].get('mcpServers', []))}")


if __name__ == "__main__":
    main()
