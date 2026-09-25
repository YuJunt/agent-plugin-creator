#!/usr/bin/env python3
"""
插件配置导出工具（配置文件热加载）

从已有插件读取配置，导出为 wizard 可用的 config.json，修改后可重新生成。

用法:
    python3 scripts/export_config.py <插件目录> --output config.json
    python3 scripts/export_config.py <插件目录> --stdout
    python3 scripts/export_config.py <插件目录> --include-servers
"""
import argparse
import json
import sys
from pathlib import Path


def export_plugin_config(plugin_dir: Path, include_servers: bool = False) -> dict:
    """从已有插件导出配置"""
    config = {
        "name": plugin_dir.name,
        "version": "0.1.0",
        "description": "",
        "components": {
            "skills": [],
            "mcp_servers": [],
        },
        "target_clients": [],
    }

    # 读取 plugin.json
    plugin_json = plugin_dir / "plugin.json"
    if plugin_json.exists():
        try:
            plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
            config["name"] = plugin.get("name", plugin_dir.name)
            config["version"] = plugin.get("version", "0.1.0")
            config["description"] = plugin.get("description", "")
            if "license" in plugin:
                config["license"] = plugin["license"]
            if "keywords" in plugin:
                config["keywords"] = plugin["keywords"]
        except json.JSONDecodeError:
            pass

    # 读取 skills
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            skill_config = {"name": skill_dir.name, "description": ""}
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8")
                # 提取 frontmatter
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        frontmatter = content[3:end]
                        for line in frontmatter.split("\n"):
                            line = line.strip()
                            if line.startswith("description:"):
                                skill_config["description"] = line.split(":", 1)[1].strip()
                                break
            config["components"]["skills"].append(skill_config)

    # 读取 mcp.json
    mcp_json = plugin_dir / "mcp.json"
    if mcp_json.exists():
        try:
            mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
            for server_name, server_config in mcp.get("mcpServers", {}).items():
                server = {
                    "name": server_name,
                    "language": "python",
                    "transport": server_config.get("type", "stdio"),
                    "tools": [],
                }

                # 检测语言
                command = server_config.get("command", "")
                if "node" in command:
                    server["language"] = "typescript"

                # 如果包含服务器代码，尝试提取工具
                server_dir = plugin_dir / "servers" / server_name
                if server_dir.exists() and include_servers:
                    server["tools"] = _extract_tools_from_server(server_dir, server["language"])

                config["components"]["mcp_servers"].append(server)
        except json.JSONDecodeError:
            pass

    # 检测目标客户端
    client_dirs = [".claude-plugin", ".cursor", "com.github.copilot", ".codex-plugin", ".gemini"]
    for cd in client_dirs:
        if (plugin_dir / cd).exists():
            client_name = cd.replace(".", "").replace("com.github.", "")
            config["target_clients"].append(client_name)

    if not config["target_clients"]:
        config["target_clients"] = ["all"]

    return config


def _extract_tools_from_server(server_dir: Path, language: str) -> list:
    """从服务器代码提取工具定义（简化版）"""
    tools = []

    if language == "python":
        for py_file in server_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                import ast
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for dec in node.decorator_list:
                            dec_str = ast.dump(dec)
                            if "tool" in dec_str:
                                tools.append({
                                    "name": node.name,
                                    "description": ast.get_docstring(node) or "",
                                    "parameters": {"type": "object", "properties": {}},
                                })
                                break
            except Exception:
                pass
    else:
        for ts_file in list(server_dir.rglob("*.ts")) + list(server_dir.rglob("*.js")):
            if "node_modules" in str(ts_file):
                continue
            try:
                import re
                content = ts_file.read_text(encoding="utf-8")
                pattern = r'server\.tool\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']'
                for match in re.finditer(pattern, content):
                    tools.append({
                        "name": match.group(1),
                        "description": match.group(2),
                        "parameters": {"type": "object", "properties": {}},
                    })
            except Exception:
                pass

    return tools


def main():
    parser = argparse.ArgumentParser(description="插件配置导出工具")
    parser.add_argument("plugin_dir", help="已有插件目录路径")
    parser.add_argument("--output", help="输出配置文件路径")
    parser.add_argument("--stdout", action="store_true", help="输出到标准输出")
    parser.add_argument("--include-servers", action="store_true", help="包含从服务器代码提取的工具定义")
    parser.add_argument("--pretty", action="store_true", default=True, help="格式化输出")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    if not (plugin_dir / "plugin.json").exists():
        print(f"错误: 目录中缺少 plugin.json: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    config = export_plugin_config(plugin_dir, include_servers=args.include_servers)

    output = json.dumps(config, ensure_ascii=False, indent=2) + "\n"

    if args.stdout or not args.output:
        print(output)
    else:
        output_path = Path(args.output).resolve()
        output_path.write_text(output, encoding="utf-8")
        print(f"✅ 配置已导出: {output_path}")
        print(f"   插件: {config['name']} v{config['version']}")
        print(f"   Skills: {len(config['components']['skills'])} 个")
        print(f"   MCP 服务器: {len(config['components']['mcp_servers'])} 个")
        print(f"   目标客户端: {', '.join(config['target_clients'])}")
        print()
        print("使用方法:")
        print(f"  1. 编辑 {output_path} 修改配置")
        print(f"  2. python3 scripts/wizard.py --config {output_path} --output <新目录>")


if __name__ == "__main__":
    main()
