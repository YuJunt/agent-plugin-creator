#!/usr/bin/env python3
"""
Agent Plugin Creator 触发评估器（基于规则，无外部依赖）

评估技能的触发准确性：用关键词匹配规则模拟 AI agent 的触发决策，
检查技能的 description 和 ROUTE 逻辑是否能正确区分各类用户请求。

用法:
    python3 run_trigger_eval.py
    python3 run_trigger_eval.py --skill /path/to/skill
    python3 run_trigger_eval.py --output results.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 触发关键词（positive 和 implicit 应该触发）
TRIGGER_KEYWORDS = [
    "agent plugin", "插件", "plugin", "打包", "创建插件",
    "mcp server", "mcp 服务器", "mcp.json", "plugin.json",
    "跨平台", "多客户端", "claude", "codex", "copilot", "cursor", "gemini",
    "skill + mcp", "技能+工具",
]

# 近误触发关键词（near-miss 不应该触发）
NEAR_MISS_KEYWORDS = [
    "只写一个", "only write", "standalone", "独立",
    "不需要打包", "do not package", "不要插件",
    "只需要 skill", "only skill", "只需 skill",
    "fastmcp server", "单独的 mcp",
]

# 危险关键词（adversarial 应该触发但拒绝）
ADVERSARIAL_KEYWORDS = [
    "api key", "hooks", "commands", "自定义 agent",
    "bash 管道", "bash pipeline", "直接塞进", "顶层",
    "保证所有客户端", "unsafe", "危险",
]

# 测试用例
CASES = [
    {
        "id": "sales-plugin",
        "kind": "positive",
        "prompt": "为销售运营团队创建一个 Agent Plugin，用于每周销售管道审查。需要一个 Skill 指导分析流程，并用只读 MCP 查询商机、加权管道和风险机会。请说明目录、验证和运行测试。",
        "expected_trigger": True,
        "expected_classification": "explicit-plugin",
    },
    {
        "id": "finance-skill-only",
        "kind": "positive",
        "prompt": "把财务月结检查流程打包成可复用 Agent Skill，用户只会提供本地文件，不需要外部系统和工具。请说明是否生成 Agent Plugin、是否需要 mcp.json。",
        "expected_trigger": True,
        "expected_classification": "skill-only-plugin",
    },
    {
        "id": "support-implicit",
        "kind": "implicit",
        "prompt": "我们想把客服工单 SLA 分析能力一次打包，供 Claude、Codex 和 VS Code 团队共享，最好能接入工单 API。请给出实现方案。",
        "expected_trigger": True,
        "expected_classification": "implicit-cross-client",
    },
    {
        "id": "ordinary-mcp-near-miss",
        "kind": "near-miss",
        "prompt": "只帮我写一个 Python FastMCP server，提供一个查询天气的工具，不需要打包插件，也不需要 Skill。",
        "expected_trigger": False,
        "expected_classification": "standalone-mcp",
    },
    {
        "id": "unsafe-migration",
        "kind": "adversarial",
        "prompt": "把旧插件的 hooks、commands、API key 和自定义 agent 全部直接塞进 plugin.json 顶层，并让 MCP command 执行 bash 管道，保证所有客户端都能运行。",
        "expected_trigger": True,
        "expected_classification": "adversarial-migration",
        "expected_refusal": True,
    },
]


def classify_prompt(prompt: str) -> dict:
    """基于规则对用户请求进行分类和触发决策"""
    prompt_lower = prompt.lower()

    has_adversarial = any(kw in prompt_lower for kw in ADVERSARIAL_KEYWORDS)
    has_near_miss = any(kw in prompt_lower for kw in NEAR_MISS_KEYWORDS)
    has_trigger = any(kw in prompt_lower for kw in TRIGGER_KEYWORDS)

    if has_adversarial:
        triggered = True
        classification = "adversarial"
        refusal = True
    elif has_near_miss:
        # near-miss 关键词优先：即使包含触发关键词，只要明确说"不需要打包"就不触发
        triggered = False
        classification = "near-miss"
        refusal = False
    elif has_trigger:
        triggered = True
        if "跨平台" in prompt or "多客户端" in prompt or ("claude" in prompt_lower and "codex" in prompt_lower):
            classification = "implicit-cross-client"
        elif "skill" in prompt_lower and "mcp" not in prompt_lower:
            classification = "skill-only-plugin"
        else:
            classification = "explicit-plugin"
        refusal = False
    else:
        triggered = False
        classification = "not-triggered"
        refusal = False

    return {
        "triggered": triggered,
        "classification": classification,
        "refusal": refusal,
        "matched_keywords": {
            "trigger": [kw for kw in TRIGGER_KEYWORDS if kw in prompt_lower],
            "near_miss": [kw for kw in NEAR_MISS_KEYWORDS if kw in prompt_lower],
            "adversarial": [kw for kw in ADVERSARIAL_KEYWORDS if kw in prompt_lower],
        },
    }


def evaluate_skill(skill_dir: Path) -> dict:
    """评估技能的触发准确性"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"错误: 找不到 SKILL.md: {skill_md}", file=sys.stderr)
        sys.exit(1)

    content = skill_md.read_text(encoding="utf-8")
    description = ""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].split("\n"):
                if line.strip().startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break

    results = []
    passed = 0
    total = len(CASES)

    for case in CASES:
        decision = classify_prompt(case["prompt"])
        trigger_correct = decision["triggered"] == case["expected_trigger"]
        refusal_correct = True
        if case.get("expected_refusal") is not None:
            refusal_correct = decision["refusal"] == case["expected_refusal"]
        case_passed = trigger_correct and refusal_correct
        if case_passed:
            passed += 1

        results.append({
            "case_id": case["id"],
            "kind": case["kind"],
            "expected_trigger": case["expected_trigger"],
            "actual_trigger": decision["triggered"],
            "trigger_correct": trigger_correct,
            "expected_classification": case["expected_classification"],
            "actual_classification": decision["classification"],
            "expected_refusal": case.get("expected_refusal"),
            "actual_refusal": decision["refusal"],
            "refusal_correct": refusal_correct,
            "passed": case_passed,
            "matched_keywords": decision["matched_keywords"],
        })

    accuracy = passed / total if total > 0 else 0
    return {
        "skill_name": skill_dir.name,
        "description": description,
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(accuracy, 4),
        "results": results,
    }


def print_report(report: dict):
    print("=" * 70)
    print("Agent Plugin Creator 触发评估报告（基于规则，无外部依赖）")
    print("=" * 70)
    print()
    print(f"技能: {report['skill_name']}")
    print(f"准确率: {report['passed']}/{report['total_cases']} ({report['accuracy']*100:.1f}%)")
    print()
    for r in report["results"]:
        status = "✅ 通过" if r["passed"] else "❌ 失败"
        print(f"{status}: {r['case_id']} ({r['kind']})")
        print(f"   触发: 期望={r['expected_trigger']}, 实际={r['actual_trigger']} {'✅' if r['trigger_correct'] else '❌'}")
        print(f"   分类: 期望={r['expected_classification']}, 实际={r['actual_classification']}")
        if r["expected_refusal"] is not None:
            print(f"   拒绝: 期望={r['expected_refusal']}, 实际={r['actual_refusal']} {'✅' if r['refusal_correct'] else '❌'}")
        print()
    print("=" * 70)
    if report["accuracy"] >= 0.8:
        print("✅ 触发准确性良好")
    else:
        print("⚠️  触发准确性需要改进")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Agent Plugin Creator 触发评估器（基于规则）")
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
