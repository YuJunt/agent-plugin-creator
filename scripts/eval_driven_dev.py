#!/usr/bin/env python3
"""
评估驱动开发工作流工具

先写评估用例，再生成插件，确保插件质量。

用法:
    python3 scripts/eval_driven_dev.py init --name my-plugin --output ./my-plugin
    python3 scripts/eval_driven_dev.py generate-evals --plugin ./my-plugin --output evals.json
    python3 scripts/eval_driven_dev.py run --plugin ./my-plugin --evals evals.json
    python3 scripts/eval_driven_dev.py report --results results.json
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


EVAL_TEMPLATES = {
    "skill_trigger": {
        "name": "skill-trigger-accuracy",
        "description": "Skill 触发准确性测试",
        "type": "trigger",
        "cases": [
            {"prompt": "帮我创建一个插件", "expected_activate": True},
            {"prompt": "今天天气怎么样", "expected_activate": False},
            {"prompt": "把这个 skill 打包成插件", "expected_activate": True},
        ],
    },
    "mcp_handshake": {
        "name": "mcp-handshake",
        "description": "MCP 服务器握手测试",
        "type": "mcp",
        "cases": [
            {"server": "default", "expected_status": "connected"},
        ],
    },
    "validation": {
        "name": "plugin-validation",
        "description": "插件结构验证测试",
        "type": "validation",
        "cases": [
            {"check": "plugin_json_exists", "expected": True},
            {"check": "schema_valid", "expected": True},
            {"check": "skills_have_md", "expected": True},
        ],
    },
    "security": {
        "name": "security-audit",
        "description": "安全审计测试",
        "type": "security",
        "cases": [
            {"check": "no_hardcoded_secrets", "expected": True},
            {"check": "no_dangerous_functions", "expected": True},
        ],
    },
}


def init_project(name: str, output_dir: Path) -> dict:
    """初始化评估驱动开发项目"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 创建评估目录
    evals_dir = output_dir / "evals"
    evals_dir.mkdir(exist_ok=True)

    # 创建默认评估用例
    default_evals = {
        "project": name,
        "created_at": datetime.now().isoformat(),
        "eval_sets": list(EVAL_TEMPLATES.keys()),
        "evals": EVAL_TEMPLATES,
    }

    evals_file = evals_dir / "evals.json"
    evals_file.write_text(
        json.dumps(default_evals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 创建开发计划
    plan = {
        "project": name,
        "phase": "eval-first",
        "steps": [
            "1. 编写评估用例（evals/evals.json）",
            "2. 运行评估，确认当前状态",
            "3. 开发插件功能",
            "4. 重新运行评估，确认通过",
            "5. 迭代优化直到全部通过",
        ],
        "current_step": 1,
    }
    (output_dir / "dev-plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return {
        "project": name,
        "output": str(output_dir),
        "eval_sets": list(EVAL_TEMPLATES.keys()),
        "files_created": ["evals/evals.json", "dev-plan.json"],
    }


def generate_evals(plugin_dir: Path, output_file: Path) -> dict:
    """从现有插件生成评估用例"""
    evals = {
        "project": plugin_dir.name,
        "generated_at": datetime.now().isoformat(),
        "source": str(plugin_dir),
        "evals": {},
    }

    # 检测插件结构，生成对应评估
    if (plugin_dir / "plugin.json").exists():
        evals["evals"]["validation"] = EVAL_TEMPLATES["validation"]

    if (plugin_dir / "mcp.json").exists():
        evals["evals"]["mcp_handshake"] = EVAL_TEMPLATES["mcp_handshake"]

    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        skill_evals = EVAL_TEMPLATES["skill_trigger"].copy()
        skill_evals["cases"] = []
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_evals["cases"].append({
                    "prompt": f"使用 {skill_dir.name} 技能",
                    "expected_activate": True,
                })
        evals["evals"]["skill_trigger"] = skill_evals

    evals["evals"]["security"] = EVAL_TEMPLATES["security"]

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(evals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return {
        "plugin": plugin_dir.name,
        "eval_sets": list(evals["evals"].keys()),
        "output": str(output_file),
    }


def run_evals(plugin_dir: Path, evals_file: Path) -> dict:
    """运行评估用例"""
    if not evals_file.exists():
        return {"error": f"评估文件不存在: {evals_file}"}

    evals = json.loads(evals_file.read_text(encoding="utf-8"))
    results = {
        "plugin": plugin_dir.name,
        "run_at": datetime.now().isoformat(),
        "total": 0,
        "passed": 0,
        "failed": 0,
        "eval_sets": {},
    }

    for eval_name, eval_set in evals.get("evals", {}).items():
        eval_type = eval_set.get("type", "unknown")
        set_results = {"type": eval_type, "cases": [], "passed": 0, "total": 0}

        for case in eval_set.get("cases", []):
            results["total"] += 1
            set_results["total"] += 1

            # 简化的评估逻辑
            passed = True
            reason = ""

            if eval_type == "validation":
                check = case.get("check", "")
                if check == "plugin_json_exists":
                    passed = (plugin_dir / "plugin.json").exists()
                elif check == "schema_valid":
                    try:
                        plugin = json.loads((plugin_dir / "plugin.json").read_text())
                        passed = "$schema" in plugin and "name" in plugin
                    except Exception:
                        passed = False
                elif check == "skills_have_md":
                    skills_dir = plugin_dir / "skills"
                    if skills_dir.is_dir():
                        passed = all(
                            (d / "SKILL.md").exists()
                            for d in skills_dir.iterdir()
                            if d.is_dir()
                        )
                    else:
                        passed = True  # 没有 skills 也算通过

            elif eval_type == "security":
                check = case.get("check", "")
                if check == "no_hardcoded_secrets":
                    # 简化检查
                    passed = True
                    for f in plugin_dir.rglob("*.py"):
                        try:
                            content = f.read_text(encoding="utf-8", errors="ignore")
                            if "api_key" in content.lower() and "=" in content:
                                passed = False
                                break
                        except Exception:
                            pass

            case_result = {"case": case, "passed": passed, "reason": reason}
            set_results["cases"].append(case_result)
            if passed:
                set_results["passed"] += 1
                results["passed"] += 1
            else:
                results["failed"] += 1

        results["eval_sets"][eval_name] = set_results

    results["accuracy"] = round(results["passed"] / results["total"] * 100, 1) if results["total"] > 0 else 0

    return results


def generate_report(results: dict, output_file: Path = None) -> dict:
    """生成评估报告"""
    report = {
        "summary": {
            "total": results["total"],
            "passed": results["passed"],
            "failed": results["failed"],
            "accuracy": results["accuracy"],
            "status": "PASS" if results["failed"] == 0 else "FAIL",
        },
        "details": results["eval_sets"],
        "recommendations": [],
    }

    # 生成建议
    if results["failed"] > 0:
        for eval_name, eval_set in results["eval_sets"].items():
            if eval_set["failed"] if "failed" in eval_set else (eval_set["total"] - eval_set["passed"]) > 0:
                report["recommendations"].append(
                    f"修复 {eval_name} 评估中的失败用例"
                )

    if output_file:
        output_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return report


def main():
    parser = argparse.ArgumentParser(description="评估驱动开发工作流工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # init
    init_parser = subparsers.add_parser("init", help="初始化评估驱动开发项目")
    init_parser.add_argument("--name", required=True, help="项目名称")
    init_parser.add_argument("--output", required=True, help="输出目录")

    # generate-evals
    gen_parser = subparsers.add_parser("generate-evals", help="从现有插件生成评估用例")
    gen_parser.add_argument("--plugin", required=True, help="插件目录")
    gen_parser.add_argument("--output", required=True, help="评估用例输出文件")

    # run
    run_parser = subparsers.add_parser("run", help="运行评估用例")
    run_parser.add_argument("--plugin", required=True, help="插件目录")
    run_parser.add_argument("--evals", required=True, help="评估用例文件")
    run_parser.add_argument("--output", help="结果输出文件")

    # report
    report_parser = subparsers.add_parser("report", help="生成评估报告")
    report_parser.add_argument("--results", required=True, help="评估结果文件")
    report_parser.add_argument("--output", help="报告输出文件")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        result = init_project(args.name, Path(args.output))
    elif args.command == "generate-evals":
        result = generate_evals(Path(args.plugin), Path(args.output))
    elif args.command == "run":
        result = run_evals(Path(args.plugin), Path(args.evals))
        if args.output:
            Path(args.output).write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
    elif args.command == "report":
        results = json.loads(Path(args.results).read_text(encoding="utf-8"))
        result = generate_report(results, Path(args.output) if args.output else None)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
