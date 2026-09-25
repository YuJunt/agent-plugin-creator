#!/usr/bin/env python3
"""
security_check.py 单元测试
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "security_check.py"


def run_check(target_dir: Path, severity: str = "low") -> subprocess.CompletedProcess:
    """运行 security_check.py"""
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(target_dir), "--severity", severity],
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestSecurityCheck:
    """security_check.py 测试集"""

    def test_help(self):
        """测试 --help"""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0

    def test_clean_project_no_issues(self):
        """测试干净的项目应该没有安全问题"""
        result = run_check(ROOT)
        assert result.returncode == 0
        assert "未发现安全问题" in result.stdout or "0" in result.stdout

    def test_detect_hardcoded_secret(self, tmp_path):
        """测试检测硬编码密钥"""
        test_dir = tmp_path / "test-project"
        test_dir.mkdir()
        script_dir = test_dir / "scripts"
        script_dir.mkdir()
        (script_dir / "bad.py").write_text(
            'api_key = "sk-1234567890abcdef1234567890abcdef"\n'
        )
        result = run_check(test_dir, severity="critical")
        assert result.returncode != 0
        assert "api_key" in result.stdout.lower() or "硬编码" in result.stdout

    def test_no_false_positive_in_docstring(self, tmp_path):
        """测试 docstring 中的路径不会误报"""
        test_dir = tmp_path / "test-project"
        test_dir.mkdir()
        script_dir = test_dir / "scripts"
        script_dir.mkdir()
        (script_dir / "safe.py").write_text(
            '"""\n'
            '示例路径: ../1.0.0/plugin.schema.json\n'
            '不要使用绝对路径或 ../\n'
            '"""\n'
            'def main():\n'
            '    pass\n'
        )
        result = run_check(test_dir, severity="medium")
        # docstring 中的路径不应该触发路径穿越告警
        assert "path_traversal" not in result.stdout

    def test_no_false_positive_in_comments(self, tmp_path):
        """测试注释中的路径不会误报"""
        test_dir = tmp_path / "test-project"
        test_dir.mkdir()
        script_dir = test_dir / "scripts"
        script_dir.mkdir()
        (script_dir / "safe.py").write_text(
            '# 不要使用 ../ 路径\n'
            '# 正确做法: 使用相对路径\n'
            'def main():\n'
            '    pass\n'
        )
        result = run_check(test_dir, severity="medium")
        assert "path_traversal" not in result.stdout

    def test_detect_dangerous_eval(self, tmp_path):
        """测试检测 eval/exec"""
        test_dir = tmp_path / "test-project"
        test_dir.mkdir()
        script_dir = test_dir / "scripts"
        script_dir.mkdir()
        (script_dir / "dangerous.py").write_text(
            'def run(code):\n'
            '    eval(code)\n'
        )
        result = run_check(test_dir, severity="high")
        # eval 应该被检测到
        assert result.returncode != 0 or "eval" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
