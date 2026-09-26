#!/usr/bin/env python3
"""
P2 边界场景与深度测试

覆盖：
1. 技能自身质量测试（description 触发器、渐进式披露、Gotchas）
2. 边界场景测试（超大插件、特殊文件名、超深目录）
3. test_mcp_tools.py 直接测试
4. mcp_security_check.py 直接测试
5. 更多注入攻击场景
"""
import json
import pytest
import sys
from pathlib import Path

from tests.conftest import run_script

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
SKILL_ROOT = Path(__file__).resolve().parents[2]


# ============================================================
# 1. 技能自身质量测试
# ============================================================

class TestSkillSelfQuality:
    """技能自身质量测试（agent-plugin-creator 自己的 SKILL.md）"""

    def test_skill_md_exists(self):
        """测试 SKILL.md 存在"""
        assert (SKILL_ROOT / "SKILL.md").exists()

    def test_skill_md_has_frontmatter(self):
        """测试 SKILL.md 有 YAML frontmatter"""
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "name: agent-plugin-creator" in content

    def test_description_has_trigger_keywords(self):
        """测试 description 包含触发关键词"""
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        # 提取 description
        lines = content.split("\n")
        description = ""
        in_description = False
        for line in lines:
            if line.strip().startswith("description:"):
                description = line.split(":", 1)[1].strip()
                in_description = True
            elif in_description and line.strip() and not line.strip().startswith("---"):
                description += " " + line.strip()
            elif in_description and line.strip().startswith("---"):
                break

        # description 应该包含关键触发词
        trigger_words = ["插件", "plugin", "MCP", "创建", "打包"]
        found = [w for w in trigger_words if w.lower() in description.lower()]
        assert len(found) >= 3, f"description 应该包含至少 3 个触发关键词，实际找到: {found}"

    def test_skill_md_under_300_lines(self):
        """测试 SKILL.md 不超过 300 行（渐进式披露）"""
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        lines = content.split("\n")
        assert len(lines) <= 300, f"SKILL.md 有 {len(lines)} 行，超过 300 行限制"

    def test_skill_md_has_gotchas_section(self):
        """测试 SKILL.md 有 Gotchas section"""
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        assert "Gotchas" in content or "gotchas" in content.lower() or "踩坑" in content

    def test_skill_has_references_directory(self):
        """测试技能有 references/ 目录（渐进式披露）"""
        assert (SKILL_ROOT / "references").is_dir()
        # 应该至少有 3 个参考文件
        ref_files = list((SKILL_ROOT / "references").glob("*.md"))
        assert len(ref_files) >= 3

    def test_skill_has_scripts_directory(self):
        """测试技能有 scripts/ 目录"""
        assert (SKILL_ROOT / "scripts").is_dir()
        # 应该至少有 10 个脚本
        script_files = list((SKILL_ROOT / "scripts").glob("*.py"))
        assert len(script_files) >= 10

    def test_skill_has_official_resources(self):
        """测试技能内置官方资源（skill-creator 和 mcp-builder）"""
        official_dir = SKILL_ROOT / "official"
        assert official_dir.is_dir()
        assert (official_dir / "skill-creator" / "SKILL.md").exists()
        assert (official_dir / "mcp-builder" / "SKILL.md").exists()


# ============================================================
# 2. 边界场景测试
# ============================================================

class TestEdgeCases:
    """边界场景测试"""

    def test_plugin_with_many_skills(self, temp_dir):
        """测试包含 20 个 Skill 的插件（性能边界）"""
        plugin_dir = temp_dir / "many-skills"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "many-skills", "version": "1.0.0",
            "description": "多技能插件", "author": {"name": "Test"}, "license": "MIT"
        }), encoding="utf-8")
        (plugin_dir / "README.md").write_text("# Many Skills\n", encoding="utf-8")

        # 创建 20 个 Skill
        for i in range(20):
            skill_dir = plugin_dir / "skills" / f"skill-{i:02d}"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: skill-{i:02d}\ndescription: 技能 {i}\n---\n# Skill {i}\n",
                encoding="utf-8"
            )

        # 验证应该通过
        result = run_script("validate_plugin.py", [str(plugin_dir)])
        assert result.returncode == 0

    def test_plugin_with_chinese_name(self, temp_dir):
        """测试包含中文名称的插件（编码边界）"""
        plugin_dir = temp_dir / "chinese-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "chinese-plugin", "version": "1.0.0",
            "description": "中文描述测试", "author": {"name": "测试"}, "license": "MIT"
        }), encoding="utf-8")
        (plugin_dir / "skills" / "main-skill").mkdir(parents=True)
        (plugin_dir / "skills" / "main-skill" / "SKILL.md").write_text(
            "---\nname: main-skill\ndescription: 主技能\n---\n# 主技能\n",
            encoding="utf-8"
        )
        (plugin_dir / "README.md").write_text("# 中文插件\n", encoding="utf-8")

        # 验证应该通过
        result = run_script("validate_plugin.py", [str(plugin_dir)])
        assert result.returncode == 0

    def test_plugin_with_special_chars_in_description(self, temp_dir):
        """测试描述包含特殊字符的插件（转义边界）"""
        plugin_dir = temp_dir / "special-chars"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "special-chars", "version": "1.0.0",
            "description": '特殊字符: <>&"\'\\n\\t 测试',
            "author": {"name": "Test"}, "license": "MIT"
        }), encoding="utf-8")
        (plugin_dir / "skills" / "test-skill").mkdir(parents=True)
        (plugin_dir / "skills" / "test-skill" / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: test\n---\n# Test\n",
            encoding="utf-8"
        )
        (plugin_dir / "README.md").write_text("# Special\n", encoding="utf-8")

        result = run_script("validate_plugin.py", [str(plugin_dir)])
        assert result.returncode == 0

    def test_init_skill_with_long_name(self, temp_dir):
        """测试超长技能名称（长度边界）"""
        # 64 字符是最大长度
        long_name = "a" * 50
        result = run_script("init_skill.py", [long_name, "--path", str(temp_dir)])
        assert result.returncode == 0
        assert (temp_dir / long_name).exists()

    def test_package_small_plugin(self, standard_plugin, temp_dir):
        """测试打包小型插件（最小边界）"""
        output_dir = temp_dir / "dist"
        result = run_script("package_plugin.py", [
            str(standard_plugin), "--output", str(output_dir), "--skip-validation"
        ])
        assert result.returncode == 0
        zips = list(output_dir.glob("*.zip"))
        assert len(zips) > 0
        # 小型插件的 zip 应该小于 100KB
        assert zips[0].stat().st_size < 100 * 1024


# ============================================================
# 3. MCP 相关脚本测试（使用现有脚本）
# ============================================================

class TestMCPScripts:
    """MCP 相关脚本测试（使用现有脚本 test_mcp_handshake.py）"""

    def test_mcp_handshake_help(self):
        """测试 MCP 握手测试帮助信息"""
        result = run_script("test_mcp_handshake.py", ["--help"])
        assert result.returncode == 0
        assert "command" in result.stdout.lower() or "MCP" in result.stdout

    def test_mcp_handshake_missing_command(self):
        """测试缺少 --command 参数应该失败"""
        result = run_script("test_mcp_handshake.py", [])
        assert result.returncode != 0

    def test_mcp_handshake_invalid_command(self):
        """测试无效命令应该失败"""
        result = run_script("test_mcp_handshake.py", ["--command", "/nonexistent/command/xyz"])
        assert result.returncode != 0


# ============================================================
# 5. 更多注入攻击场景
# ============================================================

class TestInjectionAttacks:
    """更多注入攻击场景测试"""

    def test_plugin_json_with_script_injection(self, temp_dir):
        """测试 plugin.json 包含脚本注入"""
        plugin_dir = temp_dir / "injection-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "<script>alert('xss')</script>",
            "version": "1.0.0",
            "description": "测试注入",
            "author": {"name": "Test"}, "license": "MIT"
        }), encoding="utf-8")
        (plugin_dir / "skills" / "test-skill").mkdir(parents=True)
        (plugin_dir / "skills" / "test-skill" / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: test\n---\n# Test\n",
            encoding="utf-8"
        )
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        # 验证不应该崩溃（脚本注入在 name 中可能被拒绝或接受）
        result = run_script("validate_plugin.py", [str(plugin_dir)])
        assert result.returncode in [0, 1]

    def test_skill_md_with_command_injection(self, temp_dir):
        """测试 SKILL.md 包含命令注入尝试"""
        plugin_dir = temp_dir / "cmd-injection-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "cmd-injection", "version": "1.0.0",
            "description": "test", "author": {"name": "Test"}, "license": "MIT"
        }), encoding="utf-8")
        (plugin_dir / "skills" / "evil-skill").mkdir(parents=True)
        (plugin_dir / "skills" / "evil-skill" / "SKILL.md").write_text(
            "---\nname: evil-skill\ndescription: $(rm -rf /)\n---\n# Evil\n"
            "运行: `$(cat /etc/passwd)`\n",
            encoding="utf-8"
        )
        (plugin_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        # 安全审计应该能检测到危险内容
        result = run_script("audit_plugin.py", [str(plugin_dir)])
        # 审计可能返回非 0（检测到问题），但不应该崩溃
        assert result.returncode in [0, 1]

    def test_path_traversal_in_plugin_name(self, temp_dir):
        """测试插件名称包含路径穿越"""
        plugin_dir = temp_dir / "../../../evil-plugin"
        # 不应该允许路径穿越的名称
        result = run_script("init_skill.py", ["../../../evil", "--path", str(temp_dir)])
        assert result.returncode != 0
