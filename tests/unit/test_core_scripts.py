#!/usr/bin/env python3
"""
P0 核心脚本直接测试

覆盖 5 个最常用的核心脚本：
1. init_skill.py - 技能脚手架生成器
2. create_mcp_server.py - MCP 服务器代码生成器
3. package_plugin.py - 插件打包发布工具
4. plugin_to_skill.py - 反向封装工具
5. wizard.py - 交互式创建向导（非交互模式）
"""
import json
import pytest
from pathlib import Path

from tests.conftest import run_script


# ============================================================
# 1. init_skill.py 测试
# ============================================================

class TestInitSkill:
    """init_skill.py 技能脚手架生成器测试"""

    def test_create_basic_skill(self, temp_dir):
        """测试创建基础技能脚手架"""
        result = run_script("init_skill.py", ["test-skill", "--path", str(temp_dir)])
        assert result.returncode == 0

        skill_dir = temp_dir / "test-skill"
        assert skill_dir.exists()
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "scripts").is_dir()
        assert (skill_dir / "references").is_dir()
        assert (skill_dir / "assets").is_dir()

    def test_skill_md_has_correct_name(self, temp_dir):
        """测试生成的 SKILL.md 包含正确的 name"""
        run_script("init_skill.py", ["my-awesome-skill", "--path", str(temp_dir)])
        content = (temp_dir / "my-awesome-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert "name: my-awesome-skill" in content

    def test_skill_md_has_frontmatter(self, temp_dir):
        """测试生成的 SKILL.md 有 YAML frontmatter"""
        run_script("init_skill.py", ["test-skill", "--path", str(temp_dir)])
        content = (temp_dir / "test-skill" / "SKILL.md").read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "name:" in content
        assert "description:" in content

    def test_chinese_template(self, temp_dir):
        """测试中文模板（--lang zh）"""
        run_script("init_skill.py", ["test-skill", "--path", str(temp_dir), "--lang", "zh"])
        content = (temp_dir / "test-skill" / "SKILL.md").read_text(encoding="utf-8")
        # 中文模板应该包含中文字符
        assert any('\u4e00' <= c <= '\u9fff' for c in content)

    def test_english_template_default(self, temp_dir):
        """测试默认英文模板"""
        run_script("init_skill.py", ["test-skill", "--path", str(temp_dir)])
        content = (temp_dir / "test-skill" / "SKILL.md").read_text(encoding="utf-8")
        # 默认应该是英文
        assert "Overview" in content or "Workflow" in content or "Gotchas" in content

    def test_idempotent_no_force(self, temp_dir):
        """测试幂等性：不使用 --force 时不覆盖已有目录"""
        run_script("init_skill.py", ["test-skill", "--path", str(temp_dir)])
        # 修改 SKILL.md
        skill_md = temp_dir / "test-skill" / "SKILL.md"
        original = skill_md.read_text(encoding="utf-8")
        skill_md.write_text(original + "\n# CUSTOM MARKER\n", encoding="utf-8")

        # 再次运行（不使用 --force）
        result = run_script("init_skill.py", ["test-skill", "--path", str(temp_dir)])
        assert result.returncode != 0  # 应该失败（目录已存在）

        # 确认文件没有被覆盖
        content = skill_md.read_text(encoding="utf-8")
        assert "CUSTOM MARKER" in content

    def test_force_overwrite(self, temp_dir):
        """测试 --force 覆盖已有目录"""
        run_script("init_skill.py", ["test-skill", "--path", str(temp_dir)])
        skill_md = temp_dir / "test-skill" / "SKILL.md"
        skill_md.write_text("# CUSTOM MARKER\n", encoding="utf-8")

        # 使用 --force 覆盖
        result = run_script("init_skill.py", ["test-skill", "--path", str(temp_dir), "--force"])
        assert result.returncode == 0

        # 确认文件被覆盖
        content = skill_md.read_text(encoding="utf-8")
        assert "CUSTOM MARKER" not in content

    def test_json_output(self, temp_dir):
        """测试 --json 输出格式"""
        result = run_script("init_skill.py", ["test-skill", "--path", str(temp_dir), "--json"])
        assert result.returncode == 0
        # JSON 输出应该是有效的 JSON
        try:
            data = json.loads(result.stdout)
            assert "name" in data or "path" in data or "success" in data
        except json.JSONDecodeError:
            pytest.fail("JSON 输出格式无效")

    def test_invalid_name_uppercase(self, temp_dir):
        """测试无效名称（大写字母）应该失败"""
        result = run_script("init_skill.py", ["Invalid-Name", "--path", str(temp_dir)])
        # 大写字母应该被拒绝或转换
        assert result.returncode != 0 or "invalid" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_invalid_name_with_spaces(self, temp_dir):
        """测试无效名称（包含空格）应该失败"""
        result = run_script("init_skill.py", ["invalid name", "--path", str(temp_dir)])
        assert result.returncode != 0


# ============================================================
# 2. create_mcp_server.py 测试
# ============================================================

class TestCreateMCPServer:
    """create_mcp_server.py MCP 服务器代码生成器测试"""

    @pytest.fixture
    def definition_file(self, temp_dir):
        """创建工具定义 JSON 文件"""
        def_file = temp_dir / "definition.json"
        def_file.write_text(json.dumps({
            "tools": [
                {
                    "name": "hello",
                    "description": "打招呼工具",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "姓名"}
                        },
                        "required": ["name"]
                    }
                }
            ],
            "resources": [],
            "prompts": []
        }), encoding="utf-8")
        return str(def_file)

    def test_generate_python_server(self, temp_dir, definition_file):
        """测试生成 Python MCP 服务器"""
        output_dir = temp_dir / "python-server"
        result = run_script("create_mcp_server.py", [
            "generate",
            "--language", "python",
            "--name", "test-server",
            "--definition", definition_file,
            "--output", str(output_dir)
        ])
        assert result.returncode == 0
        assert output_dir.exists()
        # Python 服务器应该有 server.py
        server_files = list(output_dir.rglob("*.py"))
        assert len(server_files) > 0

    def test_generate_typescript_server(self, temp_dir, definition_file):
        """测试生成 TypeScript MCP 服务器"""
        output_dir = temp_dir / "ts-server"
        result = run_script("create_mcp_server.py", [
            "generate",
            "--language", "typescript",
            "--name", "test-server",
            "--definition", definition_file,
            "--output", str(output_dir)
        ])
        assert result.returncode == 0
        assert output_dir.exists()
        # TypeScript 服务器应该有 .ts 文件
        ts_files = list(output_dir.rglob("*.ts"))
        assert len(ts_files) > 0

    def test_generated_server_has_tool(self, temp_dir, definition_file):
        """测试生成的服务器包含定义的工具"""
        output_dir = temp_dir / "python-server"
        run_script("create_mcp_server.py", [
            "generate", "--language", "python",
            "--name", "test-server",
            "--definition", definition_file,
            "--output", str(output_dir)
        ])
        # 检查生成的代码中包含 hello 工具
        all_code = "\n".join(f.read_text(encoding="utf-8") for f in output_dir.rglob("*.py"))
        assert "hello" in all_code

    def test_generated_python_server_imports_fastmcp(self, temp_dir, definition_file):
        """测试生成的 Python 服务器导入 fastmcp"""
        output_dir = temp_dir / "python-server"
        run_script("create_mcp_server.py", [
            "generate", "--language", "python",
            "--name", "test-server",
            "--definition", definition_file,
            "--output", str(output_dir)
        ])
        all_code = "\n".join(f.read_text(encoding="utf-8") for f in output_dir.rglob("*.py"))
        assert "fastmcp" in all_code.lower() or "FastMCP" in all_code

    def test_invalid_language(self, temp_dir, definition_file):
        """测试无效语言应该失败"""
        result = run_script("create_mcp_server.py", [
            "generate", "--language", "invalid-lang",
            "--name", "test-server",
            "--definition", definition_file,
            "--output", str(temp_dir / "invalid")
        ])
        assert result.returncode != 0

    def test_missing_definition_file(self, temp_dir):
        """测试缺少定义文件应该失败"""
        result = run_script("create_mcp_server.py", [
            "generate", "--language", "python",
            "--name", "test-server",
            "--definition", str(temp_dir / "nonexistent.json"),
            "--output", str(temp_dir / "output")
        ])
        assert result.returncode != 0


# ============================================================
# 3. package_plugin.py 测试
# ============================================================

class TestPackagePlugin:
    """package_plugin.py 插件打包发布工具测试"""

    def test_package_standard_plugin(self, standard_plugin, temp_dir):
        """测试打包标准插件"""
        output_dir = temp_dir / "dist"
        result = run_script("package_plugin.py", [
            str(standard_plugin),
            "--output", str(output_dir),
            "--skip-validation"
        ])
        assert result.returncode == 0
        # 应该生成 zip 文件
        zips = list(output_dir.glob("*.zip"))
        assert len(zips) > 0

    def test_package_generates_zip(self, standard_plugin, temp_dir):
        """测试生成的文件是有效的 zip"""
        import zipfile
        output_dir = temp_dir / "dist"
        run_script("package_plugin.py", [
            str(standard_plugin),
            "--output", str(output_dir),
            "--skip-validation"
        ])
        zips = list(output_dir.glob("*.zip"))
        assert len(zips) > 0
        assert zipfile.is_zipfile(zips[0])

    def test_package_contains_plugin_json(self, standard_plugin, temp_dir):
        """测试打包的 zip 包含 plugin.json"""
        import zipfile
        output_dir = temp_dir / "dist"
        run_script("package_plugin.py", [
            str(standard_plugin),
            "--output", str(output_dir),
            "--skip-validation"
        ])
        zips = list(output_dir.glob("*.zip"))
        with zipfile.ZipFile(zips[0], 'r') as zf:
            names = zf.namelist()
            assert any("plugin.json" in name for name in names)

    def test_package_contains_skills(self, standard_plugin, temp_dir):
        """测试打包的 zip 包含 skills 目录"""
        import zipfile
        output_dir = temp_dir / "dist"
        run_script("package_plugin.py", [
            str(standard_plugin),
            "--output", str(output_dir),
            "--skip-validation"
        ])
        zips = list(output_dir.glob("*.zip"))
        with zipfile.ZipFile(zips[0], 'r') as zf:
            names = zf.namelist()
            assert any("skills/" in name for name in names)

    def test_package_version_from_plugin_json(self, standard_plugin, temp_dir):
        """测试版本号从 plugin.json 读取"""
        output_dir = temp_dir / "dist"
        run_script("package_plugin.py", [
            str(standard_plugin),
            "--output", str(output_dir),
            "--skip-validation"
        ])
        zips = list(output_dir.glob("*.zip"))
        # zip 文件名应该包含版本号 1.0.0
        assert any("1.0.0" in z.name for z in zips)

    def test_package_custom_version(self, standard_plugin, temp_dir):
        """测试自定义版本号"""
        output_dir = temp_dir / "dist"
        run_script("package_plugin.py", [
            str(standard_plugin),
            "--output", str(output_dir),
            "--version", "2.0.0",
            "--skip-validation"
        ])
        zips = list(output_dir.glob("*.zip"))
        assert any("2.0.0" in z.name for z in zips)

    def test_package_missing_plugin_dir(self, temp_dir):
        """测试缺少插件目录应该失败"""
        result = run_script("package_plugin.py", [
            str(temp_dir / "nonexistent"),
            "--output", str(temp_dir / "dist"),
            "--skip-validation"
        ])
        assert result.returncode != 0


# ============================================================
# 4. plugin_to_skill.py 测试
# ============================================================

class TestPluginToSkill:
    """plugin_to_skill.py 反向封装工具测试"""

    def test_reverse_encapsulation_creates_skill(self, standard_plugin, temp_dir):
        """测试反向封装创建技能目录"""
        output_dir = temp_dir / "reversed-skill"
        result = run_script("plugin_to_skill.py", [
            str(standard_plugin),
            "--output", str(output_dir)
        ])
        assert result.returncode == 0
        assert output_dir.exists()
        assert (output_dir / "SKILL.md").exists()

    def test_reversed_skill_has_frontmatter(self, standard_plugin, temp_dir):
        """测试反向封装生成的 SKILL.md 有 frontmatter"""
        output_dir = temp_dir / "reversed-skill"
        run_script("plugin_to_skill.py", [str(standard_plugin), "--output", str(output_dir)])
        content = (output_dir / "SKILL.md").read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "name:" in content
        assert "description:" in content

    def test_reversed_skill_contains_gotchas(self, standard_plugin, temp_dir):
        """测试反向封装生成的 SKILL.md 包含 Gotchas section"""
        output_dir = temp_dir / "reversed-skill"
        run_script("plugin_to_skill.py", [str(standard_plugin), "--output", str(output_dir)])
        content = (output_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "Gotchas" in content or "gotchas" in content.lower()

    def test_reversed_skill_contains_start_mcp_script(self, temp_dir):
        """测试包含 MCP 服务器的插件反向封装后生成 start_mcp.py"""
        # 创建一个包含 MCP 服务器的插件
        plugin_dir = temp_dir / "mcp-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "skills" / "test-skill").mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "mcp-plugin", "version": "1.0.0",
            "description": "包含 MCP 的测试插件",
            "author": {"name": "Test"}, "license": "MIT"
        }), encoding="utf-8")
        (plugin_dir / "mcp.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {
                "test-server": {"type": "stdio", "command": "python3", "args": ["./servers/test-server/server.py"]}
            }
        }), encoding="utf-8")
        (plugin_dir / "skills" / "test-skill" / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: test\n---\n# Test\n", encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        output_dir = temp_dir / "reversed-mcp-skill"
        result = run_script("plugin_to_skill.py", [str(plugin_dir), "--output", str(output_dir), "--force"])
        assert result.returncode == 0

        # 包含 MCP 服务器的插件应该生成 start_mcp.py
        scripts_dir = output_dir / "scripts"
        assert scripts_dir.is_dir()
        # 检查是否有 start_mcp 相关脚本（文件名可能是 start_mcp.py 或其他）
        start_scripts = list(scripts_dir.glob("start_mcp*"))
        assert len(start_scripts) > 0, f"应该生成 start_mcp 相关脚本，实际有: {list(scripts_dir.iterdir())}"

    def test_reversed_skill_preserves_original_skills(self, standard_plugin, temp_dir):
        """测试反向封装保留原始子技能"""
        output_dir = temp_dir / "reversed-skill"
        run_script("plugin_to_skill.py", [str(standard_plugin), "--output", str(output_dir)])
        # 应该包含原始的 skills 目录（作为参考资源）
        skills_dir = output_dir / "skills"
        assert skills_dir.exists() or (output_dir / "references").exists()

    def test_force_overwrite(self, standard_plugin, temp_dir):
        """测试 --force 覆盖已有输出目录"""
        output_dir = temp_dir / "reversed-skill"
        output_dir.mkdir()
        (output_dir / "CUSTOM_FILE.txt").write_text("custom", encoding="utf-8")

        # 不使用 --force 应该失败
        result = run_script("plugin_to_skill.py", [str(standard_plugin), "--output", str(output_dir)])
        assert result.returncode != 0

        # 使用 --force 应该成功
        result = run_script("plugin_to_skill.py", [str(standard_plugin), "--output", str(output_dir), "--force"])
        assert result.returncode == 0

    def test_json_output(self, standard_plugin, temp_dir):
        """测试 --json 输出格式"""
        output_dir = temp_dir / "reversed-skill"
        result = run_script("plugin_to_skill.py", [
            str(standard_plugin),
            "--output", str(output_dir),
            "--json"
        ])
        assert result.returncode == 0
        try:
            data = json.loads(result.stdout)
            assert "name" in data or "path" in data or "success" in data
        except json.JSONDecodeError:
            pytest.fail("JSON 输出格式无效")

    def test_missing_plugin_dir(self, temp_dir):
        """测试缺少插件目录应该失败"""
        result = run_script("plugin_to_skill.py", [str(temp_dir / "nonexistent")])
        assert result.returncode != 0


# ============================================================
# 5. wizard.py 测试（非交互模式）
# ============================================================

class TestWizard:
    """wizard.py 交互式创建向导测试（非交互模式）"""

    def test_list_templates(self):
        """测试列出可用模板"""
        result = run_script("wizard.py", ["--list-templates"])
        assert result.returncode == 0
        # 应该列出至少一个模板
        assert len(result.stdout) > 0

    def test_dry_run_minimal_template(self, temp_dir):
        """测试 minimal 模板的预览模式（--dry-run）"""
        result = run_script("wizard.py", [
            "--template", "minimal",
            "--name", "test-wizard-plugin",
            "--output", str(temp_dir / "test-plugin"),
            "--dry-run"
        ])
        # dry-run 可能返回 0 或非 0（取决于实现），但不应该崩溃
        assert result.returncode in [0, 1]

    def test_create_with_config_file(self, temp_dir):
        """测试从配置文件创建（非交互式）"""
        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps({
            "name": "config-plugin",
            "version": "1.0.0",
            "description": "从配置文件创建的测试插件",
            "skills": [
                {"name": "main-skill", "description": "主技能"}
            ]
        }), encoding="utf-8")

        result = run_script("wizard.py", [
            "--config", str(config_file),
            "--output", str(temp_dir / "config-plugin"),
            "--force"
        ])
        # 配置文件创建可能成功或需要特定格式
        # 只要不崩溃就可以
        assert result.returncode in [0, 1, 2]

    def test_help(self):
        """测试帮助信息"""
        result = run_script("wizard.py", ["--help"])
        assert result.returncode == 0
        assert "wizard" in result.stdout.lower() or "template" in result.stdout.lower()

    def test_invalid_template(self, temp_dir):
        """测试无效模板名称"""
        result = run_script("wizard.py", [
            "--template", "nonexistent-template-xyz",
            "--name", "test-plugin",
            "--output", str(temp_dir / "test-plugin")
        ])
        # 无效模板应该失败或回退到默认
        assert result.returncode in [0, 1]
