"""
第3层：契约测试（输入输出格式、退出码、错误格式）
"""
import json
import pytest
from tests.conftest import run_script


class TestExitCodeContract:
    def test_validate_success_exit_0(self, standard_plugin):
        assert run_script("validate_plugin.py", [str(standard_plugin)]).returncode == 0

    def test_validate_failure_exit_nonzero(self, empty_plugin):
        assert run_script("validate_plugin.py", [str(empty_plugin)]).returncode != 0

    def test_audit_success_exit_0(self, standard_plugin):
        assert run_script("audit_plugin.py", [str(standard_plugin)]).returncode == 0

    def test_smoke_success_exit_0(self, standard_plugin):
        assert run_script("smoke_test.py", [str(standard_plugin)]).returncode == 0

    def test_invalid_args_exit_2(self):
        assert run_script("validate_plugin.py", ["--nonexistent"]).returncode == 2


class TestOutputFormatContract:
    def test_validate_has_header_footer(self, standard_plugin):
        result = run_script("validate_plugin.py", [str(standard_plugin)])
        assert "=" * 10 in result.stdout
        assert "结论" in result.stdout

    def test_audit_has_severity(self, standard_plugin):
        result = run_script("audit_plugin.py", [str(standard_plugin)])
        assert any(w in result.stdout.lower() for w in ["critical", "high", "medium", "low", "未发现"])

    def test_smoke_has_checks(self, standard_plugin):
        result = run_script("smoke_test.py", [str(standard_plugin)])
        assert "通过" in result.stdout or "PASS" in result.stdout


class TestErrorFormatContract:
    def test_error_has_reason(self, empty_plugin):
        result = run_script("validate_plugin.py", [str(empty_plugin)])
        combined = result.stdout + result.stderr
        assert any(w in combined for w in ["缺少", "不存在", "错误", "失败"])

    def test_error_mentions_plugin_json(self, empty_plugin):
        result = run_script("validate_plugin.py", [str(empty_plugin)])
        assert "plugin.json" in result.stdout


class TestPluginPyContract:
    def test_help_lists_commands(self):
        result = run_script("plugin.py", ["--help"])
        assert result.returncode == 0
        assert "validate" in result.stdout

    def test_validate_works(self, standard_plugin):
        assert run_script("plugin.py", ["validate", str(standard_plugin)]).returncode == 0

    def test_audit_works(self, standard_plugin):
        assert run_script("plugin.py", ["audit", str(standard_plugin)]).returncode == 0

    def test_smoke_works(self, standard_plugin):
        assert run_script("plugin.py", ["smoke", str(standard_plugin)]).returncode == 0

    def test_smart_defaults(self, standard_plugin):
        result = run_script("plugin.py", ["validate"], cwd=standard_plugin)
        combined = result.stdout + result.stderr
        assert "自动检测" in combined or "符合" in combined
