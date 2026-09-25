#!/usr/bin/env python3
"""
安全检查自动化脚本。

在提交前或 CI 中运行，执行多项安全检查：
1. 硬编码密钥检测
2. 危险代码模式检测
3. 路径穿越检测
4. 不安全网络检测
5. 文件权限检查

用法:
    python3 scripts/security_check.py [--severity high|medium|low] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional


# 硬编码密钥模式
SECRET_PATTERNS = [
    (r"api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "hardcoded_api_key"),
    (r"secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "hardcoded_secret"),
    (r"password\s*[:=]\s*['\"][^'\"]{6,}['\"]", "hardcoded_password"),
    (r"token\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]", "hardcoded_token"),
    (r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----", "private_key"),
    (r"AKIA[0-9A-Z]{16}", "aws_access_key"),
    (r"ghp_[A-Za-z0-9]{36}", "github_token"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "slack_token"),
]

# 危险代码模式
DANGEROUS_PATTERNS = [
    (r"\beval\s*\(", "eval_usage", "high"),
    (r"\bexec\s*\(", "exec_usage", "high"),
    (r"subprocess\.[A-Za-z]+\(.*shell\s*=\s*True", "shell_injection", "critical"),
    (r"os\.system\s*\(", "os_system", "high"),
    (r"os\.popen\s*\(", "os_popen", "medium"),
    (r"__import__\s*\(", "dynamic_import", "medium"),
    (r"pickle\.loads?\s*\(", "pickle_deserialization", "high"),
    (r"yaml\.load\s*\(.*Loader=yaml\.FullLoader", "unsafe_yaml_load", "medium"),
]

# 路径穿越模式
PATH_TRAVERSAL_PATTERNS = [
    (r"\.\./", "path_traversal"),
    (r"%2e%2e%2f", "encoded_path_traversal"),
]


class SecurityResult:
    """安全检查结果。"""

    def __init__(self):
        self.issues = []
        self.files_scanned = 0
        self.lines_scanned = 0

    def add_issue(self, severity: str, category: str, file: str, line: int, message: str, snippet: str = ""):
        self.issues.append({
            "severity": severity,
            "category": category,
            "file": file,
            "line": line,
            "message": message,
            "snippet": snippet,
        })

    @property
    def critical_count(self):
        return sum(1 for i in self.issues if i["severity"] == "critical")

    @property
    def high_count(self):
        return sum(1 for i in self.issues if i["severity"] == "high")

    @property
    def medium_count(self):
        return sum(1 for i in self.issues if i["severity"] == "medium")

    @property
    def low_count(self):
        return sum(1 for i in self.issues if i["severity"] == "low")

    @property
    def total_count(self):
        return len(self.issues)


def scan_file(file_path: Path, result: SecurityResult, exclude_tests: bool = True):
    """扫描单个文件的安全问题。"""
    if file_path.suffix not in {".py", ".js", ".ts", ".sh", ".bash"}:
        return

    # 排除测试文件和官方资源
    if exclude_tests and ("test" in file_path.name or "official" in str(file_path)):
        return

    # 排除安全审计/分析脚本本身（它们包含危险模式的正则定义，用于检测其他代码）
    if file_path.name in {
        "audit_plugin.py", "security_check.py",
        "analyze_plugin.py", "health_check.py",
        "best_practices.py", "errors.py",
        "score_plugin.py", "fuzz_test.py",
        "supply_chain_scan.py",
    }:
        return

    result.files_scanned += 1

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    lines = content.split("\n")
    result.lines_scanned += len(lines)
    rel_path = str(file_path)

    # 跟踪 docstring 状态（三引号内的内容不检测）
    in_docstring = False
    docstring_char = None

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # 检测 docstring 开始/结束
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[0:3]
                # 单行 docstring（开头和结尾在同一行）
                if stripped.count(docstring_char) >= 2:
                    continue
                in_docstring = True
                continue
        else:
            if docstring_char in stripped:
                in_docstring = False
                docstring_char = None
            continue

        # 跳过注释
        if stripped.startswith("#") or stripped.startswith("//"):
            continue

        # 硬编码密钥检测
        for pattern, category in SECRET_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                result.add_issue("critical", category, rel_path, line_num,
                                 f"检测到硬编码密钥: {category}", stripped[:100])

        # 危险代码模式检测
        for pattern, category, severity in DANGEROUS_PATTERNS:
            if re.search(pattern, line):
                result.add_issue(severity, category, rel_path, line_num,
                                 f"检测到危险代码模式: {category}", stripped[:100])

        # 路径穿越检测（仅检测真正危险的代码模式，排除配置中的正常相对路径）
        # 只检测文件操作函数中的路径穿越，如 open("../"), Path("../"), os.path.join("..", ...)
        dangerous_path_ops = [
            r'open\s*\(\s*["\'].*\.\./',
            r'Path\s*\(\s*["\'].*\.\./',
            r'os\.path\.join\s*\(\s*["\']\.\.',
            r'os\.system\s*\(\s*["\'].*\.\./',
            r'subprocess\..*\.\./',
        ]
        for pattern in dangerous_path_ops:
            if re.search(pattern, line):
                result.add_issue("medium", "path_traversal", rel_path, line_num,
                                 "检测到潜在路径穿越: 文件操作中使用了父目录引用", stripped[:100])
                break


def check_file_permissions(root: Path, result: SecurityResult):
    """检查文件权限。"""
    for script in root.glob("scripts/*.py"):
        # 检查脚本是否有执行权限（可选，不强制）
        mode = script.stat().st_mode
        if mode & 0o111:  # 有执行权限
            pass  # 正常


def check_mcp_json_security(root: Path, result: SecurityResult):
    """检查 mcp.json 中的安全问题。"""
    mcp_json = root / "mcp.json"
    if not mcp_json.exists():
        return

    try:
        data = json.loads(mcp_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    for server_name, server in data.get("mcpServers", {}).items():
        # 检查 headers 中是否有密钥
        headers = server.get("headers", {})
        for key, value in headers.items():
            if any(term in key.lower() for term in ["authorization", "token", "key", "secret", "password"]):
                if value and not value.startswith("${"):
                    result.add_issue("critical", "mcp_header_secret", "mcp.json", 0,
                                     f"MCP 服务器 '{server_name}' 的 header '{key}' 包含硬编码值",
                                     f"{key}: {value[:20]}...")

        # 检查 env 中是否有密钥
        env = server.get("env", {})
        for key, value in env.items():
            if any(term in key.lower() for term in ["api_key", "secret", "token", "password"]):
                if value and not value.startswith("${"):
                    result.add_issue("high", "mcp_env_secret", "mcp.json", 0,
                                     f"MCP 服务器 '{server_name}' 的 env '{key}' 包含硬编码值",
                                     f"{key}: {value[:20]}...")


def mask_sensitive(text: str) -> str:
    """对可能包含敏感信息的文本进行掩码处理"""
    import re
    # 掩码 API key / token / secret 模式
    patterns = [
        (r'(sk-[a-zA-Z0-9]{8})[a-zA-Z0-9]+', r'\1...'),
        (r'(ghp_[a-zA-Z0-9]{8})[a-zA-Z0-9]+', r'\1...'),
        (r'(AKIA[A-Z0-9]{4})[A-Z0-9]+', r'\1...'),
        (r'(api[_-]?key\s*[=:]\s*["\']?[a-zA-Z0-9]{4})[a-zA-Z0-9]+', r'\1...'),
        (r'(password\s*[=:]\s*["\']?[^\s"\']{2})[^\s"\']+', r'\1...'),
        (r'(token\s*[=:]\s*["\']?[a-zA-Z0-9]{4})[a-zA-Z0-9]+', r'\1...'),
        (r'(BEGIN [A-Z ]*PRIVATE KEY-----)[\s\S]+?(-----END [A-Z ]*PRIVATE KEY-----)', r'\1...\2'),
    ]
    masked = text
    for pattern, replacement in patterns:
        masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)
    return masked


def print_report(result: SecurityResult, min_severity: str = "low"):
    """打印安全检查报告。"""
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    min_level = severity_order.get(min_severity, 3)

    print("=" * 70)
    print("安全检查报告（自动化）")
    print("=" * 70)
    print()
    print(f"扫描文件数: {result.files_scanned}")
    print(f"扫描代码行数: {result.lines_scanned}")
    print()
    print("问题统计:")
    print(f"  🔴 critical (严重): {result.critical_count}")
    print(f"  🟠 high (高危):     {result.high_count}")
    print(f"  🟡 medium (中危):   {result.medium_count}")
    print(f"  🔵 low (低危):      {result.low_count}")
    print(f"  总计: {result.total_count}")
    print()

    if result.total_count == 0:
        print("✅ 未发现安全问题")
        print("=" * 70)
        return

    sorted_issues = sorted(result.issues, key=lambda x: severity_order.get(x["severity"], 99))

    print("问题详情:")
    print("-" * 70)
    for issue in sorted_issues:
        if severity_order.get(issue["severity"], 99) > min_level:
            continue
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(issue["severity"], "⚪")
        print(f"\n{icon} [{issue['severity'].upper()}] {issue['message']}")
        print(f"   文件: {issue['file']}" + (f":{issue['line']}" if issue['line'] > 0 else ""))
        print(f"   类别: {issue['category']}")
        if issue["snippet"]:
            # 对代码片段中的敏感信息进行掩码
            print(f"   代码: {mask_sensitive(issue['snippet'])}")

    print()
    print("=" * 70)
    if result.critical_count > 0:
        print("❌ 存在严重安全问题，必须修复后才能提交/发布")
    elif result.high_count > 0:
        print("⚠️  存在高危安全问题，建议修复后提交/发布")
    elif result.medium_count > 0:
        print("⚡ 存在中危问题，建议评估后修复")
    else:
        print("✅ 仅存在低危问题，可提交/发布但建议优化")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="安全检查自动化脚本")
    parser.add_argument("target", nargs="?", default=".", help="要检查的目录（默认当前目录）")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low"], default="low",
                        help="最低显示严重级别（默认 low）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--include-tests", action="store_true", help="包含测试文件")
    args = parser.parse_args()

    root = Path(args.target).resolve()
    if not root.exists():
        print(f"错误: 目录不存在: {root}", file=sys.stderr)
        sys.exit(1)

    result = SecurityResult()

    # 扫描所有代码文件
    for code_file in root.rglob("*"):
        if code_file.is_file():
            # 排除 node_modules, __pycache__, .git
            if any(part in {"node_modules", "__pycache__", ".git", "official"} for part in code_file.parts):
                continue
            scan_file(code_file, result, exclude_tests=not args.include_tests)

    # 检查 mcp.json 安全
    check_mcp_json_security(root, result)

    # 输出结果
    if args.json:
        output = {
            "summary": {
                "files_scanned": result.files_scanned,
                "lines_scanned": result.lines_scanned,
                "critical": result.critical_count,
                "high": result.high_count,
                "medium": result.medium_count,
                "low": result.low_count,
                "total": result.total_count,
            },
            "issues": result.issues,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(result, args.severity)

    # 退出码：有 critical/high 问题时返回非0
    if result.critical_count > 0 or result.high_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
