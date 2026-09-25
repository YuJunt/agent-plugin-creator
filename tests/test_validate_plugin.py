#!/usr/bin/env python3
"""
validate_plugin.py 单元测试
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_plugin.py"


def run_validate(plugin_dir: Path) -> subprocess.CompletedProcess:
    """运行 validate_plugin.py"""
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(plugin_dir)],
        capture_output=True,
        text=True,
        timeout=30,
    )


def create_minimal_plugin(tmp_path: Path) -> Path:
    """创建最小可用插件"""
    plugin_dir = tmp_path / "test-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "test-plugin",
        "version": "0.1.0",
        "description": "Test plugin"
    }))
    return plugin_dir


class TestValidatePlugin:
    """validate_plugin.py 测试集"""

    def test_help(self):
        """测试 --help 正常输出"""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "用法" in result.stdout or "usage" in result.stdout.lower()

    def test_missing_directory(self):
        """测试不存在的目录"""
        result = run_validate(Path("/nonexistent/path"))
        assert result.returncode != 0

    def test_minimal_valid_plugin(self, tmp_path):
        """测试最小有效插件"""
        plugin_dir = create_minimal_plugin(tmp_path)
        result = run_validate(plugin_dir)
        assert result.returncode == 0
        assert "通过" in result.stdout

    def test_missing_plugin_json(self, tmp_path):
        """测试缺少 plugin.json"""
        plugin_dir = tmp_path / "no-plugin-json"
        plugin_dir.mkdir()
        result = run_validate(plugin_dir)
        assert result.returncode != 0
        assert "plugin.json" in result.stdout

    def test_invalid_plugin_name(self, tmp_path):
        """测试无效的插件名称"""
        plugin_dir = tmp_path / "Invalid-Name"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "Invalid-Name",
        }))
        result = run_validate(plugin_dir)
        # 名称与目录名不一致应该报错
        assert result.returncode != 0

    def test_valid_skill_in_plugin(self, tmp_path):
        """测试包含有效 Skill 的插件"""
        plugin_dir = create_minimal_plugin(tmp_path)
        skill_dir = plugin_dir / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: Test skill for validation.\n---\n\nTest.\n"
        )
        result = run_validate(plugin_dir)
        assert result.returncode == 0

    def test_invalid_skill_frontmatter(self, tmp_path):
        """测试包含无效 Skill frontmatter 的插件"""
        plugin_dir = create_minimal_plugin(tmp_path)
        skill_dir = plugin_dir / "skills" / "bad-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("not frontmatter")
        result = run_validate(plugin_dir)
        assert result.returncode != 0

    def test_mcp_json_schema_mismatch(self, tmp_path):
        """测试 mcp.json 与 plugin.json schema 版本不一致"""
        plugin_dir = create_minimal_plugin(tmp_path)
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/9.9.9/mcp.schema.json",
            "mcpServers": {}
        }))
        result = run_validate(plugin_dir)
        assert result.returncode != 0

    def test_mcp_env_reserved_variable(self, tmp_path):
        """测试 mcp.json 中使用保留变量名"""
        plugin_dir = create_minimal_plugin(tmp_path)
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {
                "test": {
                    "type": "stdio",
                    "command": "python3",
                    "env": {"PLUGIN_ROOT": "/bad"}
                }
            }
        }))
        result = run_validate(plugin_dir)
        assert result.returncode != 0
        assert "PLUGIN_ROOT" in result.stdout or "保留" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
