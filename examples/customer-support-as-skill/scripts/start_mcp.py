#!/usr/bin/env python3
"""
MCP 服务器启动与管理工具（由 plugin_to_skill.py 自动生成）

用法:
    python3 start_mcp.py --list          # 列出可用服务器
    python3 start_mcp.py --server <名称>  # 启动指定服务器（stdio 交互模式）
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# 服务器配置（由 plugin_to_skill.py 从原始 mcp.json 提取）
SERVERS = {
    "support-tickets": {
        "transport": "stdio",
        "command": "python3",
        "args": ["${PLUGIN_ROOT}/servers/support-tickets/support_ticket_server.py"],
        "env": {},
        "url": "",
    },
}


def list_servers():
    """列出所有可用服务器"""
    print("可用 MCP 服务器:")
    for name, config in SERVERS.items():
        print(f"  - {name} (transport={config['transport']})")


def start_server(name: str):
    """启动指定服务器（stdio 交互模式）"""
    if name not in SERVERS:
        print(f"错误: 找不到服务器 '{name}'", file=sys.stderr)
        print(f"可用服务器: {', '.join(SERVERS.keys())}", file=sys.stderr)
        sys.exit(1)

    config = SERVERS[name]
    print(f"启动 MCP 服务器: {name} (transport={config['transport']})")

    if config['transport'] == 'stdio':
        cmd = [config['command']] + config['args']
        env = config.get('env', {})
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, **env},
            )
            print("服务器已启动，进入 stdio 交互模式（输入 JSON-RPC 请求，Ctrl+C 退出）")
            print()
            # 简单的交互循环
            while True:
                try:
                    line = input("> ")
                    if not line.strip():
                        continue
                    proc.stdin.write(line + '\n')
                    proc.stdin.flush()
                    response = proc.stdout.readline()
                    if response:
                        print(response.strip())
                except (EOFError, KeyboardInterrupt):
                    print("\n退出")
                    break
            proc.terminate()
            proc.wait()
        except FileNotFoundError:
            print(f"错误: 找不到可执行文件 '{config['command']}'", file=sys.stderr)
            print("请确保 MCP 服务器已正确安装，或检查命令路径", file=sys.stderr)
            sys.exit(1)
    elif config['transport'] == 'streamable-http':
        print(f"HTTP 服务器地址: {config['url']}")
        print("请使用 HTTP 客户端发送 JSON-RPC 请求到上述地址")
    else:
        print(f"不支持的 transport: {config['transport']}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='MCP 服务器启动与管理工具')
    parser.add_argument('--list', action='store_true', help='列出可用服务器')
    parser.add_argument('--server', help='启动指定服务器')
    args = parser.parse_args()

    if args.list:
        list_servers()
    elif args.server:
        start_server(args.server)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
