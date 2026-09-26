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

# 导入共享模板生成器
sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_template import generate_skill_md_template

# agentskills.io 官方 name 规范: 小写字母+数字+连字符, 1-64字符, 不以连字符开头/结尾, 无连续连字符
NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

EXAMPLE_SCRIPT_CONTENT = '''#!/usr/bin/env python3
"""TODO - 替换为实际功能描述

> **AI 生成指南（生成后删除此部分）**
>
> 生成此模板后，AI 必须根据用户需求自动生成完整脚本，不要留 TODO：
>
> 1. 功能实现：根据用户需求，实现实际业务逻辑
> 2. 错误处理：所有边界情况都要有错误处理
> 3. 命令行参数：用 argparse，不要交互式提示
> 4. 输出格式：输出要友好，用户能直接看懂
> 5. 依赖说明：顶部 docstring 说明依赖
>
> 质量标准：所有参数有 help、错误有提示和退出码、输出友好
> 示例代码见 references/script-example.md

技能脚本应:
- 自包含或清楚记录依赖
- 包含有帮助的错误消息
- 优雅处理边界情况
- 避免交互式提示（agent 在非交互式 shell 中运行）
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="TODO - 替换为实际功能",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 script.py --param "test"
  python3 script.py --param ""  # 会报错
""",
    )
    parser.add_argument("--param", required=True, help="TODO - 参数说明（必填）")
    args = parser.parse_args()

    # 错误处理：检查参数
    if not args.param.strip():
        print("错误: 参数不能为空", file=sys.stderr)
        print("提示: 请提供有效的参数值", file=sys.stderr)
        return 1

    # TODO: 实现实际逻辑
    print(f"处理中: {args.param}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

SCRIPT_EXAMPLE_CONTENT = '''# 脚本示例（天气查询）

```python
#!/usr/bin/env python3
"""天气查询脚本 - 查询指定城市的实时天气
依赖: 无（使用模拟数据）
"""
import argparse

WEATHER_DATA = {
    "北京": {"temp": 25, "condition": "多云", "humidity": 60},
    "上海": {"temp": 28, "condition": "晴", "humidity": 70},
}

def main():
    parser = argparse.ArgumentParser(description="天气查询")
    parser.add_argument("--city", required=True, help="城市名称")
    args = parser.parse_args()

    if args.city in WEATHER_DATA:
        w = WEATHER_DATA[args.city]
        print(f"{args.city}: {w['temp']}°C, {w['condition']}, 湿度 {w['humidity']}%")
    else:
        print(f"错误: 不支持的城市: {args.city}")
        print(f"支持的城市: {', '.join(WEATHER_DATA.keys())}")
        return 1

if __name__ == "__main__":
    main()
```
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


def create_skill(name: str, output_path: str, force: bool = False, lang: str = "en") -> Path:
    """创建 skill 目录结构

    幂等设计：默认不覆盖已有目录。如需覆盖，使用 force=True。
    lang: 模板语言，"en"（默认）或 "zh"
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

    # 创建 SKILL.md（默认英文模板，--lang zh 使用中文模板）
    if lang == "zh":
        skill_md_content = generate_skill_md_template(
            name=name,
            description="",
            lang="zh",
            title=title
        )
    else:
        skill_md_content = generate_skill_md_template(
            name=name,
            description="",
            lang="en",
            title=title
        )
    (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

    # 创建示例脚本
    example_script = skill_dir / "scripts" / "example.py"
    example_script.write_text(EXAMPLE_SCRIPT_CONTENT, encoding="utf-8")
    os.chmod(example_script, 0o755)

    # 创建脚本示例文档
    (skill_dir / "references" / "script-example.md").write_text(
        SCRIPT_EXAMPLE_CONTENT, encoding="utf-8"
    )

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
    parser.add_argument("--lang", choices=["en", "zh"], default="en", help="SKILL.md 模板语言（默认 en 英文，zh 中文）")
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
    skill_dir = create_skill(args.name, args.path, force=args.force, lang=args.lang)

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
    print()
    print("=" * 60)
    print("✅ Skill 创建成功！接下来怎么做：")
    print("=" * 60)
    print()
    print("1. 【填充内容】编辑 SKILL.md，根据 AI 填充指南写实际内容")
    print(f"   文件: {args.name}/SKILL.md")
    print()
    print("2. 【写脚本】删除 example.py，写实际功能脚本")
    print(f"   目录: {args.name}/scripts/")
    print()
    print("3. 【验证】运行验证，检查是否符合规范")
    print(f"   命令: python3 scripts/validate_skill.py {args.name}")
    print()
    print("4. 【打包】如果是完整插件，运行打包命令")
    print(f"   命令: python3 scripts/plugin.py package .")
    print()


if __name__ == "__main__":
    main()
