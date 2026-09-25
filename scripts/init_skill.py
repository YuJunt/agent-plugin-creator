#!/usr/bin/env python3
"""
Agent Skill 脚手架生成器（基于 agentskills.io 官方规范）

用法:
    python3 init_skill.py <skill-name> --path <输出目录> [--force]

幂等设计: 默认不覆盖已有目录。使用 --force 覆盖。

生成符合 agentskills.io 官方规范的 skill 目录结构:
    skill-name/
    ├── SKILL.md          # 含官方规范的 frontmatter 模板
    ├── scripts/          # 示例脚本（可删除）
    ├── references/       # 示例参考（可删除）
    └── assets/           # 示例资源（可删除）
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# agentskills.io 官方 name 规范: 小写字母+数字+连字符, 1-64字符, 不以连字符开头/结尾, 无连续连字符
NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

EXAMPLE_SCRIPT_CONTENT = '''#!/usr/bin/env python3
"""示例脚本 - 根据需要修改或删除。

技能脚本应:
- 自包含或清楚记录依赖
- 包含有帮助的错误消息
- 优雅处理边界情况
- 避免交互式提示（agent 在非交互式 shell 中运行）
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="示例脚本")
    parser.add_argument("--input", help="输入文件路径")
    args = parser.parse_args()

    # TODO: 实现实际逻辑
    print(f"处理中: {args.input or '(无输入)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

REFERENCE_CONTENT = """# 参考文档

在此放置详细的技术参考、API 文档、领域知识等。
agent 按需加载此文件，保持内容聚焦。
"""


def validate_name(name: str) -> list:
    """验证 skill name 是否符合 agentskills.io 官方规范"""
    errors = []
    if not name:
        errors.append("name 不能为空")
        return errors
    if len(name) > 64:
        errors.append(f"name 长度超过 64 字符: {len(name)}")
    if not NAME_PATTERN.match(name):
        errors.append(
            f"name 不符合官方规范: '{name}'\n"
            f"   规则: 1-64字符，仅小写字母(a-z)、数字(0-9)、连字符(-)\n"
            f"   必须以字母数字开头和结尾，不能有连续连字符(--)"
        )
    if "--" in name:
        errors.append("name 不能包含连续连字符 (--)")
    return errors


def create_skill(name: str, output_path: str, force: bool = False) -> Path:
    """创建 skill 目录结构

    幂等设计：默认不覆盖已有目录。如需覆盖，使用 force=True。
    """
    skill_dir = Path(output_path) / name

    if skill_dir.exists():
        if force:
            shutil.rmtree(skill_dir)
            print(f"⚠️  已删除已有目录并重新创建: {skill_dir}")
        else:
            print(f"错误: 目录已存在: {skill_dir}", file=sys.stderr)
            print(f"提示: 使用 --force 覆盖已有目录", file=sys.stderr)
            sys.exit(1)

    # 创建目录
    for sub in ["", "scripts", "references", "assets"]:
        (skill_dir / sub).mkdir(parents=True, exist_ok=True)

    # 生成 title（首字母大写，连字符转空格）
    title = name.replace("-", " ").title()

    # 创建 SKILL.md
    skill_md_content = f"""---
name: {name}
description: 描述这个 skill 做什么，以及什么时候应该使用它。包含具体的触发场景和关键词。（1-1024字符）
---

# {title}

## 概述
简要说明这个 skill 的用途和它解决的问题。

## 工作流程
按步骤描述执行流程：

1. 第一步做什么
2. 第二步做什么
3. 第三步做什么

## 关键规则
- 规则一
- 规则二

## 边界情况与 Gotchas
- 列出违背合理假设的环境特定事实
- 这些通常是 skill 中价值最高的内容

## 参考资源
- 详细文档参见 references/ 目录
- 可执行脚本参见 scripts/ 目录
"""
    (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

    # 创建示例脚本
    example_script = skill_dir / "scripts" / "example.py"
    example_script.write_text(EXAMPLE_SCRIPT_CONTENT, encoding="utf-8")
    os.chmod(example_script, 0o755)

    # 创建示例参考
    (skill_dir / "references" / "REFERENCE.md").write_text(REFERENCE_CONTENT, encoding="utf-8")

    # assets 占位
    (skill_dir / "assets" / ".gitkeep").write_text("", encoding="utf-8")

    return skill_dir


def main():
    import json
    parser = argparse.ArgumentParser(
        description="Agent Skill 脚手架生成器（基于 agentskills.io 官方规范）"
    )
    parser.add_argument("name", help="Skill 名称（小写字母+数字+连字符）")
    parser.add_argument("--path", default=".", help="输出目录（默认当前目录）")
    parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已有目录（默认不覆盖，幂等设计）",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    args = parser.parse_args()

    # 验证 name
    errors = validate_name(args.name)
    if errors:
        if args.json:
            print(json.dumps({"success": False, "errors": errors}, ensure_ascii=False, indent=2))
        else:
            print("名称验证失败:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    # 创建 skill
    skill_dir = create_skill(args.name, args.path, force=args.force)

    if args.json:
        result = {
            "success": True,
            "name": args.name,
            "path": str(skill_dir),
            "structure": ["SKILL.md", "scripts/", "references/", "assets/"],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    print(f"✅ Skill 创建成功: {skill_dir}")
    print()

    # 用官方 skill-creator 的 quick_validate.py 做额外验证
    quick_validate = Path(__file__).resolve().parent.parent / "official" / "skill-creator" / "scripts" / "quick_validate.py"
    if quick_validate.exists():
        print("🔍 官方规范验证（official/skill-creator/quick_validate.py）...")
        result = subprocess.run(
            [sys.executable, str(quick_validate), str(skill_dir)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
        else:
            print(f"⚠️  {result.stdout.strip()}")
        print()

    print("目录结构:")
    print(f"  {args.name}/")
    print(f"  ├── SKILL.md          # 必需：编辑 frontmatter 和指令")
    print(f"  ├── scripts/          # 可执行代码（示例可删除）")
    print(f"  ├── references/       # 参考文档（示例可删除）")
    print(f"  └── assets/           # 静态资源（按需添加）")
    print()
    print("下一步:")
    print(f"  1. 编辑 {args.name}/SKILL.md 的 description 字段（描述做什么+什么时候用）")
    print(f"  2. 编写 SKILL.md body 的工作流和 gotchas")
    print(f"  3. 删除不需要的示例文件，添加实际需要的脚本和参考")
    print(f"  4. 运行 validate_skill.py 验证规范符合性")


if __name__ == "__main__":
    main()
