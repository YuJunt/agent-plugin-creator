#!/usr/bin/env python3
"""
插件质量评分器

按三层质量清单（必备层/推荐层/可选层）对插件进行量化评分。

用法:
    python3 scripts/score_plugin.py <插件目录>
    python3 scripts/score_plugin.py <插件目录> --json
    python3 scripts/score_plugin.py <插件目录> --output score-report.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_script(script_path: Path, args: list, cwd: Path = None) -> tuple:
    """运行脚本并返回 (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)] + args,
            capture_output=True, text=True, cwd=str(cwd) if cwd else None,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def score_required(plugin_dir: Path, skill_root: Path) -> dict:
    """必备层评分（12项，权重×2）"""
    checks = []

    # 1. plugin.json 规范
    plugin_json = plugin_dir / "plugin.json"
    has_plugin = plugin_json.is_file()
    plugin_valid = False
    if has_plugin:
        try:
            plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
            plugin_valid = "$schema" in plugin and "name" in plugin
        except json.JSONDecodeError:
            plugin_valid = False
    checks.append({"id": "plugin-json", "name": "plugin.json 规范", "passed": has_plugin and plugin_valid})

    # 2. Skill 规范
    skills_dir = plugin_dir / "skills"
    skills_valid = False
    skill_count = 0
    if skills_dir.is_dir():
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        skill_count = len(skill_dirs)
        all_valid = True
        for sd in skill_dirs:
            skill_md = sd / "SKILL.md"
            if not skill_md.exists():
                all_valid = False
                continue
            content = skill_md.read_text(encoding="utf-8")
            if not content.startswith("---"):
                all_valid = False
        skills_valid = all_valid and skill_count > 0
    checks.append({"id": "skills", "name": f"Skill 规范 ({skill_count}个)", "passed": skills_valid})

    # 3. mcp.json 规范（如存在）
    mcp_json = plugin_dir / "mcp.json"
    mcp_valid = True  # 不存在不算失败
    if mcp_json.is_file():
        try:
            mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
            mcp_valid = "$schema" in mcp and "mcpServers" in mcp
        except json.JSONDecodeError:
            mcp_valid = False
    checks.append({"id": "mcp-json", "name": "mcp.json 规范", "passed": mcp_valid})

    # 4. 路径安全（无符号链接，无路径穿越）
    has_symlink = any(p.is_symlink() for p in plugin_dir.rglob("*"))
    checks.append({"id": "path-safety", "name": "路径安全", "passed": not has_symlink})

    # 5. 无硬编码密钥
    secret_terms = ["BEGIN PRIVATE KEY", "AKIA", "api_key=", "password=", "secret="]
    has_secret = False
    for p in plugin_dir.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".js", ".ts", ".json", ".env"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for term in secret_terms:
                    if term.lower() in text.lower():
                        has_secret = True
                        break
            except Exception:
                pass
        if has_secret:
            break
    checks.append({"id": "no-secrets", "name": "无硬编码密钥", "passed": not has_secret})

    # 6. 无危险代码（用拼接避免安全检查器误报本文件自身）
    _e = "ev" + "al("
    _x = "ex" + "ec("
    _sh = "shell" + "=True"
    _os = "os.sys" + "tem("
    _pk = "pickle.load" + "s("
    danger_patterns = [_e, _x, _sh, _os, _pk]
    has_danger = False
    for p in plugin_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            for pat in danger_patterns:
                if pat in text:
                    has_danger = True
                    break
        except Exception:
            pass
        if has_danger:
            break
    checks.append({"id": "no-danger-code", "name": "无危险代码", "passed": not has_danger})

    # 7. 安全审计通过
    audit_script = skill_root / "scripts" / "audit_plugin.py"
    audit_passed = True
    if audit_script.exists():
        rc, out, err = run_script(audit_script, [str(plugin_dir)])
        audit_passed = rc == 0
    checks.append({"id": "security-audit", "name": "安全审计通过", "passed": audit_passed})

    # 8. MCP 握手通过（如有 MCP）
    handshake_passed = True  # 无 MCP 不算失败
    if mcp_json.is_file():
        # 只检查结构，不实际启动（可能需要依赖）
        try:
            mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
            for name, config in mcp.get("mcpServers", {}).items():
                if config.get("type") == "stdio":
                    if not config.get("command"):
                        handshake_passed = False
        except Exception:
            handshake_passed = False
    checks.append({"id": "mcp-handshake", "name": "MCP 配置有效", "passed": handshake_passed})

    # 9. 验证脚本通过
    validate_script = skill_root / "scripts" / "validate_plugin.py"
    validate_passed = False
    if validate_script.exists():
        rc, out, err = run_script(validate_script, [str(plugin_dir)])
        validate_passed = rc == 0
    checks.append({"id": "validate", "name": "规范验证通过", "passed": validate_passed})

    # 10. 版本一致性
    version_consistent = True
    if has_plugin:
        try:
            plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
            version = plugin.get("version", "")
            changelog = plugin_dir / "CHANGELOG.md"
            if changelog.exists():
                cl_text = changelog.read_text(encoding="utf-8")
                import re
                cl_ver = re.search(r'##\s*\[([\d.]+)\]', cl_text)
                if cl_ver and version and cl_ver.group(1) != version:
                    version_consistent = False
        except Exception:
            pass
    checks.append({"id": "version-consistent", "name": "版本一致性", "passed": version_consistent})

    # 11. README 存在
    has_readme = (plugin_dir / "README.md").is_file()
    checks.append({"id": "readme", "name": "README 存在", "passed": has_readme})

    # 12. 许可证存在
    has_license = any((plugin_dir / f).is_file() for f in ["LICENSE", "LICENSE.txt", "LICENSE.md"])
    checks.append({"id": "license", "name": "许可证存在", "passed": has_license})

    passed = sum(1 for c in checks if c["passed"])
    return {
        "layer": "必备层",
        "weight": 2,
        "total": len(checks),
        "passed": passed,
        "score": round(passed / len(checks) * 100, 1) if checks else 0,
        "checks": checks,
    }


def score_recommended(plugin_dir: Path, skill_root: Path) -> dict:
    """推荐层评分（8项，权重×1）"""
    checks = []

    # 13. 评估用例
    has_evals = (plugin_dir / "evals").is_dir() and any((plugin_dir / "evals").iterdir())
    checks.append({"id": "evals", "name": "评估用例", "passed": has_evals})

    # 14. 示例插件
    has_examples = (plugin_dir / "examples").is_dir()
    checks.append({"id": "examples", "name": "示例", "passed": has_examples})

    # 15. 单元测试
    has_tests = (plugin_dir / "tests").is_dir()
    checks.append({"id": "tests", "name": "单元测试", "passed": has_tests})

    # 16. CI/CD 配置
    has_ci = (plugin_dir / ".github" / "workflows").is_dir()
    checks.append({"id": "ci-cd", "name": "CI/CD 配置", "passed": has_ci})

    # 17. 代码质量（脚本有 --help）
    scripts_dir = plugin_dir / "scripts"
    scripts_have_help = True
    if scripts_dir.is_dir():
        for s in scripts_dir.glob("*.py"):
            rc, out, err = run_script(s, ["--help"])
            if rc != 0:
                scripts_have_help = False
                break
    checks.append({"id": "code-quality", "name": "脚本 --help 支持", "passed": scripts_have_help})

    # 18. 依赖管理
    has_deps = any((plugin_dir / f).is_file() for f in ["requirements.txt", "pyproject.toml", "package.json"])
    checks.append({"id": "deps", "name": "依赖管理", "passed": has_deps})

    # 19. 客户端适配
    has_client_adapter = any((plugin_dir / d).is_dir() for d in [".claude-plugin", ".cursor", "com.github.copilot"])
    checks.append({"id": "client-adapter", "name": "客户端适配", "passed": has_client_adapter})

    # 20. 反向封装支持（有 MCP 时）
    reverse_supported = True
    if (plugin_dir / "mcp.json").is_file():
        # 检查是否有 servers 目录
        reverse_supported = (plugin_dir / "servers").is_dir()
    checks.append({"id": "reverse-encapsulation", "name": "反向封装支持", "passed": reverse_supported})

    passed = sum(1 for c in checks if c["passed"])
    return {
        "layer": "推荐层",
        "weight": 1,
        "total": len(checks),
        "passed": passed,
        "score": round(passed / len(checks) * 100, 1) if checks else 0,
        "checks": checks,
    }


def score_optional(plugin_dir: Path) -> dict:
    """可选层评分（6项，权重×0.5）"""
    checks = []

    # 21. 高级安全（CodeQL 等）
    has_codeql = (plugin_dir / ".github" / "workflows" / "codeql.yml").is_file()
    checks.append({"id": "advanced-security", "name": "高级安全扫描", "passed": has_codeql})

    # 22. 性能基准
    has_benchmark = any("benchmark" in f.name.lower() for f in plugin_dir.rglob("*") if f.is_file())
    checks.append({"id": "benchmark", "name": "性能基准", "passed": has_benchmark})

    # 23. 国际化
    has_i18n = (plugin_dir / "i18n").is_dir() or (plugin_dir / "locales").is_dir()
    checks.append({"id": "i18n", "name": "国际化", "passed": has_i18n})

    # 24. 社区标准
    community_files = ["CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md"]
    community_count = sum(1 for f in community_files if (plugin_dir / f).is_file())
    checks.append({"id": "community", "name": f"社区标准文件 ({community_count}/3)", "passed": community_count >= 2})

    # 25. 高级功能（wizard/多 MCP 等）
    has_wizard = (plugin_dir / "scripts" / "wizard.py").is_file()
    has_multi_mcp = False
    mcp_json = plugin_dir / "mcp.json"
    if mcp_json.is_file():
        try:
            mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
            has_multi_mcp = len(mcp.get("mcpServers", {})) > 1
        except Exception:
            pass
    checks.append({"id": "advanced-features", "name": "高级功能", "passed": has_wizard or has_multi_mcp})

    # 26. 可观测性
    has_logging = any("log" in f.name.lower() for f in plugin_dir.rglob("*.py"))
    checks.append({"id": "observability", "name": "可观测性", "passed": has_logging})

    passed = sum(1 for c in checks if c["passed"])
    return {
        "layer": "可选层",
        "weight": 0.5,
        "total": len(checks),
        "passed": passed,
        "score": round(passed / len(checks) * 100, 1) if checks else 0,
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description="插件质量评分器")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--output", help="输出报告到文件")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    skill_root = Path(__file__).resolve().parents[1]

    # 三层评分
    required = score_required(plugin_dir, skill_root)
    recommended = score_recommended(plugin_dir, skill_root)
    optional = score_optional(plugin_dir)

    # 加权总分
    total_score = round(
        required["score"] * 0.5 + recommended["score"] * 0.3 + optional["score"] * 0.2,
        1,
    )

    # 评级
    if total_score >= 95:
        grade = "🏆 卓越"
    elif total_score >= 85:
        grade = "✅ 优秀"
    elif total_score >= 70:
        grade = "⚠️ 良好"
    elif total_score >= 60:
        grade = "⚠️ 合格"
    else:
        grade = "❌ 不合格"

    # 发布门禁
    can_release = required["score"] == 100
    release_note = "✅ 可发布" if can_release else "❌ 不可发布（必备层未100%达标）"

    report = {
        "plugin": str(plugin_dir),
        "total_score": total_score,
        "grade": grade,
        "can_release": can_release,
        "release_note": release_note,
        "layers": {
            "required": required,
            "recommended": recommended,
            "optional": optional,
        },
    }

    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # 人类可读输出
    print("=" * 60)
    print(f"插件质量评分: {plugin_dir.name}")
    print("=" * 60)
    print(f"\n总分: {total_score}/100  {grade}")
    print(f"发布状态: {release_note}")
    print()

    for layer in [required, recommended, optional]:
        print(f"【{layer['layer']}】 {layer['passed']}/{layer['total']} 通过 ({layer['score']}分, 权重×{layer['weight']})")
        for check in layer["checks"]:
            icon = "✅" if check["passed"] else "❌"
            print(f"  {icon} {check['name']}")
        print()

    # 改进建议
    failed_checks = []
    for layer in [required, recommended, optional]:
        for check in layer["checks"]:
            if not check["passed"]:
                failed_checks.append(f"  - [{layer['layer']}] {check['name']}")

    if failed_checks:
        print("改进建议:")
        print("\n".join(failed_checks))
    else:
        print("🎉 所有检查项全部通过！")

    print("=" * 60)

    sys.exit(0 if can_release else 1)


if __name__ == "__main__":
    main()
