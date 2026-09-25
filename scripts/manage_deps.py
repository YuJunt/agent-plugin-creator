#!/usr/bin/env python3
"""
MCP 服务器依赖管理工具

扫描 MCP 服务器代码的 import，自动生成 requirements.txt / package.json，
检查未使用的依赖和缺失的依赖。

用法:
    python3 scripts/manage_deps.py <服务器目录> --check
    python3 scripts/manage_deps.py <服务器目录> --generate
    python3 scripts/manage_deps.py <服务器目录> --language python
    python3 scripts/manage_deps.py <服务器目录> --json
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path

# Python 标准库模块列表（常见）
PYTHON_STDLIB = {
    "abc", "argparse", "asyncio", "base64", "collections", "concurrent", "contextlib",
    "copy", "csv", "dataclasses", "datetime", "decimal", "difflib", "enum", "errno",
    "fnmatch", "functools", "glob", "gzip", "hashlib", "heapq", "hmac", "html",
    "http", "importlib", "inspect", "io", "ipaddress", "itertools", "json", "logging",
    "math", "mimetypes", "multiprocessing", "operator", "os", "pathlib", "pickle",
    "platform", "pprint", "queue", "random", "re", "shutil", "signal", "site",
    "smtplib", "socket", "sqlite3", "ssl", "stat", "string", "struct", "subprocess",
    "sys", "tempfile", "textwrap", "threading", "time", "timeit", "traceback",
    "types", "typing", "unicodedata", "unittest", "urllib", "uuid", "warnings",
    "weakref", "xml", "zipfile", "zlib", "configparser", "csv", "tarfile", "tomllib",
}

# Python 包名到 import 名的映射（常见）
PYTHON_PACKAGE_MAP = {
    "yaml": "pyyaml",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "torch": "torch",
    "tensorflow": "tensorflow",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "jwt": "pyjwt",
    "crypto": "pycryptodome",
    "OpenSSL": "pyopenssl",
    "serial": "pyserial",
    "markdown": "markdown",
    "requests": "requests",
    "fastmcp": "fastmcp",
    "mcp": "mcp",
    "pydantic": "pydantic",
    "click": "click",
    "rich": "rich",
    "tqdm": "tqdm",
}


def scan_python_imports(server_dir: Path) -> dict:
    """扫描 Python 代码的 import"""
    imports = set()
    files_scanned = 0

    for py_file in server_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        files_scanned += 1
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:  # 非相对导入
                    imports.add(node.module.split(".")[0])

    # 分类
    stdlib = set()
    third_party = set()
    local = set()

    for imp in imports:
        if imp in PYTHON_STDLIB:
            stdlib.add(imp)
        elif (server_dir / f"{imp}.py").exists() or (server_dir / imp).is_dir():
            local.add(imp)
        else:
            third_party.add(imp)

    return {
        "files_scanned": files_scanned,
        "all_imports": sorted(imports),
        "stdlib": sorted(stdlib),
        "third_party": sorted(third_party),
        "local": sorted(local),
    }


def scan_typescript_imports(server_dir: Path) -> dict:
    """扫描 TypeScript/JavaScript 代码的 import"""
    imports = set()
    files_scanned = 0

    for ts_file in list(server_dir.rglob("*.ts")) + list(server_dir.rglob("*.js")):
        if "node_modules" in str(ts_file):
            continue
        files_scanned += 1
        try:
            content = ts_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        # 匹配 import ... from "..."
        pattern = r'import\s+.*?from\s+["\']([^"\']+)["\']'
        for match in re.finditer(pattern, content):
            module = match.group(1)
            if not module.startswith(".") and not module.startswith("/"):
                imports.add(module.split("/")[0] if module.startswith("@") else module)

        # 匹配 require("...")
        require_pattern = r'require\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(require_pattern, content):
            module = match.group(1)
            if not module.startswith(".") and not module.startswith("/"):
                imports.add(module.split("/")[0] if module.startswith("@") else module)

    # Node.js 内置模块
    node_builtin = {
        "fs", "path", "os", "http", "https", "url", "util", "events", "stream",
        "crypto", "child_process", "process", "buffer", "console", "net", "tls",
        "zlib", "querystring", "string_decoder", "timers", "dgram", "dns",
    }

    builtin = set()
    external = set()
    for imp in imports:
        if imp in node_builtin or imp.startswith("node:"):
            builtin.add(imp)
        else:
            external.add(imp)

    return {
        "files_scanned": files_scanned,
        "all_imports": sorted(imports),
        "builtin": sorted(builtin),
        "external": sorted(external),
    }


def check_python_deps(server_dir: Path, imports: dict) -> dict:
    """检查 Python 依赖"""
    result = {"missing": [], "unused": [], "existing": []}

    req_file = server_dir / "requirements.txt"
    existing_deps = set()

    if req_file.exists():
        for line in req_file.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # 提取包名（去掉版本号）
                pkg_name = re.split(r"[<>=!~]", line)[0].strip().lower()
                existing_deps.add(pkg_name)

    # 检查缺失的依赖
    for imp in imports["third_party"]:
        pkg_name = PYTHON_PACKAGE_MAP.get(imp, imp).lower()
        if pkg_name not in existing_deps:
            result["missing"].append({"import": imp, "package": pkg_name})

    # 检查未使用的依赖
    import_packages = {PYTHON_PACKAGE_MAP.get(imp, imp).lower() for imp in imports["third_party"]}
    for dep in existing_deps:
        if dep not in import_packages and dep not in {imp.lower() for imp in imports["third_party"]}:
            result["unused"].append(dep)

    result["existing"] = sorted(existing_deps)
    return result


def generate_requirements(server_dir: Path, imports: dict) -> Path:
    """生成 requirements.txt"""
    req_file = server_dir / "requirements.txt"
    lines = ["# Auto-generated by manage_deps.py", ""]

    for imp in sorted(imports["third_party"]):
        pkg_name = PYTHON_PACKAGE_MAP.get(imp, imp)
        lines.append(pkg_name)

    req_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return req_file


def generate_package_json(server_dir: Path, imports: dict, server_name: str) -> Path:
    """生成 package.json"""
    pkg_file = server_dir / "package.json"
    deps = {}
    for imp in imports["external"]:
        deps[imp] = "^1.0.0"  # 默认版本，用户需手动调整

    pkg = {
        "name": server_name,
        "version": "0.1.0",
        "description": f"MCP server: {server_name}",
        "main": "dist/server.js",
        "scripts": {
            "build": "tsc",
            "start": "node dist/server.js",
            "dev": "tsx src/server.ts",
        },
        "dependencies": deps,
        "devDependencies": {
            "typescript": "^5.0.0",
            "@types/node": "^20.0.0",
        },
    }

    pkg_file.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return pkg_file


def main():
    parser = argparse.ArgumentParser(description="MCP 服务器依赖管理工具")
    parser.add_argument("server_dir", help="MCP 服务器目录路径")
    parser.add_argument("--language", choices=["python", "typescript", "auto"], default="auto")
    parser.add_argument("--check", action="store_true", help="检查依赖（缺失/未使用）")
    parser.add_argument("--generate", action="store_true", help="生成依赖文件")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--name", help="服务器名称（用于 package.json）")
    args = parser.parse_args()

    server_dir = Path(args.server_dir).resolve()
    if not server_dir.is_dir():
        print(f"错误: 目录不存在: {server_dir}", file=sys.stderr)
        sys.exit(1)

    # 检测语言
    language = args.language
    if language == "auto":
        if list(server_dir.rglob("*.py")):
            language = "python"
        elif list(server_dir.rglob("*.ts")) or list(server_dir.rglob("*.js")):
            language = "typescript"
        else:
            print("错误: 无法自动检测语言，请使用 --language 指定", file=sys.stderr)
            sys.exit(1)

    result = {"language": language, "server_dir": str(server_dir)}

    if language == "python":
        imports = scan_python_imports(server_dir)
        result["imports"] = imports

        if args.check:
            deps_check = check_python_deps(server_dir, imports)
            result["deps_check"] = deps_check

        if args.generate:
            req_file = generate_requirements(server_dir, imports)
            result["generated"] = str(req_file)

    else:  # typescript
        imports = scan_typescript_imports(server_dir)
        result["imports"] = imports

        if args.generate:
            server_name = args.name or server_dir.name
            pkg_file = generate_package_json(server_dir, imports, server_name)
            result["generated"] = str(pkg_file)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print(f"依赖分析: {server_dir.name} ({language})")
        print("=" * 50)

        imp = result["imports"]
        print(f"\n扫描文件: {imp['files_scanned']} 个")
        print(f"总 import: {len(imp['all_imports'])} 个")

        if language == "python":
            print(f"  标准库: {len(imp['stdlib'])} 个")
            print(f"  第三方: {len(imp['third_party'])} 个")
            print(f"  本地模块: {len(imp['local'])} 个")
            if imp["third_party"]:
                print(f"  第三方包: {', '.join(imp['third_party'])}")
        else:
            print(f"  Node内置: {len(imp['builtin'])} 个")
            print(f"  外部依赖: {len(imp['external'])} 个")
            if imp["external"]:
                print(f"  外部包: {', '.join(imp['external'])}")

        if "deps_check" in result:
            dc = result["deps_check"]
            print(f"\n依赖检查:")
            if dc["missing"]:
                print(f"  ❌ 缺失 ({len(dc['missing'])}):")
                for m in dc["missing"]:
                    print(f"     - import '{m['import']}' → 需安装 {m['package']}")
            else:
                print(f"  ✅ 无缺失依赖")

            if dc["unused"]:
                print(f"  ⚠️  未使用 ({len(dc['unused'])}):")
                for u in dc["unused"]:
                    print(f"     - {u}")
            else:
                print(f"  ✅ 无未使用依赖")

        if "generated" in result:
            print(f"\n✅ 已生成: {result['generated']}")

        print("=" * 50)

    sys.exit(0)


if __name__ == "__main__":
    main()
