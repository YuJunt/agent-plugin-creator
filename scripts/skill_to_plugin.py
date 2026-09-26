#!/usr/bin/env python3
"""
将现有 Skill 转化为完整专业的 Agent Plugin

与 plugin_to_skill.py（反向封装：插件→Skill）对称，
本脚本实现正向封装：Skill→插件。

功能：
  - 读取现有技能的 SKILL.md，自动提取 name 和 description
  - 创建符合 Agent Plugins 1.0.0 规范的插件目录结构
  - 生成 plugin.json（自动填充元数据）
  - 将现有技能完整复制到 skills/<skill-name>/ 下
  - 生成 README.md
  - 自动运行 validate 验证

用法：
    python3 skill_to_plugin.py <技能目录> [--output <输出目录>] [--force]
    python3 skill_to_plugin.py ./my-skill --output ./my-plugin
    python3 skill_to_plugin.py ./my-skill --name my-plugin --version 1.0.0 --force
    python3 skill_to_plugin.py ./my-skill --no-validate
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def parse_skill_frontmatter(skill_md_path: Path) -> dict:
    """解析 SKILL.md 的 YAML frontmatter，提取 name 和 description"""
    if not skill_md_path.exists():
        return {"name": "", "description": ""}

    content = skill_md_path.read_text(encoding="utf-8")
    result = {"name": "", "description": ""}

    if not content.startswith("---"):
        return result

    parts = content.split("---", 2)
    if len(parts) < 3:
        return result

    frontmatter = parts[1]
    for line in frontmatter.split("\n"):
        line = line.strip()
        if line.startswith("name:"):
            result["name"] = line.split(":", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            result["description"] = line.split(":", 1)[1].strip().strip('"').strip("'")

    return result


def generate_plugin_json(name: str, version: str, description: str) -> dict:
    """生成符合规范的 plugin.json"""
    return {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": name,
        "version": version,
        "description": description if description else f"{name} 插件",
        "author": {"name": "skill_to_plugin", "email": "example@example.com"},
        "license": "MIT",
        "keywords": [name, "skill", "agent-plugin"]
    }


def generate_readme(plugin_name: str, skill_name: str, description: str) -> str:
    """生成 README.md"""
    return f"""# {plugin_name}

> 由 skill_to_plugin.py 从 Skill `{skill_name}` 自动转化生成

{description if description else '基于现有 Skill 转化的 Agent Plugin。'}

## 目录结构

```
{plugin_name}/
├── plugin.json          # 插件清单
├── README.md            # 本文件
└── skills/
    └── {skill_name}/    # 原始 Skill（完整保留）
        ├── SKILL.md
        ├── scripts/
        ├── references/
        └── assets/
```

## 验证

```bash
python3 scripts/validate_plugin.py .
python3 scripts/audit_plugin.py .
```

## 安全检查清单（发布前必读）

本插件由现有 Skill 转化生成，原始技能可能存在以下安全问题，**发布前必须检查**：

### 1. 硬编码密钥/令牌
- [ ] 检查所有 Python 文件中是否有硬编码的 API key、token、secret、password
- [ ] 如有，使用 `--sanitize` 选项重新转化，或手动替换为环境变量引用
- [ ] 示例：`api_key = "xxx"` → `api_key = os.environ.get("API_KEY", "")`

### 2. 危险代码
- [ ] 检查是否使用了 `eval()`、`exec()`、`shell=True` 等危险调用
- [ ] 如有，评估是否可以替换为更安全的实现
- [ ] 如必须使用，添加严格的输入验证

### 3. 数据泄露
- [ ] 检查是否有将对话内容、用户数据发送到外部的代码
- [ ] 检查日志中是否打印了敏感信息（密钥、密码、用户隐私）

### 4. 路径安全
- [ ] 检查文件操作是否存在路径穿越风险（`../`）
- [ ] 检查是否限制了文件操作的根目录

### 5. 输入验证
- [ ] 检查所有工具参数是否有类型和范围验证
- [ ] 检查是否处理了异常输入

**自动检查命令：**
```bash
python3 scripts/audit_plugin.py .  # 安全审计
python3 scripts/check_completion.py .  # 完成度检查
```

## 打包

```bash
python3 scripts/package_plugin.py . --output ./dist
```

## 说明

本插件由现有 Skill 正向封装生成，原始 Skill 内容完整保留在 `skills/{skill_name}/` 下。
如需添加 MCP 服务器，请参考 `create_mcp_server.py`。

**注意：** 安全审计发现的问题是原始技能本身的问题，转化工具不会自动修改技能内容（除 `--sanitize` 选项外），请手动修复后再发布。
"""


def skill_to_plugin(skill_dir: Path, output_dir: Path, name: str = "",
                    version: str = "0.1.0", description: str = "",
                    force: bool = False, run_validate: bool = True,
                    run_audit: bool = True, sanitize: bool = False) -> dict:
    """
    将现有 Skill 转化为 Agent Plugin

    Args:
        skill_dir: 现有 Skill 目录路径
        output_dir: 输出插件目录路径
        name: 插件名称（默认从技能名推断）
        version: 版本号（默认 0.1.0）
        description: 插件描述（默认从技能 description 推断）
        force: 是否覆盖已有目录
        run_validate: 是否自动运行验证
        run_audit: 是否自动运行安全审计
        sanitize: 是否自动净化（替换硬编码密钥为环境变量引用）

    Returns:
        转化结果字典
    """
    result = {
        "success": False,
        "skill_dir": str(skill_dir),
        "output_dir": str(output_dir),
        "plugin_name": "",
        "skill_name": "",
        "files_copied": 0,
        "validate_passed": None,
        "audit_passed": None,
        "audit_critical": 0,
        "audit_high": 0,
        "audit_medium": 0,
        "audit_low": 0,
        "audit_issues": [],
        "sanitized": False,
        "secrets_replaced": 0,
        "errors": [],
        "warnings": []
    }

    # 1. 检查输入
    if not skill_dir.exists():
        result["errors"].append(f"技能目录不存在: {skill_dir}")
        return result

    if not skill_dir.is_dir():
        result["errors"].append(f"不是目录: {skill_dir}")
        return result

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result["errors"].append(f"找不到 SKILL.md: {skill_md}")
        return result

    # 2. 解析技能元数据
    meta = parse_skill_frontmatter(skill_md)
    skill_name = meta["name"] or skill_dir.name
    result["skill_name"] = skill_name

    # 插件名称：优先用 --name，其次用输出目录名（确保 name 与目录一致，符合规范）
    if name:
        plugin_name = name
    else:
        plugin_name = output_dir.name
    result["plugin_name"] = plugin_name

    plugin_description = description or meta["description"]
    if not plugin_description:
        plugin_description = f"基于 Skill '{skill_name}' 转化的插件"
        result["warnings"].append("技能 description 为空，使用默认描述")

    # 3. 检查输出目录
    if output_dir.exists():
        if not force:
            result["errors"].append(f"输出目录已存在: {output_dir}（使用 --force 覆盖）")
            return result
        shutil.rmtree(output_dir)

    # 4. 创建目录结构
    output_dir.mkdir(parents=True, exist_ok=True)
    skills_dir = output_dir / "skills" / skill_name
    skills_dir.mkdir(parents=True, exist_ok=True)

    # 5. 复制技能内容（排除 __pycache__、.git 等，跳过空目录）
    exclude_dirs = {"__pycache__", ".git", ".pytest_cache", "node_modules", "dist", "build"}
    exclude_files = {".pyc", ".pyo"}

    def _is_dir_empty(d: Path) -> bool:
        """检查目录是否为空（递归检查）"""
        for item in d.iterdir():
            if item.is_dir() and item.name not in exclude_dirs:
                if not _is_dir_empty(item):
                    return False
            elif item.is_file() and item.suffix not in exclude_files:
                return False
        return True

    files_copied = 0
    for item in skill_dir.iterdir():
        if item.is_dir():
            if item.name in exclude_dirs:
                continue
            if _is_dir_empty(item):
                continue  # 跳过空目录
            dest = skills_dir / item.name
            shutil.copytree(item, dest, ignore=shutil.ignore_patterns(*exclude_dirs, "*.pyc"))
            files_copied += 1
        elif item.is_file():
            if item.suffix in exclude_files:
                continue
            dest = skills_dir / item.name
            shutil.copy2(item, dest)
            files_copied += 1

    result["files_copied"] = files_copied

    # 6.5 可选：自动净化（替换硬编码密钥为环境变量引用）
    if sanitize:
        secrets_replaced = _sanitize_secrets(skills_dir)
        result["sanitized"] = True
        result["secrets_replaced"] = secrets_replaced
        if secrets_replaced > 0:
            result["warnings"].append(f"已自动净化 {secrets_replaced} 处硬编码密钥，替换为环境变量引用，请检查环境变量配置")

    # 6. 生成 plugin.json
    plugin_json = generate_plugin_json(plugin_name, version, plugin_description)
    (output_dir / "plugin.json").write_text(
        json.dumps(plugin_json, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    # 7. 生成 README.md
    readme = generate_readme(plugin_name, skill_name, plugin_description)
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    # 8. 自动验证
    if run_validate:
        try:
            script_dir = Path(__file__).resolve().parent
            validate_script = script_dir / "validate_plugin.py"
            if validate_script.exists():
                import subprocess
                proc = subprocess.run(
                    [sys.executable, str(validate_script), str(output_dir)],
                    capture_output=True, text=True, timeout=30
                )
                result["validate_passed"] = proc.returncode == 0
                if proc.returncode != 0:
                    result["warnings"].append("验证未完全通过，请检查输出")
            else:
                result["warnings"].append("找不到 validate_plugin.py，跳过验证")
        except Exception as e:
            result["warnings"].append(f"验证执行失败: {e}")

    # 9. 自动安全审计
    if run_audit:
        try:
            script_dir = Path(__file__).resolve().parent
            audit_script = script_dir / "audit_plugin.py"
            if audit_script.exists():
                import subprocess
                proc = subprocess.run(
                    [sys.executable, str(audit_script), str(output_dir)],
                    capture_output=True, text=True, timeout=60
                )
                # 解析审计结果
                audit_output = proc.stdout + proc.stderr
                import re
                critical_match = re.search(r"critical.*?:\s*(\d+)", audit_output, re.IGNORECASE)
                high_match = re.search(r"high.*?:\s*(\d+)", audit_output, re.IGNORECASE)
                medium_match = re.search(r"medium.*?:\s*(\d+)", audit_output, re.IGNORECASE)
                low_match = re.search(r"low.*?:\s*(\d+)", audit_output, re.IGNORECASE)

                result["audit_critical"] = int(critical_match.group(1)) if critical_match else 0
                result["audit_high"] = int(high_match.group(1)) if high_match else 0
                result["audit_medium"] = int(medium_match.group(1)) if medium_match else 0
                result["audit_low"] = int(low_match.group(1)) if low_match else 0
                result["audit_passed"] = (result["audit_critical"] == 0 and result["audit_high"] == 0)

                # 提取前 5 个具体问题
                issues = []
                for line in audit_output.split("\n"):
                    if any(kw in line for kw in ["CRITICAL", "HIGH", "[CRITICAL]", "[HIGH]"]):
                        issues.append(line.strip())
                        if len(issues) >= 5:
                            break
                result["audit_issues"] = issues

                if not result["audit_passed"]:
                    result["warnings"].append(
                        f"安全审计发现 {result['audit_critical']} 个 critical、{result['audit_high']} 个 high 问题，"
                        f"这些是原始技能本身的安全问题，建议修复后再发布"
                    )
            else:
                result["warnings"].append("找不到 audit_plugin.py，跳过安全审计")
        except Exception as e:
            result["warnings"].append(f"安全审计执行失败: {e}")

    result["success"] = len(result["errors"]) == 0
    return result


def _sanitize_secrets(skills_dir: Path) -> int:
    """
    自动净化硬编码密钥，替换为环境变量引用

    检测常见的硬编码密钥模式：
    - API key: api_key = "xxx", API_KEY = "xxx"
    - Token: token = "xxx", TOKEN = "xxx"
    - Secret: secret = "xxx", SECRET = "xxx"
    - Password: password = "xxx", PASSWORD = "xxx"

    替换为：os.environ.get("XXX")

    Returns:
        替换的密钥数量
    """
    import re

    replaced = 0
    # 常见的密钥变量名模式
    secret_patterns = [
        (r'(api_key\s*=\s*["\'])([^"\']+)(["\'])', 'API_KEY'),
        (r'(API_KEY\s*=\s*["\'])([^"\']+)(["\'])', 'API_KEY'),
        (r'(token\s*=\s*["\'])([^"\']+)(["\'])', 'TOKEN'),
        (r'(TOKEN\s*=\s*["\'])([^"\']+)(["\'])', 'TOKEN'),
        (r'(secret\s*=\s*["\'])([^"\']+)(["\'])', 'SECRET'),
        (r'(SECRET\s*=\s*["\'])([^"\']+)(["\'])', 'SECRET'),
        (r'(password\s*=\s*["\'])([^"\']+)(["\'])', 'PASSWORD'),
        (r'(PASSWORD\s*=\s*["\'])([^"\']+)(["\'])', 'PASSWORD'),
        (r'(app_id\s*=\s*["\'])([^"\']+)(["\'])', 'APP_ID'),
        (r'(APP_ID\s*=\s*["\'])([^"\']+)(["\'])', 'APP_ID'),
        (r'(app_secret\s*=\s*["\'])([^"\']+)(["\'])', 'APP_SECRET'),
        (r'(APP_SECRET\s*=\s*["\'])([^"\']+)(["\'])', 'APP_SECRET'),
    ]

    # 只处理 Python 文件
    for py_file in skills_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            original_content = content

            for pattern, env_name in secret_patterns:
                def replace_func(match, env_name=env_name):
                    nonlocal replaced
                    replaced += 1
                    # 提取变量名（去掉原始引号，直接赋值环境变量引用）
                    var_part = match.group(1).split('=')[0].strip() + ' = '
                    return f'{var_part}os.environ.get("{env_name}", "")'
                content = re.sub(pattern, replace_func, content)

            if content != original_content:
                # 确保导入了 os
                if "import os" not in content and "from os" not in content:
                    content = "import os\n" + content
                py_file.write_text(content, encoding="utf-8")
        except Exception:
            continue

    return replaced


def print_result(result: dict):
    """打印转化结果"""
    print("=" * 60)
    print("Skill → Agent Plugin 转化结果")
    print("=" * 60)

    if result["success"]:
        print(f"\n✅ 转化成功！")
    else:
        print(f"\n❌ 转化失败！")

    print(f"   技能目录: {result['skill_dir']}")
    print(f"   插件目录: {result['output_dir']}")
    print(f"   插件名称: {result['plugin_name']}")
    print(f"   技能名称: {result['skill_name']}")
    print(f"   复制文件: {result['files_copied']} 个")

    if result["validate_passed"] is not None:
        status = "✅ 通过" if result["validate_passed"] else "⚠️ 未完全通过"
        print(f"   自动验证: {status}")

    if result["audit_passed"] is not None:
        if result["audit_passed"]:
            print(f"   安全审计: ✅ 通过（0 critical, 0 high）")
        else:
            print(f"   安全审计: ⚠️ 发现问题（{result['audit_critical']} critical, {result['audit_high']} high）")
            print(f"             这些是原始技能本身的安全问题，建议修复后再发布")
            if result["audit_issues"]:
                print(f"             主要问题:")
                for issue in result["audit_issues"][:3]:
                    print(f"               - {issue[:80]}")

    if result.get("sanitized"):
        print(f"   自动净化: ✅ 已替换 {result['secrets_replaced']} 处硬编码密钥为环境变量引用")

    if result["warnings"]:
        print(f"\n⚠️  警告 ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"   - {w}")

    if result["errors"]:
        print(f"\n❌ 错误 ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"   - {e}")

    print("\n" + "=" * 60)
    if result["success"]:
        print("下一步:")
        print(f"  1. cd {result['output_dir']}")
        print("  2. 编辑 plugin.json 补充元数据")
        print("  3. python3 scripts/audit_plugin.py .  # 安全审计")
        print("  4. python3 scripts/package_plugin.py . --output ./dist  # 打包")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="将现有 Skill 转化为完整专业的 Agent Plugin（正向封装，与 plugin_to_skill.py 对称）"
    )
    parser.add_argument("skill_dir", help="现有 Skill 目录路径（必须包含 SKILL.md）")
    parser.add_argument("--output", "-o", help="输出插件目录路径（默认 ./<skill-name>-plugin）")
    parser.add_argument("--name", help="插件名称（默认从技能 name 推断）")
    parser.add_argument("--version", default="0.1.0", help="版本号（默认 0.1.0）")
    parser.add_argument("--description", help="插件描述（默认从技能 description 推断）")
    parser.add_argument("--force", "-f", action="store_true", help="覆盖已有输出目录")
    parser.add_argument("--no-validate", action="store_true", help="跳过自动验证")
    parser.add_argument("--no-audit", action="store_true", help="跳过自动安全审计")
    parser.add_argument("--sanitize", action="store_true", help="自动净化：替换硬编码密钥为环境变量引用")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()

    # 推断默认输出目录（用技能名，不带 -plugin 后缀，确保 name 与目录一致）
    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        output_dir = Path.cwd() / skill_dir.name

    result = skill_to_plugin(
        skill_dir=skill_dir,
        output_dir=output_dir,
        name=args.name,
        version=args.version,
        description=args.description,
        force=args.force,
        run_validate=not args.no_validate,
        run_audit=not args.no_audit,
        sanitize=args.sanitize
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_result(result)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
