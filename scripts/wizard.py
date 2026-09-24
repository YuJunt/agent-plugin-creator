#!/usr/bin/env python3
"""
Agent Plugin 交互式创建向导

通过问答引导用户完成 Agent Plugin 的创建，自动生成完整的插件结构。

支持两种模式:
  1. 交互式模式（默认）：通过问答收集信息
  2. 配置文件模式：通过 JSON 配置文件批量生成

用法:
    python3 wizard.py                        # 交互式创建
    python3 wizard.py --config config.json  # 从配置文件创建
    python3 wizard.py --dry-run              # 预览将生成的内容，不实际写入
    python3 wizard.py --output ./my-plugin  # 指定输出目录

配置文件格式 (config.json):
    {
      "name": "my-plugin",
      "version": "0.1.0",
      "description": "插件描述",
      "author": {"name": "作者名"},
      "license": "MIT",
      "keywords": ["keyword1", "keyword2"],
      "components": {
        "skills": [
          {"name": "skill-name", "description": "skill 描述"}
        ],
        "mcp_servers": [
          {
            "name": "server-name",
            "language": "typescript",
            "transport": "stdio",
            "tools": [
              {"name": "tool_name", "description": "工具描述", "parameters": {}}
            ]
          }
        ]
      },
      "target_clients": ["claude", "copilot", "cursor"]
    }
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent


def ask_question(question: str, default: str = None, required: bool = True) -> str:
    """交互式提问"""
    prompt = f"{question}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "

    while True:
        try:
            answer = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n操作取消")
            sys.exit(0)

        if answer:
            return answer
        if default:
            return default
        if not required:
            return ""
        print("  ⚠️  此项为必填，请输入")


def ask_yes_no(question: str, default: bool = False) -> bool:
    """交互式 yes/no 提问"""
    default_str = "Y/n" if default else "y/N"
    while True:
        try:
            answer = input(f"{question} [{default_str}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n操作取消")
            sys.exit(0)

        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  ⚠️  请输入 y 或 n")


def interactive_collect() -> dict:
    """交互式收集插件配置"""
    print("=" * 60)
    print("Agent Plugin 创建向导")
    print("=" * 60)
    print()
    print("本向导将引导你创建一个符合 Agent Plugins 1.0 标准的插件。")
    print("按 Ctrl+C 可随时取消。")
    print()

    config = {}

    # 基本信息
    print("--- 基本信息 ---")
    config["name"] = ask_question("插件名称（小写字母+数字+连字符）", "my-plugin")
    config["version"] = ask_question("版本号", "0.1.0")
    config["description"] = ask_question("插件描述")
    author_name = ask_question("作者名称", required=False)
    config["author"] = {"name": author_name} if author_name else {}
    config["license"] = ask_question("许可证", "MIT")
    keywords_str = ask_question("关键词（逗号分隔）", required=False)
    config["keywords"] = [k.strip() for k in keywords_str.split(",") if k.strip()] if keywords_str else []

    print()
    print("--- 组件配置 ---")

    # Skills
    config["components"] = {}
    has_skills = ask_yes_no("是否包含 Agent Skills？", True)
    if has_skills:
        skills = []
        skill_count = int(ask_question("Skill 数量", "1"))
        for i in range(skill_count):
            print(f"\n  Skill {i + 1}/{skill_count}:")
            skill_name = ask_question(f"  Skill {i + 1} 名称", f"skill-{i + 1}")
            skill_desc = ask_question(f"  Skill {i + 1} 描述")
            skills.append({"name": skill_name, "description": skill_desc})
        config["components"]["skills"] = skills

    # MCP 服务器
    has_mcp = ask_yes_no("是否包含 MCP 服务器？", False)
    if has_mcp:
        servers = []
        server_count = int(ask_question("MCP 服务器数量", "1"))
        for i in range(server_count):
            print(f"\n  MCP 服务器 {i + 1}/{server_count}:")
            server_name = ask_question(f"  服务器 {i + 1} 名称", f"server-{i + 1}")
            language = ask_question("  编程语言 (typescript/python)", "typescript")
            transport = ask_question("  传输类型 (stdio/streamable-http)", "stdio")

            tools = []
            has_tools = ask_yes_no(f"  是否为 {server_name} 定义工具？", True)
            if has_tools:
                tool_count = int(ask_question(f"  工具数量", "1"))
                for j in range(tool_count):
                    print(f"\n    工具 {j + 1}/{tool_count}:")
                    tool_name = ask_question(f"    工具 {j + 1} 名称", f"tool_{j + 1}")
                    tool_desc = ask_question(f"    工具 {j + 1} 描述")
                    tools.append({"name": tool_name, "description": tool_desc, "parameters": {}})

            servers.append({
                "name": server_name,
                "language": language,
                "transport": transport,
                "tools": tools,
            })
        config["components"]["mcp_servers"] = servers

    # 目标客户端
    print()
    print("--- 目标客户端 ---")
    print("支持的客户端: claude, codex, copilot, cursor, gemini")
    clients_str = ask_question("目标客户端（逗号分隔，all 表示所有）", "all")
    config["target_clients"] = ["all"] if clients_str.lower() == "all" else [c.strip() for c in clients_str.split(",")]

    print()
    print("=" * 60)
    print("配置收集完成")
    print("=" * 60)
    print(f"  名称: {config['name']}")
    print(f"  版本: {config['version']}")
    print(f"  描述: {config['description']}")
    if config["components"].get("skills"):
        print(f"  Skills: {len(config['components']['skills'])} 个")
    if config["components"].get("mcp_servers"):
        print(f"  MCP 服务器: {len(config['components']['mcp_servers'])} 个")
    print(f"  目标客户端: {', '.join(config['target_clients'])}")
    print()

    confirm = ask_yes_no("确认创建？", True)
    if not confirm:
        print("创建取消")
        sys.exit(0)

    return config


def generate_plugin(config: dict, output_dir: Path, dry_run: bool = False) -> list:
    """根据配置生成插件"""
    generated = []

    def add_file(path: str, content: str):
        full_path = output_dir / path
        if dry_run:
            generated.append(f"[预览] {path} ({len(content)} 字节)")
        else:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            generated.append(path)

    # 1. 生成 plugin.json
    # 从 provenance.json 读取技能版本，用于 generated-by 标注
    skill_version = "1.2.0"
    provenance_path = SKILL_DIR / "provenance.json"
    if provenance_path.exists():
        try:
            skill_version = json.loads(provenance_path.read_text(encoding="utf-8")).get("version", skill_version)
        except Exception:
            pass

    plugin_json = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": config["name"],
        "version": config["version"],
        "description": config["description"],
        "author": config.get("author", {}),
        "license": config.get("license", "MIT"),
        "keywords": config.get("keywords", []),
        "generated-by": {
            "tool": "agent-plugin-creator",
            "version": skill_version
        }
    }
    add_file("plugin.json", json.dumps(plugin_json, indent=2, ensure_ascii=False) + "\n")

    # 2. 生成 skills
    for skill in config.get("components", {}).get("skills", []):
        skill_name = skill["name"]
        skill_desc = skill["description"]
        title = skill_name.replace("-", " ").title()

        skill_md = f"""---
name: {skill_name}
description: {skill_desc}
---

# {title}

## 概述
{skill_desc}

## 工作流程
1. 第一步
2. 第二步
3. 第三步

## 关键规则
- 规则一
- 规则二

## 参考资源
- 详细文档参见 references/ 目录（超过100行的文件请在开头加目录）
- 可执行脚本参见 scripts/ 目录
- 输出模板参见 assets/ 目录
"""
        add_file(f"skills/{skill_name}/SKILL.md", skill_md)
        add_file(f"skills/{skill_name}/scripts/.gitkeep", "")
        add_file(f"skills/{skill_name}/references/.gitkeep", "")
        add_file(f"skills/{skill_name}/assets/.gitkeep", "")

    # 3. 生成 MCP 服务器
    mcp_servers = config.get("components", {}).get("mcp_servers", [])
    if mcp_servers:
        # 生成 mcp.json
        mcp_json = {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {},
        }
        for server in mcp_servers:
            server_name = server["name"]
            if server["transport"] == "stdio":
                if server["language"] == "typescript":
                    mcp_json["mcpServers"][server_name] = {
                        "type": "stdio",
                        "command": "node",
                        "args": [f"servers/{server_name}/dist/server.js"],
                    }
                else:
                    mcp_json["mcpServers"][server_name] = {
                        "type": "stdio",
                        "command": "python3",
                        "args": [f"servers/{server_name}/server.py"],
                    }
            else:
                mcp_json["mcpServers"][server_name] = {
                    "type": "streamable-http",
                    "url": f"http://localhost:3000/{server_name}",
                }
        add_file("mcp.json", json.dumps(mcp_json, indent=2, ensure_ascii=False) + "\n")

        # 生成服务器代码（简化模板）
        for server in mcp_servers:
            server_name = server["name"]
            language = server["language"]
            tools = server.get("tools", [])

            if language == "typescript":
                # package.json
                pkg = {
                    "name": server_name,
                    "version": "1.0.0",
                    "type": "module",
                    "scripts": {"build": "tsc", "start": "node dist/server.js"},
                    "dependencies": {"@modelcontextprotocol/sdk": "^1.0.0", "zod": "^3.22.0"},
                    "devDependencies": {"typescript": "^5.0.0", "@types/node": "^20.0.0"},
                }
                add_file(f"servers/{server_name}/package.json", json.dumps(pkg, indent=2) + "\n")

                # tsconfig.json
                tsconfig = {
                    "compilerOptions": {
                        "target": "ES2022",
                        "module": "ES2022",
                        "moduleResolution": "node",
                        "outDir": "./dist",
                        "rootDir": "./src",
                        "strict": True,
                        "esModuleInterop": True,
                    },
                    "include": ["src/**/*"],
                }
                add_file(f"servers/{server_name}/tsconfig.json", json.dumps(tsconfig, indent=2) + "\n")

                # server.ts
                if server["transport"] == "stdio":
                    server_ts = f"""import {{ McpServer }} from "@modelcontextprotocol/sdk/server/mcp.js";
import {{ StdioServerTransport }} from "@modelcontextprotocol/sdk/server/stdio.js";
import {{ z }} from "zod";

const server = new McpServer({{ name: "{server_name}", version: "1.0.0" }});

"""
                else:
                    server_ts = f"""import {{ McpServer }} from "@modelcontextprotocol/sdk/server/mcp.js";
import {{ StreamableHTTPServerTransport }} from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {{ z }} from "zod";

const server = new McpServer({{ name: "{server_name}", version: "1.0.0" }});

"""
                for tool in tools:
                    server_ts += f"""server.tool(
  "{tool['name']}",
  "{tool['description']}",
  {{}},
  async () => {{
    // TODO: 实现工具逻辑
    return {{ content: [{{ type: "text", text: "Tool {tool['name']} executed" }}] }};
  }}
);

"""
                if server["transport"] == "stdio":
                    server_ts += """async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("MCP server started (stdio)");
}

main().catch(console.error);
"""
                else:
                    server_ts += """async function main() {
  const port = process.env.PORT ? parseInt(process.env.PORT) : 3000;
  console.error(`MCP server starting on port ${port} (streamable-http)`);
}

main().catch(console.error);
"""
                add_file(f"servers/{server_name}/src/server.ts", server_ts)

            else:  # python
                # pyproject.toml
                pyproject = f"""[project]
name = "{server_name}"
version = "1.0.0"
dependencies = ["fastmcp"]

[project.scripts]
{server_name} = "server:main"
"""
                add_file(f"servers/{server_name}/pyproject.toml", pyproject)

                # server.py
                server_py = f"""from fastmcp import FastMCP

mcp = FastMCP("{server_name}")

"""
                for tool in tools:
                    server_py += f"""@mcp.tool()
def {tool['name']}() -> str:
    \"\"\"{tool['description']}\"\"\"
    # TODO: 实现工具逻辑
    return "Tool {tool['name']} executed"

"""
                if server["transport"] == "stdio":
                    server_py += """def main():
    print("Starting MCP server (stdio)", file=sys.stderr)
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
"""
                else:
                    server_py += """def main():
    import os
    port = int(os.environ.get("PORT", "3000"))
    print(f"Starting MCP server on port {port} (streamable-http)", file=sys.stderr)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
"""
                add_file(f"servers/{server_name}/server.py", server_py)

    # 4. 生成 README
    readme = f"""# {config['name']}

> {config['description']}

## 安装

将此插件目录复制到客户端的插件目录，或通过插件市场安装。

## 功能

"""
    if config["components"].get("skills"):
        readme += "### Skills\n\n"
        for skill in config["components"]["skills"]:
            readme += f"- **{skill['name']}**: {skill['description']}\n"
        readme += "\n"
    if config["components"].get("mcp_servers"):
        readme += "### MCP 服务器\n\n"
        for server in config["components"]["mcp_servers"]:
            readme += f"- **{server['name']}** ({server['language']}, {server['transport']})\n"
            for tool in server.get("tools", []):
                readme += f"  - `{tool['name']}()`: {tool['description']}\n"
        readme += "\n"

    readme += f"""## 许可证

{config.get('license', 'MIT')}
"""
    add_file("README.md", readme)

    # 5. 生成 CHANGELOG.md
    changelog = f"""# Changelog

本文件记录 {config['name']} 的版本变更。

## [{config['version']}] - 初始版本

- 初始发布
"""
    add_file("CHANGELOG.md", changelog)

    # 6. 生成 LICENSE.txt（根据 plugin.json 的 license 字段）
    license_name = config.get("license", "MIT")
    author_name = config.get("author", {}).get("name", "Your Name")
    if license_name.upper() == "MIT":
        license_text = f"""MIT License

Copyright (c) 2026 {author_name}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
        add_file("LICENSE.txt", license_text)

    # 7. 生成 .gitignore
    gitignore = """node_modules/
dist/
__pycache__/
*.pyc
.env
.DS_Store
"""
    add_file(".gitignore", gitignore)

    return generated


def normalize_config(config: dict) -> dict:
    """为非交互配置补全默认值，避免 KeyError。"""
    config.setdefault("version", "0.1.0")
    config.setdefault("description", "")
    config.setdefault("author", {})
    config.setdefault("license", "MIT")
    config.setdefault("keywords", [])
    components = config.setdefault("components", {})
    components.setdefault("skills", [])
    components.setdefault("mcp_servers", [])
    config.setdefault("target_clients", ["all"])
    return config


def main():
    parser = argparse.ArgumentParser(description="Agent Plugin 交互式创建向导")
    parser.add_argument("--config", help="从 JSON 配置文件创建（非交互式）")
    parser.add_argument("--output", help="输出目录（默认使用插件名称）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入文件")
    parser.add_argument("--force", action="store_true", help="覆盖已有输出目录")
    args = parser.parse_args()

    # 收集配置
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"错误: 配置文件不存在: {config_path}", file=sys.stderr)
            sys.exit(1)
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"错误: 配置文件不是有效 JSON: {e}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(config, dict):
            print("错误: 配置文件必须是 JSON 对象", file=sys.stderr)
            sys.exit(1)
        if "name" not in config:
            print("错误: 配置文件缺少必需字段 name", file=sys.stderr)
            sys.exit(1)
        config = normalize_config(config)
        print(f"📋 从配置文件加载: {config_path}")
    else:
        config = interactive_collect()

    # 确定输出目录
    output_dir = Path(args.output) if args.output else Path(config["name"])
    output_dir = output_dir.resolve()

    # 确保 plugin name 与目录名一致（Agent Plugins 规范要求）
    if output_dir.name != config["name"]:
        print(f"⚠️  注意: 输出目录名 '{output_dir.name}' 与配置 name '{config['name']}' 不一致")
        print(f"   已自动将 plugin name 更新为 '{output_dir.name}'（符合 Agent Plugins 规范要求）")
        config["name"] = output_dir.name

    # 校验 plugin name 合法性
    import re as _re
    if not _re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', config["name"]):
        print(f"错误: plugin name '{config['name']}' 不符合规范", file=sys.stderr)
        print("   规则: 小写字母/数字/连字符/点，以字母数字开头结尾", file=sys.stderr)
        print("   提示: 请修改 --output 目录名或 config 中的 name 字段", file=sys.stderr)
        sys.exit(1)

    if output_dir.exists() and not args.dry_run:
        if not args.force:
            print(f"错误: 输出目录已存在: {output_dir}", file=sys.stderr)
            print("提示: 使用 --force 覆盖，或手动删除已有目录", file=sys.stderr)
            sys.exit(1)
        import shutil
        shutil.rmtree(output_dir)
        print(f"⚠️  已删除已有目录: {output_dir}")

    # 生成插件
    print()
    print(f"🚀 生成插件: {config['name']} v{config['version']}")
    print(f"   输出目录: {output_dir}")
    if args.dry_run:
        print("   模式: 预览（不实际写入）")
    print()

    generated = generate_plugin(config, output_dir, dry_run=args.dry_run)

    print()
    print("=" * 60)
    print(f"✅ 插件生成完成: {config['name']}")
    print("=" * 60)
    print(f"生成文件: {len(generated)} 个")
    for f in generated:
        print(f"  - {f}")

    # 用官方 skill-creator 的 quick_validate.py 验证每个子 skill
    quick_validate = SKILL_DIR / "official" / "skill-creator" / "scripts" / "quick_validate.py"
    if quick_validate.exists() and not args.dry_run:
        print()
        print("🔍 官方规范验证（official/skill-creator/quick_validate.py）...")
        skills_dir = output_dir / "skills"
        if skills_dir.exists():
            for skill_dir in sorted(skills_dir.iterdir()):
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    result = subprocess.run(
                        [sys.executable, str(quick_validate), str(skill_dir)],
                        capture_output=True, text=True
                    )
                    status = "✅" if result.returncode == 0 else "⚠️"
                    print(f"  {status} {skill_dir.name}: {result.stdout.strip()}")

    print()
    print("下一步:")
    print(f"  1. cd {output_dir}")
    print("  2. 编辑 plugin.json 和 skills/*/SKILL.md，填充实际内容")
    if config["components"].get("mcp_servers"):
        print("  3. 实现 MCP 服务器的工具逻辑")
        print("  4. 安装依赖并测试 MCP 服务器")
    print(f"  5. 运行验证: python3 {SKILL_DIR}/scripts/validate_plugin.py .")
    print(f"  6. 运行安全审计: python3 {SKILL_DIR}/scripts/audit_plugin.py .")


if __name__ == "__main__":
    main()
