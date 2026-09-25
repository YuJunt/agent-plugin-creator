#!/usr/bin/env python3
"""
从已有 MCP 服务器代码反推生成插件

扫描已有 MCP 服务器代码，提取工具名称和参数，自动生成 plugin.json + mcp.json + skill 骨架。

用法:
    python3 scripts/reverse_engineer.py <服务器目录> --output <插件目录>
    python3 scripts/reverse_engineer.py ./my-mcp-server --output ./my-plugin --name my-plugin
    python3 scripts/reverse_engineer.py ./server --output ./plugin --language python
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path


def detect_language(server_dir: Path) -> str:
    """检测服务器语言"""
    if (server_dir / "server.py").exists() or list(server_dir.glob("*.py")):
        return "python"
    if (server_dir / "src" / "server.ts").exists() or list(server_dir.glob("*.ts")):
        return "typescript"
    if (server_dir / "package.json").exists():
        return "typescript"
    return "unknown"


def extract_python_tools(server_dir: Path) -> list:
    """从 Python FastMCP 代码提取工具"""
    tools = []
    py_files = list(server_dir.glob("**/*.py"))

    for py_file in py_files:
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            # FastMCP @mcp.tool() 装饰器
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    dec_str = ast.dump(decorator)
                    if "tool" in dec_str or "tool" in getattr(decorator, "attr", ""):
                        tool = {
                            "name": node.name,
                            "description": ast.get_docstring(node) or "",
                            "parameters": _extract_python_params(node),
                            "source_file": str(py_file.relative_to(server_dir)),
                        }
                        tools.append(tool)
                        break

            # 也检查 mcp.tool() 调用方式
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "tool":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        tool_name = node.args[0].value
                        tools.append({
                            "name": tool_name,
                            "description": node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "",
                            "parameters": {"type": "object", "properties": {}},
                            "source_file": str(py_file.relative_to(server_dir)),
                        })

    return tools


def _extract_python_params(func_node: ast.FunctionDef) -> dict:
    """从 Python 函数提取参数 schema"""
    properties = {}
    required = []

    type_map = {
        "str": "string", "int": "integer", "float": "number",
        "bool": "boolean", "list": "array", "dict": "object",
    }

    args = func_node.args
    all_args = args.args + args.kwonlyargs
    defaults = args.defaults + [None] * (len(args.kwonlyargs) - len(args.kw_defaults))

    for i, arg in enumerate(all_args):
        if arg.arg in ("self", "cls"):
            continue

        param_type = "string"
        if arg.annotation:
            ann_str = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else ""
            for py_type, json_type in type_map.items():
                if py_type in ann_str:
                    param_type = json_type
                    break

        properties[arg.arg] = {"type": param_type}

        # 判断是否必填（没有默认值）
        default_idx = len(all_args) - len(defaults)
        if i >= default_idx:
            default_val = defaults[i - default_idx]
            if default_val is None:
                required.append(arg.arg)
        else:
            required.append(arg.arg)

    return {"type": "object", "properties": properties, "required": required}


def extract_typescript_tools(server_dir: Path) -> list:
    """从 TypeScript MCP 代码提取工具"""
    tools = []
    ts_files = list(server_dir.glob("**/*.ts")) + list(server_dir.glob("**/*.js"))

    for ts_file in ts_files:
        try:
            content = ts_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        # 匹配 server.tool("name", "desc", schema, handler)
        pattern = r'server\.tool\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']'
        for match in re.finditer(pattern, content):
            tool_name = match.group(1)
            tool_desc = match.group(2)
            tools.append({
                "name": tool_name,
                "description": tool_desc,
                "parameters": {"type": "object", "properties": {}},
                "source_file": str(ts_file.relative_to(server_dir)),
            })

        # 匹配 @mcp.tool() 装饰器（TypeScript 装饰器风格）
        decorator_pattern = r'@mcp\.tool\(\)[\s\S]*?(?:async\s+)?(\w+)\s*\('
        for match in re.finditer(decorator_pattern, content):
            tool_name = match.group(1)
            tools.append({
                "name": tool_name,
                "description": "",
                "parameters": {"type": "object", "properties": {}},
                "source_file": str(ts_file.relative_to(server_dir)),
            })

    return tools


def generate_plugin(name: str, version: str, language: str, tools: list, server_dir: Path, output_dir: Path):
    """生成插件结构"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. plugin.json
    plugin = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": name,
        "version": version,
        "description": f"Auto-generated plugin from {server_dir.name}",
    }
    (output_dir / "plugin.json").write_text(
        json.dumps(plugin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 2. mcp.json
    server_name = name.replace(".", "-") + "-server"
    if language == "python":
        command = "python3"
        args = [f"./servers/{server_name}/server.py"]
    else:
        command = "node"
        args = [f"./servers/{server_name}/dist/server.js"]

    mcp = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        "mcpServers": {
            server_name: {
                "type": "stdio",
                "command": command,
                "args": args,
                "cwd": "./",
            }
        },
    }
    (output_dir / "mcp.json").write_text(
        json.dumps(mcp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 3. 复制服务器代码
    import shutil
    dest_server = output_dir / "servers" / server_name
    if dest_server.exists():
        shutil.rmtree(dest_server)
    shutil.copytree(server_dir, dest_server)

    # 4. 生成 Skill 骨架
    skill_name = name.replace(".", "-")
    skill_dir = output_dir / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    tool_list_md = "\n".join(f"- `{t['name']}`: {t['description'] or '（无描述）'}" for t in tools)

    skill_md = f"""---
name: {skill_name}
description: Auto-generated skill for {name} plugin. Provides access to {len(tools)} MCP tools. Use when user needs to interact with {server_name}.
---

# {skill_name}

> 由 reverse_engineer.py 自动生成，请根据实际需求修改 description 和工作流。

## 可用工具

{tool_list_md}

## 工作流

1. 确认用户需要调用哪个工具
2. 通过 MCP 连接器调用对应工具
3. 解析返回结果并展示给用户

## 注意事项

- 此 Skill 为自动生成骨架，需要人工完善
- 工具参数详情请参考服务器代码
- 建议添加具体的使用示例和边界情况处理
"""
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # 5. 生成工具定义文件（供参考）
    tools_def = {
        "server": server_name,
        "language": language,
        "tools": tools,
    }
    (output_dir / "tools-definition.json").write_text(
        json.dumps(tools_def, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return {
        "plugin": plugin,
        "mcp": mcp,
        "tools_count": len(tools),
        "skill_name": skill_name,
        "server_name": server_name,
    }


def main():
    parser = argparse.ArgumentParser(description="从已有 MCP 服务器代码反推生成插件")
    parser.add_argument("server_dir", help="MCP 服务器目录路径")
    parser.add_argument("--output", required=True, help="输出插件目录")
    parser.add_argument("--name", help="插件名称（默认使用服务器目录名）")
    parser.add_argument("--version", default="0.1.0", help="插件版本号")
    parser.add_argument("--language", choices=["python", "typescript", "auto"], default="auto", help="服务器语言")
    parser.add_argument("--dry-run", action="store_true", help="只分析不生成")
    args = parser.parse_args()

    server_dir = Path(args.server_dir).resolve()
    if not server_dir.is_dir():
        print(f"错误: 服务器目录不存在: {server_dir}", file=sys.stderr)
        sys.exit(1)

    # 检测语言
    language = args.language
    if language == "auto":
        language = detect_language(server_dir)
        if language == "unknown":
            print("错误: 无法自动检测服务器语言，请使用 --language 指定", file=sys.stderr)
            sys.exit(1)

    print(f"🔍 检测到语言: {language}")

    # 提取工具
    if language == "python":
        tools = extract_python_tools(server_dir)
    else:
        tools = extract_typescript_tools(server_dir)

    print(f"🔍 提取到 {len(tools)} 个工具:")
    for t in tools:
        print(f"  - {t['name']}: {t['description'][:50] if t['description'] else '（无描述）'}")

    if not tools:
        print("⚠️  未提取到工具，可能是代码风格不支持自动解析", file=sys.stderr)

    if args.dry_run:
        print("\n📋 Dry-run 模式，不生成文件")
        return

    # 生成插件
    plugin_name = args.name or server_dir.name
    output_dir = Path(args.output).resolve()

    result = generate_plugin(plugin_name, args.version, language, tools, server_dir, output_dir)

    print(f"\n✅ 插件已生成: {output_dir}")
    print(f"   名称: {plugin_name} v{args.version}")
    print(f"   工具: {result['tools_count']} 个")
    print(f"   Skill: {result['skill_name']}")
    print(f"   服务器: {result['server_name']}")
    print(f"\n⚠️  注意: 这是自动生成的骨架，请人工完善:")
    print(f"   1. 修改 skills/{result['skill_name']}/SKILL.md 的 description 和工作流")
    print(f"   2. 验证 mcp.json 的 command 和 args 路径正确")
    print(f"   3. 运行 validate_plugin.py 验证规范合规性")
    print(f"   4. 运行 test_mcp_handshake.py 验证服务器可启动")


if __name__ == "__main__":
    main()
