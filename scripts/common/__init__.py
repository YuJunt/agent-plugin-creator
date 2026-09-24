#!/usr/bin/env python3
"""
统一日志工具模块。

提供标准化的日志输出，支持：
- 4个日志级别：DEBUG / INFO / WARNING / ERROR
- 彩色输出（终端环境）
- 统一格式：[级别] 时间 - 消息
- --verbose 全局调试模式
- 错误自动输出到 stderr

用法：
    from common.logger import get_logger, setup_logging
    
    setup_logging(verbose=True)
    log = get_logger("my-script")
    log.info("开始处理")
    log.error("处理失败")
"""

from __future__ import annotations

import sys
import time
from typing import Optional


# 颜色代码
_COLORS = {
    "DEBUG": "\033[36m",     # 青色
    "INFO": "\033[32m",      # 绿色
    "WARNING": "\033[33m",   # 黄色
    "ERROR": "\033[31m",     # 红色
    "CRITICAL": "\033[35m",  # 紫色
    "RESET": "\033[0m",
}

# 全局配置
_verbose = False
_use_color = sys.stdout.isatty()


def setup_logging(verbose: bool = False, use_color: Optional[bool] = None):
    """初始化日志配置。

    Args:
        verbose: 是否启用 DEBUG 级别
        use_color: 是否使用彩色输出，None 表示自动检测
    """
    global _verbose, _use_color
    _verbose = verbose
    if use_color is not None:
        _use_color = use_color


def get_logger(name: str) -> "Logger":
    """获取日志器实例。

    Args:
        name: 日志器名称（通常是脚本名）

    Returns:
        Logger 实例
    """
    return Logger(name)


class Logger:
    """轻量级日志器。"""

    def __init__(self, name: str):
        self.name = name

    def _format(self, level: str, message: str) -> str:
        timestamp = time.strftime("%H:%M:%S")
        prefix = f"[{level}] {timestamp} {self.name}"
        if _use_color:
            color = _COLORS.get(level, "")
            reset = _COLORS["RESET"]
            return f"{color}{prefix}{reset} - {message}"
        return f"{prefix} - {message}"

    def debug(self, message: str):
        """调试级别日志（仅 verbose 模式下输出）。"""
        if _verbose:
            print(self._format("DEBUG", message), file=sys.stderr)

    def info(self, message: str):
        """信息级别日志。"""
        print(self._format("INFO", message), file=sys.stdout)

    def warning(self, message: str):
        """警告级别日志。"""
        print(self._format("WARNING", message), file=sys.stderr)

    def error(self, message: str):
        """错误级别日志。"""
        print(self._format("ERROR", message), file=sys.stderr)

    def critical(self, message: str):
        """严重错误级别日志。"""
        print(self._format("CRITICAL", message), file=sys.stderr)

    def success(self, message: str):
        """成功消息（INFO 级别，带 ✅ 标记）。"""
        self.info(f"✅ {message}")

    def fail(self, message: str):
        """失败消息（ERROR 级别，带 ❌ 标记）。"""
        self.error(f"❌ {message}")

    def step(self, number: int, total: int, message: str):
        """步骤进度消息。"""
        self.info(f"[{number}/{total}] {message}")


def parse_verbose_args(argv: list) -> tuple[list, bool]:
    """从命令行参数中解析 --verbose 选项。

    Args:
        argv: 原始命令行参数列表

    Returns:
        (过滤后的参数列表, 是否启用 verbose)
    """
    verbose = "--verbose" in argv or "-v" in argv
    filtered = [a for a in argv if a not in ("--verbose", "-v")]
    if verbose:
        setup_logging(verbose=True)
    return filtered, verbose
