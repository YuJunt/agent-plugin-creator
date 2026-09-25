#!/usr/bin/env python3
"""
init_skill.py 和 package_plugin.py 单元测试
"""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = ROOT / "scripts" / "init_skill.py"
PACKAGE_SCRIPT = ROOT / "scripts" / "package_plugin.py"


class TestInitSkill:
    """init_skill.py 测试集"""

    def test_help(self):
        """测试 --help"""
        result = subprocess.run(
            [sys.executable, str(INIT_SCRIPT), "--help"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0

    def test_create_skill_scaffold(self, tmp_path):
        """测试创建 Skill 脚手架"""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = subprocess.run(
            [sys.executable, str(INIT_SCRIPT), "test-skill", "--path", str(output_dir)],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        skill_dir = output_dir / "test-skill"
        assert skill_dir.exists()
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "scripts").exists()
        assert (skill_dir / "references").exists()
        assert (skill_dir / "assets").exists()

    def test_skill_name_in_skill_md(self, tmp_path):
        """测试生成的 SKILL.md 包含正确的 name"""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        subprocess.run(
            [sys.executable, str(INIT_SCRIPT), "my-awesome-skill", "--path", str(output_dir)],
            capture_output=True, text=True, timeout=30
        )
        skill_md = (output_dir / "my-awesome-skill" / "SKILL.md").read_text()
        assert "name: my-awesome-skill" in skill_md

    def test_no_overwrite_without_force(self, tmp_path):
        """测试不使用 --force 时不覆盖已有目录"""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        skill_dir = output_dir / "existing-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("existing content")
        result = subprocess.run(
            [sys.executable, str(INIT_SCRIPT), "existing-skill", "--path", str(output_dir)],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode != 0
        # 原有内容不应被覆盖
        assert "existing content" in (skill_dir / "SKILL.md").read_text()


class TestPackagePlugin:
    """package_plugin.py 测试集"""

    def test_help(self):
        """测试 --help"""
        result = subprocess.run(
            [sys.executable, str(PACKAGE_SCRIPT), "--help"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0

    def test_package_minimal_plugin(self, tmp_path):
        """测试打包最小插件"""
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "test-plugin",
            "version": "1.0.0"
        }))
        output_dir = tmp_path / "dist"
        result = subprocess.run(
            [sys.executable, str(PACKAGE_SCRIPT), str(plugin_dir), "--output", str(output_dir)],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        zip_files = list(output_dir.glob("*.zip"))
        assert len(zip_files) > 0
        # 验证 zip 文件包含 plugin.json
        with zipfile.ZipFile(zip_files[0], "r") as zf:
            assert "plugin.json" in zf.namelist() or any("plugin.json" in n for n in zf.namelist())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
