#!/usr/bin/env python3
"""
Skill 质量自动检查器

**核心设计理念：**
不要靠提示词要求 AI 遵守规则，用脚本强制检查。
AI 只需要运行这个脚本，脚本会自动告诉你哪里不合格。

检查项：
1. 基本结构：frontmatter、行数
2. 内容完整性：概述、工作流程、关键规则、Gotchas、触发场景
3. 三大能力：渐进式披露、触发路由、Gotchas
4. 第四大能力：对抗 LLM 不可靠性（关键逻辑是否写成脚本）

用法:
    python3 check_skill_quality.py ./my-skill
    python3 check_skill_quality.py ./my-skill --json
"""
import argparse
import re
import sys
from pathlib import Path


def check_structure(skill_dir: Path) -> dict:
    """检查 1：基本结构"""
    results = []
    passed = 0
    total = 0
    
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"name": "基本结构", "passed": 0, "total": 1, "results": [{"item": "SKILL.md 存在", "status": "FAIL", "detail": "文件不存在"}]}
    
    content = skill_md.read_text(encoding="utf-8")
    lines = content.split("\n")
    line_count = len(lines)
    
    # 检查 frontmatter
    total += 1
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            frontmatter = content[3:end]
            has_name = "name:" in frontmatter
            has_desc = "description:" in frontmatter
            if has_name and has_desc:
                results.append({"item": "frontmatter 完整", "status": "PASS", "detail": "有 name 和 description"})
                passed += 1
            else:
                results.append({"item": "frontmatter 完整", "status": "FAIL", "detail": "缺少 name 或 description"})
        else:
            results.append({"item": "frontmatter 完整", "status": "FAIL", "detail": "frontmatter 未正确闭合"})
    else:
        results.append({"item": "frontmatter 完整", "status": "FAIL", "detail": "没有 frontmatter"})
    
    # 检查行数（渐进式披露）
    total += 1
    if line_count < 300:
        results.append({"item": f"SKILL.md 行数 < 300", "status": "PASS", "detail": f"{line_count} 行"})
        passed += 1
    else:
        results.append({"item": f"SKILL.md 行数 < 300", "status": "FAIL", "detail": f"{line_count} 行，太长了，需要拆分到 references/"})
    
    return {"name": "基本结构", "passed": passed, "total": total, "results": results}


def check_completeness(skill_dir: Path) -> dict:
    """检查 2：内容完整性"""
    results = []
    passed = 0
    total = 0
    
    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    
    sections = [
        ("概述", ["概述", "Overview"]),
        ("工作流程", ["工作流程", "Workflow"]),
        ("关键规则", ["关键规则", "Key Rules"]),
        ("Gotchas", ["Gotchas", "坑", "踩过的坑"]),
        ("触发场景", ["触发", "When to Use", "Trigger"]),
    ]
    
    for section_name, keywords in sections:
        total += 1
        found = any(kw in content for kw in keywords)
        if found:
            results.append({"item": f"有 {section_name} 章节", "status": "PASS", "detail": ""})
            passed += 1
        else:
            results.append({"item": f"有 {section_name} 章节", "status": "FAIL", "detail": f"缺少 {section_name} 章节"})
    
    return {"name": "内容完整性", "passed": passed, "total": total, "results": results}


def check_three_capabilities(skill_dir: Path) -> dict:
    """检查 3：三大能力"""
    results = []
    passed = 0
    total = 0
    
    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    
    # 渐进式披露：有 references/ 目录
    total += 1
    refs_dir = skill_dir / "references"
    if refs_dir.exists() and any(refs_dir.iterdir()):
        ref_count = len(list(refs_dir.iterdir()))
        results.append({"item": "渐进式披露：有 references/", "status": "PASS", "detail": f"{ref_count} 个文件"})
        passed += 1
    else:
        results.append({"item": "渐进式披露：有 references/", "status": "WARN", "detail": "没有 references/ 目录（小技能可以没有）"})
    
    # 触发路由：description 足够长
    total += 1
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            frontmatter = content[3:end]
            desc_match = re.search(r'description:\s*(.+)', frontmatter)
            if desc_match:
                desc = desc_match.group(1)
                if len(desc) > 50:
                    results.append({"item": "触发路由：description 足够详细", "status": "PASS", "detail": f"{len(desc)} 字符"})
                    passed += 1
                else:
                    results.append({"item": "触发路由：description 足够详细", "status": "FAIL", "detail": f"只有 {len(desc)} 字符，太短了"})
            else:
                results.append({"item": "触发路由：description 足够详细", "status": "FAIL", "detail": "找不到 description"})
        else:
            results.append({"item": "触发路由：description 足够详细", "status": "FAIL", "detail": "frontmatter 未闭合"})
    else:
        results.append({"item": "触发路由：description 足够详细", "status": "FAIL", "detail": "没有 frontmatter"})
    
    # Gotchas：至少 3 个坑
    total += 1
    gotcha_count = content.count("### 坑") + content.count("### Gotcha")
    if gotcha_count >= 3:
        results.append({"item": "Gotchas：至少 3 个坑", "status": "PASS", "detail": f"{gotcha_count} 个"})
        passed += 1
    else:
        results.append({"item": "Gotchas：至少 3 个坑", "status": "FAIL", "detail": f"只有 {gotcha_count} 个，建议至少 3 个"})
    
    return {"name": "三大能力", "passed": passed, "total": total, "results": results}


def check_anti_llm_unreliability(skill_dir: Path) -> dict:
    """检查 4：对抗 LLM 不可靠性"""
    results = []
    passed = 0
    total = 0
    
    scripts_dir = skill_dir / "scripts"
    has_scripts = scripts_dir.exists() and any(scripts_dir.glob("*.py"))
    
    # 有验证脚本（不只是创建）
    total += 1
    if has_scripts:
        script_files = list(scripts_dir.glob("*.py"))
        has_validate = any("validate" in f.name or "check" in f.name or "verify" in f.name for f in script_files)
        if has_validate:
            results.append({"item": "有自动验证脚本", "status": "PASS", "detail": "不只是创建，还有验证"})
            passed += 1
        else:
            results.append({"item": "有自动验证脚本", "status": "WARN", "detail": "只有创建脚本，没有验证脚本"})
    else:
        results.append({"item": "有自动验证脚本", "status": "WARN", "detail": "没有脚本（纯文档技能可以）"})
    
    # 关键逻辑是否写成脚本（而不是靠提示词）
    total += 1
    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    
    # 检查有没有"AI 必须"这类文字
    must_count = content.count("AI 必须") + content.count("必须执行") + content.count("必须运行")
    if must_count <= 2:
        results.append({"item": "关键逻辑不靠提示词", "status": "PASS", "detail": f"只有 {must_count} 处'必须'"})
        passed += 1
    else:
        results.append({"item": "关键逻辑不靠提示词", "status": "WARN", "detail": f"有 {must_count} 处'AI 必须'，建议改成脚本强制"})
    
    return {"name": "对抗 LLM 不可靠性", "passed": passed, "total": total, "results": results}


def main():
    parser = argparse.ArgumentParser(description="Skill 质量自动检查器（不靠提示词，靠脚本强制）")
    parser.add_argument("skill_dir", help="Skill 目录路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()
    
    skill_path = Path(args.skill_dir).resolve()
    if not skill_path.exists():
        print(f"错误: 目录不存在: {skill_path}", file=sys.stderr)
        sys.exit(1)
    
    checks = [
        check_structure(skill_path),
        check_completeness(skill_path),
        check_three_capabilities(skill_path),
        check_anti_llm_unreliability(skill_path),
    ]
    
    total_passed = sum(c["passed"] for c in checks)
    total_total = sum(c["total"] for c in checks)
    percentage = round(total_passed / total_total * 100, 1) if total_total > 0 else 0
    
    result = {
        "skill": str(skill_path),
        "total_passed": total_passed,
        "total_total": total_total,
        "percentage": percentage,
        "checks": checks,
    }
    
    if args.json:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if percentage >= 80 else 1)
    
    # 文本输出
    print("=" * 60)
    print(f"Skill 质量检查: {skill_path.name}")
    print("=" * 60)
    
    for check in checks:
        print(f"\n{check['name']}: {check['passed']}/{check['total']}")
        for r in check["results"]:
            icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(r["status"], "❓")
            detail = f" ({r['detail']})" if r["detail"] else ""
            print(f"  {icon} {r['item']}{detail}")
    
    print("\n" + "=" * 60)
    print(f"总分: {total_passed}/{total_total} ({percentage}%)")
    print("=" * 60)
    
    if percentage >= 90:
        grade = "A+（优秀）"
    elif percentage >= 80:
        grade = "A（良好）"
    elif percentage >= 70:
        grade = "B（一般）"
    elif percentage >= 60:
        grade = "C（及格）"
    else:
        grade = "D（不及格）"
    
    print(f"评级: {grade}")
    print("=" * 60)
    
    sys.exit(0 if percentage >= 80 else 1)


if __name__ == "__main__":
    main()
