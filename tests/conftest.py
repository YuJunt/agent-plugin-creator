"""
共享测试夹具（fixtures）
"""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"


@pytest.fixture
def temp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def standard_plugin(temp_dir):
    plugin_dir = temp_dir / "standard-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "skills" / "test-skill").mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "standard-plugin",
        "version": "1.0.0",
        "description": "标准测试插件",
        "author": {"name": "Test Author"},
        "license": "MIT"
    }, indent=2), encoding="utf-8")
    (plugin_dir / "skills" / "test-skill" / "SKILL.md").write_text("""---
name: test-skill
description: 测试技能
---
# Test Skill
## 概述
测试
## 工作流程
1. 测试
## Gotchas
### 坑 1
- **症状**：测试
- **修正**：测试
- **原因**：测试
""", encoding="utf-8")
    (plugin_dir / "README.md").write_text("# Standard Plugin\n", encoding="utf-8")
    return plugin_dir


@pytest.fixture
def empty_plugin(temp_dir):
    plugin_dir = temp_dir / "empty-plugin"
    plugin_dir.mkdir()
    return plugin_dir


@pytest.fixture
def invalid_json_plugin(temp_dir):
    plugin_dir = temp_dir / "invalid-json-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text("{invalid json", encoding="utf-8")
    return plugin_dir


@pytest.fixture
def name_mismatch_plugin(temp_dir):
    plugin_dir = temp_dir / "my-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "wrong-name",
        "version": "1.0.0",
        "description": "name 不一致测试"
    }), encoding="utf-8")
    return plugin_dir


@pytest.fixture
def multi_skill_plugin(temp_dir):
    plugin_dir = temp_dir / "multi-skill-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "multi-skill-plugin",
        "version": "2.0.0",
        "description": "多 Skill 测试插件",
        "author": {"name": "Test"}
    }), encoding="utf-8")
    for skill_name in ["skill-a", "skill-b", "skill-c"]:
        skill_dir = plugin_dir / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"""---
name: {skill_name}
description: {skill_name} 测试技能
---
# {skill_name}
## 概述
测试
""", encoding="utf-8")
    (plugin_dir / "README.md").write_text("# Multi Skill Plugin\n", encoding="utf-8")
    return plugin_dir


def run_script(script_name: str, args: list, cwd: Path = None, timeout: int = 30):
    import subprocess
    import sys
    script_path = SCRIPT_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
