#!/usr/bin/env python3
"""
渐进式披露 Token 预算审计工具

审计 Skill 的三层渐进式披露结构，计算每层的 token 用量，
确保符合 Anthropic 最佳实践：
  - Level 1（元数据）：~100 tokens
  - Level 2（SKILL.md body）：< 500 lines / ~5k tokens
  - Level 3（外部资源）：按需加载

用法:
    python3 scripts/audit_progressive_disclosure.py --skill ./my-skill
    python3 scripts/audit_progressive_disclosure.py --skill ./my-skill --json
"""
import argparse
import json
import re
import sys
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数量（英文 ~4 chars/token，中文 ~1.5 chars/token）"""
    # 简单估算：英文按 4 字符/token，中文按 1.5 字符/token
    # 这里用混合估算：总字符数 / 2.5
    return len(text) // 3


def audit_progressive_disclosure(skill_dir: Path) -> dict:
    """审计 Skill 的渐进式披露结构"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"error": "SKILL.md 不存在"}

    content = skill_md.read_text(encoding="utf-8")
    lines = content.split("\n")

    # === Level 1: Frontmatter 元数据 ===
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        return {"error": "未找到 frontmatter"}

    fm_text = fm_match.group(1)
    level1_tokens = estimate_tokens(fm_text)

    # 提取 name 和 description
    name_match = re.search(r'name:\s*(.+)', fm_text)
    desc_match = re.search(r'description:\s*(.+)', fm_text)
    level1_name = name_match.group(1).strip() if name_match else ""
    level1_desc = desc_match.group(1).strip() if desc_match else ""
    level1_desc_tokens = estimate_tokens(level1_desc)

    # === Level 2: SKILL.md Body ===
    body = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
    level2_tokens = estimate_tokens(body)
    level2_lines = len(body.split("\n"))

    # === Level 3: 外部资源 ===
    references_dir = skill_dir / "references"
    scripts_dir = skill_dir / "scripts"
    assets_dir = skill_dir / "assets"

    level3_files = []
    level3_total_tokens = 0

    if references_dir.exists():
        for ref_file in references_dir.glob("*.md"):
            ref_content = ref_file.read_text(encoding="utf-8", errors="ignore")
            ref_tokens = estimate_tokens(ref_content)
            level3_files.append({
                "path": f"references/{ref_file.name}",
                "tokens": ref_tokens,
                "lines": len(ref_content.split("\n")),
            })
            level3_total_tokens += ref_tokens

    if scripts_dir.exists():
        script_count = len(list(scripts_dir.glob("*.py")))
        level3_files.append({
            "path": "scripts/",
            "files": script_count,
            "note": "脚本不加载到上下文，只执行",
        })

    # === 评分 ===
    issues = []
    suggestions = []

    # Level 1 检查
    if level1_tokens > 100:
        issues.append(f"Level 1 元数据 {level1_tokens} tokens，超过 100 tokens 最佳实践")
        suggestions.append("精简 frontmatter，只保留 name 和 description")
    elif level1_tokens < 50:
        issues.append(f"Level 1 元数据 {level1_tokens} tokens，可能过于简单")
        suggestions.append("确保 description 包含三要素：what + when + triggers")

    # Level 2 检查
    if level2_lines > 500:
        issues.append(f"SKILL.md 正文 {level2_lines} 行，超过 500 行限制")
        suggestions.append("将详细内容拆分到 references/ 目录")
    elif level2_tokens > 5000:
        issues.append(f"SKILL.md 正文 ~{level2_tokens} tokens，接近 5k tokens 上限")
        suggestions.append("考虑拆分详细内容到 references/")

    # Level 3 检查
    deep_refs = 0
    for f in level3_files:
        if "references/" in f["path"] and f.get("tokens", 0) > 10000:
            deep_refs += 1
            suggestions.append(f"{f['path']} 超过 10k tokens，建议内部再拆分")

    # 渐进式披露评分
    score = 100
    if level1_tokens > 100:
        score -= 15
    if level2_lines > 500:
        score -= 25
    if not references_dir.exists():
        score -= 20
        suggestions.append("没有 references/ 目录，详细内容都塞在 SKILL.md 中")
    if deep_refs > 0:
        score -= 10 * deep_refs

    return {
        "skill": skill_dir.name,
        "overall_score": max(0, score),
        "level1_metadata": {
            "tokens": level1_tokens,
            "name": level1_name,
            "description_tokens": level1_desc_tokens,
            "target": "~100 tokens",
            "status": "good" if 50 <= level1_tokens <= 150 else "needs-attention",
        },
        "level2_body": {
            "tokens": level2_tokens,
            "lines": level2_lines,
            "target": "< 500 lines / ~5k tokens",
            "status": "good" if level2_lines <= 500 else "too-long",
        },
        "level3_resources": {
            "total_tokens": level3_total_tokens,
            "files": level3_files,
            "target": "按需加载（不计入常驻上下文）",
        },
        "issues": issues,
        "suggestions": suggestions,
    }


def main():
    parser = argparse.ArgumentParser(description="渐进式披露 Token 预算审计")
    parser.add_argument("--skill", required=True, help="Skill 目录路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    skill_dir = Path(args.skill).resolve()
    if not skill_dir.exists():
        print(f"错误: Skill 目录不存在: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    result = audit_progressive_disclosure(skill_dir)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"渐进式披露审计: {result['skill']}")
        print(f"综合评分: {result['overall_score']}/100")
        print("=" * 60)

        l1 = result["level1_metadata"]
        print(f"\n📊 Level 1: 元数据（常驻上下文）")
        print(f"   Tokens: {l1['tokens']} (目标: {l1['target']})")
        print(f"   Description: {l1['description_tokens']} tokens")
        status_icon = "✅" if l1["status"] == "good" else "⚠️"
        print(f"   状态: {status_icon} {l1['status']}")

        l2 = result["level2_body"]
        print(f"\n📄 Level 2: SKILL.md Body（触发后加载）")
        print(f"   Tokens: ~{l2['tokens']}")
        print(f"   Lines: {l2['lines']} (目标: {l2['target']})")
        status_icon = "✅" if l2["status"] == "good" else "❌"
        print(f"   状态: {status_icon} {l2['status']}")

        l3 = result["level3_resources"]
        print(f"\n📚 Level 3: 外部资源（按需加载）")
        print(f"   总 Tokens: ~{l3['total_tokens']}")
        print(f"   文件数: {len(l3['files'])}")
        for f in l3["files"][:5]:
            if "tokens" in f:
                print(f"     - {f['path']}: ~{f['tokens']} tokens ({f['lines']} lines)")
            else:
                print(f"     - {f['path']}: {f.get('files', '')} 个文件")

        if result["issues"]:
            print(f"\n⚠️  发现问题 ({len(result['issues'])}):")
            for issue in result["issues"]:
                print(f"   - {issue}")

        if result["suggestions"]:
            print(f"\n💡 改进建议 ({len(result['suggestions'])}):")
            for sug in result["suggestions"]:
                print(f"   - {sug}")

        print("\n" + "=" * 60)

    sys.exit(0 if result["overall_score"] >= 80 else 1)


if __name__ == "__main__":
    main()
