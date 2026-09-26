"""
第4层：集成测试（多脚本协同工作）
"""
import json
import pytest
from tests.conftest import run_script


class TestFullWorkflow:
    def test_create_validate_audit_smoke_docs(self, temp_dir):
        plugin_dir = temp_dir / "full-workflow"
        plugin_dir.mkdir()
        (plugin_dir / "skills" / "main-skill").mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "full-workflow", "version": "1.0.0",
            "description": "完整工作流测试", "author": {"name": "Test"}, "license": "MIT"
        }, indent=2), encoding="utf-8")
        (plugin_dir / "skills" / "main-skill" / "SKILL.md").write_text(
            "---\nname: main-skill\ndescription: test\n---\n# Test\n## 概述\n测试\n## 工作流程\n1. 测试\n## Gotchas\n### 坑1\n- **症状**：测试\n- **修正**：测试\n- **原因**：测试\n", encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Full Workflow\n", encoding="utf-8")

        assert run_script("validate_plugin.py", [str(plugin_dir)]).returncode == 0
        assert run_script("audit_plugin.py", [str(plugin_dir)]).returncode == 0
        assert run_script("smoke_test.py", [str(plugin_dir)]).returncode == 0
        assert run_script("generate_docs.py", [str(plugin_dir), "--force"]).returncode == 0


class TestErrorRecovery:
    def test_fix_name_mismatch_then_revalidate(self, temp_dir):
        plugin_dir = temp_dir / "my-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "skills" / "test-skill").mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "wrong-name", "version": "1.0.0", "description": "测试"
        }), encoding="utf-8")
        (plugin_dir / "skills" / "test-skill" / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: test\n---\n# Test\n", encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        assert run_script("validate_plugin.py", [str(plugin_dir)]).returncode != 0

        plugin_json = json.loads((plugin_dir / "plugin.json").read_text())
        plugin_json["name"] = "my-plugin"
        (plugin_dir / "plugin.json").write_text(json.dumps(plugin_json), encoding="utf-8")

        assert run_script("validate_plugin.py", [str(plugin_dir)]).returncode == 0


class TestMultiScriptCoordination:
    def test_validate_and_audit_consistent(self, standard_plugin):
        assert run_script("validate_plugin.py", [str(standard_plugin)]).returncode == 0
        assert run_script("audit_plugin.py", [str(standard_plugin)]).returncode == 0

    def test_smoke_checks_readme(self, standard_plugin):
        result = run_script("smoke_test.py", [str(standard_plugin)])
        assert "README" in result.stdout
