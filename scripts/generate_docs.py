#!/usr/bin/env python3
"""
Agent Plugin 文档自动生成工具

从 plugin.json + skills/ + mcp.json + servers/ 自动生成 README.md 文档。

生成的文档包含：
  - 插件标题、描述、版本、作者、许可证
  - 功能特性列表
  - 安装说明
  - 使用方法
  - 技能列表（每个 skill 的名称、描述、工作流摘要）
  - MCP 服务器和工具列表
  - 配置说明
  - 兼容性说明
  - 开发说明

用法:
    python3 generate_docs.py <插件目录路径>
    python3 generate_docs.py ./my-plugin --output README.md
    python3 generate_docs.py ./my-plugin --force
"""
import argparse
import json
import re
import sys
from pathlib import Path
from _common import load_plugin_json



def parse_skill_md(skill_md_path: Path) -> dict:
    """解析 SKILL.md，提取 frontmatter 和 body 摘要"""
    info = {"name": skill_md_path.parent.name, "description": "", "body": "", "sections": []}
    if not skill_md_path.exists():
        return info

    content = skill_md_path.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            for line in fm.split("\n"):
                line = line.strip()
                if line.startswith("name:"):
                    info["name"] = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("description:"):
                    info["description"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            info["body"] = parts[2].strip()

    # 提取主要章节标题
    for line in info["body"].split("\n"):
        if line.startswith("## "):
            info["sections"].append(line[3:].strip())

    return info


def load_mcp_json(plugin_dir: Path) -> dict:
    """加载 mcp.json"""
    mcp_json = plugin_dir / "mcp.json"
    if not mcp_json.exists():
        return {}
    try:
        return json.loads(mcp_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def extract_tools_from_server(server_dir: Path) -> list:
    """从 MCP 服务器代码中提取工具列表"""
    tools = []
    code_extensions = {".py", ".js", ".ts"}

    for code_file in server_dir.rglob("*"):
        if not code_file.is_file() or code_file.suffix not in code_extensions:
            continue
        if "node_modules" in code_file.parts or "__pycache__" in code_file.parts:
            continue

        try:
            content = code_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # TypeScript: server.tool("name", "description", ...)
        for match in re.finditer(r'server\.tool\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']', content):
            tools.append({"name": match.group(1), "description": match.group(2), "source": code_file.name})

        # Python: @mcp.tool() \n def name(...):
        for match in re.finditer(r'@mcp\.tool\(\)\s*\n\s*def\s+(\w+)\s*\([^)]*\)\s*(?::[^"\']*)?(?:"""([^"]*)""")?', content):
            name = match.group(1)
            desc = match.group(2) or ""
            # 取 docstring 第一行
            if desc:
                desc = desc.strip().split("\n")[0].strip()
            tools.append({"name": name, "description": desc, "source": code_file.name})

    # 去重
    seen = set()
    unique_tools = []
    for t in tools:
        if t["name"] not in seen:
            seen.add(t["name"])
            unique_tools.append(t)
    return unique_tools


def generate_readme(plugin_dir: Path, plugin: dict, skills: list, mcp: dict, servers_tools: dict) -> str:
    """生成 README.md 内容"""
    lines = []

    # 标题
    name = plugin.get("name", "my-plugin")
    version = plugin.get("version", "0.1.0")
    description = plugin.get("description", "")
    author = plugin.get("author", {})
    if isinstance(author, dict):
        author_name = author.get("name", "")
    else:
        author_name = str(author)
    license_name = plugin.get("license", "MIT")
    keywords = plugin.get("keywords", [])

    lines.append(f"# {name}")
    lines.append("")
    if description:
        lines.append(f"> {description}")
        lines.append("")

    # 元信息徽章
    badges = []
    badges.append(f"![Version](https://img.shields.io/badge/version-{version}-blue)")
    badges.append(f"![License](https://img.shields.io/badge/license-{license_name}-green)")
    if skills:
        badges.append(f"![Skills](https://img.shields.io/badge/skills-{len(skills)}-purple)")
    if mcp:
        server_count = len(mcp.get("mcpServers", {}))
        badges.append(f"![MCP Servers](https://img.shields.io/badge/MCP-{server_count}-orange)")
    lines.append(" ".join(badges))
    lines.append("")

    # 功能特性
    lines.append("## 功能特性")
    lines.append("")
    features = []
    if skills:
        features.append(f"- 包含 {len(skills)} 个 Agent Skill")
        for skill in skills:
            if skill["description"]:
                features.append(f"  - **{skill['name']}**: {skill['description'][:80]}")
    if mcp:
        server_count = len(mcp.get("mcpServers", {}))
        features.append(f"- 包含 {server_count} 个 MCP 服务器")
        for server_name in mcp.get("mcpServers", {}):
            server_tools = servers_tools.get(server_name, [])
            if server_tools:
                features.append(f"  - **{server_name}**: {len(server_tools)} 个工具")
    if keywords:
        features.append(f"- 关键词: {', '.join(keywords)}")
    if not features:
        features.append("- 待补充功能特性")
    lines.extend(features)
    lines.append("")

    # 安装说明
    lines.append("## 安装")
    lines.append("")
    lines.append("### 前置要求")
    lines.append("")
    lines.append("- 支持 Agent Plugins 1.0 标准的客户端（Claude Code、Cursor、VS Code Copilot、Codex 等）")
    if mcp:
        lines.append("- Node.js 18+ 或 Python 3.10+（取决于 MCP 服务器实现语言）")
    lines.append("")
    lines.append("### 安装步骤")
    lines.append("")
    lines.append("1. 将此插件目录复制到客户端的插件目录，或通过插件市场安装")
    lines.append("2. 在客户端配置中启用此插件")
    lines.append("3. 如果包含 MCP 服务器，确保已安装相应依赖：")
    if mcp:
        for server_name, server_config in mcp.get("mcpServers", {}).items():
            command = server_config.get("command", "")
            if "node" in command or "npx" in command or "tsx" in command:
                lines.append(f"   - `{server_name}`: `cd servers/{server_name} && npm install`")
            elif "python" in command:
                lines.append(f"   - `{server_name}`: `cd servers/{server_name} && pip install -e .`")
    lines.append("")

    # 使用方法
    lines.append("## 使用方法")
    lines.append("")
    if skills:
        lines.append("### Skills")
        lines.append("")
        lines.append("插件包含以下技能，在对话中提及相关场景时会自动触发：")
        lines.append("")
        for skill in skills:
            lines.append(f"#### {skill['name']}")
            lines.append("")
            if skill["description"]:
                lines.append(f"{skill['description']}")
                lines.append("")
            if skill["sections"]:
                lines.append("**主要功能:**")
                lines.append("")
                for section in skill["sections"][:5]:
                    lines.append(f"- {section}")
                lines.append("")
    if mcp:
        lines.append("### MCP 工具")
        lines.append("")
        for server_name, server_config in mcp.get("mcpServers", {}).items():
            lines.append(f"#### {server_name}")
            lines.append("")
            transport = "stdio" if server_config.get("command") else "streamable-http"
            lines.append(f"- **传输方式**: {transport}")
            if server_config.get("command"):
                lines.append(f"- **启动命令**: `{server_config['command']}`")
            if server_config.get("url"):
                lines.append(f"- **服务地址**: `{server_config['url']}`")
            lines.append("")
            server_tools = servers_tools.get(server_name, [])
            if server_tools:
                lines.append("**工具列表:**")
                lines.append("")
                lines.append("| 工具名 | 描述 |")
                lines.append("|--------|------|")
                for tool in server_tools:
                    lines.append(f"| `{tool['name']}` | {tool['description'][:60] if tool['description'] else '-'} |")
                lines.append("")
            else:
                lines.append("*工具列表请参考服务器源代码*")
                lines.append("")

    # 配置说明
    lines.append("## 配置")
    lines.append("")
    lines.append("### plugin.json")
    lines.append("")
    lines.append("插件的核心配置文件，包含插件元数据。")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps({k: plugin[k] for k in ["name", "version", "description"] if k in plugin}, indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    if mcp:
        lines.append("### mcp.json")
        lines.append("")
        lines.append("MCP 服务器配置文件，定义插件包含的 MCP 服务器。")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(mcp, indent=2, ensure_ascii=False)[:500])
        lines.append("```")
        lines.append("")

    # 兼容性
    lines.append("## 兼容性")
    lines.append("")
    lines.append("此插件符合 [Agent Plugins 1.0](https://github.com/agentplugins/agent-plugins-spec) 开放规范，支持以下客户端：")
    lines.append("")
    lines.append("- ✅ Claude Code")
    lines.append("- ✅ Cursor")
    lines.append("- ✅ VS Code (GitHub Copilot)")
    lines.append("- ✅ OpenAI Codex")
    lines.append("- ✅ Google Gemini (部分支持)")
    lines.append("")

    # 开发
    lines.append("## 开发")
    lines.append("")
    lines.append("### 目录结构")
    lines.append("")
    lines.append("```")
    lines.append(f"{name}/")
    lines.append("├── plugin.json          # 插件清单（必需）")
    if skills:
        lines.append("├── skills/              # Agent Skills")
        for skill in skills:
            lines.append(f"│   └── {skill['name']}/")
            lines.append("│       └── SKILL.md")
    if mcp:
        lines.append("├── mcp.json             # MCP 服务器配置")
        lines.append("├── servers/             # MCP 服务器代码")
        for server_name in mcp.get("mcpServers", {}):
            lines.append(f"│   └── {server_name}/")
    lines.append("└── com.<client>/        # 客户端专属扩展（可选）")
    lines.append("```")
    lines.append("")
    lines.append("### 验证")
    lines.append("")
    lines.append("使用 agent-plugin-creator 技能的验证工具：")
    lines.append("")
    lines.append("```bash")
    lines.append(f"# 验证插件结构")
    lines.append(f"python3 scripts/validate_plugin.py .")
    lines.append("")
    lines.append(f"# 安全审计")
    lines.append(f"python3 scripts/audit_plugin.py .")
    lines.append("```")
    lines.append("")

    # 许可证
    lines.append("## 许可证")
    lines.append("")
    lines.append(f"{license_name}" + (f" © {author_name}" if author_name else ""))
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Agent Plugin 文档自动生成工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--output", default="README.md", help="输出文件路径（默认 README.md）")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的 README.md")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.exists():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    # 加载数据
    plugin = load_plugin_json(plugin_dir)

    # 加载 skills
    skills = []
    skills_dir = plugin_dir / "skills"
    if skills_dir.exists() and skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    skills.append(parse_skill_md(skill_md))

    # 加载 mcp.json
    mcp = load_mcp_json(plugin_dir)

    # 从 servers/ 提取工具列表
    servers_tools = {}
    servers_dir = plugin_dir / "servers"
    if servers_dir.exists() and servers_dir.is_dir():
        for server_dir in servers_dir.iterdir():
            if server_dir.is_dir():
                servers_tools[server_dir.name] = extract_tools_from_server(server_dir)

    # 生成文档
    readme_content = generate_readme(plugin_dir, plugin, skills, mcp, servers_tools)

    # 写入文件
    output_path = plugin_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)
    if output_path.exists() and not args.force:
        print(f"错误: 文件已存在: {output_path}", file=sys.stderr)
        print(f"提示: 使用 --force 覆盖", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(readme_content, encoding="utf-8")

    print(f"✅ 文档已生成: {output_path}")
    print(f"   插件: {plugin.get('name', 'unknown')} v{plugin.get('version', '0.1.0')}")
    print(f"   Skills: {len(skills)} 个")
    print(f"   MCP 服务器: {len(mcp.get('mcpServers', {}))} 个")
    total_tools = sum(len(tools) for tools in servers_tools.values())
    print(f"   MCP 工具: {total_tools} 个（从源代码提取）")
    print(f"   文档行数: {len(readme_content.split(chr(10)))} 行")


if __name__ == "__main__":
    main()
