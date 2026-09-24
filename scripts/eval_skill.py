#!/usr/bin/env python3
"""
Agent Skill 质量评估工具

参考官方 skill-creator 的评估系统，提供：
  1. 评估用例模板生成
  2. 描述触发率优化查询生成（should-trigger / should-not-trigger）
  3. 评估结果统计与报告生成

用法:
    # 生成评估用例模板
    python3 eval_skill.py init --skill ./my-skill --output evals.json

    # 生成描述触发率优化查询
    python3 eval_skill.py describe-optimize --skill ./my-skill --output trigger_evals.json

    # 从评估结果生成报告
    python3 eval_skill.py report --evals evals.json --results results.json --output report.md

    # 列出评估用例
    python3 eval_skill.py list --evals evals.json

评估用例格式 (evals.json):
    {
      "skill_name": "my-skill",
      "evals": [
        {
          "id": "eval-001",
          "input": "用户输入文本",
          "expected": {
            "contains": ["应该包含的文本"],
            "not_contains": ["不应该包含的文本"],
            "regex": ["应该匹配的正则表达式"]
          },
          "description": "评估用例描述"
        }
      ]
    }

评估结果格式 (results.json):
    {
      "eval-001": {
        "with_skill": {"passed": true, "output": "实际输出", "assertions": [{"type": "contains", "passed": true, "detail": "..."}]},
        "without_skill": {"passed": false, "output": "实际输出", "assertions": [...]}
      }
    }
"""
import argparse
import json
import re
import sys
from pathlib import Path


def load_skill_info(skill_dir: Path) -> dict:
    """加载 skill 的基本信息"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"错误: 缺少 SKILL.md: {skill_md}", file=sys.stderr)
        sys.exit(1)
    content = skill_md.read_text(encoding="utf-8")
    info = {"name": skill_dir.name, "description": "", "body": ""}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            for line in fm.split("\n"):
                line = line.strip()
                if line.startswith("name:"):
                    info["name"] = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("description:"):
                    info["description"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            info["body"] = parts[2].strip()
    return info


def cmd_init(args):
    """生成评估用例模板"""
    skill_dir = Path(args.skill).resolve()
    info = load_skill_info(skill_dir)

    evals = {
        "skill_name": info["name"],
        "description": f"评估用例 for {info['name']}",
        "evals": [
            {
                "id": "eval-001",
                "description": "基本功能测试 - 验证 skill 能正确响应典型输入",
                "input": f"使用 {info['name']} 完成一个典型任务",
                "expected": {
                    "contains": ["期望的输出关键词"],
                    "not_contains": ["错误信息", "未实现"],
                    "regex": []
                }
            },
            {
                "id": "eval-002",
                "description": "边缘情况测试 - 验证 skill 能处理异常输入",
                "input": "空输入或异常输入",
                "expected": {
                    "contains": ["错误处理", "提示"],
                    "not_contains": ["崩溃", "traceback"],
                    "regex": []
                }
            },
            {
                "id": "eval-003",
                "description": "输出格式测试 - 验证 skill 输出符合预期格式",
                "input": "需要特定输出格式的任务",
                "expected": {
                    "contains": [],
                    "not_contains": [],
                    "regex": ["格式正则表达式"]
                }
            }
        ]
    }

    output = Path(args.output)
    output.write_text(json.dumps(evals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ 评估用例模板已生成: {output}")
    print(f"   Skill: {info['name']}")
    print(f"   用例数: {len(evals['evals'])}")
    print()
    print("下一步:")
    print("  1. 编辑 evals.json，添加实际的评估用例和期望断言")
    print("  2. 分别在 with_skill 和 without_skill 模式下运行每个用例")
    print("  3. 将结果记录到 results.json")
    print("  4. 运行: python3 eval_skill.py report --evals evals.json --results results.json")


def cmd_describe_optimize(args):
    """生成描述触发率优化查询"""
    skill_dir = Path(args.skill).resolve()
    info = load_skill_info(skill_dir)

    # 生成 should-trigger 查询（不同表达方式）
    should_trigger = [
        f"帮我用 {info['name']} 处理一下这个任务",
        f"我需要 {info['name']} 的功能来解决这个问题",
        f"使用 {info['name']} 技能",
        f"调用 {info['name']}",
        f"这个任务适合用 {info['name']} 吗？帮我做",
        f"按照 {info['name']} 的流程来",
        f"执行 {info['name']} 的步骤",
        f"用 {info['name']} 的方法",
        f"启动 {info['name']}",
        f"运行 {info['name']}",
    ]

    # 生成 should-not-trigger 查询（近邻但不应该触发）
    should_not_trigger = [
        f"什么是 {info['name']}？（只是询问概念，不需要执行）",
        f"{info['name']} 和其他工具有什么区别？（比较询问）",
        f"帮我写一个类似 {info['name']} 的脚本（开发任务，不是使用技能）",
        f"解释一下 {info['name']} 的原理（知识询问）",
        f"{info['name']} 的文档在哪里？（文档查找）",
        f"我可以不用 {info['name']} 完成这个任务吗？（替代方案询问）",
        f"评价一下 {info['name']} 的优缺点（评价询问）",
        f"{info['name']} 支持哪些平台？（技术询问）",
        f"如何卸载 {info['name']}？（管理任务）",
        f"{info['name']} 的最新版本是什么？（版本询问）",
    ]

    trigger_evals = {
        "skill_name": info["name"],
        "current_description": info["description"],
        "purpose": "描述触发率优化评估 - 验证 skill 的 description 能否正确区分应该触发和不应该触发的查询",
        "should_trigger": [
            {"query": q, "should_trigger": True, "notes": ""}
            for q in should_trigger
        ],
        "should_not_trigger": [
            {"query": q, "should_trigger": False, "notes": ""}
            for q in should_not_trigger
        ],
        "optimization_tips": [
            "description 应同时描述'做什么'和'什么时候用'",
            "包含具体的触发关键词和场景",
            "避免过于宽泛的描述（会导致误触发）",
            "避免过于狭窄的描述（会导致漏触发）",
            "参考官方 skill-creator 的 'pushy' 写法建议"
        ]
    }

    output = Path(args.output)
    output.write_text(json.dumps(trigger_evals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ 描述触发率优化查询已生成: {output}")
    print(f"   Skill: {info['name']}")
    print(f"   should-trigger 查询: {len(should_trigger)} 个")
    print(f"   should-not-trigger 查询: {len(should_not_trigger)} 个")
    print()
    print("下一步:")
    print("  1. 编辑 trigger_evals.json，根据实际场景调整查询")
    print("  2. 在 agent 中测试每个查询，记录是否正确触发")
    print("  3. 根据结果优化 SKILL.md 的 description 字段")


def cmd_list(args):
    """列出评估用例"""
    evals_path = Path(args.evals)
    if not evals_path.exists():
        print(f"错误: 评估用例文件不存在: {evals_path}", file=sys.stderr)
        sys.exit(1)
    evals = json.loads(evals_path.read_text(encoding="utf-8"))
    print(f"评估用例: {evals.get('skill_name', 'unknown')}")
    print(f"用例总数: {len(evals.get('evals', []))}")
    print()
    for e in evals.get("evals", []):
        print(f"  [{e['id']}] {e.get('description', '(无描述)')}")
        print(f"       输入: {e.get('input', '')[:60]}...")
        expected = e.get("expected", {})
        checks = []
        if expected.get("contains"):
            checks.append(f"contains:{len(expected['contains'])}")
        if expected.get("not_contains"):
            checks.append(f"not_contains:{len(expected['not_contains'])}")
        if expected.get("regex"):
            checks.append(f"regex:{len(expected['regex'])}")
        print(f"       断言: {', '.join(checks) if checks else '(无)'}")


def evaluate_assertions(output: str, expected: dict) -> list:
    """评估输出是否满足断言"""
    assertions = []
    for text in expected.get("contains", []):
        passed = text in output
        assertions.append({"type": "contains", "expected": text, "passed": passed,
                           "detail": f"{'✓' if passed else '✗'} 包含 '{text}'"})
    for text in expected.get("not_contains", []):
        passed = text not in output
        assertions.append({"type": "not_contains", "expected": text, "passed": passed,
                           "detail": f"{'✓' if passed else '✗'} 不包含 '{text}'"})
    for pattern in expected.get("regex", []):
        try:
            passed = bool(re.search(pattern, output))
            assertions.append({"type": "regex", "expected": pattern, "passed": passed,
                               "detail": f"{'✓' if passed else '✗'} 匹配正则 '{pattern}'"})
        except re.error as e:
            assertions.append({"type": "regex", "expected": pattern, "passed": False,
                               "detail": f"✗ 正则错误: {e}"})
    return assertions


def cmd_report(args):
    """从评估结果生成报告"""
    evals_path = Path(args.evals)
    results_path = Path(args.results)

    if not evals_path.exists():
        print(f"错误: 评估用例文件不存在: {evals_path}", file=sys.stderr)
        sys.exit(1)
    if not results_path.exists():
        print(f"错误: 评估结果文件不存在: {results_path}", file=sys.stderr)
        sys.exit(1)

    evals = json.loads(evals_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))

    # 统计
    total = len(evals.get("evals", []))
    with_skill_passed = 0
    without_skill_passed = 0
    eval_details = []

    for e in evals.get("evals", []):
        eid = e["id"]
        result = results.get(eid, {})
        with_result = result.get("with_skill", {})
        without_result = result.get("without_skill", {})

        with_passed = with_result.get("passed", False)
        without_passed = without_result.get("passed", False)

        if with_passed:
            with_skill_passed += 1
        if without_passed:
            without_skill_passed += 1

        eval_details.append({
            "id": eid,
            "description": e.get("description", ""),
            "with_skill_passed": with_passed,
            "without_skill_passed": without_passed,
            "improvement": with_passed and not without_passed,
        })

    # 生成报告
    lines = []
    lines.append(f"# Skill 评估报告: {evals.get('skill_name', 'unknown')}")
    lines.append("")
    lines.append("## 概览")
    lines.append("")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 评估用例总数 | {total} |")
    lines.append(f"| with_skill 通过数 | {with_skill_passed} ({with_skill_passed/total*100:.1f}%) |" if total else "| with_skill 通过数 | 0 |")
    lines.append(f"| without_skill 通过数 | {without_skill_passed} ({without_skill_passed/total*100:.1f}%) |" if total else "| without_skill 通过数 | 0 |")
    improvement_count = sum(1 for d in eval_details if d["improvement"])
    lines.append(f"| skill 带来提升的用例数 | {improvement_count} |")
    lines.append("")

    lines.append("## 用例详情")
    lines.append("")
    lines.append("| ID | 描述 | with_skill | without_skill | 提升 |")
    lines.append("|----|------|-----------|--------------|------|")
    for d in eval_details:
        ws = "✅ 通过" if d["with_skill_passed"] else "❌ 失败"
        wos = "✅ 通过" if d["without_skill_passed"] else "❌ 失败"
        imp = "⬆️ 是" if d["improvement"] else "—"
        lines.append(f"| {d['id']} | {d['description'][:40]} | {ws} | {wos} | {imp} |")
    lines.append("")

    lines.append("## 结论与建议")
    lines.append("")
    if total > 0:
        pass_rate = with_skill_passed / total * 100
        if pass_rate >= 80:
            lines.append(f"- ✅ Skill 整体表现良好，通过率 {pass_rate:.1f}%")
        elif pass_rate >= 50:
            lines.append(f"- ⚠️ Skill 通过率 {pass_rate:.1f}%，建议优化失败用例")
        else:
            lines.append(f"- ❌ Skill 通过率 {pass_rate:.1f}%，需要重大改进")

        if improvement_count > 0:
            lines.append(f"- ✅ Skill 在 {improvement_count} 个用例中带来了明显提升")
        else:
            lines.append("- ⚠️ Skill 未在任何用例中带来明显提升，建议重新评估 skill 的价值")

        failed = [d for d in eval_details if not d["with_skill_passed"]]
        if failed:
            lines.append(f"- ❌ 失败用例 ({len(failed)} 个): {', '.join(d['id'] for d in failed)}")
            lines.append("  建议: 检查这些用例的期望断言是否合理，或优化 skill 的工作流")
    lines.append("")

    output = Path(args.output)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ 评估报告已生成: {output}")
    print(f"   用例总数: {total}")
    print(f"   with_skill 通过率: {with_skill_passed}/{total} ({with_skill_passed/total*100:.1f}%)" if total else "   with_skill 通过率: 0%")
    print(f"   without_skill 通过率: {without_skill_passed}/{total} ({without_skill_passed/total*100:.1f}%)" if total else "   without_skill 通过率: 0%")
    print(f"   skill 带来提升: {improvement_count} 个用例")


def main():
    parser = argparse.ArgumentParser(description="Agent Skill 质量评估工具")
    subparsers = parser.add_subparsers(dest="command")

    init_p = subparsers.add_parser("init", help="生成评估用例模板")
    init_p.add_argument("--skill", required=True, help="Skill 目录路径")
    init_p.add_argument("--output", default="evals.json", help="输出文件路径")

    desc_p = subparsers.add_parser("describe-optimize", help="生成描述触发率优化查询")
    desc_p.add_argument("--skill", required=True, help="Skill 目录路径")
    desc_p.add_argument("--output", default="trigger_evals.json", help="输出文件路径")

    list_p = subparsers.add_parser("list", help="列出评估用例")
    list_p.add_argument("--evals", required=True, help="评估用例文件路径")

    report_p = subparsers.add_parser("report", help="生成评估报告")
    report_p.add_argument("--evals", required=True, help="评估用例文件路径")
    report_p.add_argument("--results", required=True, help="评估结果文件路径")
    report_p.add_argument("--output", default="eval_report.md", help="输出报告路径")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "describe-optimize":
        cmd_describe_optimize(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()
        sys.exit(1)

    # 提示参考官方评估框架
    if args.command in ("init", "report"):
        print()
        print("📚 官方评估框架参考（对齐 official/skill-creator）:")
        print("  - 评估数据结构: official/skill-creator/references/schemas.md")
        print("  - 评估子代理: official/skill-creator/agents/{grader,comparator,analyzer}.md")
        print("  - 官方评估脚本: official/skill-creator/scripts/run_eval.py")


if __name__ == "__main__":
    main()
