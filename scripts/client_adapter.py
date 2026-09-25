#!/usr/bin/env python3
"""
Agent Plugin 多客户端适配工具（合并版）

整合兼容性检查、原地适配生成、全量编译三种模式，支持 5 个客户端平台。

支持的客户端:
  - claude    Claude Code（.claude-plugin/ + marketplace.json）
  - codex     OpenAI Codex CLI（.codex-plugin/）
  - copilot   GitHub Copilot / VS Code（com.github.copilot/hooks/）
  - cursor    Cursor IDE（.cursor/rules/，自动从 skills 转换）
  - gemini    Google Gemini（.gemini/）
  - zed       Zed Editor（.zed/settings.json）
  - continue  Continue.dev（.continue/config.json）
  - roo       Roo Code（.roo/rules/）
  - windsurf  Windsurf（.windsurf/rules/）
  - cline     Cline（.cline/settings.json）

三种模式:
  --check     只检查兼容性，不修改文件（默认）
  --generate  在原插件目录中生成缺失的客户端扩展（不覆盖已有文件）
  --build     全量编译到输出目录，每个平台一个完整副本（支持 --force 覆盖）

用法:
    python3 client_adapter.py <插件目录> --check
    python3 client_adapter.py <插件目录> --generate --clients claude,copilot
    python3 client_adapter.py <插件目录> --build --output dist --target all
    python3 client_adapter.py <插件目录> --build --output dist --force
    python3 client_adapter.py --list-targets
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

CLIENT_CONFIGS = {
    "claude": {
        "name": "Claude Code",
        "extension_dir": ".claude-plugin",
        "required_files": ["plugin.json"],
        "optional_files": ["marketplace.json"],
    },
    "codex": {
        "name": "OpenAI Codex CLI",
        "extension_dir": ".codex-plugin",
        "required_files": ["plugin.json"],
        "optional_files": [],
    },
    "copilot": {
        "name": "GitHub Copilot / VS Code",
        "extension_dir": "com.github.copilot",
        "required_files": [],
        "optional_files": ["hooks/hooks.json"],
    },
    "cursor": {
        "name": "Cursor IDE",
        "extension_dir": ".cursor",
        "required_files": [],
        "optional_files": ["rules/"],
    },
    "gemini": {
        "name": "Google Gemini",
        "extension_dir": ".gemini",
        "required_files": ["plugin.json"],
        "optional_files": [],
    },
    "zed": {
        "name": "Zed Editor",
        "extension_dir": ".zed",
        "required_files": [],
        "optional_files": ["settings.json"],
    },
    "continue": {
        "name": "Continue.dev",
        "extension_dir": ".continue",
        "required_files": [],
        "optional_files": ["config.json"],
    },
    "roo": {
        "name": "Roo Code",
        "extension_dir": ".roo",
        "required_files": [],
        "optional_files": ["rules/"],
    },
    "windsurf": {
        "name": "Windsurf",
        "extension_dir": ".windsurf",
        "required_files": [],
        "optional_files": ["rules/"],
    },
    "cline": {
        "name": "Cline",
        "extension_dir": ".cline",
        "required_files": [],
        "optional_files": ["settings.json"],
    },
}

SUPPORTED_TARGETS = list(CLIENT_CONFIGS.keys())


def load_plugin_json(plugin_dir: Path) -> dict:
    """加载 plugin.json"""
    plugin_json = plugin_dir / "plugin.json"
    if not plugin_json.exists():
        print(f"错误: 缺少 plugin.json: {plugin_json}", file=sys.stderr)
        sys.exit(1)
    try:
        plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"错误: plugin.json 不是有效 JSON: {e}", file=sys.stderr)
        sys.exit(1)
    if "name" not in plugin:
        print("错误: plugin.json 缺少必需字段 name", file=sys.stderr)
        sys.exit(1)
    return plugin


def extract_skill_description(skill_md: Path) -> str:
    """从 SKILL.md 提取 description"""
    try:
        content = skill_md.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].split("\n"):
                    if line.strip().startswith("description:"):
                        return line.split(":", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return skill_md.parent.name


def check_client_compatibility(plugin_dir: Path, client: str) -> dict:
    """检查插件在特定客户端的兼容性"""
    config = CLIENT_CONFIGS[client]
    result = {
        "client": client,
        "name": config["name"],
        "compatible": True,
        "issues": [],
        "warnings": [],
        "extension_dir_exists": False,
        "missing_required_files": [],
        "missing_optional_files": [],
    }

    ext_dir = plugin_dir / config["extension_dir"]
    result["extension_dir_exists"] = ext_dir.exists()

    for req_file in config["required_files"]:
        file_path = ext_dir / req_file
        if not file_path.exists():
            if req_file == "plugin.json" and (plugin_dir / "plugin.json").exists():
                result["warnings"].append(f"根目录有 plugin.json，但 {config['extension_dir']}/ 下没有")
            else:
                result["missing_required_files"].append(req_file)
                result["issues"].append(f"缺少必需文件: {config['extension_dir']}/{req_file}")
                result["compatible"] = False

    for opt_file in config["optional_files"]:
        file_path = ext_dir / opt_file
        if not file_path.exists():
            result["missing_optional_files"].append(opt_file)

    if client == "cursor":
        skills_dir = plugin_dir / "skills"
        rules_dir = ext_dir / "rules"
        if skills_dir.exists() and not rules_dir.exists():
            result["warnings"].append("有 skills 但没有 .cursor/rules/ 规则文件，建议生成")

    if client == "copilot":
        hooks_dir = ext_dir / "hooks"
        if not hooks_dir.exists():
            result["warnings"].append("没有 com.github.copilot/hooks/ 目录，Copilot 特定功能不可用")

    return result


def generate_client_extension(plugin_dir: Path, client: str, plugin: dict, force: bool = False) -> list:
    """在原插件目录中生成缺失的客户端扩展文件"""
    config = CLIENT_CONFIGS[client]
    ext_dir = plugin_dir / config["extension_dir"]
    ext_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    def write_if_missing(path: Path, content: str):
        if not path.exists() or force:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            generated.append(str(path.relative_to(plugin_dir)))

    if client == "claude":
        claude_plugin = {
            "name": plugin.get("name", "my-plugin"),
            "description": plugin.get("description", ""),
            "version": plugin.get("version", "0.1.0"),
            "author": plugin.get("author", {}).get("name", ""),
            "license": plugin.get("license", "MIT"),
        }
        write_if_missing(ext_dir / "plugin.json", json.dumps(claude_plugin, indent=2, ensure_ascii=False) + "\n")
        marketplace = {
            "name": plugin.get("name", "my-plugin"),
            "description": plugin.get("description", ""),
            "plugins": [{"name": plugin.get("name", "my-plugin"), "path": "..", "description": plugin.get("description", "")}],
        }
        write_if_missing(ext_dir / "marketplace.json", json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n")

    elif client == "codex":
        codex_plugin = {
            "name": plugin.get("name", "my-plugin"),
            "description": plugin.get("description", ""),
            "version": plugin.get("version", "0.1.0"),
        }
        write_if_missing(ext_dir / "plugin.json", json.dumps(codex_plugin, indent=2, ensure_ascii=False) + "\n")

    elif client == "copilot":
        hooks = {"hooks": [], "_comment": "在此定义 Copilot hooks，参考 https://code.visualstudio.com/docs/copilot/agent-plugins"}
        write_if_missing(ext_dir / "hooks" / "hooks.json", json.dumps(hooks, indent=2, ensure_ascii=False) + "\n")

    elif client == "cursor":
        rules_dir = ext_dir / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        skills_dir = plugin_dir / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                desc = extract_skill_description(skill_md)
                content = skill_md.read_text(encoding="utf-8")
                body = content.split("---", 2)[-1].strip() if content.count("---") >= 2 else content
                rule_content = f"---\ndescription: {desc}\n---\n\n{body}\n"
                write_if_missing(rules_dir / f"{skill_dir.name}.mdc", rule_content)

    elif client == "gemini":
        gemini_plugin = {
            "name": plugin.get("name", "my-plugin"),
            "description": plugin.get("description", ""),
            "version": plugin.get("version", "0.1.0"),
            "skills": [],
        }
        skills_dir = plugin_dir / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    gemini_plugin["skills"].append({"name": skill_dir.name, "path": f"../skills/{skill_dir.name}"})
        write_if_missing(ext_dir / "plugin.json", json.dumps(gemini_plugin, indent=2, ensure_ascii=False) + "\n")

    elif client == "zed":
        zed_settings = {
            "language_servers": {},
            "agent": {
                "enabled": True,
                "provider": "openai",
            },
            "_comment": "Zed Editor 配置，参考 https://zed.dev/docs/agent",
        }
        write_if_missing(ext_dir / "settings.json", json.dumps(zed_settings, indent=2, ensure_ascii=False) + "\n")

    elif client == "continue":
        continue_config = {
            "models": {},
            "slashCommands": [],
            "customCommands": [],
            "_comment": "Continue.dev 配置，参考 https://docs.continue.dev/customize",
        }
        write_if_missing(ext_dir / "config.json", json.dumps(continue_config, indent=2, ensure_ascii=False) + "\n")

    elif client in ("roo", "windsurf"):
        # Roo Code 和 Windsurf 使用类似 Cursor 的 rules 格式
        rules_dir = ext_dir / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        skills_dir = plugin_dir / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                desc = extract_skill_description(skill_md)
                content = skill_md.read_text(encoding="utf-8")
                body = content.split("---", 2)[-1].strip() if content.count("---") >= 2 else content
                rule_content = f"---\ndescription: {desc}\n---\n\n{body}\n"
                write_if_missing(rules_dir / f"{skill_dir.name}.md", rule_content)

    elif client == "cline":
        cline_settings = {
            "cline": {
                "enabled": True,
                "rules": [],
            },
            "_comment": "Cline 配置，参考 https://github.com/cline/cline",
        }
        write_if_missing(ext_dir / "settings.json", json.dumps(cline_settings, indent=2, ensure_ascii=False) + "\n")

    return generated


def copy_common_files(src: Path, dst: Path, force: bool = False):
    """复制通用文件到目标目录"""
    for item in ["plugin.json", "mcp.json"]:
        src_file = src / item
        if src_file.exists() and (not (dst / item).exists() or force):
            shutil.copy2(src_file, dst / item)
    for item in ["skills", "servers"]:
        src_dir = src / item
        dst_dir = dst / item
        if src_dir.exists() and src_dir.is_dir():
            if dst_dir.exists() and force:
                shutil.rmtree(dst_dir)
            if not dst_dir.exists():
                shutil.copytree(src_dir, dst_dir)


def build_to_target(src: Path, dst: Path, client: str, plugin: dict, force: bool = False):
    """全量编译到目标平台目录"""
    copy_common_files(src, dst, force)
    # 在目标目录中生成客户端扩展（force 模式下覆盖）
    generate_client_extension(dst, client, plugin, force=force)
    # 生成平台 README
    readme = f"""# {plugin['name']} ({CLIENT_CONFIGS[client]['name']})

## 安装
将此目录添加到 {CLIENT_CONFIGS[client]['name']} 的插件路径，或通过插件市场安装。

## 说明
此目录由 agent-plugin-creator 的 client_adapter.py --build 自动生成。
源插件符合 Agent Plugins 1.0 标准，已适配 {CLIENT_CONFIGS[client]['name']} 平台。
"""
    (dst / "README.md").write_text(readme, encoding="utf-8")


def print_check_report(results: list):
    """打印兼容性检查报告"""
    print("=" * 70)
    print("Agent Plugin 多客户端兼容性检查报告")
    print("=" * 70)
    print()
    compatible_count = sum(1 for r in results if r["compatible"])
    print(f"检查客户端: {len(results)} 个")
    print(f"完全兼容: {compatible_count} 个")
    print(f"存在问题: {len(results) - compatible_count} 个")
    print()
    for r in results:
        status = "✅ 兼容" if r["compatible"] else "❌ 不兼容"
        print(f"{status}: {r['name']} ({r['client']})")
        print(f"   扩展目录: {'存在' if r['extension_dir_exists'] else '不存在'}")
        if r["issues"]:
            print(f"   问题 ({len(r['issues'])}):")
            for issue in r["issues"]:
                print(f"     - ❌ {issue}")
        if r["warnings"]:
            print(f"   警告 ({len(r['warnings'])}):")
            for warning in r["warnings"]:
                print(f"     - ⚠️  {warning}")
        if r["missing_optional_files"]:
            print(f"   缺失可选文件: {', '.join(r['missing_optional_files'])}")
        print()
    print("=" * 70)
    if compatible_count == len(results):
        print("✅ 所有客户端均兼容")
    else:
        print(f"⚠️  {len(results) - compatible_count} 个客户端存在问题，建议运行 --generate 生成适配文件")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Agent Plugin 多客户端适配工具（检查/生成/编译）")
    parser.add_argument("plugin_dir", nargs="?", help="插件目录路径")
    parser.add_argument("--check", action="store_true", help="只检查兼容性（默认模式）")
    parser.add_argument("--generate", action="store_true", help="在原目录中生成缺失的客户端扩展")
    parser.add_argument("--build", action="store_true", help="全量编译到输出目录")
    parser.add_argument("--clients", help="指定客户端，逗号分隔（默认所有）")
    parser.add_argument("--target", default="all", help="--build 模式的目标平台，逗号分隔或 all")
    parser.add_argument("--output", default="dist", help="--build 模式的输出目录（默认 dist）")
    parser.add_argument("--force", action="store_true", help="覆盖已有文件（--build 和 --generate 模式）")
    parser.add_argument("--report", action="store_true", help="输出 JSON 格式报告（--check 模式）")
    parser.add_argument("--list-targets", action="store_true", help="列出支持的目标平台")
    args = parser.parse_args()

    if args.list_targets:
        print("支持的目标平台:")
        for t in SUPPORTED_TARGETS:
            print(f"  - {t}: {CLIENT_CONFIGS[t]['name']}")
        print(f"  - all: 所有平台")
        return

    if not args.plugin_dir:
        parser.print_help()
        sys.exit(1)

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.exists():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    plugin = load_plugin_json(plugin_dir)

    # 确定目标客户端
    if args.clients:
        clients = [c.strip() for c in args.clients.split(",")]
        # "all" 展开为所有支持的客户端
        if "all" in clients:
            clients = SUPPORTED_TARGETS
    elif args.target != "all":
        clients = [c.strip() for c in args.target.split(",")]
    else:
        clients = SUPPORTED_TARGETS

    for c in clients:
        if c not in CLIENT_CONFIGS:
            print(f"错误: 不支持的客户端: {c}", file=sys.stderr)
            print(f"支持的客户端: {', '.join(SUPPORTED_TARGETS)}", file=sys.stderr)
            sys.exit(1)

    # 模式 1: 检查兼容性
    if args.check or (not args.generate and not args.build):
        results = [check_client_compatibility(plugin_dir, c) for c in clients]
        if args.report:
            report = {
                "plugin": plugin.get("name", ""),
                "clients": results,
                "summary": {
                    "total": len(results),
                    "compatible": sum(1 for r in results if r["compatible"]),
                    "issues": sum(len(r["issues"]) for r in results),
                    "warnings": sum(len(r["warnings"]) for r in results),
                },
            }
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print_check_report(results)
        if any(not r["compatible"] for r in results):
            sys.exit(1)
        return

    # 模式 2: 原地生成缺失扩展
    if args.generate:
        print(f"🔧 为 {len(clients)} 个客户端生成适配文件...")
        print()
        all_generated = []
        for client in clients:
            generated = generate_client_extension(plugin_dir, client, plugin, force=args.force)
            if generated:
                print(f"  ✅ {CLIENT_CONFIGS[client]['name']}:")
                for g in generated:
                    print(f"     - {g}")
                all_generated.extend(generated)
            else:
                print(f"  ⏭️  {CLIENT_CONFIGS[client]['name']}: 无需生成（已存在或不适用）")
        print()
        print(f"共生成 {len(all_generated)} 个文件")
        return

    # 模式 3: 全量编译
    if args.build:
        print(f"📦 源插件: {plugin['name']} v{plugin.get('version', '0.1.0')}")
        print(f"🎯 目标平台: {', '.join(clients)}")
        print()
        output_dir = Path(args.output).resolve()
        for client in clients:
            target_dir = output_dir / client
            if target_dir.exists() and args.force:
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            build_to_target(plugin_dir, target_dir, client, plugin, force=args.force)
            print(f"  ✅ {client}: 已生成 {target_dir}")
        print()
        print("=" * 60)
        print(f"编译完成: {output_dir}")
        print(f"生成了 {len(clients)} 个平台的适配版本")
        print("=" * 60)
        return


if __name__ == "__main__":
    main()
