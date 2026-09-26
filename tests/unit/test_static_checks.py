"""
第1层：静态检查测试
"""
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
ALL_SCRIPTS = sorted(SCRIPTS_DIR.glob("*.py"))


class TestSyntaxCheck:
    @pytest.mark.parametrize("script", ALL_SCRIPTS, ids=lambda s: s.name)
    def test_script_compiles(self, script):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script)],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"语法错误: {result.stderr}"


class TestSecurityCheck:
    def test_no_eval_exec(self):
        import re
        dangerous = []
        for script in ALL_SCRIPTS:
            if script.name in ["audit_plugin.py", "score_plugin.py"]:
                continue
            content = script.read_text(encoding="utf-8")
            for i, line in enumerate(content.split("\n")):
                if line.strip().startswith("#"):
                    continue
                if re.search(r'\beval\s*\(', line) or re.search(r'\bexec\s*\(', line):
                    if 'r"' in line or "r'" in line:
                        continue
                    dangerous.append(f"{script.name}:{i+1}")
        if dangerous:
            pytest.fail(f"发现危险函数: {dangerous[:5]}")

    def test_no_shell_true(self):
        for script in ALL_SCRIPTS:
            if script.name in ["audit_plugin.py", "errors.py", "score_plugin.py"]:
                continue
            content = script.read_text(encoding="utf-8")
            for i, line in enumerate(content.split("\n")):
                if line.strip().startswith("#"):
                    continue
                if '"shell=True"' in line or "'shell=True'" in line:
                    continue
                if "shell=True" in line:
                    pytest.fail(f"{script.name}:{i+1} 使用了 shell=True")

    def test_no_hardcoded_secrets(self):
        secret_patterns = ["api_key", "apikey", "secret_key", "password", "token", "private_key"]
        for script in ALL_SCRIPTS:
            if script.name in ["audit_plugin.py", "validate_plugin.py", "score_plugin.py",
                               "errors.py", "mcp_security_check.py", "security_check.py"]:
                continue
            content = script.read_text(encoding="utf-8").lower()
            for pattern in secret_patterns:
                if pattern in content:
                    for line in content.split("\n"):
                        if pattern in line and "=" in line and not line.strip().startswith("#"):
                            if "os.environ" not in line and "getenv" not in line:
                                if 'r"' in line or "r'" in line:
                                    continue
                                pytest.fail(f"{script.name} 可能有硬编码密钥: {line.strip()[:60]}")


class TestDocumentationCheck:
    def test_skill_md_exists(self):
        assert (SKILL_ROOT / "SKILL.md").exists()

    def test_skill_md_has_frontmatter(self):
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "name:" in content
        assert "description:" in content

    def test_skill_md_under_300_lines(self):
        lines = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").split("\n")
        assert len(lines) <= 300, f"SKILL.md 有 {len(lines)} 行，超过 300 行"

    def test_references_directory_exists(self):
        assert (SKILL_ROOT / "references").is_dir()
