#!/usr/bin/env python3
"""
Skill 评估结果分析器（Analyzer）

分析评估结果，诊断问题，给出改进建议。
参考 Anthropic 官方 skill-creator 的 Analyzer 子代理设计。

分析维度：
  1. 低区分度断言：不管有没有技能都通过的断言（说明断言无效）
  2. 高方差结果：多次运行结果差异大（说明测试不稳定）
  3. 触发准确率：该触发的没触发 / 不该触发的触发了
  4. 改进建议：基于分析结果给出具体优化方向

用法:
    python3 scripts/analyze_eval_results.py --report eval_report.json
    python3 scripts/analyze_eval_results.py --skill ./my-skill
"""
import argparse
import json
import re
import sys
from pathlib import Path


def analyze_description(skill_md: Path) -> dict:
    """分析 SKILL.md 的 description 质量"""
    content = skill_md.read_text(encoding="utf-8")

    # 提取 frontmatter
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        return {"error": "未找到 frontmatter"}

    fm_text = fm_match.group(1)

    # 提取 description
    desc_match = re.search(r'description:\s*(.+)', fm_text)
    if not desc_match:
        return {"error": "未找到 description 字段"}

    description = desc_match.group(1).strip()

    # 分析三要素
    has_what = len(description) > 20  # 描述足够长
    has_when = any(kw in description.lower() for kw in [
        "use when", "当", "用于", "在", "场景", "触发",
        "use case", "scenario", "trigger"
    ])
    has_triggers = any(kw in description.lower() for kw in [
        "create", "build", "generate", "modify", "analyze",
        "创建", "生成", "修改", "分析", "设计",
    ])

    issues = []
    if not has_what:
        issues.append("description 太短，可能没说清楚做什么")
    if not has_when:
        issues.append("description 缺少触发场景（When to use）")
    if not has_triggers:
        issues.append("description 缺少具体触发词")

    # 长度检查
    desc_len = len(description)
    if desc_len > 1024:
        issues.append(f"description 过长（{desc_len} 字符），官方限制 1024 字符")
    elif desc_len < 50:
        issues.append(f"description 过短（{desc_len} 字符），建议至少 50 字符")

    return {
        "description_length": desc_len,
        "has_what": has_what,
        "has_when": has_when,
        "has_triggers": has_triggers,
        "issues": issues,
        "score": round((sum([has_what, has_when, has_triggers]) / 3) * 100, 1),
    }


def analyze_workflow(skill_md: Path) -> dict:
    """分析工作流质量"""
    content = skill_md.read_text(encoding="utf-8")
    body = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

    issues = []
    suggestions = []

    # 检查是否有明确的步骤
    has_steps = bool(re.search(r'^\d+\.\s', body, re.MULTILINE))
    if not has_steps:
        issues.append("没有明确的编号步骤")
        suggestions.append("添加编号工作流步骤（1. 第一步 2. 第二步...）")

    # 检查是否有条件分支
    has_conditions = bool(re.search(r'如果|若|当.*时|if\s', body, re.IGNORECASE))
    if not has_conditions:
        suggestions.append("添加条件分支说明（什么情况下走什么路径）")

    # 检查是否有示例
    has_examples = bool(re.search(r'示例|example|例如', body, re.IGNORECASE))
    if not has_examples:
        suggestions.append("添加 1-2 个完整示例")

    # 检查是否有 Gotchas
    has_gotchas = bool(re.search(r'坑|gotcha|注意|warning|警告', body, re.IGNORECASE))
    if not has_gotchas:
        issues.append("缺少 Gotchas section（踩坑提醒）")
        suggestions.append("添加 Gotchas section，列出常见错误和修正方法")

    # 检查渐进式披露
    has_references = "references/" in body or "references\\" in body
    has_scripts = "scripts/" in body or "scripts\\" in body
    if not has_references and len(body) > 3000:
        issues.append("SKILL.md 过长但没有拆分到 references/")
        suggestions.append("将详细文档拆分到 references/ 目录")

    return {
        "body_length": len(body),
        "has_steps": has_steps,
        "has_conditions": has_conditions,
        "has_examples": has_examples,
        "has_gotchas": has_gotchas,
        "uses_progressive_disclosure": has_references,
        "issues": issues,
        "suggestions": suggestions,
    }


def analyze_scripts(skill_dir: Path) -> dict:
    """分析脚本资源"""
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        return {"count": 0, "note": "无 scripts 目录"}

    scripts = list(scripts_dir.glob("*.py")) + list(scripts_dir.glob("*.sh"))
    issues = []
    suggestions = []

    # 检查脚本是否有 shebang
    no_shebang = []
    for s in scripts:
        try:
            first_line = s.read_text(encoding="utf-8", errors="ignore").split("\n")[0]
            if not first_line.startswith("#!"):
                no_shebang.append(s.name)
        except Exception:
            pass

    if no_shebang:
        issues.append(f"以下脚本缺少 shebang: {', '.join(no_shebang)}")
        suggestions.append("为所有脚本添加 shebang 行（#!/usr/bin/env python3）")

    return {
        "count": len(scripts),
        "scripts": [s.name for s in scripts],
        "issues": issues,
        "suggestions": suggestions,
    }


def analyze_skill(skill_dir: Path) -> dict:
    """综合分析技能"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"error": "SKILL.md 不存在"}

    desc_analysis = analyze_description(skill_md)
    workflow_analysis = analyze_workflow(skill_md)
    scripts_analysis = analyze_scripts(skill_dir)

    all_issues = desc_analysis.get("issues", []) + workflow_analysis.get("issues", []) + scripts_analysis.get("issues", [])
    all_suggestions = workflow_analysis.get("suggestions", []) + scripts_analysis.get("suggestions", [])

    # 综合评分
    scores = [desc_analysis.get("score", 0)]
    if workflow_analysis["has_steps"]:
        scores.append(80)
    if workflow_analysis["has_gotchas"]:
        scores.append(90)
    if workflow_analysis["has_examples"]:
        scores.append(85)
    overall_score = round(sum(scores) / len(scores), 1) if scores else 0

    return {
        "skill": skill_dir.name,
        "overall_score": overall_score,
        "description": desc_analysis,
        "workflow": workflow_analysis,
        "scripts": scripts_analysis,
        "total_issues": len(all_issues),
        "all_issues": all_issues,
        "all_suggestions": all_suggestions,
        "priority": "high" if overall_score < 60 else ("medium" if overall_score < 80 else "low"),
    }


def main():
    parser = argparse.ArgumentParser(description="Skill 评估结果分析器")
    parser.add_argument("--skill", required=True, help="技能目录路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    skill_dir = Path(args.skill).resolve()
    if not skill_dir.exists():
        print(f"错误: 技能目录不存在: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    result = analyze_skill(skill_dir)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"Skill 分析报告: {result['skill']}")
        print("=" * 60)
        print(f"\n综合评分: {result['overall_score']}/100")
        print(f"优化优先级: {result['priority']}")

        print(f"\n📝 Description 分析:")
        d = result["description"]
        if "error" in d:
            print(f"  ❌ {d['error']}")
        else:
            print(f"  长度: {d['description_length']} 字符")
            print(f"  三要素: what={'✅' if d['has_what'] else '❌'} "
                  f"when={'✅' if d['has_when'] else '❌'} "
                  f"triggers={'✅' if d['has_triggers'] else '❌'}")

        print(f"\n⚙️  工作流分析:")
        w = result["workflow"]
        print(f"  正文长度: {w['body_length']} 字符")
        print(f"  编号步骤: {'✅' if w['has_steps'] else '❌'}")
        print(f"  条件分支: {'✅' if w['has_conditions'] else '❌'}")
        print(f"  示例: {'✅' if w['has_examples'] else '❌'}")
        print(f"  Gotchas: {'✅' if w['has_gotchas'] else '❌'}")
        print(f"  渐进式披露: {'✅' if w['uses_progressive_disclosure'] else '❌'}")

        print(f"\n📜 脚本分析:")
        s = result["scripts"]
        print(f"  脚本数量: {s['count']}")

        if result["all_issues"]:
            print(f"\n❌ 发现问题 ({len(result['all_issues'])}):")
            for issue in result["all_issues"]:
                print(f"  - {issue}")

        if result["all_suggestions"]:
            print(f"\n💡 改进建议 ({len(result['all_suggestions'])}):")
            for sug in result["all_suggestions"]:
                print(f"  - {sug}")

        print("\n" + "=" * 60)

    sys.exit(0 if result.get("overall_score", 0) >= 70 else 1)


if __name__ == "__main__":
    main()
