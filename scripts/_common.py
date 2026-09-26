#!/usr/bin/env python3
"""
共享工具函数模块

所有脚本共用的工具函数放在这里，避免代码重复。
"""
import json
import sys
from pathlib import Path
from typing import Optional


def load_plugin_json(plugin_dir: Path) -> dict:
    """加载并解析 plugin.json

    Args:
        plugin_dir: 插件目录路径

    Returns:
        解析后的 plugin.json 字典

    Raises:
        FileNotFoundError: plugin.json 不存在
        json.JSONDecodeError: plugin.json 格式错误
    """
    plugin_json = plugin_dir / "plugin.json"
    if not plugin_json.exists():
        raise FileNotFoundError(f"plugin.json 不存在: {plugin_json}")
    with plugin_json.open(encoding="utf-8") as f:
        return json.load(f)


def load_mcp_json(plugin_dir: Path) -> Optional[dict]:
    """加载并解析 mcp.json（如果存在）

    Args:
        plugin_dir: 插件目录路径

    Returns:
        解析后的 mcp.json 字典，不存在则返回 None
    """
    mcp_json = plugin_dir / "mcp.json"
    if not mcp_json.exists():
        return None
    with mcp_json.open(encoding="utf-8") as f:
        return json.load(f)


def print_header(title: str, width: int = 60):
    """打印统一的标题头

    Args:
        title: 标题文本
        width: 分隔线宽度
    """
    print("=" * width)
    print(title)
    print("=" * width)


def print_footer(success: bool, success_msg: str, fail_msg: str, width: int = 60):
    """打印统一的结尾

    Args:
        success: 是否成功
        success_msg: 成功消息
        fail_msg: 失败消息
        width: 分隔线宽度
    """
    print("=" * width)
    if success:
        print(f"✅ {success_msg}")
    else:
        print(f"❌ {fail_msg}")
    print("=" * width)


def error_exit(message: str, code: int = 1):
    """统一的错误退出

    Args:
        message: 错误消息
        code: 退出码
    """
    print(f"错误: {message}", file=sys.stderr)
    sys.exit(code)


def detect_plugin_dir(path: Optional[str] = None) -> Path:
    """智能检测插件目录

    如果指定了路径就用指定的，否则检查当前目录是否有 plugin.json。

    Args:
        path: 用户指定的路径，可为 None

    Returns:
        插件目录的绝对路径

    Raises:
        FileNotFoundError: 找不到 plugin.json
    """
    if path:
        plugin_dir = Path(path).resolve()
    else:
        plugin_dir = Path.cwd().resolve()

    if (plugin_dir / "plugin.json").exists():
        return plugin_dir

    # 如果指定的路径是文件，取父目录
    if plugin_dir.is_file():
        plugin_dir = plugin_dir.parent
        if (plugin_dir / "plugin.json").exists():
            return plugin_dir

    raise FileNotFoundError(
        f"在 {plugin_dir} 找不到 plugin.json。"
        f"请在插件目录内运行，或指定插件目录路径。"
    )
