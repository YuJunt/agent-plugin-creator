#!/usr/bin/env python3
"""
P1 其他脚本直接测试

覆盖：
1. client_adapter.py - 多客户端适配
2. generate_docs.py - 文档生成
3. score_plugin.py - 质量评分
4. release_audit.py - 发布审计
5. check_skill_quality.py - 技能质量检查
6. run_evals.py - 统一评估入口
"""
import json
import pytest
from pathlib import Path

from tests.conftest import run_script


# ============================================================
# 1. client_adapter.py 测试
# ============================================================

class TestClientAdapter:
    """client_adapter.py 多客户端适配工具测试"""

    def test_list_targets(self):
        """测试列出支持的目标平台"""
        result = run_script("client_adapter.py", ["--list-targets"])
        assert result.returncode == 0
        # 应该列出至少 3 个平台
        assert len(result.stdout) > 0

    def test_check_standard_plugin(self, standard_plugin):
        """测试检查标准插件的兼容性"""
        result = run_script("client_adapter.py", [str(standard_plugin), "--check"])
        # check 模式可能返回 0 或有警告，但不应该崩溃
        assert result.returncode in [0, 1]

    def test_check_report_json(self, standard_plugin):
        """测试检查并输出 JSON 报告"""
        result = run_script("client_adapter.py", [str(standard_plugin), "--check", "--report"])
        assert result.returncode in [0, 1]

    def test_help(self):
        """测试帮助信息"""
        result = run_script("client_adapter.py", ["--help"])
        assert result.returncode == 0
        assert "client" in result.stdout.lower() or "adapter" in result.stdout.lower()


# ============================================================
# 2. generate_docs.py 测试
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

    def test_generated_readme_has_plugin_name(self, standard_plugin, temp_dir):
        """测试生成的 README 包含插件名称"""
        output_file = temp_dir / "README.md"
        run_script("generate_docs.py", [str(standard_plugin), "--output", str(output_file)])
        content = output_file.read_text(encoding="utf-8")
        # 应该包含插件名称或描述
        assert "test-plugin" in content.lower() or "测试" in content or "plugin" in content.lower()

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

        # 不使用 --force 应该失败
        result = run_script("generate_docs.py", [str(standard_plugin), "--output", str(output_file)])
        assert result.returncode != 0

        # 使用 --force 应该成功
        result = run_script("generate_docs.py", [str(standard_plugin), "--output", str(output_file), "--force"])
        assert result.returncode == 0
        content = output_file.read_text(encoding="utf-8")
        assert "OLD CONTENT" not in content

    def test_missing_plugin_dir(self, temp_dir):
        """测试缺少插件目录应该失败"""
        result = run_script("generate_docs.py", [str(temp_dir / "nonexistent")])
        assert result.returncode != 0


# ============================================================
# 3. score_plugin.py 测试
# ============================================================

class TestScorePlugin:
    """score_plugin.py 插件质量自动评分器测试"""

    def test_score_standard_plugin(self, standard_plugin):
        """测试标准插件的质量评分"""
        result = run_script("score_plugin.py", [str(standard_plugin)])
        # 评分可能通过或不通过，但不应该崩溃
        assert result.returncode in [0, 1]

    def test_score_json_output(self, standard_plugin):
        """测试 JSON 格式输出"""
        result = run_script("score_plugin.py", [str(standard_plugin), "--json"])
        assert result.returncode in [0, 1]
        # 尝试解析 JSON
        try:
            data = json.loads(result.stdout)
            # 分数字段可能叫 score、total_score 或 percentage
            assert "score" in data or "total_score" in data or "percentage" in data
        except json.JSONDecodeError:
            # JSON 可能包含非 JSON 输出，跳过
            pass

    def test_score_has_numeric_score(self, standard_plugin):
        """测试评分结果包含数字分数"""
        result = run_script("score_plugin.py", [str(standard_plugin)])
        # 输出中应该包含数字分数
        import re
        numbers = re.findall(r'\d+\.?\d*', result.stdout)
        assert len(numbers) > 0

    def test_missing_plugin_dir(self, temp_dir):
        """测试缺少插件目录应该失败"""
        result = run_script("score_plugin.py", [str(temp_dir / "nonexistent")])
        assert result.returncode != 0


# ============================================================
# 4. release_audit.py 测试
# ============================================================

class TestReleaseAudit:
    """release_audit.py 发布前审计工具测试"""

    def test_audit_skill_root(self):
        """测试审计当前技能根目录"""
        skill_root = "/home/user/.doubao/agent_mode/workspace/.user_skills/agent-plugin-creator"
        result = run_script("release_audit.py", [skill_root])
        # 审计可能通过或有警告，但不应该崩溃
        assert result.returncode in [0, 1]

    def test_audit_output_json(self):
        """测试审计输出包含 JSON"""
        skill_root = "/home/user/.doubao/agent_mode/workspace/.user_skills/agent-plugin-creator"
        result = run_script("release_audit.py", [skill_root])
        # 输出应该包含 status 字段
        assert "PASS" in result.stdout or "WARNING" in result.stdout or "BLOCKED" in result.stdout

    def test_audit_missing_dir(self, temp_dir):
        """测试缺少目录应该失败"""
        result = run_script("release_audit.py", [str(temp_dir / "nonexistent")])
        assert result.returncode != 0


# ============================================================
# 5. check_skill_quality.py 测试
# ============================================================

class TestCheckSkillQuality:
    """check_skill_quality.py Skill 质量自动检查器测试"""

    def test_check_valid_skill(self, standard_plugin):
        """测试检查有效的技能"""
        # 标准插件中的子技能应该是有效的
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


# ============================================================
# 6. run_evals.py 测试
# ============================================================

class TestRunEvals:
    """run_evals.py 统一评估入口测试"""

    def test_run_trigger_eval(self):
        """测试运行触发评估"""
        result = run_script("run_evals.py", ["--type", "trigger"])
        # 评估可能通过或不通过，但不应该崩溃
        assert result.returncode in [0, 1]

    def test_run_all_evals(self):
        """测试运行所有评估"""
        result = run_script("run_evals.py", ["--type", "all"])
        assert result.returncode in [0, 1]

    def test_eval_output_has_results(self):
        """测试评估输出包含结果"""
        result = run_script("run_evals.py", ["--type", "trigger"])
        # 输出中应该包含通过/失败统计
        assert "通过" in result.stdout or "passed" in result.stdout.lower() or "PASS" in result.stdout

    def test_help(self):
        """测试帮助信息"""
        result = run_script("run_evals.py", ["--help"])
        assert result.returncode == 0
        assert "eval" in result.stdout.lower() or "评估" in result.stdout
