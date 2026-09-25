#!/usr/bin/env python3
"""
插件深度分析器

对插件进行全面的架构、安全、性能、可维护性分析，给出改进建议。

用法:
    python3 scripts/analyze_plugin.py <插件目录>
    python3 scripts/analyze_plugin.py <插件目录> --deep
    python3 scripts/analyze_plugin.py <插件目录> --json
    python3 scripts/analyze_plugin.py <插件目录> --output analysis-report.json
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path


def analyze_structure(plugin_dir: Path) -> dict:
    """分析插件结构"""
    result = {
        "has_plugin_json": (plugin_dir / "plugin.json").exists(),
        "has_mcp_json": (plugin_dir / "mcp.json").exists(),
        "has_readme": (plugin_dir / "README.md").exists(),
        "has_license": any((plugin_dir / f).exists() for f in ["LICENSE", "LICENSE.txt", "LICENSE.md"]),
        "skills_count": 0,
        "mcp_servers_count": 0,
        "total_files": 0,
        "total_size": 0,
        "file_types": {},
    }

    # Skills
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        result["skills_count"] = len([d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])

    # MCP 服务器
    mcp_json = plugin_dir / "mcp.json"
    if mcp_json.exists():
        try:
            mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
            result["mcp_servers_count"] = len(mcp.get("mcpServers", {}))
        except Exception:
            pass

    # 文件统计
    for f in plugin_dir.rglob("*"):
        if f.is_file() and "__pycache__" not in str(f) and ".git" not in str(f):
            result["total_files"] += 1
            result["total_size"] += f.stat().st_size
            ext = f.suffix.lower() or "no_extension"
            result["file_types"][ext] = result["file_types"].get(ext, 0) + 1

    return result


def analyze_code_quality(plugin_dir: Path) -> dict:
    """分析代码质量"""
    result = {
        "python_files": 0,
        "total_python_lines": 0,
        "avg_function_length": 0,
        "functions": [],
        "todo_count": 0,
        "fixme_count": 0,
        "hack_count": 0,
        "empty_except": 0,
        "long_functions": [],
    }

    functions = []
    for py_file in plugin_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        result["python_files"] += 1
        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            result["total_python_lines"] += len(lines)

            # 统计 TODO/FIXME/HACK
            result["todo_count"] += len(re.findall(r"TODO", content))
            result["fixme_count"] += len(re.findall(r"FIXME", content))
            result["hack_count"] += len(re.findall(r"HACK|XXX", content))

            # 统计空 except
            result["empty_except"] += len(re.findall(r"except\s*:", content))

            # 分析函数长度
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_lines = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
                    functions.append({
                        "name": node.name,
                        "file": str(py_file.relative_to(plugin_dir)),
                        "lines": func_lines,
                    })
                    if func_lines > 50:
                        result["long_functions"].append({
                            "name": node.name,
                            "file": str(py_file.relative_to(plugin_dir)),
                            "lines": func_lines,
                        })
        except Exception:
            pass

    if functions:
        result["avg_function_length"] = round(sum(f["lines"] for f in functions) / len(functions), 1)
    result["functions"] = len(functions)

    return result


def analyze_security(plugin_dir: Path) -> dict:
    """分析安全性"""
    result = {
        "hardcoded_secrets": [],
        "dangerous_patterns": [],
        "path_traversal_risks": [],
        "issues": [],
    }

    secret_patterns = [
        (r"api[_-]?key\s*=\s*['\"][^'\"]{20,}['\"]", "API Key"),
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Password"),
        (r"token\s*=\s*['\"][^'\"]{20,}['\"]", "Token"),
        (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private Key"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Token"),
        (r"sk-[a-zA-Z0-9]{48}", "OpenAI Key"),
    ]

    danger_patterns = [
        (r"\beval\s*\(", "eval() 调用"),
        (r"\bexec\s*\(", "exec() 调用"),
        (r"shell\s*=\s*True", "shell=True"),
        (r"\bos\.system\s*\(", "os.system() 调用"),
        (r"\bpickle\.loads?\s*\(", "pickle 反序列化"),
        (r"\bsubprocess\.call\s*\(.*shell", "subprocess shell 调用"),
    ]

    for f in plugin_dir.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".ts", ".json", ".env") and "__pycache__" not in str(f):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(f.relative_to(plugin_dir))

                for pattern, desc in secret_patterns:
                    if re.search(pattern, content):
                        result["hardcoded_secrets"].append({"file": rel_path, "type": desc})

                for pattern, desc in danger_patterns:
                    if re.search(pattern, content):
                        result["dangerous_patterns"].append({"file": rel_path, "type": desc})

                # 路径穿越风险
                if ".." in content and ("open(" in content or "Path(" in content):
                    if "../" in content:
                        result["path_traversal_risks"].append({"file": rel_path})
            except Exception:
                pass

    result["issues"] = (
        result["hardcoded_secrets"] + result["dangerous_patterns"] + result["path_traversal_risks"]
    )

    return result


def analyze_maintainability(plugin_dir: Path) -> dict:
    """分析可维护性"""
    result = {
        "has_tests": (plugin_dir / "tests").is_dir(),
        "has_ci": (plugin_dir / ".github" / "workflows").is_dir(),
        "has_changelog": (plugin_dir / "CHANGELOG.md").exists(),
        "has_contributing": (plugin_dir / "CONTRIBUTING.md").exists(),
        "has_security_md": (plugin_dir / "SECURITY.md").exists(),
        "comment_ratio": 0,
        "documentation_files": 0,
    }

    # 文档文件统计
    for f in plugin_dir.rglob("*.md"):
        if f.is_file():
            result["documentation_files"] += 1

    # 注释比例（Python 文件）
    total_lines = 0
    comment_lines = 0
    for py_file in plugin_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            for line in content.split("\n"):
                total_lines += 1
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    comment_lines += 1
        except Exception:
            pass

    if total_lines > 0:
        result["comment_ratio"] = round(comment_lines / total_lines * 100, 1)

    return result


def generate_recommendations(structure: dict, code_quality: dict, security: dict, maintainability: dict) -> list:
    """生成改进建议"""
    recommendations = []

    # 结构建议
    if not structure["has_readme"]:
        recommendations.append({"priority": "high", "category": "structure", "suggestion": "添加 README.md"})
    if not structure["has_license"]:
        recommendations.append({"priority": "high", "category": "structure", "suggestion": "添加 LICENSE 文件"})
    if structure["skills_count"] == 0:
        recommendations.append({"priority": "medium", "category": "structure", "suggestion": "插件没有 Skill，考虑添加至少一个 Skill"})

    # 代码质量建议
    if code_quality["long_functions"]:
        recommendations.append({
            "priority": "medium",
            "category": "code-quality",
            "suggestion": f"有 {len(code_quality['long_functions'])} 个函数超过 50 行，建议拆分",
        })
    if code_quality["empty_except"] > 0:
        recommendations.append({
            "priority": "high",
            "category": "code-quality",
            "suggestion": f"发现 {code_quality['empty_except']} 个空 except，建议添加具体异常处理",
        })
    if code_quality["todo_count"] > 5:
        recommendations.append({
            "priority": "low",
            "category": "code-quality",
            "suggestion": f"有 {code_quality['todo_count']} 个 TODO，建议跟踪处理",
        })

    # 安全建议
    if security["hardcoded_secrets"]:
        recommendations.append({
            "priority": "critical",
            "category": "security",
            "suggestion": f"发现 {len(security['hardcoded_secrets'])} 处硬编码密钥，必须移除",
        })
    if security["dangerous_patterns"]:
        recommendations.append({
            "priority": "high",
            "category": "security",
            "suggestion": f"发现 {len(security['dangerous_patterns'])} 处危险代码模式，建议审查",
        })

    # 可维护性建议
    if not maintainability["has_tests"]:
        recommendations.append({"priority": "medium", "category": "maintainability", "suggestion": "添加单元测试"})
    if not maintainability["has_ci"]:
        recommendations.append({"priority": "low", "category": "maintainability", "suggestion": "添加 CI/CD 配置"})
    if maintainability["comment_ratio"] < 10:
        recommendations.append({
            "priority": "low",
            "category": "maintainability",
            "suggestion": f"注释比例仅 {maintainability['comment_ratio']}%，建议增加注释",
        })

    # 按优先级排序
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda x: priority_order.get(x["priority"], 99))

    return recommendations


def main():
    parser = argparse.ArgumentParser(description="插件深度分析器")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--deep", action="store_true", help="深度分析（包含更多维度）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--output", help="输出报告到文件")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    # 执行分析
    structure = analyze_structure(plugin_dir)
    code_quality = analyze_code_quality(plugin_dir)
    security = analyze_security(plugin_dir)
    maintainability = analyze_maintainability(plugin_dir)
    recommendations = generate_recommendations(structure, code_quality, security, maintainability)

    # 计算总体评分
    score = 100
    if not structure["has_readme"]:
        score -= 5
    if not structure["has_license"]:
        score -= 5
    if security["hardcoded_secrets"]:
        score -= 20
    if security["dangerous_patterns"]:
        score -= 10
    if code_quality["empty_except"]:
        score -= 5
    if not maintainability["has_tests"]:
        score -= 10
    score = max(0, score)

    report = {
        "plugin": plugin_dir.name,
        "overall_score": score,
        "structure": structure,
        "code_quality": code_quality,
        "security": security,
        "maintainability": maintainability,
        "recommendations": recommendations,
    }

    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"插件深度分析报告: {plugin_dir.name}")
        print("=" * 60)
        print(f"\n总体评分: {score}/100")
        if score >= 90:
            print("评级: 🏆 优秀")
        elif score >= 75:
            print("评级: ✅ 良好")
        elif score >= 60:
            print("评级: ⚠️ 合格")
        else:
            print("评级: ❌ 需要改进")

        print(f"\n【结构】")
        print(f"  文件数: {structure['total_files']}, 大小: {structure['total_size']} bytes")
        print(f"  Skills: {structure['skills_count']}, MCP 服务器: {structure['mcp_servers_count']}")
        print(f"  README: {'✅' if structure['has_readme'] else '❌'}, LICENSE: {'✅' if structure['has_license'] else '❌'}")

        print(f"\n【代码质量】")
        print(f"  Python 文件: {code_quality['python_files']}, 总行数: {code_quality['total_python_lines']}")
        print(f"  函数数: {code_quality['functions']}, 平均长度: {code_quality['avg_function_length']} 行")
        print(f"  长函数(>50行): {len(code_quality['long_functions'])}")
        print(f"  TODO: {code_quality['todo_count']}, FIXME: {code_quality['fixme_count']}")
        print(f"  空 except: {code_quality['empty_except']}")

        print(f"\n【安全】")
        print(f"  硬编码密钥: {len(security['hardcoded_secrets'])}")
        print(f"  危险代码模式: {len(security['dangerous_patterns'])}")
        print(f"  路径穿越风险: {len(security['path_traversal_risks'])}")

        print(f"\n【可维护性】")
        print(f"  测试: {'✅' if maintainability['has_tests'] else '❌'}")
        print(f"  CI/CD: {'✅' if maintainability['has_ci'] else '❌'}")
        print(f"  文档文件: {maintainability['documentation_files']} 个")
        print(f"  注释比例: {maintainability['comment_ratio']}%")

        if recommendations:
            print(f"\n【改进建议】({len(recommendations)} 条)")
            for r in recommendations[:10]:
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(r["priority"], "⚪")
                print(f"  {icon} [{r['priority'].upper()}] {r['suggestion']}")

        print("\n" + "=" * 60)

    sys.exit(0 if score >= 60 else 1)


if __name__ == "__main__":
    main()
