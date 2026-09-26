#!/usr/bin/env python3
"""
错误码系统测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from errors import ErrorCode, PluginError, format_error


def test_error_codes_exist():
    """测试所有错误码都有定义"""
    assert len(ErrorCode) > 30, "错误码数量应该大于 30"


def test_error_code_format():
    """测试错误码格式化输出"""
    result = format_error(ErrorCode.VALIDATION_FAILED, "测试错误")
    assert "E2001" in result
    assert "验证失败" in result
    assert "测试错误" in result
    assert "下一步" in result


def test_error_code_json():
    """测试错误码 JSON 输出"""
    result = format_error(ErrorCode.INVALID_ARGUMENT, "参数错误", as_json=True)
    import json
    data = json.loads(result)
    assert data["code"] == 1001
    assert data["failure"] == "无效参数"
    assert data["cause"] == "参数错误"
    assert "next_action" in data


def test_plugin_error_exception():
    """测试 PluginError 异常"""
    try:
        raise PluginError(ErrorCode.FILE_NOT_FOUND, "文件不存在", "test.py", 10)
    except PluginError as e:
        assert e.error_code == ErrorCode.FILE_NOT_FOUND
        assert e.detail == "文件不存在"
        assert e.file == "test.py"
        assert e.line == 10


def test_error_severity():
    """测试错误严重性级别"""
    # 安全错误应该是 critical
    result = format_error(ErrorCode.HARDCODED_SECRET, as_json=True)
    import json
    data = json.loads(result)
    assert data["severity"] in ("critical", "error")


def test_internal_error_bug_report():
    """测试内部错误包含 bug report URL"""
    result = format_error(ErrorCode.INTERNAL_ERROR, "unexpected")
    assert "github.com" in result
    assert "issues" in result
