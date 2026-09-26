#!/usr/bin/env python3
"""
Vercel skills.sh 发布元数据生成器

生成 Vercel skills.sh 市场所需的元数据格式。
skills.sh 是当前最大的 Agent Skills 市场（60万+ OSS 技能）。

发布流程:
  1. 生成 skills.sh 所需的 package.json 元数据
  2. 生成 SKILL.md 的标准化格式
  3. 生成发布检查清单

用法:
    python3 scripts/generate_skillsh_metadata.py --plugin ./my-plugin
    python3 scripts/generate_skillsh_metadata.py --plugin ./my-plugin --output ./dist
"""
import argparse
import json
import sys
from pathlib import Path


# skills.sh 支持的分类
SKILLSH_CATEGORIES = [
    "web-development",
    "data-analysis",
    "productivity",
    "design",
    "devops",
    "testing",
    "documentation",
    "research",
    "marketing",
    "sales",
    "support",
    "other",
]


def categorize_plugin(plugin: dict) -> str:
    """根据插件内容自动分类"""
    desc = plugin.get("description", "").lower()
    tags = [t.lower() for t in plugin.get("keywords", plugin.get("tags", []))]

    # 关键词匹配
    if any(kw in desc or kw in tags for kw in ["web", "frontend", "react", "nextjs", "html", "css"]):
        return "web-development"
    if any(kw in desc or kw in tags for kw in ["data", "analytics", "sql", "excel", "chart"]):
        return "data-analysis"
    if any(kw in desc or kw in tags for kw in ["design", "ui", "ux", "figma", "image"]):
        return "design"
    if any(kw in desc or kw in tags for kw in ["devops", "deploy", "docker", "kubernetes", "ci/cd"]):
        return "devops"
    if any(kw in desc or kw in tags for kw in ["test", "qa", "quality", "lint"]):
        return "testing"
    if any(kw in desc or kw in tags for kw in ["doc", "documentation", "wiki", "readme"]):
        return "documentation"
    if any(kw in desc or kw in tags for kw in ["research", "search", "scrape", "crawl"]):
        return "research"
    if any(kw in desc or kw in tags for kw in ["marketing", "seo", "content", "social"]):
        return "marketing"
    if any(kw in desc or kw in tags for kw in ["sales", "crm", "lead"]):
        return "sales"
    if any(kw in desc or kw in tags for kw in ["support", "customer", "ticket", "helpdesk"]):
        return "support"

    return "productivity"


def generate_skillsh_metadata(plugin_dir: Path) -> dict:
    """生成 skills.sh 所需的元数据"""
    plugin_json_path = plugin_dir / "plugin.json"
    if not plugin_json_path.exists():
        print(f"错误: plugin.json 不存在: {plugin_json_path}", file=sys.stderr)
        sys.exit(1)

    plugin = json.loads(plugin_json_path.read_text(encoding="utf-8"))

    # 收集技能信息
    skills = []
    skills_dir = plugin_dir / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            content = skill_md.read_text(encoding="utf-8", errors="ignore")
            # 提取 description
            desc = ""
            for line in content.split("\n"):
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                    break
            skills.append({
                "name": skill_dir.name,
                "description": desc,
                "path": f"skills/{skill_dir.name}",
            })

    category = categorize_plugin(plugin)

    # skills.sh package.json 格式
    skillsh_metadata = {
        "name": plugin["name"],
        "version": plugin["version"],
        "description": plugin.get("description", ""),
        "author": plugin.get("author", {}),
        "license": plugin.get("license", "MIT"),
        "category": category,
        "tags": plugin.get("keywords", plugin.get("tags", [])),
        "homepage": plugin.get("homepage", ""),
        "repository": plugin.get("repository", ""),
        # skills.sh 特有字段
        "skills": [s["name"] for s in skills],
        "installs": 0,  # 初始为 0，由 skills.sh 更新
        "verified": False,  # 提交后由 Vercel 审核
    }

    # 发布检查清单
    checklist = {
        "required": [
            {"item": "SKILL.md 有完整 frontmatter", "status": "pass" if skills else "fail"},
            {"item": "description 三要素（what + when + triggers）", "status": "warn"},
            {"item": "版本号从 1.0.0 开始", "status": "pass" if plugin["version"].startswith("1.") else "warn"},
            {"item": "README.md 存在", "status": "pass" if (plugin_dir / "README.md").exists() else "fail"},
            {"item": "LICENSE 文件", "status": "pass" if (plugin_dir / "LICENSE").exists() else "fail"},
        ],
        "recommended": [
            {"item": "示例代码", "status": "warn"},
            {"item": "CHANGELOG.md", "status": "warn"},
            {"item": "GitHub 仓库链接", "status": "pass" if plugin.get("repository") else "fail"},
        ],
    }

    return {
        "skillsh_metadata": skillsh_metadata,
        "publish_checklist": checklist,
        "publish_commands": [
            f"# 1. 初始化 npm 包（如果还没有）",
            f"npm init -y",
            f"",
            f"# 2. 发布到 skills.sh",
            f"npx skills.sh publish",
            f"",
            f"# 3. 或直接安装测试",
            f"npx plugins add {plugin.get('author', {}).get('name', 'your-org')}/{plugin['name']}",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Vercel skills.sh 发布元数据生成器")
    parser.add_argument("--plugin", required=True, help="插件目录路径")
    parser.add_argument("--output", help="输出目录（默认写到插件目录）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin).resolve()
    if not plugin_dir.exists():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    result = generate_skillsh_metadata(plugin_dir)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        metadata = result["skillsh_metadata"]
        print("=" * 60)
        print("Vercel skills.sh 发布元数据")
        print("=" * 60)
        print(f"\n插件名称: {metadata['name']}")
        print(f"版本: {metadata['version']}")
        print(f"分类: {metadata['category']}")
        print(f"标签: {', '.join(metadata['tags']) if metadata['tags'] else '无'}")
        print(f"包含技能: {len(metadata['skills'])} 个")

        print(f"\n发布检查清单:")
        for section, items in result["publish_checklist"].items():
            print(f"\n  {section.upper()}:")
            for item in items:
                icon = {"pass": "✅", "fail": "❌", "warn": "⚠️"}[item["status"]]
                print(f"    {icon} {item['item']}")

        print(f"\n发布命令:")
        for line in result["publish_commands"]:
            print(f"  {line}")

        print("=" * 60)

        # 保存元数据
        output_dir = Path(args.output) if args.output else plugin_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "skillsh.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\n✅ 元数据已保存: {output_dir / 'skillsh.json'}")


if __name__ == "__main__":
    main()
