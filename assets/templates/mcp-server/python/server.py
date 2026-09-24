"""
MCP Server - Python Template

基于官方 FastMCP 的 MCP 服务器模板。
在此文件中注册你的工具，然后打包进 Agent Plugin。

启动方式:
    python server.py              # stdio 传输（默认）
    python server.py --http      # streamable-http 传输
"""

import argparse
import sys
from datetime import datetime, timezone

from fastmcp import FastMCP

# ============================================================
# 服务器配置
# ============================================================

mcp = FastMCP("mcp-server-template")


# ============================================================
# 工具注册
# ============================================================

@mcp.tool()
def add(a: int, b: int) -> str:
    """Add two numbers together.

    Use when the user needs to perform basic arithmetic addition.

    Args:
        a: First number to add
        b: Second number to add
    """
    result = a + b
    return f"{a} + {b} = {result}"


@mcp.tool()
def get_current_time() -> str:
    """Get the current date and time in ISO 8601 format.

    Use when the user asks what time it is or needs a timestamp.
    """
    now = datetime.now(timezone.utc).isoformat()
    return f"Current time (UTC): {now}"


# ============================================================
# 在此添加更多工具...
# ============================================================

# @mcp.tool()
# def your_tool_name(param1: str, param2: int = 0) -> str:
#     """Description of what your tool does and when to use it.
#
#     Args:
#         param1: Description of param1
#         param2: Description of optional param2
#     """
#     # 你的业务逻辑
#     return f"Result: {param1} = {param2}"


# ============================================================
# 启动服务器
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="MCP Server Template")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use streamable-http transport instead of stdio",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="HTTP host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP port (default: 8000)",
    )
    args = parser.parse_args()

    if args.http:
        # streamable-http 传输（远程服务）
        print(f"Starting MCP server on http://{args.host}:{args.port}/mcp", file=sys.stderr)
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        # stdio 传输（本地子进程，Agent Plugin 默认）
        print("Starting MCP server (stdio transport)", file=sys.stderr)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
