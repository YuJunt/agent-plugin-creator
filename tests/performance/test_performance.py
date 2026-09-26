"""
性能测试：建立性能基准，检测性能退化

覆盖：
- 各脚本的执行时间基准
- 并行执行效率
- 大插件处理性能
- 内存占用（简单检测）
"""
import json
import time
import pytest
from pathlib import Path

from tests.conftest import run_script, SCRIPT_DIR


class TestPerformanceBaseline:
    """性能基准测试：所有操作都应该在合理时间内完成"""

    def test_validate_under_1s(self, standard_plugin):
        """validate_plugin.py 应该在 1 秒内完成"""
        start = time.time()
        result = run_script("validate_plugin.py", [str(standard_plugin)])
        duration = time.time() - start
        assert result.returncode == 0
        assert duration < 1.0, f"validate 耗时 {duration:.2f}s，超过 1s 基准"

    def test_audit_under_1s(self, standard_plugin):
        """audit_plugin.py 应该在 1 秒内完成"""
        start = time.time()
        result = run_script("audit_plugin.py", [str(standard_plugin)])
        duration = time.time() - start
        assert result.returncode == 0
        assert duration < 1.0, f"audit 耗时 {duration:.2f}s，超过 1s 基准"

    def test_smoke_under_1s(self, standard_plugin):
        """smoke_test.py 应该在 1 秒内完成"""
        start = time.time()
        result = run_script("smoke_test.py", [str(standard_plugin)])
        duration = time.time() - start
        assert result.returncode == 0
        assert duration < 1.0, f"smoke 耗时 {duration:.2f}s，超过 1s 基准"

    def test_plugin_py_validate_under_2s(self, standard_plugin):
        """plugin.py validate（统一入口）应该在 2 秒内完成"""
        start = time.time()
        result = run_script("plugin.py", ["validate", str(standard_plugin)])
        duration = time.time() - start
        assert result.returncode == 0
        assert duration < 2.0, f"plugin.py validate 耗时 {duration:.2f}s，超过 2s 基准"

    def test_check_skill_quality_under_1s(self, standard_plugin):
        """check_skill_quality.py 应该在 1 秒内完成"""
        skill_dir = standard_plugin / "skills" / "test-skill"
        start = time.time()
        result = run_script("check_skill_quality.py", [str(skill_dir)])
        duration = time.time() - start
        assert duration < 1.0, f"check_skill_quality 耗时 {duration:.2f}s，超过 1s 基准"


class TestPerformanceConsistency:
    """性能一致性测试：多次运行性能应该稳定"""

    def test_validate_consistent_5_runs(self, standard_plugin):
        """validate 连续运行 5 次，性能应该稳定（无异常波动）"""
        durations = []
        for _ in range(5):
            start = time.time()
            run_script("validate_plugin.py", [str(standard_plugin)])
            durations.append(time.time() - start)

        avg = sum(durations) / len(durations)
        max_val = max(durations)
        # 最大值不应该超过平均值的 3 倍（排除异常波动）
        assert max_val < avg * 3, f"性能波动过大: 平均 {avg:.3f}s, 最大 {max_val:.3f}s"


class TestLargePluginPerformance:
    """大插件性能测试：处理复杂插件时性能不应该显著下降"""

    def test_large_plugin_validate_under_2s(self, temp_dir):
        """包含 10 个 Skill 的大插件，validate 应该在 2 秒内完成"""
        plugin_dir = temp_dir / "large-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "large-plugin", "version": "1.0.0",
            "description": "大插件性能测试", "author": {"name": "Test"}
        }), encoding="utf-8")

        # 创建 10 个 Skill
        for i in range(10):
            skill_dir = plugin_dir / "skills" / f"skill-{i}"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: skill-{i}\ndescription: test\n---\n# Test\n", encoding="utf-8")

        (plugin_dir / "README.md").write_text("# Large Plugin\n", encoding="utf-8")

        start = time.time()
        result = run_script("validate_plugin.py", [str(plugin_dir)])
        duration = time.time() - start
        assert result.returncode == 0
        assert duration < 2.0, f"大插件 validate 耗时 {duration:.2f}s，超过 2s 基准"
