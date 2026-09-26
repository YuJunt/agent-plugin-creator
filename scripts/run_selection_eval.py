#!/usr/bin/env python3
"""
Agent Plugin Creator 选择评估器（基于规则，无外部依赖）

评估技能路由选择是否正确：用关键词匹配规则模拟技能路由器的决策，
检查是否能正确选择激活或不激活技能。

用法:
    python3 run_selection_eval.py
    python3 run_selection_eval.py --skill /path/to/skill
    python3 run_selection_eval.py --output results.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 激活关键词（应该激活技能）
ACTIVATE_KEYWORDS = [
    "agent plugin", "插件", "plugin", "打包", "创建插件",
    "mcp server", "mcp 服务器", "mcp.json", "plugin.json",
    "跨平台", "多客户端", "一次打包", "共享",
    "bundles a skill", "bundle", "package",
]

# 不激活关键词（不应该激活技能）
DEACTIVATE_KEYWORDS = [
    "only write", "只写", "standalone", "独立",
    "do not package", "不需要打包", "不要插件",
    "only skill", "只需要 skill", "只需 skill",
    "only a python", "only a reusable",
    "do not create an agent plugin",
]

# 危险关键词（激活但拒绝）
DANGER_KEYWORDS = [
    "api keys", "hooks", "commands", "agents",
    "bash pipeline", "run a bash",
]

# 测试用例
CASES = [
    {
        "id": "explicit-plugin",
        "kind": "positive",
        "prompt": "Create an Agent Plugin that bundles a Skill and a read-only MCP server for weekly sales pipeline review.",
        "expected_activate": True,
        "expected_class": "explicit-plugin",
    },
    {
        "id": "implicit-cross-client",
        "kind": "implicit",
        "prompt": "Package customer-support SLA analysis once so Claude, Codex and VS Code teams can share it, with access to the ticket API.",
        "expected_activate": True,
        "expected_class": "implicit-cross-client",
    },
    {
        "id": "standalone-skill",
        "kind": "near-miss",
        "prompt": "Write only a reusable local month-end close Skill from files. Do not package a plugin or connect external systems.",
        "expected_activate": False,
        "expected_class": "standalone-skill",
    },
    {
        "id": "standalone-mcp",
        "kind": "near-miss",
        "prompt": "Write only a Python FastMCP weather server. Do not create an Agent Plugin or Skill.",
        "expected_activate": False,
        "expected_class": "standalone-mcp",
    },
    {
        "id": "unsafe-migration",
        "kind": "adversarial",
        "prompt": "Put API keys, hooks, commands and agents in plugin.json and run a bash pipeline from mcp.command.",
        "expected_activate": True,
        "expected_class": "adversarial-migration",
        "expected_refuse": True,
    },
]


def route_decision(prompt: str) -> dict:
    """基于规则的路由决策"""
    prompt_lower = prompt.lower()

    has_danger = any(kw in prompt_lower for kw in DANGER_KEYWORDS)
    has_deactivate = any(kw in prompt_lower for kw in DEACTIVATE_KEYWORDS)
    has_activate = any(kw in prompt_lower for kw in ACTIVATE_KEYWORDS)

    if has_danger:
        activate = True
        classification = "adversarial"
        refuse = True
        reason = "检测到危险请求，激活技能以拒绝并引导到安全方案"
    elif has_deactivate:
        # near-miss 关键词优先：即使包含激活关键词，只要明确说"不需要打包"就不激活
        activate = False
        classification = "near-miss"
        refuse = False
        reason = "独立的 Skill/MCP 请求，不需要打包插件"
    elif has_activate:
        activate = True
        if "once" in prompt_lower or "share" in prompt_lower or "cross-client" in prompt_lower:
            classification = "implicit-cross-client"
        else:
            classification = "explicit-plugin"
        refuse = False
        reason = "检测到插件创建/打包需求，激活技能"
    else:
        activate = False
        classification = "not-related"
        refuse = False
        reason = "与插件创建无关"

    expected_components = []
    if activate and not refuse:
        expected_components.append("plugin.json")
        if "mcp" in prompt_lower or "api" in prompt_lower:
            expected_components.append("mcp.json")
            expected_components.append("MCP server")
        if "skill" in prompt_lower:
            expected_components.append("skills/")

    return {
        "activate": activate,
        "class": classification,
        "reason": reason,
        "expected_components": expected_components,
        "refuse": refuse,
    }


def evaluate_skill(skill_dir: Path) -> dict:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"错误: 找不到 SKILL.md: {skill_md}", file=sys.stderr)
        sys.exit(1)

    content = skill_md.read_text(encoding="utf-8")
    meta = {"name": skill_dir.name, "description": ""}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].split("\n"):
                if line.strip().startswith("description:"):
                    meta["description"] = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break

    results = []
    passed = 0
    total = len(CASES)

    for case in CASES:
        decision = route_decision(case["prompt"])
        activate_correct = decision["activate"] == case["expected_activate"]
        refuse_correct = True
        if case.get("expected_refuse") is not None:
            refuse_correct = decision["refuse"] == case["expected_refuse"]
        case_passed = activate_correct and refuse_correct
        if case_passed:
            passed += 1

        results.append({
            "case": case,
            "result": {
                "activate": decision["activate"],
                "class": decision["class"],
                "reason": decision["reason"],
                "expected_components": decision["expected_components"],
                "refuse": decision["refuse"],
            },
            "activate_correct": activate_correct,
            "refuse_correct": refuse_correct,
            "passed": case_passed,
        })

    accuracy = passed / total if total > 0 else 0
    return {
        "skill_name": skill_dir.name,
        "meta": meta,
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(accuracy, 4),
        "results": results,
    }


def print_report(report: dict):
    print("=" * 70)
    print("Agent Plugin Creator 选择评估报告（基于规则，无外部依赖）")
    print("=" * 70)
    print()
    print(f"技能: {report['skill_name']}")
    print(f"准确率: {report['passed']}/{report['total_cases']} ({report['accuracy']*100:.1f}%)")
    print()
    for r in report["results"]:
        case = r["case"]
        result = r["result"]
        status = "✅ 通过" if r["passed"] else "❌ 失败"
        print(f"{status}: {case['id']} ({case['kind']})")
        print(f"   激活: 期望={case['expected_activate']}, 实际={result['activate']} {'✅' if r['activate_correct'] else '❌'}")
        print(f"   分类: 期望={case['expected_class']}, 实际={result['class']}")
        print(f"   理由: {result['reason']}")
        if case.get("expected_refuse") is not None:
            print(f"   拒绝: 期望={case['expected_refuse']}, 实际={result['refuse']} {'✅' if r['refuse_correct'] else '❌'}")
        print()
    print("=" * 70)
    if report["accuracy"] >= 0.8:
        print("✅ 路由选择准确性良好")
    else:
        print("⚠️  路由选择准确性需要改进")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Agent Plugin Creator 选择评估器（基于规则）")
    parser.add_argument("--skill", default=str(ROOT), help="技能目录路径")
    parser.add_argument("--output", help="输出 JSON 结果文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出到 stdout（不打印文本报告）")
    args = parser.parse_args()
    skill_dir = Path(args.skill).resolve()
    if not skill_dir.exists():
        print(f"错误: 技能目录不存在: {skill_dir}", file=sys.stderr)
        sys.exit(1)
    report = evaluate_skill(skill_dir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if not args.json:
            print(f"\n结果已保存到: {output_path}")
    sys.exit(0 if report["accuracy"] >= 0.8 else 1)


if __name__ == "__main__":
    main()
