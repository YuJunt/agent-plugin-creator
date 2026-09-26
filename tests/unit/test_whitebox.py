#!/usr/bin/env python3
"""
P1 白盒测试（直接 import 函数，提升覆盖率）

覆盖：
1. _common.py - 6 个通用函数
2. errors.py - 统一错误码系统（31 个错误码 + 辅助函数）
"""
import json
import pytest
import sys
from pathlib import Path

# 添加 scripts 目录到 sys.path，以便直接 import
SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# ============================================================
# 1. _common.py 白盒测试
# ============================================================

class TestCommonModule:
    """_common.py 共享模块白盒测试"""

    def test_load_plugin_json_valid(self, temp_dir):
        """测试加载有效的 plugin.json"""
        from _common import load_plugin_json
        plugin_dir = temp_dir / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "name": "test-plugin", "version": "1.0.0"
        }), encoding="utf-8")

        result = load_plugin_json(plugin_dir)
        assert result["name"] == "test-plugin"
        assert result["version"] == "1.0.0"

    def test_load_plugin_json_missing(self, temp_dir):
        """测试缺少 plugin.json 应该抛出异常"""
        from _common import load_plugin_json
        with pytest.raises(FileNotFoundError):
            load_plugin_json(temp_dir / "nonexistent")

    def test_load_plugin_json_invalid_json(self, temp_dir):
        """测试无效 JSON 应该抛出异常"""
        from _common import load_plugin_json
        plugin_dir = temp_dir / "bad-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text("not valid json {{{", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_plugin_json(plugin_dir)

    def test_load_mcp_json_exists(self, temp_dir):
        """测试加载存在的 mcp.json"""
        from _common import load_mcp_json
        plugin_dir = temp_dir / "mcp-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "mcpServers": {"test": {"command": "python3"}}
        }), encoding="utf-8")

        result = load_mcp_json(plugin_dir)
        assert result is not None
        assert "test" in result["mcpServers"]

    def test_load_mcp_json_missing(self, temp_dir):
        """测试缺少 mcp.json 应该返回 None"""
        from _common import load_mcp_json
        result = load_mcp_json(temp_dir / "no-mcp-plugin")
        assert result is None

    def test_print_header(self, capsys):
        """测试 print_header 输出格式"""
        from _common import print_header
        print_header("测试标题")
        captured = capsys.readouterr()
        assert "测试标题" in captured.out
        assert "=" in captured.out

    def test_print_header_custom_width(self, capsys):
        """测试 print_header 自定义宽度"""
        from _common import print_header
        print_header("测试", width=40)
        captured = capsys.readouterr()
        # 宽度 40 的分隔线
        assert len(captured.out.split("\n")[0]) <= 42

    def test_print_footer_success(self, capsys):
        """测试 print_footer 成功情况"""
        from _common import print_footer
        print_footer(True, "成功消息", "失败消息")
        captured = capsys.readouterr()
        assert "成功消息" in captured.out

    def test_print_footer_failure(self, capsys):
        """测试 print_footer 失败情况"""
        from _common import print_footer
        print_footer(False, "成功消息", "失败消息")
        captured = capsys.readouterr()
        assert "失败消息" in captured.out

    def test_error_exit(self):
        """测试 error_exit 应该调用 sys.exit"""
        from _common import error_exit
        with pytest.raises(SystemExit) as exc_info:
            error_exit("测试错误", code=42)
        assert exc_info.value.code == 42

    def test_detect_plugin_dir_explicit(self, temp_dir):
        """测试 detect_plugin_dir 显式指定路径"""
        from _common import detect_plugin_dir
        plugin_dir = temp_dir / "my-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text("{}", encoding="utf-8")
        result = detect_plugin_dir(str(plugin_dir))
        assert result == plugin_dir.resolve()

    def test_detect_plugin_dir_current_dir(self, monkeypatch, temp_dir):
        """测试 detect_plugin_dir 自动检测当前目录"""
        from _common import detect_plugin_dir
        plugin_dir = temp_dir / "current-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text("{}", encoding="utf-8")
        monkeypatch.chdir(plugin_dir)
        result = detect_plugin_dir(None)
        assert result == plugin_dir.resolve()

    def test_detect_plugin_dir_not_found(self, monkeypatch, temp_dir):
        """测试 detect_plugin_dir 找不到插件目录应该抛出异常"""
        from _common import detect_plugin_dir
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()
        monkeypatch.chdir(empty_dir)
        with pytest.raises(FileNotFoundError):
            detect_plugin_dir(None)



