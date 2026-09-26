"""
第2层：参数化单元测试（validate_plugin 各种输入）
"""
import json
import pytest
from tests.conftest import run_script


class TestValidateValidInputs:
    @pytest.mark.parametrize("version", ["1.0.0", "0.1.0", "2.3.4"])
    def test_valid_semver_versions(self, standard_plugin, version):
        plugin_json = json.loads((standard_plugin / "plugin.json").read_text())
        plugin_json["version"] = version
        (standard_plugin / "plugin.json").write_text(json.dumps(plugin_json), encoding="utf-8")
        result = run_script("validate_plugin.py", [str(standard_plugin)])
        assert result.returncode == 0

    def test_plugin_without_skills(self, temp_dir):
        plugin_dir = temp_dir / "mcp-only"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "mcp-only", "version": "1.0.0", "description": "纯 MCP"
        }), encoding="utf-8")
        (plugin_dir / "README.md").write_text("# MCP Only\n", encoding="utf-8")
        result = run_script("validate_plugin.py", [str(plugin_dir)])
        assert result.returncode == 0

    def test_multi_skill_plugin(self, multi_skill_plugin):
        result = run_script("validate_plugin.py", [str(multi_skill_plugin)])
        assert result.returncode == 0


class TestValidateInvalidInputs:
    def test_missing_plugin_json(self, empty_plugin):
        result = run_script("validate_plugin.py", [str(empty_plugin)])
        assert result.returncode != 0

    def test_invalid_json(self, invalid_json_plugin):
        result = run_script("validate_plugin.py", [str(invalid_json_plugin)])
        assert result.returncode != 0

    def test_name_mismatch(self, name_mismatch_plugin):
        result = run_script("validate_plugin.py", [str(name_mismatch_plugin)])
        assert result.returncode != 0
        assert "不一致" in result.stdout

    @pytest.mark.parametrize("version", ["1", "1.0", "v1.0.0", "abc", "latest"])
    def test_invalid_semver_warns(self, standard_plugin, version):
        plugin_json = json.loads((standard_plugin / "plugin.json").read_text())
        plugin_json["version"] = version
        (standard_plugin / "plugin.json").write_text(json.dumps(plugin_json), encoding="utf-8")
        result = run_script("validate_plugin.py", [str(standard_plugin)])
        combined = result.stdout + result.stderr
        assert "version" in combined.lower() or "版本" in combined


class TestValidateBoundary:
    def test_empty_description(self, standard_plugin):
        plugin_json = json.loads((standard_plugin / "plugin.json").read_text())
        plugin_json["description"] = ""
        (standard_plugin / "plugin.json").write_text(json.dumps(plugin_json), encoding="utf-8")
        result = run_script("validate_plugin.py", [str(standard_plugin)])
        assert result.returncode in [0, 1]

    def test_special_characters(self, standard_plugin):
        plugin_json = json.loads((standard_plugin / "plugin.json").read_text())
        plugin_json["description"] = "测试!@#$%^&*()特殊字符"
        (standard_plugin / "plugin.json").write_text(json.dumps(plugin_json), encoding="utf-8")
        result = run_script("validate_plugin.py", [str(standard_plugin)])
        assert result.returncode == 0


class TestValidateOutput:
    def test_output_has_summary(self, standard_plugin):
        result = run_script("validate_plugin.py", [str(standard_plugin)])
        assert "结论" in result.stdout

    def test_failure_has_fix_suggestions(self, name_mismatch_plugin):
        result = run_script("validate_plugin.py", [str(name_mismatch_plugin)])
        assert "修复" in result.stdout or "建议" in result.stdout
