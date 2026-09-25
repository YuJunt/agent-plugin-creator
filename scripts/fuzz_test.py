#!/usr/bin/env python3
"""
模糊测试工具

对验证脚本进行输入边界测试，发现潜在的崩溃和异常处理问题。

用法:
    python3 scripts/fuzz_test.py --target validate_plugin
    python3 scripts/fuzz_test.py --target validate_skill
    python3 scripts/fuzz_test.py --target all --iterations 100
    python3 scripts/fuzz_test.py --target validate_plugin --json
"""
import argparse
import json
import os
import random
import string
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path


def random_string(length: int = 10) -> str:
    """生成随机字符串"""
    return "".join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=length))


def random_name() -> str:
    """生成随机名称（可能含非法字符）"""
    chars = string.ascii_lowercase + string.digits + "-._/\\ " + string.punctuation
    return "".join(random.choices(chars, k=random.randint(1, 30)))


def generate_malformed_plugin(tmpdir: Path) -> Path:
    """生成畸形的插件目录"""
    plugin_dir = tmpdir / random_name()
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # 随机选择畸形类型
    malformation_type = random.choice([
        "no_plugin_json",
        "invalid_json",
        "missing_schema",
        "invalid_name",
        "empty_skills",
        "malformed_skill",
        "invalid_mcp",
        "path_traversal",
        "symlink",
        "huge_file",
        "binary_file",
        "nested_dirs",
    ])

    if malformation_type == "no_plugin_json":
        pass  # 不创建 plugin.json
    elif malformation_type == "invalid_json":
        (plugin_dir / "plugin.json").write_text("{invalid json,,,", encoding="utf-8")
    elif malformation_type == "missing_schema":
        (plugin_dir / "plugin.json").write_text(json.dumps({"name": "test"}), encoding="utf-8")
    elif malformation_type == "invalid_name":
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                        "name": random_string(50)}), encoding="utf-8")
    elif malformation_type == "empty_skills":
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                        "name": "test"}), encoding="utf-8")
        (plugin_dir / "skills").mkdir()
    elif malformation_type == "malformed_skill":
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                        "name": "test"}), encoding="utf-8")
        skill_dir = plugin_dir / "skills" / "bad-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("not frontmatter\n" + random_string(100), encoding="utf-8")
    elif malformation_type == "invalid_mcp":
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                        "name": "test"}), encoding="utf-8")
        (plugin_dir / "mcp.json").write_text("{bad mcp json", encoding="utf-8")
    elif malformation_type == "path_traversal":
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                        "name": "test"}), encoding="utf-8")
        (plugin_dir / "mcp.json").write_text(
            json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
                        "mcpServers": {"s": {"type": "stdio", "command": "../../../etc/passwd"}}}),
            encoding="utf-8")
    elif malformation_type == "symlink":
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                        "name": "test"}), encoding="utf-8")
        try:
            (plugin_dir / "link").symlink_to("/etc/passwd")
        except (OSError, NotImplementedError):
            pass
    elif malformation_type == "huge_file":
        (plugin_dir / "plugin.json").write_text("x" * 1000000, encoding="utf-8")
    elif malformation_type == "binary_file":
        (plugin_dir / "plugin.json").write_bytes(bytes([0x00, 0x01, 0x02, 0xFF] * 100))
    elif malformation_type == "nested_dirs":
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                        "name": "test"}), encoding="utf-8")
        nested = plugin_dir
        for _ in range(20):
            nested = nested / "deep"
            nested.mkdir(exist_ok=True)
        (nested / "file.txt").write_text("deep file", encoding="utf-8")

    return plugin_dir


def generate_malformed_skill(tmpdir: Path) -> Path:
    """生成畸形的 skill 目录"""
    skill_dir = tmpdir / random_name()
    skill_dir.mkdir(parents=True, exist_ok=True)

    malformation_type = random.choice([
        "no_skill_md",
        "invalid_frontmatter",
        "bad_name",
        "long_description",
        "empty_body",
        "huge_file",
        "binary_content",
        "missing_name",
        "unknown_fields",
    ])

    if malformation_type == "no_skill_md":
        pass
    elif malformation_type == "invalid_frontmatter":
        (skill_dir / "SKILL.md").write_text("not frontmatter\n" + random_string(50), encoding="utf-8")
    elif malformation_type == "bad_name":
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {random_string(70)}\ndescription: test\n---\n", encoding="utf-8")
    elif malformation_type == "long_description":
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: test\ndescription: {'x' * 2000}\n---\n", encoding="utf-8")
    elif malformation_type == "empty_body":
        (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: test\n---\n", encoding="utf-8")
    elif malformation_type == "huge_file":
        (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: test\n---\n" + "x" * 100000, encoding="utf-8")
    elif malformation_type == "binary_content":
        (skill_dir / "SKILL.md").write_bytes(bytes([0x00, 0xFF] * 50))
    elif malformation_type == "missing_name":
        (skill_dir / "SKILL.md").write_text("---\ndescription: test\n---\n", encoding="utf-8")
    elif malformation_type == "unknown_fields":
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: test\ndescription: test\nversion: 1.0\nauthor: someone\n---\n", encoding="utf-8")

    return skill_dir


def run_fuzz(target: str, iterations: int, skill_root: Path) -> dict:
    """运行模糊测试"""
    results = {
        "target": target,
        "iterations": iterations,
        "crashes": [],
        "errors": [],
        "passed": 0,
        "failed": 0,
    }

    script_map = {
        "validate_plugin": skill_root / "scripts" / "validate_plugin.py",
        "validate_skill": skill_root / "scripts" / "validate_skill.py",
        "audit_plugin": skill_root / "scripts" / "audit_plugin.py",
        "security_check": skill_root / "scripts" / "security_check.py",
    }

    targets = [target] if target != "all" else list(script_map.keys())

    for tgt in targets:
        script = script_map.get(tgt)
        if not script or not script.exists():
            results["errors"].append(f"脚本不存在: {tgt}")
            continue

        for i in range(iterations):
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)

                if tgt in ("validate_plugin", "audit_plugin", "security_check"):
                    test_dir = generate_malformed_plugin(tmp_path)
                else:
                    test_dir = generate_malformed_skill(tmp_path)

                try:
                    result = subprocess.run(
                        [sys.executable, str(script), str(test_dir)],
                        capture_output=True, text=True, timeout=10,
                    )
                    # 非零退出码是正常的（验证失败），但不应该崩溃
                    if result.returncode < 0:
                        results["crashes"].append({
                            "iteration": i,
                            "target": tgt,
                            "signal": -result.returncode,
                            "stderr": result.stderr[:500],
                        })
                    else:
                        results["passed"] += 1
                except subprocess.TimeoutExpired:
                    results["crashes"].append({
                        "iteration": i,
                        "target": tgt,
                        "error": "timeout",
                    })
                except Exception as e:
                    results["crashes"].append({
                        "iteration": i,
                        "target": tgt,
                        "error": str(e),
                        "traceback": traceback.format_exc()[:500],
                    })

    results["failed"] = len(results["crashes"])
    return results


def main():
    parser = argparse.ArgumentParser(description="模糊测试工具")
    parser.add_argument("--target", choices=["validate_plugin", "validate_skill", "audit_plugin", "security_check", "all"],
                        default="validate_plugin", help="测试目标")
    parser.add_argument("--iterations", type=int, default=50, help="迭代次数")
    parser.add_argument("--seed", type=int, help="随机种子（用于复现）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    if args.seed:
        random.seed(args.seed)

    skill_root = Path(__file__).resolve().parents[1]

    if not args.json:
        print(f"🔍 模糊测试: target={args.target}, iterations={args.iterations}")
        if args.seed:
            print(f"   随机种子: {args.seed}")
        print()

    results = run_fuzz(args.target, args.iterations, skill_root)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("模糊测试结果")
        print("=" * 50)
        print(f"目标: {results['target']}")
        print(f"迭代: {results['iterations']}")
        print(f"通过: {results['passed']}")
        print(f"崩溃: {results['failed']}")
        print(f"错误: {len(results['errors'])}")

        if results["errors"]:
            print("\n错误:")
            for e in results["errors"]:
                print(f"  - {e}")

        if results["crashes"]:
            print("\n崩溃详情:")
            for c in results["crashes"][:10]:
                print(f"  迭代 {c['iteration']} ({c['target']}):")
                if "signal" in c:
                    print(f"    信号: {c['signal']}")
                if "error" in c:
                    print(f"    错误: {c['error']}")
                if "stderr" in c and c["stderr"]:
                    print(f"    stderr: {c['stderr'][:200]}")
        else:
            print("\n✅ 未发现崩溃！")

        print("=" * 50)

    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
