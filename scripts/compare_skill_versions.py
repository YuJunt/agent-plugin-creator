#!/usr/bin/env python3
"""
Skill 版本盲测对比工具（Comparator）

对比两个版本的技能，用相同的测试提示词分别运行，然后盲测评分。
参考 Anthropic 官方 skill-creator 的 Comparator 子代理设计。

用法:
    python3 scripts/compare_skill_versions.py \
        --old ./skills/my-skill-old \
        --new ./skills/my-skill-new \
        --prompts evals/prompts.json

prompts.json 格式:
    [
      {"prompt": "用户说的话", "expected": "期望的行为描述"},
      ...
    ]
"""
import argparse
import json
import random
import sys
from pathlib import Path


def run_skill_on_prompt(skill_dir: Path, prompt: str, expected: str) -> dict:
    """模拟运行技能（规则引擎版，实际使用时可替换为 LLM 调用）

    返回:
        {
            "skill": skill_dir.name,
            "prompt": prompt,
            "expected": expected,
            "output": "模拟输出",
            "score": 0.0-1.0,
            "reasoning": "评分理由",
        }
    """
    # 这是一个简化的规则引擎版本
    # 实际使用时，应该调用 LLM 来生成输出并评分
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"skill": skill_dir.name, "prompt": prompt, "score": 0.0,
                "reasoning": "SKILL.md 不存在"}

    content = skill_md.read_text(encoding="utf-8")

    # 简单规则：检查 prompt 中的关键词是否在 description 中
    desc_match = 0
    for word in prompt.lower().split():
        if len(word) > 2 and word in content[:500].lower():
            desc_match += 1
    score = min(1.0, desc_match / 5) if prompt else 0.5

    return {
        "skill": skill_dir.name,
        "prompt": prompt[:100],
        "expected": expected[:100],
        "score": round(score, 2),
        "reasoning": f"关键词匹配度: {desc_match}/5",
    }


def compare_two_versions(old_dir: Path, new_dir: Path, prompts: list) -> dict:
    """盲测对比两个版本"""
    results = []
    wins = {"old": 0, "new": 0, "tie": 0}

    for i, item in enumerate(prompts):
        prompt = item.get("prompt", "")
        expected = item.get("expected", "")

        # 运行两个版本
        old_result = run_skill_on_prompt(old_dir, prompt, expected)
        new_result = run_skill_on_prompt(new_dir, prompt, expected)

        # 盲测：随机决定先展示哪个
        order = random.choice(["A", "B"])
        if order == "A":
            a, b = old_result, new_result
            a_version, b_version = "old", "new"
        else:
            a, b = new_result, old_result
            a_version, b_version = "new", "old"

        # 比较得分
        if a["score"] > b["score"]:
            winner = a_version
            wins[winner] += 1
        elif b["score"] > a["score"]:
            winner = b_version
            wins[winner] += 1
        else:
            winner = "tie"
            wins["tie"] += 1

        results.append({
            "index": i + 1,
            "prompt": prompt[:80],
            "order": order,
            "old_score": old_result["score"],
            "new_score": new_result["score"],
            "winner": winner,
            "old_reasoning": old_result["reasoning"],
            "new_reasoning": new_result["reasoning"],
        })

    total = len(prompts)
    return {
        "old_version": old_dir.name,
        "new_version": new_dir.name,
        "total_prompts": total,
        "wins": wins,
        "win_rate": {
            "old": round(wins["old"] / total * 100, 1) if total else 0,
            "new": round(wins["new"] / total * 100, 1) if total else 0,
            "tie": round(wins["tie"] / total * 100, 1) if total else 0,
        },
        "details": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Skill 版本盲测对比工具")
    parser.add_argument("--old", required=True, help="旧版技能目录")
    parser.add_argument("--new", required=True, help="新版技能目录")
    parser.add_argument("--prompts", required=True, help="测试提示词 JSON 文件")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    old_dir = Path(args.old).resolve()
    new_dir = Path(args.new).resolve()
    prompts_path = Path(args.prompts).resolve()

    if not old_dir.exists() or not new_dir.exists():
        print("错误: 技能目录不存在", file=sys.stderr)
        sys.exit(1)

    if not prompts_path.exists():
        print("错误: 提示词文件不存在", file=sys.stderr)
        sys.exit(1)

    prompts = json.loads(prompts_path.read_text(encoding="utf-8"))
    if not isinstance(prompts, list):
        print("错误: 提示词文件必须是数组格式", file=sys.stderr)
        sys.exit(1)

    result = compare_two_versions(old_dir, new_dir, prompts)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("Skill 版本盲测对比")
        print("=" * 60)
        print(f"\n旧版: {result['old_version']}")
        print(f"新版: {result['new_version']}")
        print(f"测试用例: {result['total_prompts']}")
        print()
        print("胜负统计:")
        print(f"  旧版胜: {result['wins']['old']} ({result['win_rate']['old']}%)")
        print(f"  新版胜: {result['wins']['new']} ({result['win_rate']['new']}%)")
        print(f"  平局: {result['wins']['tie']} ({result['win_rate']['tie']}%)")
        print()
        print("详细结果:")
        for d in result["details"]:
            winner_mark = "🏆" if d["winner"] == "new" else ("⬇️" if d["winner"] == "old" else "➖")
            print(f"  {d['index']}. {winner_mark} old={d['old_score']:.2f} new={d['new_score']:.2f} | {d['prompt']}")

        print("\n" + "=" * 60)
        if result["win_rate"]["new"] > result["win_rate"]["old"]:
            print("结论: 新版技能表现更好 ✅")
        elif result["win_rate"]["old"] > result["win_rate"]["new"]:
            print("结论: 旧版技能表现更好 ❌")
        else:
            print("结论: 两个版本表现相当 ⚖️")
        print("=" * 60)

    sys.exit(0 if result["win_rate"]["new"] >= result["win_rate"]["old"] else 1)


if __name__ == "__main__":
    main()
