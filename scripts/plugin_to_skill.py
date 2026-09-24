#!/usr/bin/env python3
"""
Agent Plugin 反向封装为 Skill 工具

将一个符合 Agent Plugins 1.0.0 规范的插件，反向封装为一个普通 Skill，
使其可以在任何支持 Agent Skills 的平台上使用（包括不原生支持 Agent Plugins 的平台）。

原理：
  - 生成一个封装层 SKILL.md，指导 AI 何时读取子技能、如何启动 MCP 服务器
  - 保留原始 skills/ 目录作为参考资源
  - 保留原始 servers/ 目录（MCP 服务器代码）
  - 生成 start_mcp.py 辅助脚本，用于启动和管理 MCP 服务器
  - 用"AI 手动执行"替代"平台自动执行"，换取平台兼容性

用法:
    python3 plugin_to_skill.py <插件目录> [--output <输出目录>] [--force]
    python3 plugin_to_skill.py ./my-plugin --output ./my-plugin-as-skill
    python3 plugin_to_skill.py ./my-plugin --force
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def plugin_name_to_skill_name(plugin_name: str) -> str:
    """将 Plugin name 转换为合法的 Skill name。

    Plugin name 允许点（如 customer-support.triage），
    但 Skill name 只允许字母、数字和连字符，不允许点。
    因此将点替换为连字符。
    """
    return plugin_name.replace(".", "-")


def load_json(file_path: Path) -> dict:
    """加载 JSON 文件，失败返回空字典"""
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"⚠️  警告: {file_path} 不是有效 JSON: {e}", file=sys.stderr)
        return {}


def discover_skills(plugin_dir: Path) -> list:
    """发现插件中的所有子技能"""
    skills = []
    skills_dir = plugin_dir / "skills"
    if not skills_dir.exists() or not skills_dir.is_dir():
        return skills

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        # 读取 frontmatter 中的 description
        description = skill_dir.name
        try:
            content = skill_md.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].split("\n"):
                        if line.strip().startswith("description:"):
                            description = line.split(":", 1)[1].strip().strip('"').strip("'")
                            break
        except Exception:
            pass

        skills.append({
            "name": skill_dir.name,
            "description": description,
            "path": f"skills/{skill_dir.name}/SKILL.md",
            "has_scripts": (skill_dir / "scripts").exists(),
            "has_references": (skill_dir / "references").exists(),
            "has_assets": (skill_dir / "assets").exists(),
        })
    return skills


def discover_mcp_servers(plugin_dir: Path) -> list:
    """发现插件中的 MCP 服务器"""
    mcp_json = load_json(plugin_dir / "mcp.json")
    servers = []

    for name, config in mcp_json.get("mcpServers", {}).items():
        transport = config.get("transport", "stdio")
        command = config.get("command", "")
        args = config.get("args", [])
        env = config.get("env", {})
        url = config.get("url", "")

        servers.append({
            "name": name,
            "transport": transport,
            "command": command,
            "args": args,
            "env": env,
            "url": url,
        })
    return servers


def generate_wrapper_skill_md(plugin: dict, skills: list, mcp_servers: list, skill_name: str = None) -> str:
    """生成封装层 SKILL.md"""
    plugin_name = plugin.get("name", "my-plugin")
    if skill_name is None:
        skill_name = plugin_name_to_skill_name(plugin_name)
    plugin_description = plugin.get("description", "")
    plugin_version = plugin.get("version", "0.1.0")

    # 构建 description（包含触发场景）
    # 先去除 plugin_description 末尾的句号，避免双句号
    clean_desc = plugin_description.rstrip("。.")
    skill_description = f"{clean_desc}。本技能由 Agent Plugin 反向封装而来，"
    if skills:
        skill_names = "、".join(s["name"] for s in skills)
        skill_description += f"提供以下能力：{skill_names}。"
    if mcp_servers:
        mcp_names = "、".join(s["name"] for s in mcp_servers)
        skill_description += f"可调用 MCP 服务器：{mcp_names}。"
    # 用具体的能力名作为触发词，而不是泛泛的"相关功能"
    trigger_names = []
    if skills:
        trigger_names.extend(s["name"] for s in skills)
    if mcp_servers:
        trigger_names.extend(s["name"] for s in mcp_servers)
    if trigger_names:
        skill_description += f"当用户需要{'、'.join(trigger_names)}相关功能时使用。"
    else:
        skill_description += "当用户需要相关功能时使用。"

    lines = []
    lines.append("---")
    lines.append(f"name: {skill_name}")
    lines.append(f"description: {skill_description}")
    lines.append(f"metadata:")
    lines.append(f"  source: agent-plugin")
    lines.append(f"  plugin-version: {plugin_version}")
    # 从 provenance.json 读取技能版本，wrapper-version 跟随技能版本
    skill_version = "1.2.0"
    provenance_path = Path(__file__).resolve().parent.parent / "provenance.json"
    if provenance_path.exists():
        try:
            skill_version = json.loads(provenance_path.read_text(encoding="utf-8")).get("version", skill_version)
        except Exception:
            pass
    lines.append(f"  wrapper-version: {skill_version}")
    lines.append(f"  generated-by:")
    lines.append(f"    tool: agent-plugin-creator")
    lines.append(f"    version: {skill_version}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {skill_name}（Skill 封装版）")
    lines.append("")
    lines.append(f"> 本技能由 Agent Plugin v{plugin_version} 反向封装生成。")
    lines.append(f"> 原始插件描述：{plugin_description}")
    lines.append(f"> 封装原理：用 AI 手动读取子技能和启动 MCP 服务器，替代平台自动加载，")
    lines.append(f"> 使其可以在任何支持 Agent Skills 的平台上使用。")
    lines.append("")

    # 能力清单
    lines.append("## 能力清单")
    lines.append("")

    if skills:
        lines.append("### 子技能")
        lines.append("")
        for skill in skills:
            lines.append(f"- **{skill['name']}**：{skill['description']}")
            lines.append(f"  - 位置：`{skill['path']}`")
            extra = []
            if skill["has_scripts"]:
                extra.append("scripts")
            if skill["has_references"]:
                extra.append("references")
            if skill["has_assets"]:
                extra.append("assets")
            if extra:
                lines.append(f"  - 附加资源：{', '.join(extra)}")
        lines.append("")

    if mcp_servers:
        lines.append("### MCP 服务器")
        lines.append("")
        for server in mcp_servers:
            lines.append(f"- **{server['name']}**：transport={server['transport']}")
            if server["command"]:
                lines.append(f"  - 启动命令：`{server['command']} {' '.join(server['args'])}`")
            if server["url"]:
                lines.append(f"  - 连接地址：`{server['url']}`")
        lines.append("")
        lines.append("使用 MCP 工具前，先运行 `scripts/start_mcp.py` 启动服务器，")
        lines.append("然后通过 stdio（JSON-RPC）或 HTTP 与服务器通信调用工具。")
        lines.append("")

    # 使用指南
    lines.append("## 使用指南")
    lines.append("")
    lines.append("### 路由判断")
    lines.append("")
    lines.append("根据用户请求，判断使用哪种能力：")
    lines.append("")

    if skills:
        lines.append("| 用户意图 | 使用的子技能 | 操作 |")
        lines.append("|---------|------------|------|")
        for skill in skills:
            lines.append(f"| 需要{skill['description'][:20]}... | {skill['name']} | 读取 `{skill['path']}` 并按其步骤执行 |")
        lines.append("")

    if mcp_servers:
        lines.append("| 用户意图 | 使用的 MCP | 操作 |")
        lines.append("|---------|-----------|------|")
        for server in mcp_servers:
            lines.append(f"| 需要调用{server['name']}相关工具 | {server['name']} | 运行 `scripts/start_mcp.py --server {server['name']}` 启动后调用 |")
        lines.append("")

    lines.append("### 使用子技能")
    lines.append("")
    lines.append("当需要使用某个子技能时：")
    lines.append("")
    lines.append("1. 读取对应子技能的 `SKILL.md` 完整内容")
    lines.append("2. 按照其中的步骤、规则和最佳实践执行")
    lines.append("3. 如果子技能有 `scripts/`，按需运行其中的脚本")
    lines.append("4. 如果子技能有 `references/`，按需读取参考文档")
    lines.append("")

    if mcp_servers:
        lines.append("### 使用 MCP 服务器")
        lines.append("")
        lines.append("当需要调用 MCP 工具时：")
        lines.append("")
        lines.append("1. 运行 `scripts/start_mcp.py --list` 查看可用服务器")
        lines.append("2. 运行 `scripts/start_mcp.py --info <名称>` 获取服务器完整配置（JSON格式）")
        lines.append("3. 用 subprocess.Popen 启动服务器（stdin=PIPE, stdout=PIPE），发送 JSON-RPC 请求（initialize → tools/list → tools/call）")
        lines.append("4. 获取结果后，terminate() 关闭服务器进程")
        lines.append("")
        lines.append("**注意**：MCP 服务器是独立进程，使用完毕后应确保关闭，避免资源泄漏。`--server` 交互模式仅供人手动调试，AI 应使用 `--info` + 自己的 subprocess 代码。")
        lines.append("")

    # 原始配置参考
    lines.append("## 原始插件配置")
    lines.append("")
    lines.append("- 插件元数据：`references/plugin.json`")
    if mcp_servers:
        lines.append("- MCP 配置：`references/mcp.json`")
    lines.append("")
    lines.append("如需了解原始插件的完整结构和配置，可查阅上述文件。")
    lines.append("")

    # 限制说明
    lines.append("## 限制说明")
    lines.append("")
    lines.append("本封装版与原生 Agent Plugin 支持的区别：")
    lines.append("")
    lines.append("1. **子技能不会被自动发现**——需要 AI 主动读取对应子技能的 SKILL.md")
    lines.append("2. **MCP 不会被自动启动**——需要 AI 运行 start_mcp.py 手动启动")
    lines.append("3. **客户端扩展不可用**——原生插件的客户端专属扩展（hooks、commands 等）在封装版中不生效")
    lines.append("4. **功能基本完整**——核心的 skills 和 MCP 能力均可正常使用，用户体验基本无缝")
    lines.append("")

    # Gotchas section
    lines.append("## Gotchas（踩过的坑）")
    lines.append("")
    lines.append("1. **子技能需要主动读取**——平台不会自动发现子技能，必须由 AI 主动读取对应子技能的 SKILL.md 才能使用其能力。")
    lines.append("2. **MCP 服务器需要手动启动**——平台不会自动启动 MCP 服务器，必须运行 `scripts/start_mcp.py` 手动启动，使用完毕后确保关闭进程。")
    if mcp_servers:
        lines.append("3. **stdio 服务器不要打印到 stdout**——stdout 是 JSON-RPC 通道，打印调试信息会破坏协议，调试信息必须打到 stderr（对齐 official/mcp-builder 最佳实践）。")
    lines.append("4. **客户端扩展不可用**——原生插件的 .cursor/、.claude-plugin/ 等客户端专属扩展在封装版中不生效，已被排除。")
    lines.append("5. **MCP 服务器和工具命名遵循官方规范**——Python 服务器用 `{service}_mcp`，Node 用 `{service}-mcp-server`，工具用 snake_case 加服务前缀（详见 official/mcp-builder/reference/mcp_best_practices.md）。")
    lines.append("")

    return "\n".join(lines) + "\n"


def generate_start_mcp_script(mcp_servers: list) -> str:
    """生成 start_mcp.py 辅助脚本"""
    lines = []
    lines.append("#!/usr/bin/env python3")
    lines.append('"""')
    lines.append("MCP 服务器启动与管理工具（由 plugin_to_skill.py 自动生成）")
    lines.append("")
    lines.append("用法:")
    lines.append("    python3 start_mcp.py --list          # 列出可用服务器")
    lines.append("    python3 start_mcp.py --server <名称>  # 启动指定服务器（stdio 交互模式）")
    lines.append('"""')
    lines.append("import argparse")
    lines.append("import json")
    lines.append("import os")
    lines.append("import subprocess")
    lines.append("import sys")
    lines.append("from pathlib import Path")
    lines.append("")
    lines.append("# 服务器配置（由 plugin_to_skill.py 从原始 mcp.json 提取）")
    lines.append("SERVERS = {")
    for server in mcp_servers:
        lines.append(f'    "{server["name"]}": {{')
        lines.append(f'        "transport": "{server["transport"]}",')
        lines.append(f'        "command": "{server["command"]}",')
        lines.append(f'        "args": {json.dumps(server["args"])},')
        lines.append(f'        "env": {json.dumps(server["env"])},')
        lines.append(f'        "url": "{server["url"]}",')
        lines.append("    },")
    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("def list_servers():")
    lines.append('    """列出所有可用服务器"""')
    lines.append('    print("可用 MCP 服务器:")')
    lines.append("    for name, config in SERVERS.items():")
    lines.append(f'        print(f"  - {{name}} (transport={{config[\'transport\']}})")')
    lines.append("")
    lines.append("")
    lines.append("def info_server(name: str):")
    lines.append('    """输出服务器的完整配置（JSON格式，方便AI读取后自己启动）"""')
    lines.append("    if name not in SERVERS:")
    lines.append(f'        print(f"错误: 找不到服务器 \'{{name}}\'", file=sys.stderr)')
    lines.append('        print(f"可用服务器: {\', \'.join(SERVERS.keys())}", file=sys.stderr)')
    lines.append("        sys.exit(1)")
    lines.append("    print(json.dumps(SERVERS[name], ensure_ascii=False, indent=2))")
    lines.append("")
    lines.append("")
    lines.append("def start_server(name: str):")
    lines.append('    """启动指定服务器（stdio 交互模式）"""')
    lines.append("    if name not in SERVERS:")
    lines.append(f'        print(f"错误: 找不到服务器 \'{{name}}\'", file=sys.stderr)')
    lines.append('        print(f"可用服务器: {\', \'.join(SERVERS.keys())}", file=sys.stderr)')
    lines.append("        sys.exit(1)")
    lines.append("")
    lines.append("    config = SERVERS[name]")
    lines.append(f'    print(f"启动 MCP 服务器: {{name}} (transport={{config[\'transport\']}})")')
    lines.append("")
    lines.append("    if config['transport'] == 'stdio':")
    lines.append("        cmd = [config['command']] + config['args']")
    lines.append("        env = config.get('env', {})")
    lines.append("        try:")
    lines.append("            proc = subprocess.Popen(")
    lines.append("                cmd,")
    lines.append("                stdin=subprocess.PIPE,")
    lines.append("                stdout=subprocess.PIPE,")
    lines.append("                stderr=subprocess.PIPE,")
    lines.append("                text=True,")
    lines.append("                env={**os.environ, **env},")
    lines.append("            )")
    lines.append('            print("服务器已启动，进入 stdio 交互模式（输入 JSON-RPC 请求，Ctrl+C 退出）")')
    lines.append("            print()")
    lines.append("            # 简单的交互循环")
    lines.append("            while True:")
    lines.append("                try:")
    lines.append('                    line = input("> ")')
    lines.append("                    if not line.strip():")
    lines.append("                        continue")
    lines.append("                    proc.stdin.write(line + '\\n')")
    lines.append("                    proc.stdin.flush()")
    lines.append("                    response = proc.stdout.readline()")
    lines.append("                    if response:")
    lines.append("                        print(response.strip())")
    lines.append("                except (EOFError, KeyboardInterrupt):")
    lines.append('                    print("\\n退出")')
    lines.append("                    break")
    lines.append("            proc.terminate()")
    lines.append("            proc.wait()")
    lines.append("        except FileNotFoundError:")
    lines.append(f'            print(f"错误: 找不到可执行文件 \'{{config[\'command\']}}\'", file=sys.stderr)')
    lines.append('            print("请确保 MCP 服务器已正确安装，或检查命令路径", file=sys.stderr)')
    lines.append("            sys.exit(1)")
    lines.append("    elif config['transport'] == 'streamable-http':")
    lines.append(f'        print(f"HTTP 服务器地址: {{config[\'url\']}}")')
    lines.append('        print("请使用 HTTP 客户端发送 JSON-RPC 请求到上述地址")')
    lines.append("    else:")
    lines.append(f'        print(f"不支持的 transport: {{config[\'transport\']}}", file=sys.stderr)')
    lines.append("        sys.exit(1)")
    lines.append("")
    lines.append("")
    lines.append("def main():")
    lines.append("    parser = argparse.ArgumentParser(description='MCP 服务器启动与管理工具')")
    lines.append("    parser.add_argument('--list', action='store_true', help='列出可用服务器')")
    lines.append("    parser.add_argument('--server', help='启动指定服务器（stdio交互模式，供人使用）')")
    lines.append("    parser.add_argument('--info', help='输出指定服务器的完整配置（JSON格式，供AI读取）')")
    lines.append("    args = parser.parse_args()")
    lines.append("")
    lines.append("    if args.list:")
    lines.append("        list_servers()")
    lines.append("    elif args.info:")
    lines.append("        info_server(args.info)")
    lines.append("    elif args.server:")
    lines.append("        start_server(args.server)")
    lines.append("    else:")
    lines.append("        parser.print_help()")
    lines.append("")
    lines.append("")
    lines.append('if __name__ == "__main__":')
    lines.append("    main()")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Agent Plugin 反向封装为 Skill 工具")
    parser.add_argument("plugin_dir", help="Agent Plugin 目录路径")
    parser.add_argument("--output", help="输出 Skill 目录路径（默认：<skill-name>-skill）")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的输出目录")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.exists():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    # 加载插件元数据
    plugin = load_json(plugin_dir / "plugin.json")
    if not plugin:
        print("错误: 缺少或无效的 plugin.json", file=sys.stderr)
        sys.exit(1)

    plugin_name = plugin.get("name", plugin_dir.name)
    skill_name = plugin_name_to_skill_name(plugin_name)

    # 确定输出目录
    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        output_dir = plugin_dir.parent / f"{skill_name}-skill"

    # 安全检查：输出目录不能等于输入目录
    if output_dir.resolve() == plugin_dir.resolve():
        output_dir = plugin_dir.parent / f"{skill_name}-skill"
        print(f"⚠️  注意: 输出目录与输入目录相同，已自动改为: {output_dir.name}")

    if output_dir.exists():
        if args.force:
            shutil.rmtree(output_dir)
        else:
            print(f"错误: 输出目录已存在: {output_dir}", file=sys.stderr)
            print("使用 --force 覆盖，或指定其他 --output 路径", file=sys.stderr)
            sys.exit(1)

    # 最终 skill name 用插件名转换的（不是输出目录名）
    final_skill_name = skill_name
    # 警告：如果输出目录名和 skill name 不一致，validate_skill 会报错
    if output_dir.name != final_skill_name:
        print(f"⚠️  注意: 输出目录名 '{output_dir.name}' 与 skill name '{final_skill_name}' 不一致")
        print(f"   validate_skill.py 会要求目录名与 skill name 一致，建议使用 --output {final_skill_name}")
    # 发现组件
    skills = discover_skills(plugin_dir)
    mcp_servers = discover_mcp_servers(plugin_dir)

    print(f"🔄 反向封装 Agent Plugin → Skill")
    print(f"   源插件: {plugin_dir.name} (v{plugin.get('version', 'unknown')})")
    print(f"   Plugin name: {plugin_name}")
    print(f"   Skill name: {skill_name}")
    print(f"   子技能: {len(skills)} 个")
    print(f"   MCP 服务器: {len(mcp_servers)} 个")
    print(f"   输出目录: {output_dir}")
    print()

    # 创建目录结构
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "scripts").mkdir(exist_ok=True)
    (output_dir / "references").mkdir(exist_ok=True)

    # 1. 生成封装层 SKILL.md
    wrapper_md = generate_wrapper_skill_md(plugin, skills, mcp_servers, skill_name=final_skill_name)
    (output_dir / "SKILL.md").write_text(wrapper_md, encoding="utf-8")
    print("✅ 生成封装层 SKILL.md")

    # 2. 复制原始 skills/ 目录
    src_skills = plugin_dir / "skills"
    if src_skills.exists():
        shutil.copytree(src_skills, output_dir / "skills")
        print(f"✅ 复制 skills/ 目录 ({len(skills)} 个子技能)")

    # 3. 复制原始 servers/ 目录（MCP 服务器代码）
    src_servers = plugin_dir / "servers"
    if src_servers.exists():
        shutil.copytree(src_servers, output_dir / "servers")
        print("✅ 复制 servers/ 目录 (MCP 服务器代码)")

    # 4. 复制原始配置到 references/
    shutil.copy2(plugin_dir / "plugin.json", output_dir / "references" / "plugin.json")
    print("✅ 复制 references/plugin.json")

    src_mcp = plugin_dir / "mcp.json"
    if src_mcp.exists():
        shutil.copy2(src_mcp, output_dir / "references" / "mcp.json")
        print("✅ 复制 references/mcp.json")

    # 5. 生成 start_mcp.py（如果有 MCP 服务器）
    if mcp_servers:
        start_mcp_content = generate_start_mcp_script(mcp_servers)
        start_mcp_path = output_dir / "scripts" / "start_mcp.py"
        start_mcp_path.write_text(start_mcp_content, encoding="utf-8")
        start_mcp_path.chmod(0o755)
        print(f"✅ 生成 scripts/start_mcp.py ({len(mcp_servers)} 个服务器配置)")

    # 6. 复制其他可能的目录（排除客户端扩展，因为封装版不支持）
    client_ext_dirs = {".cursor", ".claude-plugin", ".codex-plugin", ".gemini",
                        "com.github.copilot", "com.cursor", "com.anthropic"}
    for item in plugin_dir.iterdir():
        if item.is_dir() and item.name not in ("skills", "servers", "__pycache__") and item.name not in client_ext_dirs:
            if not (output_dir / item.name).exists():
                shutil.copytree(item, output_dir / item.name)
                print(f"✅ 复制 {item.name}/ 目录")

    # 7. 用官方 skill-creator 的 quick_validate.py 做额外验证
    quick_validate = Path(__file__).resolve().parent.parent / "official" / "skill-creator" / "scripts" / "quick_validate.py"
    if quick_validate.exists():
        print()
        print("🔍 官方规范验证（official/skill-creator/quick_validate.py）...")
        result = subprocess.run(
            [sys.executable, str(quick_validate), str(output_dir)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
        else:
            print(f"⚠️  {result.stdout.strip()}")
            print("   （警告不影响封装完成，但建议检查上述问题）")

    print()
    print("=" * 60)
    print("✅ 反向封装完成!")
    print("=" * 60)
    print()
    print(f"输出目录: {output_dir}")
    print(f"文件总数: {sum(1 for _ in output_dir.rglob('*') if _.is_file())}")
    print()
    print("下一步:")
    print(f"  1. cd {output_dir}")
    print("  2. 查看 SKILL.md，确认封装层描述准确")
    print("  3. 将此目录作为 Skill 安装到目标平台")
    if mcp_servers:
        print("  4. 确保 MCP 服务器的依赖已安装（参考 servers/ 目录）")
    print()
    print("注意: 此封装版用 AI 手动执行替代平台自动加载，")
    print("      可以在任何支持 Agent Skills 的平台上使用。")


if __name__ == "__main__":
    main()
