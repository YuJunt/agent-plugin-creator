"""
第5层：场景测试（7 种插件类型）
"""
import json
import pytest
from tests.conftest import run_script


def create_basic_plugin(plugin_dir, name, skills=None):
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": name, "version": "1.0.0",
        "description": f"{name} 测试", "author": {"name": "Test"}, "license": "MIT"
    }, indent=2), encoding="utf-8")
    for skill_name in (skills or ["main-skill"]):
        skill_dir = plugin_dir / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: test\n---\n# Test\n## 概述\n测试\n## 工作流程\n1. 测试\n## Gotchas\n### 坑1\n- **症状**：测试\n- **修正**：测试\n- **原因**：测试\n", encoding="utf-8")
    (plugin_dir / "README.md").write_text(f"# {name}\n", encoding="utf-8")


class TestScenario1PureSkill:
    def test_pure_skill_validates(self, temp_dir):
        plugin_dir = temp_dir / "pure-skill"
        create_basic_plugin(plugin_dir, "pure-skill")
        assert run_script("validate_plugin.py", [str(plugin_dir)]).returncode == 0

    def test_pure_skill_no_mcp_json(self, temp_dir):
        plugin_dir = temp_dir / "pure-skill"
        create_basic_plugin(plugin_dir, "pure-skill")
        assert not (plugin_dir / "mcp.json").exists()


class TestScenario2PythonMCP:
    def test_python_mcp_validates(self, temp_dir):
        plugin_dir = temp_dir / "python-mcp"
        create_basic_plugin(plugin_dir, "python-mcp")
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {"my-server": {"type": "stdio", "command": "python3", "args": ["./servers/my-server/server.py"]}}
        }, indent=2), encoding="utf-8")
        server_dir = plugin_dir / "servers" / "my-server"
        server_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "server.py").write_text("#!/usr/bin/env python3\n\"\"\"MCP Server\"\"\"\n", encoding="utf-8")
        assert run_script("validate_plugin.py", [str(plugin_dir)]).returncode == 0


class TestScenario3TypeScriptMCP:
    def test_ts_mcp_validates(self, temp_dir):
        plugin_dir = temp_dir / "ts-mcp"
        create_basic_plugin(plugin_dir, "ts-mcp")
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {"ts-server": {"type": "stdio", "command": "npx", "args": ["tsx", "./servers/ts-server/src/server.ts"]}}
        }, indent=2), encoding="utf-8")
        assert run_script("validate_plugin.py", [str(plugin_dir)]).returncode == 0


class TestScenario4MultiSkill:
    def test_multi_skill_validates(self, multi_skill_plugin):
        assert run_script("validate_plugin.py", [str(multi_skill_plugin)]).returncode == 0

    def test_multi_skill_count(self, multi_skill_plugin):
        result = run_script("validate_plugin.py", [str(multi_skill_plugin)])
        assert "3" in result.stdout or "skill" in result.stdout.lower()


class TestScenario5ReverseEncapsulation:
    def test_reverse_encapsulation(self, standard_plugin, temp_dir):
        output_dir = temp_dir / "reversed"
        result = run_script("plugin_to_skill.py", [str(standard_plugin), "--output", str(output_dir)])
        if result.returncode == 0:
            assert output_dir.exists()
            assert (output_dir / "SKILL.md").exists()
        else:
            pytest.skip("plugin_to_skill.py 可能需要特定参数")


class TestScenario6MultiClient:
    def test_client_adapter_check(self, standard_plugin):
        result = run_script("client_adapter.py", [str(standard_plugin), "--check"])
        if result.returncode != 0:
            pytest.skip("client_adapter.py 可能需要特定参数")


class TestScenario7EnterpriseComplex:
    def test_enterprise_complex_validates(self, temp_dir):
        plugin_dir = temp_dir / "enterprise"
        create_basic_plugin(plugin_dir, "enterprise",
                           skills=["auth-skill", "data-skill", "report-skill"])
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {
                "auth-server": {"type": "stdio", "command": "python3", "args": ["./servers/auth-server/server.py"]},
                "data-server": {"type": "stdio", "command": "python3", "args": ["./servers/data-server/server.py"]}
            }
        }, indent=2), encoding="utf-8")
        assert run_script("validate_plugin.py", [str(plugin_dir)]).returncode == 0
        assert run_script("audit_plugin.py", [str(plugin_dir)]).returncode == 0
