#!/usr/bin/env python3
"""
MCP 服务器代码生成器（基于官方 SDK，支持 tools/resources/prompts）

用法:
    # 生成完整服务器（支持 tools + resources + prompts）
    python3 create_mcp_server.py generate \
        --language typescript --transport stdio --name my-server \
        --definition definition.json --output ./output [--force]

    # 向已有项目添加新工具
    python3 create_mcp_server.py add --project ./existing --tool new_tool.json

    # 列出已有项目的组件
    python3 create_mcp_server.py list --project ./existing

定义文件格式（对象格式）:
    {"tools": [...], "resources": [...], "prompts": [...]}
向后兼容：也支持纯数组格式（只包含 tools）。
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_DIR / "assets" / "templates" / "mcp-server"


def load_definition(def_path: str) -> dict:
    """加载定义文件，支持对象格式和纯数组格式（向后兼容）"""
    path = Path(def_path)
    if not path.exists():
        print(f"错误: 定义文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: 定义文件不是有效 JSON: {e}", file=sys.stderr)
        sys.exit(1)
    if isinstance(data, list):
        data = {"tools": data}
    if not isinstance(data, dict):
        print("错误: 定义必须是对象或数组", file=sys.stderr)
        sys.exit(1)
    data.setdefault("tools", [])
    data.setdefault("resources", [])
    data.setdefault("prompts", [])
    for i, tool in enumerate(data["tools"]):
        if not isinstance(tool, dict) or "name" not in tool:
            print(f"错误: 第 {i+1} 个工具格式无效（缺少 name 字段）", file=sys.stderr)
            sys.exit(1)
        # description 可选（MCP 规范中为推荐字段），缺省补空字符串
        tool.setdefault("description", "")
    return data


def normalize_params(tool: dict) -> dict:
    """从 tool 定义中提取参数表，兼容两种格式。

    1. 扁平格式（旧）:
       {"parameters": {"order_id": {"type": "string", "required": True, "description": "..."}}}
    2. 标准 JSON Schema:
       {"input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                         "required": ["order_id"]}}
       或 {"parameters": {"type": "object", "properties": {...}, "required": [...]}}

    返回统一结构: {参数名: {"type": str, "required": bool, "description": str}}
    """
    raw = tool.get("input_schema") or tool.get("parameters") or {}
    tname = tool.get("name", "?")
    if not isinstance(raw, dict):
        print(f"错误: 工具 '{tname}' 的参数定义必须是对象", file=sys.stderr)
        sys.exit(1)

    # 标准 JSON Schema: {"type": "object", "properties": {...}, "required": [...]}
    if raw.get("type") == "object" and isinstance(raw.get("properties"), dict):
        props = raw["properties"]
        required_list = raw.get("required", [])
        if not isinstance(required_list, list):
            required_list = []
        params = {}
        for pname, pdef in props.items():
            if not isinstance(pdef, dict):
                print(f"错误: 工具 '{tname}' 参数 '{pname}' 定义必须是对象", file=sys.stderr)
                sys.exit(1)
            entry = {"type": pdef.get("type", "string"),
                     "required": pname in required_list}
            if "description" in pdef:
                entry["description"] = pdef["description"]
            params[pname] = entry
        return params

    # 扁平格式: {参数名: {type, required, description}}
    params = {}
    for pname, pdef in raw.items():
        if not isinstance(pdef, dict):
            print(
                f"错误: 工具 '{tname}' 参数 '{pname}' 定义必须是对象，收到 {type(pdef).__name__}。\n"
                f"      请使用标准 JSON Schema 格式: "
                f'{{"type":"object","properties":{{"{pname}":{{"type":"string"}}}},"required":["{pname}"]}}',
                file=sys.stderr,
            )
            sys.exit(1)
        entry = {"type": pdef.get("type", "string"),
                 "required": pdef.get("required", True)}
        if "description" in pdef:
            entry["description"] = pdef["description"]
        params[pname] = entry
    return params


def ts_type(param: dict) -> str:
    ptype = param.get("type", "string")
    required = param.get("required", True)
    desc = param.get("description", "")
    type_map = {"string": "z.string()", "number": "z.number()", "integer": "z.number().int()",
                "boolean": "z.boolean()", "array": "z.array(z.any())", "object": "z.record(z.any())"}
    code = type_map.get(ptype, "z.string()")
    if desc:
        code += f'.describe("{desc}")'
    if not required:
        code += ".optional()"
    return code


def _ts_param_list(names: list) -> str:
    return ", ".join([f"${{{n}}}" for n in names])


def generate_typescript_server(name: str, definition: dict, transport: str) -> str:
    tools, resources, prompts = definition["tools"], definition["resources"], definition["prompts"]
    lines = ['/**', f' * MCP Server: {name}', ' * 由 create_mcp_server.py 自动生成',
             ' * 基于官方 @modelcontextprotocol/sdk',
             ' *',
             ' * 安全基线（对齐 OWASP MCP Security Cheat Sheet）:',
             ' * 1. 认证: 生产环境必须要求认证，禁止匿名访问',
             ' * 2. 传输安全: 远程 MCP 必须使用 HTTPS/TLS',
             ' * 3. 输入验证: 所有工具参数必须验证类型和范围',
             ' * 4. 超时设置: 所有外部调用必须设置超时',
             ' * 5. 日志规范: 日志输出到 stderr，stdout 只用于 JSON-RPC',
             ' * 6. 敏感数据: 禁止在日志或响应中打印密钥/密码',
             ' * 7. 错误处理: 捕获所有异常，返回通用错误信息',
             ' * 8. 工具确认: 高风险操作必须要求用户确认',
             ' * 9. 供应链: 依赖包版本锁定，定期更新',
             ' * 10. 审计: 记录所有工具调用用于审计',
             ' */', '',
             'import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";']
    if transport == "stdio":
        lines.append('import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";')
    else:
        lines.append('import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";')
    lines += ['import { z } from "zod";', '', '// ============================================================',
              '// 服务器配置', '// ============================================================', '',
              f'const server = new McpServer({{', f'  name: "{name}",', '  version: "1.0.0",', '}});', '']

    if tools:
        lines += ['// ============================================================', '// 工具注册 (Tools)',
                  '// ============================================================', '']
        for tool in tools:
            tname, tdesc = tool["name"], tool["description"]
            params = normalize_params(tool)
            risk = classify_tool_risk(tname)
            pnames = list(params.keys())
            pdest = ", ".join(pnames) if pnames else ""
            lines += ['  /*',
                      f'   * 安全标注:',
                      f'   * - 风险等级: {risk["risk_level"]}',
                      f'   * - 有副作用: {risk["side_effect"]}',
                      f'   * - 需要用户确认: {risk["requires_confirmation"]}',
                      f'   * - {risk["advice"]}',
                      '   */',
                      f'server.tool(',
                      f'  "{tname}",',
                      f'  "{tdesc}",',
                      '  {']
            for pn, pd in params.items():
                lines.append(f'    {pn}: {ts_type(pd)},')
            lines += ['  },', f'  async ({{ {pdest} }}) => {{',
                      f'    // TODO: 实现工具 "{tname}" 的业务逻辑',
                      '    return {', '      content: [{', '        type: "text",']
            if pnames:
                lines.append(f'        text: `Tool {tname} called with: {_ts_param_list(pnames)}`,')
            else:
                lines.append(f'        text: "Tool {tname} executed successfully",')
            lines += ['      }],', '    };', '  }', ');', '']

    if resources:
        lines += ['// ============================================================', '// 资源注册 (Resources)',
                  '// ============================================================', '']
        for res in resources:
            lines += [f'server.resource(', f'  "{res["name"]}",', f'  "{res["uri"]}",',
                      f'  {{ description: "{res.get("description", "")}", mimeType: "{res.get("mime_type", "text/plain")}" }},',
                      '  async (uri) => {', f'    // TODO: 实现资源 "{res["name"]}" 的读取逻辑',
                      '    return { contents: [{ uri: uri.href, text: `Resource content` }] };', '  }', ');', '']

    if prompts:
        lines += ['// ============================================================', '// 提示模板注册 (Prompts)',
                  '// ============================================================', '']
        for prompt in prompts:
            pname = prompt["name"]
            pargs = prompt.get("arguments", [])
            anames = [a["name"] for a in pargs]
            adest = ", ".join(anames) if anames else ""
            lines += [f'server.prompt(', f'  "{pname}",', f'  "{prompt.get("description", "")}",']
            if pargs:
                lines.append('  ({')
                for a in pargs:
                    lines.append(f'    {a["name"]}: z.string().describe("{a.get("description", "")}"),')
                lines.append('  }),')
            lines += [f'  async ({{ {adest} }}) => {{',
                      f'    // TODO: 实现提示模板 "{pname}"',
                      '    return { messages: [{ role: "user", content: { type: "text", text: "Prompt" } }] };',
                      '  }', ');', '']

    lines += ['// ============================================================', '// 启动服务器',
              '// ============================================================', '', 'async function main() {']
    if transport == "stdio":
        lines += ['  const transport = new StdioServerTransport();', '  await server.connect(transport);',
                  '  console.error("MCP server started (stdio transport)");']
    else:
        lines += ['  const port = process.env.PORT ? parseInt(process.env.PORT) : 3000;',
                  '  console.error(`MCP server starting on port ${port} (streamable-http)`);']
    lines += ['}', '', 'main().catch((error) => {', '  console.error("Fatal error:", error);',
              '  process.exit(1);', '});']
    return "\n".join(lines)


def py_type(param: dict) -> str:
    ptype = param.get("type", "string")
    required = param.get("required", True)
    type_map = {"string": "str", "number": "float", "integer": "int", "boolean": "bool", "array": "list", "object": "dict"}
    pytype = type_map.get(ptype, "str")
    return pytype if required else f"Optional[{pytype}] = None"


# Python 保留关键字集合（生成代码时需转义）
PYTHON_KEYWORDS = frozenset({
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is", "lambda",
    "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
})


def safe_py_name(name: str) -> str:
    """将参数名转换为安全的 Python 标识符（保留关键字加下划线后缀）"""
    if name in PYTHON_KEYWORDS:
        return f"{name}_"
    # 替换其他非标识符字符
    safe = name.replace("-", "_").replace(".", "_")
    if safe[0].isdigit():
        safe = f"_{safe}"
    return safe


# ============================================================
# 工具风险自动分类（基于 OWASP MCP 安全标准）
# ============================================================

# 只读工具前缀（无副作用）
READONLY_PREFIXES = (
    "get_", "list_", "read_", "search_", "query_", "fetch_",
    "find_", "lookup_", "describe_", "explain_", "check_", "is_",
)

# 写操作前缀（有副作用，需用户确认）
WRITE_PREFIXES = (
    "create_", "update_", "delete_", "remove_", "send_", "post_",
    "put_", "patch_", "upload_", "download_", "execute_", "run_",
    "start_", "stop_", "restart_", "deploy_", "install_", "uninstall_",
)

# 高风险/破坏性前缀（必须 HITL）
DESTRUCTIVE_PREFIXES = (
    "delete_", "remove_", "drop_", "destroy_", "wipe_", "purge_",
    "reset_", "format_", "shutdown_", "kill_", "terminate_",
)


def classify_tool_risk(tool_name: str) -> dict:
    """根据工具名自动分类风险等级。

    返回:
        {
            "risk_level": "read-only" | "reversible-write" | "irreversible-write" | "destructive-admin",
            "side_effect": bool,
            "requires_confirmation": bool,
            "classification": str,  # validate_tool_contract.py 认可的值
            "advice": str,          # 安全建议
        }
    """
    name = tool_name.lower()

    # 破坏性操作
    if any(name.startswith(p) for p in DESTRUCTIVE_PREFIXES):
        return {
            "risk_level": "destructive-admin",
            "side_effect": True,
            "requires_confirmation": True,
            "classification": "destructive-admin",
            "advice": "破坏性操作：必须要求用户显式确认，记录审计日志，实现幂等性",
        }

    # 写操作
    if any(name.startswith(p) for p in WRITE_PREFIXES):
        return {
            "risk_level": "irreversible-write",
            "side_effect": True,
            "requires_confirmation": True,
            "classification": "irreversible-write",
            "advice": "写操作：建议要求用户确认，实现错误回滚机制",
        }

    # 只读操作
    if any(name.startswith(p) for p in READONLY_PREFIXES):
        return {
            "risk_level": "read-only",
            "side_effect": False,
            "requires_confirmation": False,
            "classification": "read-only",
            "advice": "只读操作：无副作用，可自动执行",
        }

    # 未知分类，默认中风险
    return {
        "risk_level": "reversible-write",
        "side_effect": True,
        "requires_confirmation": True,
        "classification": "reversible-write",
        "advice": "未识别操作类型：建议人工确认风险等级，默认要求用户确认",
    }


def generate_python_server(name: str, definition: dict, transport: str) -> str:
    tools, resources, prompts = definition["tools"], definition["resources"], definition["prompts"]
    lines = ['"""', f'MCP Server: {name}', '由 create_mcp_server.py 自动生成', '基于官方 FastMCP', '"""', '',
             '# ============================================================',
             '# 安全基线（对齐 OWASP MCP Security Cheat Sheet）',
             '# ============================================================',
             '# 1. 认证: 生产环境必须要求认证，禁止匿名访问',
             '# 2. 传输安全: 远程 MCP 必须使用 HTTPS/TLS',
             '# 3. 输入验证: 所有工具参数必须验证类型和范围',
             '# 4. 超时设置: 所有外部调用必须设置超时',
             '# 5. 日志规范: 日志输出到 stderr，stdout 只用于 JSON-RPC',
             '# 6. 敏感数据: 禁止在日志或响应中打印密钥/密码',
             '# 7. 错误处理: 捕获所有异常，返回通用错误信息',
             '# 8. 工具确认: 高风险操作必须要求用户确认',
             '# 9. 供应链: 依赖包版本锁定，定期更新',
             '# 10. 审计: 记录所有工具调用用于审计',
             '# ============================================================',
             '',
             '# ============================================================',
             '# 生产级特性（按需启用）',
             '# ============================================================',
             '# 1. 限流: 用 FastMCP 的 RateLimitingMiddleware 防止滥用',
             '# 2. 缓存: 对只读工具加 @cached 装饰器减少重复调用',
             '# 3. 重试: 对外部 API 调用加重试逻辑（指数退避）',
             '# 4. 中间件: 用 Middleware 链统一处理日志/错误/监控',
             '# 5. 版本化: 用 name@version 支持多版本共存',
             '# ============================================================',
             '',
             'import sys', 'from typing import Optional', '', 'from fastmcp import FastMCP', '',
             '# ============================================================', '# 服务器配置',
             '# ============================================================', '', f'mcp = FastMCP("{name}")', '']

    if tools:
        lines += ['# ============================================================', '# 工具注册 (Tools)',
                  '# ============================================================', '']
        for tool in tools:
            raw_name = tool["name"]
            tname = safe_py_name(raw_name)
            tdesc = tool["description"]
            params = normalize_params(tool)
            risk = classify_tool_risk(raw_name)
            sig = ", ".join([f"{safe_py_name(p)}: {py_type(d)}" for p, d in params.items()])
            # 如果安全函数名与原始名不同，显式指定工具名
            tool_decorator = f'@mcp.tool(name="{raw_name}")' if tname != raw_name else '@mcp.tool()'
            lines += [tool_decorator, f'def {tname}({sig}) -> str:',
                      f'    """{tdesc}',
                      '',
                      f'    安全标注:',
                      f'    - 风险等级: {risk["risk_level"]}',
                      f'    - 有副作用: {risk["side_effect"]}',
                      f'    - 需要用户确认: {risk["requires_confirmation"]}',
                      f'    - {risk["advice"]}',
                      f'    - Strict Mode: 建议使用 Pydantic 模型并设置 extra="forbid" 防止额外属性注入',
                      f'    """',
                      f'    # TODO: 实现工具 "{raw_name}" 的业务逻辑',
                      f'    return "Tool {raw_name} executed"', '']

    if resources:
        lines += ['# ============================================================', '# 资源注册 (Resources)',
                  '# ============================================================', '']
        for res in resources:
            rname = safe_py_name(res["name"])
            lines += [f'@mcp.resource("{res["uri"]}")', f'def {rname}() -> str:',
                      f'    """{res.get("description", "")}"""',
                      f'    # TODO: 实现资源 "{res["name"]}" 的读取逻辑',
                      f'    return "Resource {res["name"]} content"', '']

    if prompts:
        lines += ['# ============================================================', '# 提示模板注册 (Prompts)',
                  '# ============================================================', '']
        for prompt in prompts:
            pname = safe_py_name(prompt["name"])
            pargs = prompt.get("arguments", [])
            sig = ", ".join([f"{safe_py_name(a['name'])}: str" for a in pargs])
            lines += [f'@mcp.prompt()', f'def {pname}({sig}) -> str:',
                      f'    """{prompt.get("description", "")}"""',
                      f'    # TODO: 实现提示模板 "{prompt["name"]}"',
                      f'    return "Prompt {prompt["name"]}"', '']

    lines += ['# ============================================================', '# 启动服务器',
              '# ============================================================', '', 'def main():']
    if transport == "stdio":
        lines += ['    print("Starting MCP server (stdio transport)", file=sys.stderr)', '    mcp.run(transport="stdio")']
    else:
        lines += ['    import os', '    port = int(os.environ.get("PORT", "8000"))',
                  '    print(f"Starting MCP server on port {port} (streamable-http)", file=sys.stderr)',
                  '    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)']
    lines += ['', '', 'if __name__ == "__main__":', '    main()']
    return "\n".join(lines)


def copy_template(language: str, output_dir: Path, force: bool = False):
    template_dir = TEMPLATES_DIR / language
    if not template_dir.exists():
        print(f"错误: 模板目录不存在: {template_dir}", file=sys.stderr)
        sys.exit(1)
    for item in template_dir.rglob("*"):
        if item.is_file():
            dest = output_dir / item.relative_to(template_dir)
            if dest.exists() and not force:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)


def detect_language(project_dir: Path) -> str:
    if (project_dir / "package.json").exists():
        return "typescript"
    if (project_dir / "pyproject.toml").exists() or (project_dir / "server.py").exists():
        return "python"
    return "unknown"


def list_components(project_dir: Path):
    language = detect_language(project_dir)
    if language == "typescript":
        server_file = project_dir / "src" / "server.ts"
    elif language == "python":
        server_file = project_dir / "server.py"
    else:
        print(f"错误: 无法检测项目语言: {project_dir}", file=sys.stderr)
        sys.exit(1)
    if not server_file.exists():
        print(f"错误: 服务器文件不存在: {server_file}", file=sys.stderr)
        sys.exit(1)
    content = server_file.read_text(encoding="utf-8")
    if language == "typescript":
        tools = re.findall(r'server\.tool\(\s*"([^"]+)"', content)
        resources = re.findall(r'server\.resource\(\s*"([^"]+)"', content)
        prompts = re.findall(r'server\.prompt\(\s*"([^"]+)"', content)
    else:
        tools = re.findall(r'@mcp\.tool\(\)\s*def (\w+)', content)
        resources = re.findall(r'@mcp\.resource\("([^"]+)"\)', content)
        prompts = re.findall(r'@mcp\.prompt\(\)\s*def (\w+)', content)
    print(f"项目: {project_dir}")
    print(f"语言: {language}")
    print(f"工具 ({len(tools)}): {', '.join(tools) if tools else '(无)'}")
    print(f"资源 ({len(resources)}): {', '.join(resources) if resources else '(无)'}")
    print(f"提示 ({len(prompts)}): {', '.join(prompts) if prompts else '(无)'}")


def cmd_generate(args):
    definition = load_definition(args.definition)
    print(f"📋 加载了 {len(definition['tools'])} 个工具, {len(definition['resources'])} 个资源, {len(definition['prompts'])} 个提示")
    output_dir = Path(args.output).resolve()
    if output_dir.exists():
        if args.force:
            shutil.rmtree(output_dir)
            print(f"⚠️  已删除已有目录并重新创建: {output_dir}")
        else:
            print(f"错误: 输出目录已存在: {output_dir}", file=sys.stderr)
            print(f"提示: 使用 --force 覆盖已有目录", file=sys.stderr)
            sys.exit(1)
    output_dir.mkdir(parents=True, exist_ok=True)
    copy_template(args.language, output_dir, force=args.force)
    print(f"📦 已复制 {args.language} 模板")
    if args.language == "typescript":
        server_code = generate_typescript_server(args.name, definition, args.transport)
        server_file = output_dir / "src" / "server.ts"
    else:
        server_code = generate_python_server(args.name, definition, args.transport)
        server_file = output_dir / "server.py"
    server_file.write_text(server_code, encoding="utf-8")
    print(f"✅ 已生成服务器代码: {server_file}")
    if args.language == "typescript":
        pkg_path = output_dir / "package.json"
        if pkg_path.exists():
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            pkg["name"] = args.name
            pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
    print()
    print("=" * 60)
    print(f"MCP 服务器生成完成: {output_dir}")
    print("=" * 60)
    for t in definition["tools"]:
        print(f"  [tool]    {t['name']}()")
    for r in definition["resources"]:
        print(f"  [resource] {r['name']} ({r['uri']})")
    for p in definition["prompts"]:
        print(f"  [prompt]  {p['name']}()")
    print()
    print("握手测试: python3 scripts/test_mcp_handshake.py --command '<启动命令>'")
    print()
    print("📚 官方最佳实践参考（对齐 official/mcp-builder）:")
    print("  - 命名规范: official/mcp-builder/reference/mcp_best_practices.md")
    print(f"  - {args.language} 实现指南: official/mcp-builder/reference/{'python' if args.language == 'python' else 'node'}_mcp_server.md")
    print("  - 关键: stdio 服务器不要打印到 stdout（用 stderr），工具命名用 snake_case 加服务前缀")


def cmd_add(args):
    project_dir = Path(args.project).resolve()
    if not project_dir.exists():
        print(f"错误: 项目目录不存在: {project_dir}", file=sys.stderr)
        sys.exit(1)
    language = detect_language(project_dir)
    if language == "unknown":
        print("错误: 无法检测项目语言", file=sys.stderr)
        sys.exit(1)
    if args.tool:
        tool_def = json.loads(Path(args.tool).read_text(encoding="utf-8"))
        if isinstance(tool_def, dict):
            tool_def = [tool_def]
        definition = {"tools": tool_def, "resources": [], "prompts": []}
    elif args.definition:
        definition = load_definition(args.definition)
    else:
        print("错误: 必须指定 --tool 或 --definition", file=sys.stderr)
        sys.exit(1)
    server_file = project_dir / ("src/server.ts" if language == "typescript" else "server.py")
    if not server_file.exists():
        print(f"错误: 服务器文件不存在: {server_file}", file=sys.stderr)
        sys.exit(1)
    content = server_file.read_text(encoding="utf-8")
    added = 0
    if language == "typescript":
        new_code = ""
        for tool in definition["tools"]:
            tname = tool["name"]
            if f'server.tool("{tname}"' in content or f'server.tool(\n  "{tname}"' in content:
                print(f"⚠️  工具已存在，跳过: {tname}")
                continue
            tdesc = tool["description"]
            params = normalize_params(tool)
            pnames = list(params.keys())
            pdest = ", ".join(pnames) if pnames else ""
            new_code += f'\nserver.tool(\n  "{tname}",\n  "{tdesc}",\n  {{'
            for pn, pd in params.items():
                new_code += f'\n    {pn}: {ts_type(pd)},'
            new_code += f'\n  }},\n  async ({{ {pdest} }}) => {{\n    // TODO: 实现工具 "{tname}"\n    return {{ content: [{{ type: "text", text: "Tool {tname} added" }}] }};\n  }}\n);\n'
            added += 1
        marker = "// ============================================================\n// 启动服务器"
        content = content.replace(marker, new_code + "\n" + marker) if marker in content else content + new_code
    else:
        new_code = ""
        for tool in definition["tools"]:
            raw_name = tool["name"]
            tname = safe_py_name(raw_name)
            if f"def {tname}(" in content:
                print(f"⚠️  工具已存在，跳过: {raw_name}")
                continue
            params = normalize_params(tool)
            sig = ", ".join([f"{safe_py_name(p)}: {py_type(d)}" for p, d in params.items()])
            tool_decorator = f'@mcp.tool(name="{raw_name}")' if tname != raw_name else '@mcp.tool()'
            new_code += f'\n{tool_decorator}\ndef {tname}({sig}) -> str:\n    """{tool["description"]}"""\n    # TODO: 实现工具 "{raw_name}"\n    return "Tool {raw_name} added"\n'
            added += 1
        marker = "# ============================================================\n# 启动服务器"
        content = content.replace(marker, new_code + "\n" + marker) if marker in content else content + new_code
    server_file.write_text(content, encoding="utf-8")
    print(f"✅ 已向项目添加 {added} 个新组件: {project_dir}")


def main():
    parser = argparse.ArgumentParser(description="MCP 服务器代码生成器（支持 tools/resources/prompts + add/list）")
    subparsers = parser.add_subparsers(dest="command")
    gen = subparsers.add_parser("generate", help="生成完整 MCP 服务器")
    gen.add_argument("--language", choices=["typescript", "python"], default="typescript")
    gen.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    gen.add_argument("--name", required=True)
    gen.add_argument("--definition", required=True)
    gen.add_argument("--output", default="./mcp-server")
    gen.add_argument("--force", action="store_true")
    add = subparsers.add_parser("add", help="向已有项目添加新组件")
    add.add_argument("--project", required=True)
    add.add_argument("--tool", help="单个工具定义 JSON")
    add.add_argument("--definition", help="完整定义文件")
    lst = subparsers.add_parser("list", help="列出项目组件")
    lst.add_argument("--project", required=True)
    args = parser.parse_args()
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "list":
        list_components(Path(args.project).resolve())
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
