#!/usr/bin/env python3
"""
插件质量自动评分器

**核心原则：独立于 LLM 的客观评分**
- 分数完全由脚本计算，LLM 不能自己改分
- 6 个维度加权评分
- 发布标准：≥ 80 分

评分维度：
1. 规范合规 (25%)
2. 结构完整性 (20%)
3. 安全卫生 (20%)
4. 文档质量 (15%)
5. 测试覆盖 (10%)
6. 三大能力（渐进式披露/触发路由/Gotchas）(10%)

用法:
    python3 score_plugin.py ./my-plugin
    python3 score_plugin.py ./my-plugin --json
"""
import argparse
import json
import sys
from pathlib import Path


def check_compliance(plugin_dir: Path) -> dict:
    """维度1：规范合规 (25分)"""
    score = 0
    details = []
    
    # plugin.json 存在且有效 (10分)
    plugin_json = plugin_dir / "plugin.json"
    if plugin_json.exists():
        try:
            data = json.loads(plugin_json.read_text(encoding="utf-8"))
            if data.get("$schema"):
                score += 3
                details.append("✅ $schema 存在")
            if data.get("name"):
                score += 3
                details.append("✅ name 存在")
            if data.get("version"):
                score += 2
                details.append("✅ version 存在")
            if data.get("description"):
                score += 2
                details.append("✅ description 存在")
        except json.JSONDecodeError:
            details.append("❌ plugin.json 不是有效的 JSON")
    else:
        details.append("❌ plugin.json 不存在")
    
    # mcp.json 格式正确（如有）(10分)
    mcp_json = plugin_dir / "mcp.json"
    if mcp_json.exists():
        try:
            data = json.loads(mcp_json.read_text(encoding="utf-8"))
            if data.get("mcpServers"):
                score += 5
                details.append("✅ mcpServers 存在")
                for server_name, server_config in data["mcpServers"].items():
                    if server_config.get("type"):
                        score += 2
                        details.append(f"✅ {server_name}: type 字段存在")
                    if server_config.get("command"):
                        score += 3
                        details.append(f"✅ {server_name}: command 存在")
            else:
                details.append("❌ mcp.json 缺少 mcpServers")
        except json.JSONDecodeError:
            details.append("❌ mcp.json 不是有效的 JSON")
    else:
        # 没有 MCP 服务器不扣分
        score += 10
        details.append("ℹ️  无 MCP 服务器（满分）")
    
    # Skill 规范 (5分)
    skills_dir = plugin_dir / "skills"
    if skills_dir.exists():
        skill_count = 0
        valid_count = 0
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skill_count += 1
                # 检查 frontmatter
                skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                if skill_md.startswith("---"):
                    end = skill_md.find("---", 3)
                    if end > 0:
                        frontmatter = skill_md[3:end]
                        if "name:" in frontmatter and "description:" in frontmatter:
                            valid_count += 1
        if skill_count > 0:
            ratio = valid_count / skill_count
            earned = round(5 * ratio)
            score += earned
            details.append(f"✅ {valid_count}/{skill_count} 个 Skill 有正确的 frontmatter")
    
    return {
        "name": "规范合规",
        "max": 25,
        "score": score,
        "details": details,
    }


def check_structure(plugin_dir: Path) -> dict:
    """维度2：结构完整性 (20分)"""
    score = 0
    details = []
    
    # 必需文件 (10分)
    required = ["plugin.json"]
    optional = ["README.md", "mcp.json", "CHANGELOG.md", "LICENSE"]
    
    for f in required:
        if (plugin_dir / f).exists():
            score += 5
            details.append(f"✅ 必需文件 {f} 存在")
        else:
            details.append(f"❌ 必需文件 {f} 不存在")
    
    for f in optional:
        if (plugin_dir / f).exists():
            score += 2.5
            details.append(f"✅ 推荐文件 {f} 存在")
    
    # Skills 目录 (5分)
    skills_dir = plugin_dir / "skills"
    if skills_dir.exists() and any(skills_dir.iterdir()):
        score += 5
        skill_count = len([d for d in skills_dir.iterdir() if d.is_dir()])
        details.append(f"✅ skills/ 目录存在，含 {skill_count} 个技能")
    
    # MCP 服务器目录（如有）(5分)
    servers_dir = plugin_dir / "servers"
    if servers_dir.exists() and any(servers_dir.iterdir()):
        score += 5
        server_count = len([d for d in servers_dir.iterdir() if d.is_dir()])
        details.append(f"✅ servers/ 目录存在，含 {server_count} 个服务器")
    elif (plugin_dir / "mcp.json").exists():
        details.append("⚠️  有 mcp.json 但没有 servers/ 目录")
    
    return {
        "name": "结构完整性",
        "max": 20,
        "score": min(score, 20),
        "details": details,
    }


def check_security(plugin_dir: Path) -> dict:
    """维度3：安全卫生 (20分)"""
    score = 20
    details = []
    
    # 检查硬编码密钥
    suspicious_patterns = [
        ("api_key", "API Key"),
        ("apikey", "API Key"),
        ("password", "密码"),
        ("secret", "密钥"),
        ("token", "Token"),
    ]
    
    files_to_check = list(plugin_dir.rglob("*.py")) + list(plugin_dir.rglob("*.ts")) + list(plugin_dir.rglob("*.json"))
    found_issues = 0
    
    for f in files_to_check[:50]:  # 限制检查文件数
        try:
            content = f.read_text(encoding="utf-8", errors="ignore").lower()
            for pattern, label in suspicious_patterns:
                # 只检查硬编码的，不检查注释和变量名
                if f'"{pattern}":' in content or f"'{pattern}':" in content:
                    if "os.environ" not in content and "getenv" not in content:
                        found_issues += 1
                        details.append(f"⚠️  {f.name}: 可能有硬编码 {label}")
        except Exception:
            pass
    
    if found_issues > 0:
        deduction = min(found_issues * 2, 10)
        score -= deduction
        details.append(f"共发现 {found_issues} 处疑似硬编码密钥，扣 {deduction} 分")
    else:
        details.append("✅ 未发现硬编码密钥")
    
    # 检查 eval/exec/shell=True
    dangerous_patterns = [
        ("eval(", "eval()"),
        ("exec(", "exec()"),
        ("shell=True", "shell=True"),
    ]
    
    dangerous_count = 0
    for f in files_to_check[:50]:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            for pattern, label in dangerous_patterns:
                if pattern in content:
                    dangerous_count += 1
                    details.append(f"❌ {f.name}: 使用了危险函数 {label}")
        except Exception:
            pass
    
    if dangerous_count > 0:
        deduction = min(dangerous_count * 3, 10)
        score -= deduction
        details.append(f"共发现 {dangerous_count} 处危险函数，扣 {deduction} 分")
    else:
        details.append("✅ 未发现危险函数（eval/exec/shell=True）")
    
    return {
        "name": "安全卫生",
        "max": 20,
        "score": max(score, 0),
        "details": details,
    }


def check_documentation(plugin_dir: Path) -> dict:
    """维度4：文档质量 (15分)"""
    score = 0
    details = []
    
    # README.md (5分)
    readme = plugin_dir / "README.md"
    if readme.exists():
        content = readme.read_text(encoding="utf-8")
        lines = len(content.split("\n"))
        if lines >= 10:
            score += 5
            details.append(f"✅ README.md 存在（{lines} 行）")
        elif lines >= 5:
            score += 3
            details.append(f"⚠️  README.md 较短（{lines} 行）")
        else:
            score += 1
            details.append(f"❌ README.md 过短（{lines} 行）")
    
    # SKILL.md 质量 (10分)
    skills_dir = plugin_dir / "skills"
    if skills_dir.exists():
        total_score = 0
        skill_count = 0
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            skill_count += 1
            content = skill_md.read_text(encoding="utf-8")
            skill_score = 0
            
            # 有概述
            if "概述" in content or "Overview" in content:
                skill_score += 2
            # 有工作流程
            if "工作流程" in content or "Workflow" in content:
                skill_score += 2
            # 有 Gotchas
            if "Gotchas" in content or "坑" in content:
                skill_score += 3
            # 有触发场景
            if "触发" in content or "Trigger" in content or "should" in content:
                skill_score += 3
            
            total_score += skill_score
        
        if skill_count > 0:
            avg = total_score / skill_count
            earned = round(avg / 10 * 10)  # 归一化到10分
            score += earned
            details.append(f"✅ {skill_count} 个 Skill，平均得分 {avg:.1f}/10")
    
    return {
        "name": "文档质量",
        "max": 15,
        "score": score,
        "details": details,
    }


def check_testing(plugin_dir: Path) -> dict:
    """维度5：测试覆盖 (10分)"""
    score = 0
    details = []
    
    # 检查是否有测试文件
    test_files = list(plugin_dir.rglob("test_*.py")) + list(plugin_dir.rglob("*_test.py"))
    
    if len(test_files) >= 3:
        score = 10
        details.append(f"✅ 发现 {len(test_files)} 个测试文件")
    elif len(test_files) >= 1:
        score = 6
        details.append(f"⚠️  只有 {len(test_files)} 个测试文件（建议至少 3 个）")
    else:
        details.append("❌ 未发现测试文件")
    
    return {
        "name": "测试覆盖",
        "max": 10,
        "score": score,
        "details": details,
    }


def check_three_capabilities(plugin_dir: Path) -> dict:
    """维度6：三大能力（渐进式披露/触发路由/Gotchas）(10分)"""
    score = 0
    details = []
    
    skills_dir = plugin_dir / "skills"
    if not skills_dir.exists():
        details.append("ℹ️  无 Skills 目录（满分）")
        return {
            "name": "三大能力",
            "max": 10,
            "score": 10,
            "details": details,
        }
    
    total_score = 0
    skill_count = 0
    
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        skill_count += 1
        content = skill_md.read_text(encoding="utf-8")
        lines = len(content.split("\n"))
        skill_score = 0
        
        # 渐进式披露：SKILL.md < 300 行
        if lines < 300:
            skill_score += 3
            details.append(f"✅ {skill_dir.name}: SKILL.md {lines} 行（<300）")
        elif lines < 500:
            skill_score += 1.5
            details.append(f"⚠️  {skill_dir.name}: SKILL.md {lines} 行（接近上限）")
        else:
            details.append(f"❌ {skill_dir.name}: SKILL.md {lines} 行（>500，需要拆分）")
        
        # 触发路由：description 清晰
        if "---" in content:
            end = content.find("---", 3)
            if end > 0:
                frontmatter = content[3:end]
                desc_line = [l for l in frontmatter.split("\n") if l.startswith("description:")]
                if desc_line and len(desc_line[0]) > 50:
                    skill_score += 3
                    details.append(f"✅ {skill_dir.name}: description 详细")
                else:
                    details.append(f"⚠️  {skill_dir.name}: description 太短")
        
        # Gotchas section
        if "Gotchas" in content or "坑" in content:
            skill_score += 4
            details.append(f"✅ {skill_dir.name}: 有 Gotchas section")
        else:
            details.append(f"❌ {skill_dir.name}: 缺少 Gotchas section")
        
        total_score += skill_score
    
    if skill_count > 0:
        avg = total_score / skill_count
        earned = round(avg / 10 * 10)
        score = earned
        details.append(f"平均得分: {avg:.1f}/10")
    
    return {
        "name": "三大能力",
        "max": 10,
        "score": score,
        "details": details,
    }


def main():
    parser = argparse.ArgumentParser(description="插件质量自动评分器（独立于 LLM）")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()
    
    plugin_path = Path(args.plugin_dir).resolve()
    if not plugin_path.exists():
        print(f"错误: 目录不存在: {plugin_path}", file=sys.stderr)
        sys.exit(1)
    
    dimensions = [
        check_compliance(plugin_path),
        check_structure(plugin_path),
        check_security(plugin_path),
        check_documentation(plugin_path),
        check_testing(plugin_path),
        check_three_capabilities(plugin_path),
    ]
    
    total_score = sum(d["score"] for d in dimensions)
    total_max = sum(d["max"] for d in dimensions)
    percentage = round(total_score / total_max * 100, 1)
    
    result = {
        "plugin": str(plugin_path),
        "total_score": total_score,
        "total_max": total_max,
        "percentage": percentage,
        "dimensions": dimensions,
    }
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if percentage >= 80 else 1)
    
    # 文本输出
    print("=" * 60)
    print(f"插件质量评分: {plugin_path.name}")
    print("=" * 60)
    
    for d in dimensions:
        pct = round(d["score"] / d["max"] * 100, 1)
        print(f"\n{d['name']}: {d['score']}/{d['max']} ({pct}%)")
        for detail in d["details"]:
            print(f"  {detail}")
    
    print("\n" + "=" * 60)
    print(f"总分: {total_score}/{total_max} ({percentage}%)")
    
    # 评级
    if percentage >= 90:
        grade = "A+（优秀）"
    elif percentage >= 80:
        grade = "A（良好，可发布）"
    elif percentage >= 70:
        grade = "B（一般，需要改进）"
    elif percentage >= 60:
        grade = "C（及格，不建议发布）"
    else:
        grade = "D（不及格，必须改进）"
    
    print(f"评级: {grade}")
    print("=" * 60)
    
    # 发布标准
    if percentage >= 80:
        print("✅ 达到发布标准（≥80分）")
    else:
        print("❌ 未达到发布标准（需要≥80分）")
        print(f"   还需要 {round(80 - percentage, 1)} 分")
    
    sys.exit(0 if percentage >= 80 else 1)


if __name__ == "__main__":
    main()
