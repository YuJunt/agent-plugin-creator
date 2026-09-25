#!/usr/bin/env python3
"""
验证失败自动修复工具

运行 validate_plugin，解析错误，自动修复常见错误，然后重新验证。

用法:
    python3 scripts/auto_fix.py <插件目录>
    python3 scripts/auto_fix.py <插件目录> --dry-run
    python3 scripts/auto_fix.py <插件目录> --json
    python3 scripts/auto_fix.py <插件目录> --max-attempts 5
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run_validate(plugin_dir: Path, skill_root: Path) -> tuple:
    """运行 validate_plugin，返回 (returncode, stdout, stderr)"""
    validate_script = skill_root / "scripts" / "validate_plugin.py"
    result = subprocess.run(
        [sys.executable, str(validate_script), str(plugin_dir)],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def fix_path_issues(plugin_dir: Path, errors: list) -> list:
    """修复路径问题：command 路径加 ./ 前缀"""
    fixed = []
    mcp_json = plugin_dir / "mcp.json"

    if not mcp_json.exists():
        return fixed

    try:
        mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fixed

    changed = False
    for server_name, config in mcp.get("mcpServers", {}).items():
        command = config.get("command", "")
        # 如果 command 含 / 但不以 ./ 开头，加上 ./
        if "/" in command and not command.startswith("./") and not command.startswith("/"):
            config["command"] = "./" + command
            changed = True
            fixed.append(f"mcp.json: {server_name}.command 路径加 ./ 前缀")

        # args 中的路径也检查
        new_args = []
        for arg in config.get("args", []):
            if "/" in arg and not arg.startswith("./") and not arg.startswith("/") and not arg.startswith("-"):
                new_args.append("./" + arg)
                changed = True
                fixed.append(f"mcp.json: {server_name}.args 路径加 ./ 前缀")
            else:
                new_args.append(arg)
        if new_args != config.get("args", []):
            config["args"] = new_args

    if changed:
        mcp_json.write_text(json.dumps(mcp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return fixed


def fix_unknown_fields(plugin_dir: Path, errors: list) -> list:
    """修复未知顶层字段：移到 extensions 下"""
    fixed = []
    plugin_json = plugin_dir / "plugin.json"

    if not plugin_json.exists():
        return fixed

    try:
        plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fixed

    # 已知允许的顶层字段
    allowed_fields = {"$schema", "name", "version", "description", "license", "extensions", "skills", "mcpServers"}

    unknown = [k for k in plugin if k not in allowed_fields]
    if unknown:
        if "extensions" not in plugin:
            plugin["extensions"] = {}
        if "agent-plugin-creator" not in plugin["extensions"]:
            plugin["extensions"]["agent-plugin-creator"] = {}

        for field in unknown:
            plugin["extensions"]["agent-plugin-creator"][field] = plugin.pop(field)
            fixed.append(f"plugin.json: 未知字段 '{field}' 移到 extensions.agent-plugin-creator")

        plugin_json.write_text(json.dumps(plugin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return fixed


def fix_schema_version(plugin_dir: Path, errors: list) -> list:
    """修复 schema 版本不一致"""
    fixed = []
    plugin_json = plugin_dir / "plugin.json"
    mcp_json = plugin_dir / "mcp.json"

    if not plugin_json.exists() or not mcp_json.exists():
        return fixed

    try:
        plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
        mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fixed

    plugin_schema = plugin.get("$schema", "")
    mcp_schema = mcp.get("$schema", "")

    # 提取版本号
    plugin_ver = re.search(r"/(\d+\.\d+\.\d+)/", plugin_schema)
    mcp_ver = re.search(r"/(\d+\.\d+\.\d+)/", mcp_schema)

    if plugin_ver and mcp_ver and plugin_ver.group(1) != mcp_ver.group(1):
        # 以 plugin.json 为准
        new_mcp_schema = mcp_schema.replace(mcp_ver.group(1), plugin_ver.group(1))
        mcp["$schema"] = new_mcp_schema
        mcp_json.write_text(json.dumps(mcp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        fixed.append(f"mcp.json: schema 版本统一为 {plugin_ver.group(1)}")

    return fixed


def fix_missing_fields(plugin_dir: Path, errors: list) -> list:
    """修复缺失的必需字段"""
    fixed = []
    plugin_json = plugin_dir / "plugin.json"

    if not plugin_json.exists():
        # 创建最小 plugin.json
        plugin = {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": plugin_dir.name,
            "version": "0.1.0",
        }
        plugin_json.write_text(json.dumps(plugin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        fixed.append("plugin.json: 创建最小 plugin.json")
        return fixed

    try:
        plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fixed

    if "$schema" not in plugin:
        plugin["$schema"] = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
        fixed.append("plugin.json: 添加 $schema 字段")

    if "name" not in plugin:
        plugin["name"] = plugin_dir.name
        fixed.append("plugin.json: 添加 name 字段")

    if fixed:
        plugin_json.write_text(json.dumps(plugin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return fixed


def fix_skill_name_mismatch(plugin_dir: Path, errors: list) -> list:
    """修复 skill 目录名与 frontmatter name 不一致"""
    fixed = []
    skills_dir = plugin_dir / "skills"

    if not skills_dir.is_dir():
        return fixed

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        content = skill_md.read_text(encoding="utf-8")
        match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
        if match:
            frontmatter_name = match.group(1).strip()
            dir_name = skill_dir.name
            if frontmatter_name != dir_name:
                # 修改 frontmatter 的 name 为目录名
                content = re.sub(r'^name:\s*.+$', f'name: {dir_name}', content, flags=re.MULTILINE)
                skill_md.write_text(content, encoding="utf-8")
                fixed.append(f"skills/{dir_name}/SKILL.md: name 从 '{frontmatter_name}' 改为 '{dir_name}'")

    return fixed


def fix_env_reserved_vars(plugin_dir: Path, errors: list) -> list:
    """修复 mcp.json 中的保留环境变量名"""
    fixed = []
    mcp_json = plugin_dir / "mcp.json"

    if not mcp_json.exists():
        return fixed

    try:
        mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fixed

    reserved = {"PLUGIN_ROOT", "PLUGIN_DATA"}
    changed = False

    for server_name, config in mcp.get("mcpServers", {}).items():
        env = config.get("env", {})
        for var in list(env.keys()):
            if var in reserved:
                new_var = f"PLUGIN_{var}"  # 重命名避免冲突
                env[new_var] = env.pop(var)
                changed = True
                fixed.append(f"mcp.json: {server_name}.env 保留变量 '{var}' 重命名为 '{new_var}'")

    if changed:
        mcp_json.write_text(json.dumps(mcp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return fixed


# 修复器注册表：按优先级排序
FIXERS = [
    ("missing_fields", fix_missing_fields),
    ("unknown_fields", fix_unknown_fields),
    ("path_issues", fix_path_issues),
    ("schema_version", fix_schema_version),
    ("skill_name_mismatch", fix_skill_name_mismatch),
    ("env_reserved_vars", fix_env_reserved_vars),
]


def main():
    parser = argparse.ArgumentParser(description="验证失败自动修复工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--dry-run", action="store_true", help="只检测不修复")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--max-attempts", type=int, default=3, help="最大修复尝试次数")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    skill_root = Path(__file__).resolve().parents[1]
    all_fixes = []
    attempts = 0

    for attempt in range(args.max_attempts):
        attempts += 1

        # 运行验证
        rc, stdout, stderr = run_validate(plugin_dir, skill_root)

        if rc == 0:
            break

        if args.dry_run:
            # 只报告错误，不修复
            if not args.json:
                print(f"[尝试 {attempts}] 验证失败，但 dry-run 模式不修复")
                print(stdout[:500])
            break

        # 尝试修复
        errors = stdout + stderr
        attempt_fixes = []

        for fixer_name, fixer_func in FIXERS:
            try:
                fixes = fixer_func(plugin_dir, [errors])
                attempt_fixes.extend(fixes)
            except Exception as e:
                attempt_fixes.append(f"修复器 {fixer_name} 异常: {e}")

        if not attempt_fixes:
            # 没有可自动修复的问题
            if not args.json:
                print(f"[尝试 {attempts}] 无法自动修复以下错误:")
                print(stdout[:1000])
            break

        all_fixes.extend(attempt_fixes)

        if not args.json:
            print(f"[尝试 {attempts}] 修复了 {len(attempt_fixes)} 个问题:")
            for f in attempt_fixes:
                print(f"  - {f}")

    # 最终验证
    final_rc, final_stdout, final_stderr = run_validate(plugin_dir, skill_root)
    final_passed = final_rc == 0

    result = {
        "plugin_dir": str(plugin_dir),
        "attempts": attempts,
        "fixes": all_fixes,
        "total_fixes": len(all_fixes),
        "final_passed": final_passed,
        "dry_run": args.dry_run,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 50)
        print(f"自动修复完成")
        print("=" * 50)
        print(f"尝试次数: {attempts}")
        print(f"修复问题: {len(all_fixes)} 个")
        print(f"最终验证: {'✅ 通过' if final_passed else '❌ 仍有错误'}")

        if all_fixes:
            print("\n修复详情:")
            for f in all_fixes:
                print(f"  - {f}")

        if not final_passed and not args.dry_run:
            print("\n⚠️  仍有无法自动修复的错误，请手动处理:")
            print(final_stdout[:500])

        print("=" * 50)

    sys.exit(0 if final_passed or args.dry_run else 1)


if __name__ == "__main__":
    main()
