#!/usr/bin/env python3
"""
release_audit.py 和版本一致性测试
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RELEASE_AUDIT = ROOT / "scripts" / "release_audit.py"


class TestReleaseAudit:
    """release_audit.py 测试集"""

    def test_help(self):
        """测试 --help"""
        result = subprocess.run(
            [sys.executable, str(RELEASE_AUDIT), "--help"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0

    def test_audit_skill_root(self):
        """测试审计技能根目录"""
        result = subprocess.run(
            [sys.executable, str(RELEASE_AUDIT), str(ROOT)],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["status"] == "PASS"
        assert len(data["errors"]) == 0

    def test_version_consistency(self):
        """测试版本一致性"""
        # SKILL.md 版本
        skill_md = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        import re
        skill_ver = re.search(r">\s*\*\*版本\*\*:\s*v?([\d.]+)", skill_md)
        assert skill_ver is not None, "SKILL.md 中未找到版本号"

        # provenance.json 版本
        prov = json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))
        prov_ver = prov.get("version")

        # CHANGELOG 最新版本
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        cl_ver = re.search(r"##\s*\[([\d.]+)\]", changelog)

        assert skill_ver.group(1) == prov_ver, f"SKILL.md ({skill_ver.group(1)}) 与 provenance.json ({prov_ver}) 版本不一致"
        if cl_ver:
            assert cl_ver.group(1) == prov_ver, f"CHANGELOG ({cl_ver.group(1)}) 与 provenance.json ({prov_ver}) 版本不一致"


class TestAllScriptsHaveHelp:
    """所有脚本都应该有 --help"""

    def test_all_scripts_have_help(self):
        """测试所有 Python 脚本都有 --help"""
        scripts_dir = ROOT / "scripts"
        failed = []
        for script in scripts_dir.glob("*.py"):
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                failed.append(script.name)
        assert len(failed) == 0, f"以下脚本缺少 --help: {failed}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
