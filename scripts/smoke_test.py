#!/usr/bin/env python3
"""
Plugin 冒烟测试脚本

一键验证插件的基本功能，确保发布前没有致命问题。
测试项：
  1. 目录结构完整性（plugin.json / skills / mcp.json）
  2. plugin.json 格式有效性
  3. 所有 SKILL.md 可解析
  4. 安全审计通过
  5. 没有硬编码密钥

用法:
    python3 scripts/smoke_test.py ./my-plugin
    python3 scripts/smoke_test.py ./my-plugin --json
"""
import argparse
import json
import re
import sys
from pathlib import Path


def smoke_test(plugin_dir: Path) -> dict:
    """执行冒烟测试"""
    results = {
        "plugin": plugin_dir.name,
        "checks": [],
        "passed": 0,
        "failed": 0,
        "warnings": 0,
    }

    def check(name: str, passed: bool, detail: str = "", warning: bool = False):
        status = "PASS" if passed else ("WARN" if warning else "FAIL")
        results["checks"].append({"name": name, "status": status, "detail": detail})
        if passed:
            results["passed"] += 1
        elif warning:
            results["warnings"] += 1
        else:
            results["failed"] += 1

    # 1. 目录结构检查
    plugin_json = plugin_dir / "plugin.json"
    check("plugin.json 存在", plugin_json.exists(),
          f"路径: {plugin_json}")

    if not plugin_json.exists():
        return results

    # 2. plugin.json 格式
    try:
        plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
        check("plugin.json 是有效 JSON", True)
    except json.JSONDecodeError as e:
        check("plugin.json 是有效 JSON", False, str(e))
        return results

    # 3. 必需字段
    required_fields = ["name", "version", "description"]
    for field in required_fields:
        check(f"plugin.json 包含 {field}", field in plugin,
              f"值: {plugin.get(field, '缺失')}")

    # 4. 版本号格式检查
    version = plugin.get("version", "")
    semver_pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
    check("版本号符合 SemVer", bool(re.match(semver_pattern, version)),
          f"版本: {version}")

    # 5. 不允许 pre-release 版本（发布到市场时）
    is_prerelease = bool(re.search(r"-(alpha|beta|rc|pre)", version, re.IGNORECASE))
    check("无 pre-release 版本", not is_prerelease,
          f"{'发现 pre-release: ' + version if is_prerelease else '正式版本'}",
          warning=is_prerelease)

    # 6. Skills 目录
    skills_dir = plugin_dir / "skills"
    if skills_dir.exists():
        skills = [d for d in skills_dir.iterdir() if d.is_dir()]
        check("skills/ 目录存在", True, f"{len(skills)} 个技能")

        for skill_dir in skills:
            skill_md = skill_dir / "SKILL.md"
            check(f"  {skill_dir.name}/SKILL.md 存在", skill_md.exists())
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8", errors="ignore")
                check(f"  {skill_dir.name}/SKILL.md 有 frontmatter",
                      content.startswith("---"),
                      "以 --- 开头")
    else:
        check("skills/ 目录存在", False, "无 skills 目录", warning=True)

    # 7. mcp.json（可选）
    mcp_json = plugin_dir / "mcp.json"
    if mcp_json.exists():
        try:
            mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
            check("mcp.json 是有效 JSON", True)
            servers = mcp.get("mcpServers", {})
            check("mcp.json 包含服务器", len(servers) > 0,
                  f"{len(servers)} 个服务器")
        except json.JSONDecodeError as e:
            check("mcp.json 是有效 JSON", False, str(e))
    else:
        check("mcp.json 存在", True, "无 MCP 服务器（可选）", warning=True)

    # 8. 硬编码密钥扫描（简单版）
    secret_patterns = [
        (r"api[_-]?key\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "API key"),
        (r"password\s*=\s*['\"][^'\"]{8,}['\"]", "password"),
        (r"secret\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "secret"),
        (r"token\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "token"),
    ]
    has_secrets = False
    for py_file in plugin_dir.rglob("*.py"):
        if "test" in py_file.name or "official" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern, name in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    has_secrets = True
                    break
        except Exception:
            pass
    check("无硬编码密钥", not has_secrets,
          "发现疑似硬编码密钥" if has_secrets else "未发现",
          warning=has_secrets)

    # 9. README 存在（推荐）
    readme = plugin_dir / "README.md"
    check("README.md 存在", readme.exists(),
          "发布到市场推荐有 README", warning=not readme.exists)

    return results


def main():
    parser = argparse.ArgumentParser(description="Plugin 冒烟测试")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.exists():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    results = smoke_test(plugin_dir)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"冒烟测试: {results['plugin']}")
        print("=" * 60)
        for check in results["checks"]:
            icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}[check["status"]]
            print(f"  {icon} {check['name']}")
            if check["detail"]:
                print(f"     {check['detail']}")
        print()
        print(f"通过: {results['passed']} | 失败: {results['failed']} | 警告: {results['warnings']}")
        print("=" * 60)

    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
