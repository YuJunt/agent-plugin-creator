"""
第6层：端到端测试（E2E）- 模拟真实用户完整流程
"""
import json
import pytest
from tests.conftest import run_script


class TestE2EUserCreatesPlugin:
    def test_full_user_journey(self, temp_dir):
        """完整用户旅程：创建→验证失败→修复→验证通过→审计→冒烟→文档"""
        plugin_dir = temp_dir / "user-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "skills" / "user-skill").mkdir(parents=True)

        # Step 1: 创建 plugin.json（故意写错 name）
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "wrong-name", "version": "1.0.0", "description": "用户测试插件"
        }), encoding="utf-8")

        # Step 2: 创建 SKILL.md
        (plugin_dir / "skills" / "user-skill" / "SKILL.md").write_text(
            "---\nname: user-skill\ndescription: 用户技能\n---\n# User Skill\n## 概述\n测试\n## 工作流程\n1. 测试\n## Gotchas\n### 坑1\n- **症状**：测试\n- **修正**：测试\n- **原因**：测试\n", encoding="utf-8")

        # Step 2b: 创建 README.md
        (plugin_dir / "README.md").write_text("# User Plugin\n", encoding="utf-8")

        # Step 3: 第一次验证（应该失败）
        result = run_script("plugin.py", ["validate", str(plugin_dir)])
        assert result.returncode != 0
        assert "不一致" in result.stdout

        # Step 4: 查看修复建议
        assert "修复" in result.stdout or "建议" in result.stdout

        # Step 5: 修复 name
        plugin_json = json.loads((plugin_dir / "plugin.json").read_text())
        plugin_json["name"] = "user-plugin"
        (plugin_dir / "plugin.json").write_text(json.dumps(plugin_json, indent=2), encoding="utf-8")

        # Step 6: 第二次验证（应该通过）
        assert run_script("plugin.py", ["validate", str(plugin_dir)]).returncode == 0

        # Step 7: 安全审计
        assert run_script("plugin.py", ["audit", str(plugin_dir)]).returncode == 0

        # Step 8: 冒烟测试
        assert run_script("plugin.py", ["smoke", str(plugin_dir)]).returncode == 0

        # Step 9: 生成文档
        assert run_script("plugin.py", ["docs", str(plugin_dir), "--force"]).returncode == 0

    def test_user_uses_smart_defaults(self, temp_dir):
        """用户使用智能默认值（在插件目录内运行）"""
        plugin_dir = temp_dir / "smart-default"
        plugin_dir.mkdir()
        (plugin_dir / "skills" / "main-skill").mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "smart-default", "version": "1.0.0", "description": "测试"
        }, indent=2), encoding="utf-8")
        (plugin_dir / "skills" / "main-skill" / "SKILL.md").write_text(
            "---\nname: main-skill\ndescription: test\n---\n# Test\n", encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        result = run_script("plugin.py", ["validate"], cwd=plugin_dir)
        combined = result.stdout + result.stderr
        assert "自动检测" in combined or "符合" in combined


class TestE2EUserCreatesMCPPlugin:
    def test_user_creates_python_mcp(self, temp_dir):
        """用户创建 Python MCP 插件完整流程"""
        plugin_dir = temp_dir / "python-mcp-e2e"
        plugin_dir.mkdir()
        (plugin_dir / "skills" / "mcp-skill").mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "python-mcp-e2e", "version": "1.0.0", "description": "MCP 测试"
        }, indent=2), encoding="utf-8")
        (plugin_dir / "skills" / "mcp-skill" / "SKILL.md").write_text(
            "---\nname: mcp-skill\ndescription: test\n---\n# Test\n", encoding="utf-8")
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {"weather-server": {"type": "stdio", "command": "python3", "args": ["./servers/weather-server/server.py"]}}
        }, indent=2), encoding="utf-8")
        server_dir = plugin_dir / "servers" / "weather-server"
        server_dir.mkdir(parents=True)
        (server_dir / "server.py").write_text("#!/usr/bin/env python3\n\"\"\"Weather MCP Server\"\"\"\n", encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Weather MCP\n", encoding="utf-8")

        assert run_script("validate_plugin.py", [str(plugin_dir)]).returncode == 0
        assert run_script("audit_plugin.py", [str(plugin_dir)]).returncode == 0
        assert run_script("smoke_test.py", [str(plugin_dir)]).returncode == 0
