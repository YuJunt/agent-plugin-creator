#!/usr/bin/env python3
"""统一日志工具模块的别名导入。"""

from common import (
    setup_logging,
    get_logger,
    Logger,
    parse_verbose_args,
)

__all__ = ["setup_logging", "get_logger", "Logger", "parse_verbose_args"]
