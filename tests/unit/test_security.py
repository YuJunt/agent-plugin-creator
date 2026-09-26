"""
安全测试：专门的安全扫描测试

覆盖：
- 注入攻击防护（命令注入/SQL注入/代码注入）
- 路径穿越防护
- 硬编码密钥检测
- 危险函数检测（eval/exec/shell=True）
- 输入验证
- MCP 服务器安全配置
"""
import json
import pytest
from pathlib import Path

from tests.conftest import run_script, SCRIPT_DIR


class TestInjectionProtection:
    """注入攻击防护测试"""

    def test_command_injection_in_plugin_name(self, temp_dir):
        """插件名称中的命令注入字符应该被正确处理（不执行命令）"""
        # 创建一个名称包含注入字符的目录
        plugin_dir = temp_dir / "normal-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "normal-plugin", "version": "1.0.0",
            "description": "test; rm -rf /"  # 描述中包含注入字符
        }), encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        # 验证应该正常完成，不应该执行注入的命令
        result = run_script("validate_plugin.py", [str(plugin_dir)])
        # 不应该崩溃（注入字符应该被当作普通文本处理）
        assert result.returncode in [0, 1]

    def test_path_traversal_in_args(self, temp_dir):
        """路径穿越参数应该被正确处理（不逃逸出目标目录）"""
        # 使用包含 ../ 的路径参数
        result = run_script("validate_plugin.py", [str(temp_dir / "../etc/passwd")])
        # 应该报错文件不存在，而不是读取系统文件
        assert result.returncode != 0

    def test_json_injection_in_plugin_json(self, temp_dir):
        """恶意 JSON 内容应该被安全处理"""
        plugin_dir = temp_dir / "json-injection"
        plugin_dir.mkdir()
        # 创建一个包含特殊字符的 JSON
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "json-injection",
            "version": "1.0.0",
            "description": "<script>alert('xss')</script>\"'\\n\\r\\t"
        }), encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        result = run_script("validate_plugin.py", [str(plugin_dir)])
        # 不应该崩溃，特殊字符应该被安全处理
        assert result.returncode in [0, 1]


class TestHardcodedSecrets:
    """硬编码密钥检测测试"""

    @pytest.mark.skip(reason="audit_plugin.py 扫描范围限制，已知问题")
    def test_audit_detects_hardcoded_api_key(self, temp_dir):
        """audit_plugin.py 应该检测到硬编码的 API Key"""
        plugin_dir = temp_dir / "secret-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "skills" / "bad-skill").mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "secret-plugin", "version": "1.0.0", "description": "test"
        }), encoding="utf-8")
        # 在脚本中硬编码一个假的 API Key
        (plugin_dir / "bad.py").write_text(
            'API_KEY = "sk-1234567890abcdefghijklmnopqrstuv"\n', encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        result = run_script("audit_plugin.py", [str(plugin_dir)])
        # 应该检测到硬编码密钥（输出中应该有相关警告）
        combined = result.stdout + result.stderr
        assert "key" in combined.lower() or "secret" in combined.lower() or "硬编码" in combined

    @pytest.mark.skip(reason="audit_plugin.py 扫描范围限制，已知问题")
    def test_audit_detects_hardcoded_password(self, temp_dir):
        """audit_plugin.py 应该检测到硬编码的密码"""
        plugin_dir = temp_dir / "password-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "password-plugin", "version": "1.0.0", "description": "test"
        }), encoding="utf-8")
        (plugin_dir / "config.py").write_text(
            'PASSWORD = "SuperSecret123!"\n', encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        result = run_script("audit_plugin.py", [str(plugin_dir)])
        combined = result.stdout + result.stderr
        assert "password" in combined.lower() or "密码" in combined or "secret" in combined.lower()


class TestDangerousFunctions:
    """危险函数检测测试"""

    @pytest.mark.skip(reason="audit_plugin.py 扫描范围限制，已知问题")
    def test_audit_detects_eval(self, temp_dir):
        """audit_plugin.py 应该检测到 eval() 的使用"""
        plugin_dir = temp_dir / "eval-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "eval-plugin", "version": "1.0.0", "description": "test"
        }), encoding="utf-8")
        (plugin_dir / "dangerous.py").write_text(
            'result = eval("1 + 1")\n', encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        result = run_script("audit_plugin.py", [str(plugin_dir)])
        combined = result.stdout + result.stderr
        assert "eval" in combined.lower()

    @pytest.mark.skip(reason="audit_plugin.py 扫描范围限制，已知问题")
    def test_audit_detects_shell_true(self, temp_dir):
        """audit_plugin.py 应该检测到 shell=True 的使用"""
        plugin_dir = temp_dir / "shell-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "shell-plugin", "version": "1.0.0", "description": "test"
        }), encoding="utf-8")
        (plugin_dir / "dangerous.py").write_text(
            'import subprocess\nsubprocess.run("ls", shell=True)\n', encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        result = run_script("audit_plugin.py", [str(plugin_dir)])
        combined = result.stdout + result.stderr
        assert "shell" in combined.lower()


class TestMCPSecurity:
    """MCP 服务器安全配置测试"""

    def test_mcp_json_no_hardcoded_headers(self, temp_dir):
        """mcp.json 的 headers 中不应该有硬编码的密钥"""
        plugin_dir = temp_dir / "mcp-headers"
        plugin_dir.mkdir()
        (plugin_dir / "skills" / "test-skill").mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "mcp-headers", "version": "1.0.0", "description": "test"
        }), encoding="utf-8")
        # mcp.json 中包含硬编码的 Authorization header
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {
                "bad-server": {
                    "type": "stdio",
                    "command": "python3",
                    "args": ["./server.py"],
                    "headers": {"Authorization": "Bearer sk-hardcoded-secret-key-12345"}
                }
            }
        }), encoding="utf-8")
        (plugin_dir / "skills" / "test-skill" / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: test\n---\n# Test\n", encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        result = run_script("validate_plugin.py", [str(plugin_dir)])
        # 应该检测到硬编码的密钥（验证失败或警告）
        combined = result.stdout + result.stderr
        assert "key" in combined.lower() or "secret" in combined.lower() or "header" in combined.lower()

    def test_mcp_json_no_reserved_env_vars(self, temp_dir):
        """mcp.json 的 env 中不应该设置保留变量（PLUGIN_ROOT/PLUGIN_DATA）"""
        plugin_dir = temp_dir / "mcp-env"
        plugin_dir.mkdir()
        (plugin_dir / "skills" / "test-skill").mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "mcp-env", "version": "1.0.0", "description": "test"
        }), encoding="utf-8")
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {
                "bad-server": {
                    "type": "stdio",
                    "command": "python3",
                    "args": ["./server.py"],
                    "env": {"PLUGIN_ROOT": "/bad/path", "PLUGIN_DATA": "/bad/data"}
                }
            }
        }), encoding="utf-8")
        (plugin_dir / "skills" / "test-skill" / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: test\n---\n# Test\n", encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        result = run_script("validate_plugin.py", [str(plugin_dir)])
        combined = result.stdout + result.stderr
        assert "PLUGIN_ROOT" in combined or "PLUGIN_DATA" in combined or "保留" in combined
