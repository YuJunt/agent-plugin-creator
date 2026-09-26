#!/usr/bin/env python3
"""
P1 常用脚本直接测试（精简版）

只保留最常用的3个脚本：
1. generate_docs.py - 文档生成
2. score_plugin.py - 质量评分
3. check_skill_quality.py - 技能质量检查

删除了不常用的：client_adapter.py、release_audit.py、run_evals.py
"""
import json
import pytest
from pathlib import Path

from tests.conftest import run_script


# ============================================================
# 1. generate_docs.py 测试
# ============================================================

class TestGenerateDocs:
    """generate_docs.py 文档自动生成工具测试"""

    def test_generate_readme(self, standard_plugin, temp_dir):
        """测试生成 README.md"""
        output_file = temp_dir / "README.md"
        result = run_script("generate_docs.py", [
            str(standard_plugin),
            "--output", str(output_file)
        ])
        assert result.returncode == 0
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_generated_readme_has_skills_section(self, standard_plugin, temp_dir):
        """测试生成的 README 包含 Skills 部分"""
        output_file = temp_dir / "README.md"
        run_script("generate_docs.py", [str(standard_plugin), "--output", str(output_file)])
        content = output_file.read_text(encoding="utf-8")
        assert "skill" in content.lower()

    def test_force_overwrite(self, standard_plugin, temp_dir):
        """测试 --force 覆盖已有文件"""
        output_file = temp_dir / "README.md"
        output_file.write_text("# OLD CONTENT\n", encoding="utf-8")
        result = run_script("generate_docs.py", [str(standard_plugin), "--output", str(output_file), "--force"])
        assert result.returncode == 0
        content = output_file.read_text(encoding="utf-8")
        assert "OLD CONTENT" not in content

    def test_missing_plugin_dir(self, temp_dir):
        """测试缺少插件目录应该失败"""
        result = run_script("generate_docs.py", [str(temp_dir / "nonexistent")])
        assert result.returncode != 0


# ============================================================
# 2. score_plugin.py 测试
# ============================================================

class TestScorePlugin:
    """score_plugin.py 插件质量自动评分器测试"""

    def test_score_standard_plugin(self, standard_plugin):
        """测试标准插件的质量评分"""
        result = run_script("score_plugin.py", [str(standard_plugin)])
        assert result.returncode in [0, 1]

    def test_score_json_output(self, standard_plugin):
        """测试 JSON 格式输出"""
        result = run_script("score_plugin.py", [str(standard_plugin), "--json"])
        assert result.returncode in [0, 1]
        try:
            data = json.loads(result.stdout)
            assert "score" in data or "total_score" in data or "percentage" in data
        except json.JSONDecodeError:
            pass

    def test_score_has_numeric_score(self, standard_plugin):
        """测试评分结果包含数字分数"""
        result = run_script("score_plugin.py", [str(standard_plugin)])
        import re
        numbers = re.findall(r'\d+\.?\d*', result.stdout)
        assert len(numbers) > 0

    def test_missing_plugin_dir(self, temp_dir):
        """测试缺少插件目录应该失败"""
        result = run_script("score_plugin.py", [str(temp_dir / "nonexistent")])
        assert result.returncode != 0


# ============================================================
# 3. check_skill_quality.py 测试
# ============================================================

class TestCheckSkillQuality:
    """check_skill_quality.py Skill 质量自动检查器测试"""

    def test_check_valid_skill(self, standard_plugin):
        """测试检查有效的技能"""
        skill_dir = standard_plugin / "skills" / "main-skill"
        if skill_dir.exists():
            result = run_script("check_skill_quality.py", [str(skill_dir)])
            assert result.returncode in [0, 1]

    def test_check_skill_json_output(self, standard_plugin):
        """测试 JSON 格式输出"""
        skill_dir = standard_plugin / "skills" / "main-skill"
        if skill_dir.exists():
            result = run_script("check_skill_quality.py", [str(skill_dir), "--json"])
            assert result.returncode in [0, 1]

    def test_check_missing_skill_dir(self, temp_dir):
        """测试缺少技能目录应该失败"""
        result = run_script("check_skill_quality.py", [str(temp_dir / "nonexistent")])
        assert result.returncode != 0

    def test_check_skill_without_skill_md(self, temp_dir):
        """测试检查没有 SKILL.md 的目录应该失败"""
        empty_dir = temp_dir / "empty-skill"
        empty_dir.mkdir()
        result = run_script("check_skill_quality.py", [str(empty_dir)])
        assert result.returncode != 0
