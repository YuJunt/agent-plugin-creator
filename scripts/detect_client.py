#!/usr/bin/env python3
"""
客户端环境自动检测与推荐

自动检测当前运行环境，推荐最佳的客户端和配置方式。
支持的客户端：Claude Code, OpenAI Codex, Cursor, GitHub Copilot, Grok Build, Kimi Code

用法:
    python3 scripts/detect_client.py
    python3 scripts/detect_client.py --json
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path


# 支持的客户端列表
KNOWN_CLIENTS = [
    {
        "name": "Claude Code",
        "env_vars": ["CLAUDE_CODE_VERSION", "CLAUDE_PROJECT_DIR"],
        "cli_cmd": "claude",
        "config_files": [".claude/", "CLAUDE.md"],
        "plugin_format": "agent-plugins",
        "install_cmd": "npx plugins add {org}/{repo}",
    },
    {
        "name": "OpenAI Codex",
        "env_vars": ["CODEX_HOME", "OPENAI_CODEX_VERSION"],
        "cli_cmd": "codex",
        "config_files": [".codex/", "AGENTS.md"],
        "plugin_format": "codex-native",
        "install_cmd": "codex plugins install {org}/{repo}",
    },
    {
        "name": "Cursor",
        "env_vars": ["CURSOR_VERSION", "CURSOR_API_KEY"],
        "cli_cmd": None,  # Cursor 是 IDE，没有 CLI
        "config_files": [".cursor/", "cursor.rules"],
        "plugin_format": "cursor-native",
        "install_cmd": "/add-plugin {org}/{repo}",
    },
    {
        "name": "GitHub Copilot",
        "env_vars": ["COPILOT_VERSION", "GITHUB_COPILOT"],
        "cli_cmd": "copilot",
        "config_files": [".github/plugin/", "copilot-metadata.json"],
        "plugin_format": "github-copilot",
        "install_cmd": "gh extension install {org}/{repo}",
    },
    {
        "name": "VS Code",
        "env_vars": ["VSCODE_VERSION", "VSCODE_PID"],
        "cli_cmd": "code",
        "config_files": [".vscode/", "settings.json"],
        "plugin_format": "vscode-extension",
        "install_cmd": "code --install-extension {org}.{repo}",
    },
]


def detect_current_environment() -> dict:
    """自动检测当前环境"""
    detected = []

    for client in KNOWN_CLIENTS:
        found = False
        evidence = []

        # 检查环境变量
        for env_var in client["env_vars"]:
            if env_var in os.environ:
                found = True
                evidence.append(f"env: {env_var}")

        # 检查 CLI 命令
        if client["cli_cmd"] and shutil.which(client["cli_cmd"]):
            found = True
            evidence.append(f"cli: {client['cli_cmd']}")

        # 检查配置文件
        cwd = Path.cwd()
        for config_file in client["config_files"]:
            if (cwd / config_file).exists():
                found = True
                evidence.append(f"file: {config_file}")

        if found:
            detected.append({
                "name": client["name"],
                "evidence": evidence,
                "plugin_format": client["plugin_format"],
                "install_cmd": client["install_cmd"],
            })

    # 检测操作系统
    os_type = "unknown"
    if sys.platform.startswith("linux"):
        os_type = "linux"
    elif sys.platform.startswith("darwin"):
        os_type = "macos"
    elif sys.platform.startswith("win"):
        os_type = "windows"

    # 检测 Python 版本
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # 检测 Node.js
    node_version = None
    if shutil.which("node"):
        import subprocess
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            node_version = result.stdout.strip()
        except Exception:
            pass

    return {
        "detected_clients": detected,
        "os": os_type,
        "python_version": python_version,
        "node_version": node_version,
        "working_directory": str(Path.cwd()),
    }


def recommend_client(env: dict) -> dict:
    """根据检测结果推荐最佳客户端"""
    detected = env["detected_clients"]

    if not detected:
        return {
            "recommendation": "unknown",
            "reason": "未检测到已知客户端环境",
            "suggestions": [
                "推荐使用 Claude Code（对 Agent Plugins 支持最好）",
                "或使用 GitHub Copilot（VS Code 内置）",
            ],
        }

    # 按优先级排序
    priority = ["Claude Code", "GitHub Copilot", "Cursor", "OpenAI Codex", "VS Code"]
    detected_names = [c["name"] for c in detected]

    for client_name in priority:
        if client_name in detected_names:
            client = next(c for c in detected if c["name"] == client_name)
            return {
                "recommendation": client_name,
                "reason": f"检测到 {client_name} 环境",
                "evidence": client["evidence"],
                "plugin_format": client["plugin_format"],
                "install_command_template": client["install_cmd"],
            }

    return {
        "recommendation": detected[0]["name"],
        "reason": "检测到客户端环境",
        "detected": [c["name"] for c in detected],
    }


def main():
    parser = argparse.ArgumentParser(description="客户端环境自动检测与推荐")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    env = detect_current_environment()
    recommendation = recommend_client(env)
    result = {**env, "recommendation": recommendation}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("客户端环境检测")
        print("=" * 60)
        print(f"\n操作系统: {env['os']}")
        print(f"Python: {env['python_version']}")
        print(f"Node.js: {env['node_version'] or '未安装'}")

        print(f"\n检测到的客户端:")
        if env["detected_clients"]:
            for client in env["detected_clients"]:
                print(f"  ✅ {client['name']}")
                print(f"     证据: {', '.join(client['evidence'])}")
        else:
            print("  未检测到已知客户端")

        rec = result["recommendation"]
        print(f"\n推荐: {rec['recommendation']}")
        print(f"原因: {rec['reason']}")
        if "install_command_template" in rec:
            print(f"安装命令模板: {rec['install_command_template']}")

        print("=" * 60)


if __name__ == "__main__":
    main()
