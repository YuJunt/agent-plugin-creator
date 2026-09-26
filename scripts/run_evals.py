#!/usr/bin/env python3
"""
Agent Plugin Creator 统一评估入口

合并了 trigger / selection / edge 三种评估，用 --type 参数选择。

用法:
    python3 run_evals.py --type trigger      # 触发评估
    python3 run_evals.py --type selection    # 选择评估
    python3 run_evals.py --type edge         # 边界评估
    python3 run_evals.py --type all          # 全部评估（默认）
    python3 run_evals.py --skill . --output result.json
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run_trigger_eval(skill_dir: Path) -> dict:
    """触发评估（should-trigger / should-not-trigger）"""
    sys.path.insert(0, str(SCRIPT_DIR))
    from run_trigger_eval import evaluate_skill
    return evaluate_skill(skill_dir)


def run_selection_eval(skill_dir: Path) -> dict:
    """选择评估（accuracy 指标）"""
    sys.path.insert(0, str(SCRIPT_DIR))
    from run_selection_eval import evaluate_skill
    return evaluate_skill(skill_dir)


def run_edge_eval(skill_dir: Path) -> dict:
    """边界评估（边界用例）"""
    sys.path.insert(0, str(SCRIPT_DIR))
    from run_edge_eval import evaluate_skill
    return evaluate_skill(skill_dir)


def main():
    parser = argparse.ArgumentParser(description="Agent Plugin Creator 统一评估入口")
    parser.add_argument("--type", choices=["trigger", "selection", "edge", "all"], default="all",
                        help="评估类型：trigger（触发）/ selection（选择）/ edge（边界）/ all（全部，默认）")
    parser.add_argument("--skill", default=str(SCRIPT_DIR.parent), help="技能目录路径")
    parser.add_argument("--output", help="输出 JSON 结果文件路径")
    args = parser.parse_args()

    skill_dir = Path(args.skill).resolve()
    if not skill_dir.exists():
        print(f"错误: 技能目录不存在: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    results = {}
    all_passed = True

    eval_types = ["trigger", "selection", "edge"] if args.type == "all" else [args.type]

    for eval_type in eval_types:
        print(f"\n{'=' * 60}")
        print(f"📊 运行评估: {eval_type}")
        print(f"{'=' * 60}")

        try:
            if eval_type == "trigger":
                report = run_trigger_eval(skill_dir)
            elif eval_type == "selection":
                report = run_selection_eval(skill_dir)
            else:
                report = run_edge_eval(skill_dir)

            results[eval_type] = report
            accuracy = report.get("accuracy", 0)
            passed = accuracy >= 0.8
            if not passed:
                all_passed = False
            print(f"\n结果: accuracy={accuracy:.1%}, {'✅ 通过' if passed else '❌ 未通过'}")

        except Exception as e:
            print(f"❌ 评估失败: {e}", file=sys.stderr)
            results[eval_type] = {"error": str(e)}
            all_passed = False

    # 汇总
    print(f"\n{'=' * 60}")
    print("📋 评估汇总")
    print(f"{'=' * 60}")
    for eval_type, report in results.items():
        if "error" in report:
            print(f"  {eval_type}: ❌ 错误 - {report['error']}")
        else:
            acc = report.get("accuracy", 0)
            print(f"  {eval_type}: accuracy={acc:.1%}")

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n结果已保存到: {output_path}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
