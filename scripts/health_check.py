#!/usr/bin/env python3
"""
插件健康诊断工具

综合检查插件的健康状态，包括结构、安全、性能、可维护性等维度。

用法:
    python3 scripts/health_check.py <插件目录>
    python3 scripts/health_check.py <插件目录> --deep
    python3 scripts/health_check.py <插件目录> --json
    python3 scripts/health_check.py <插件目录> --output health-report.json
"""
import argparse
import json
import sys
from pathlib import Path


def check_structure(plugin_dir: Path) -> dict:
    """检查结构健康"""
    checks = []
    score = 100

    # 必需文件
    required_files = ["plugin.json"]
    for f in required_files:
        exists = (plugin_dir / f).exists()
        checks.append({"check": f"存在 {f}", "passed": exists, "weight": 20})
        if not exists:
            score -= 20

    # 推荐文件
    recommended = ["README.md", "LICENSE", "CHANGELOG.md"]
    for f in recommended:
        exists = any((plugin_dir / candidate).exists() for candidate in [f, f"{f}.txt", f"{f}.md"])
        checks.append({"check": f"存在 {f}", "passed": exists, "weight": 5})
        if not exists:
            score -= 5

    # Skills 检查
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        skills = [d for d in skills_dir.iterdir() if d.is_dir()]
        valid_skills = [d for d in skills if (d / "SKILL.md").exists()]
        checks.append({
            "check": f"Skills 有效 ({len(valid_skills)}/{len(skills)})",
            "passed": len(valid_skills) == len(skills),
            "weight": 10,
        })
        if len(valid_skills) != len(skills):
            score -= 10
    else:
        checks.append({"check": "无 skills 目录（纯 MCP 插件）", "passed": True, "weight": 0})

    return {"score": max(0, score), "checks": checks}


def check_security(plugin_dir: Path) -> dict:
    """检查安全健康"""
    checks = []
    score = 100

    # 硬编码密钥检测
    secret_patterns = ["api_key", "password", "secret", "token", "private_key"]
    found_secrets = []
    for f in plugin_dir.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".ts", ".json", ".env") and "__pycache__" not in str(f):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore").lower()
                for pattern in secret_patterns:
                    if pattern in content and "=" in content:
                        # 简单检测：如果有赋值且值看起来像密钥
                        import re
                        if re.search(rf'{pattern}\s*=\s*["\'][^"\']{{8,}}["\']', content):
                            found_secrets.append(str(f.relative_to(plugin_dir)))
                            break
            except Exception:
                pass

    checks.append({
        "check": "无硬编码密钥",
        "passed": len(found_secrets) == 0,
        "weight": 30,
        "details": found_secrets[:5] if found_secrets else [],
    })
    if found_secrets:
        score -= 30

    # 危险代码检测
    danger_patterns = ["eval(", "exec(", "shell=True", "os.system(", "pickle.loads("]
    found_danger = []
    for f in plugin_dir.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            for pattern in danger_patterns:
                if pattern in content:
                    found_danger.append(f"{f.relative_to(plugin_dir)}: {pattern}")
        except Exception:
            pass

    checks.append({
        "check": "无危险代码模式",
        "passed": len(found_danger) == 0,
        "weight": 20,
        "details": found_danger[:5] if found_danger else [],
    })
    if found_danger:
        score -= 20

    # 路径安全
    has_path_traversal = False
    for f in plugin_dir.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            if "../" in content and "open(" in content:
                has_path_traversal = True
                break
        except Exception:
            pass

    checks.append({"check": "无路径穿越风险", "passed": not has_path_traversal, "weight": 15})
    if has_path_traversal:
        score -= 15

    return {"score": max(0, score), "checks": checks}


def check_mcp_health(plugin_dir: Path) -> dict:
    """检查 MCP 健康"""
    checks = []
    score = 100

    mcp_json = plugin_dir / "mcp.json"
    if not mcp_json.exists():
        return {"score": 100, "checks": [{"check": "无 MCP 服务器（纯 Skill 插件）", "passed": True, "weight": 0}]}

    try:
        mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
        servers = mcp.get("mcpServers", {})

        checks.append({"check": f"MCP 服务器数量: {len(servers)}", "passed": len(servers) > 0, "weight": 10})

        for name, config in servers.items():
            # command 检查
            command = config.get("command", "")
            checks.append({
                "check": f"服务器 {name}: command 是单个 token",
                "passed": " " not in command and ";" not in command,
                "weight": 15,
            })
            if " " in command or ";" in command:
                score -= 15

            # 传输类型检查
            transport = config.get("type", "stdio")
            checks.append({
                "check": f"服务器 {name}: 传输类型有效 ({transport})",
                "passed": transport in ("stdio", "streamable-http", "sse"),
                "weight": 10,
            })
            if transport not in ("stdio", "streamable-http", "sse"):
                score -= 10

            # 密钥检查
            headers = config.get("headers", {})
            has_secret_in_header = any(
                k.lower() in ("authorization", "x-api-key", "api-key") for k in headers
            )
            checks.append({
                "check": f"服务器 {name}: 无硬编码 header 密钥",
                "passed": not has_secret_in_header,
                "weight": 20,
            })
            if has_secret_in_header:
                score -= 20

    except json.JSONDecodeError:
        checks.append({"check": "mcp.json 是有效 JSON", "passed": False, "weight": 50})
        score -= 50

    return {"score": max(0, score), "checks": checks}


def check_maintainability(plugin_dir: Path) -> dict:
    """检查可维护性"""
    checks = []
    score = 100

    # 测试
    has_tests = (plugin_dir / "tests").is_dir() or any(
        f.name.startswith("test_") for f in plugin_dir.rglob("*.py")
    )
    checks.append({"check": "有测试", "passed": has_tests, "weight": 15})
    if not has_tests:
        score -= 15

    # CI/CD
    has_ci = (plugin_dir / ".github" / "workflows").is_dir()
    checks.append({"check": "有 CI/CD 配置", "passed": has_ci, "weight": 10})
    if not has_ci:
        score -= 10

    # 文档
    doc_count = len(list(plugin_dir.rglob("*.md")))
    checks.append({"check": f"文档文件数: {doc_count}", "passed": doc_count >= 1, "weight": 10})
    if doc_count < 1:
        score -= 10

    # 代码注释比例
    total_lines = 0
    comment_lines = 0
    for f in plugin_dir.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            for line in content.split("\n"):
                total_lines += 1
                if line.strip().startswith("#") or line.strip().startswith('"""'):
                    comment_lines += 1
        except Exception:
            pass

    comment_ratio = round(comment_lines / total_lines * 100, 1) if total_lines > 0 else 0
    checks.append({
        "check": f"注释比例: {comment_ratio}%",
        "passed": comment_ratio >= 5,
        "weight": 10,
    })
    if comment_ratio < 5:
        score -= 10

    return {"score": max(0, score), "checks": checks}


def main():
    parser = argparse.ArgumentParser(description="插件健康诊断工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--deep", action="store_true", help="深度诊断")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--output", help="输出报告到文件")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    # 执行各项检查
    structure = check_structure(plugin_dir)
    security = check_security(plugin_dir)
    mcp = check_mcp_health(plugin_dir)
    maintainability = check_maintainability(plugin_dir)

    # 计算总体健康度（加权平均）
    dimensions = [
        ("结构", structure["score"], 0.3),
        ("安全", security["score"], 0.35),
        ("MCP", mcp["score"], 0.2),
        ("可维护性", maintainability["score"], 0.15),
    ]
    overall = round(sum(score * weight for _, score, weight in dimensions), 1)

    # 健康等级
    if overall >= 90:
        grade = "A+ (优秀)"
    elif overall >= 80:
        grade = "A (良好)"
    elif overall >= 70:
        grade = "B (合格)"
    elif overall >= 60:
        grade = "C (需改进)"
    else:
        grade = "D (不合格)"

    report = {
        "plugin": plugin_dir.name,
        "overall_score": overall,
        "grade": grade,
        "dimensions": {
            "structure": structure,
            "security": security,
            "mcp": mcp,
            "maintainability": maintainability,
        },
        "recommendations": [],
    }

    # 生成建议
    for dim_name, dim_data in [("结构", structure), ("安全", security), ("MCP", mcp), ("可维护性", maintainability)]:
        for check in dim_data["checks"]:
            if not check["passed"] and check.get("weight", 0) > 0:
                report["recommendations"].append({
                    "dimension": dim_name,
                    "issue": check["check"],
                    "severity": "high" if check["weight"] >= 20 else "medium",
                })

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"插件健康诊断: {plugin_dir.name}")
        print("=" * 60)
        print(f"\n总体健康度: {overall}/100")
        print(f"等级: {grade}")
        print()

        for dim_name, dim_key in [("结构", "structure"), ("安全", "security"), ("MCP", "mcp"), ("可维护性", "maintainability")]:
            dim = report["dimensions"][dim_key]
            print(f"【{dim_name}】 {dim['score']}/100")
            for check in dim["checks"]:
                icon = "✅" if check["passed"] else "❌"
                print(f"  {icon} {check['check']}")
            print()

        if report["recommendations"]:
            print(f"【改进建议】({len(report['recommendations'])} 条)")
            for r in report["recommendations"]:
                icon = "🔴" if r["severity"] == "high" else "🟡"
                print(f"  {icon} [{r['dimension']}] {r['issue']}")
            print()

        print("=" * 60)
        if overall >= 80:
            print("✅ 插件健康状态良好")
        elif overall >= 60:
            print("⚠️  插件需要改进")
        else:
            print("❌ 插件健康状态不佳，建议立即修复")
        print("=" * 60)

    sys.exit(0 if overall >= 60 else 1)


if __name__ == "__main__":
    main()
