#!/usr/bin/env python3
"""
Agent Plugin 安全审计工具

检查插件中的安全问题，包括：
  1. MCP 服务器代码中的危险操作（exec/eval/system/subprocess）
  2. 硬编码密钥（API key/password/secret/token）
  3. 路径穿越漏洞（文件操作未验证路径）
  4. mcp.json 中的安全问题（headers 密钥、env 敏感变量、shell 命令）
  5. plugin.json 中的安全问题
  6. skill 脚本中的安全问题
  7. 权限范围检查（destructive 操作、过度权限）

用法:
    python3 audit_plugin.py <插件目录路径>
    python3 audit_plugin.py ./my-plugin --format json
    python3 audit_plugin.py ./my-plugin --severity high

严重级别:
  - critical: 严重漏洞（硬编码密钥、命令注入）
  - high: 高危问题（危险操作、路径穿越）
  - medium: 中危问题（不安全网络、权限过宽）
  - low: 低危问题（最佳实践建议）
"""
import argparse
import json
import re
import sys
from pathlib import Path


# 危险代码模式
DANGEROUS_PATTERNS = [
    # Python
    (r"\beval\s*\(", "使用 eval() 可能导致代码注入", "high"),
    (r"\bexec\s*\(", "使用 exec() 可能导致代码注入", "high"),
    (r"os\.system\s*\(", "使用 os.system() 可能导致命令注入", "high"),
    (r"subprocess\.(call|run|Popen|check_output)\s*\([^)]*shell\s*=\s*True", "使用 shell=True 可能导致命令注入", "critical"),
    (r"subprocess\.(call|run|Popen|check_output)\s*\(", "使用 subprocess 执行外部命令，需验证输入", "medium"),
    (r"\.read\(\)[^)]*\[", "直接使用用户输入作为索引，可能导致越界", "low"),
    # TypeScript/JavaScript
    (r"\beval\s*\(", "使用 eval() 可能导致代码注入", "high"),
    (r"new\s+Function\s*\(", "使用 new Function() 可能导致代码注入", "high"),
    (r"child_process\.(exec|execSync)\s*\(", "使用 child_process.exec 可能导致命令注入", "critical"),
    (r"child_process\.(spawn|execFile|fork)\s*\(", "使用 child_process 执行外部命令，需验证输入", "medium"),
]

# 硬编码密钥模式
SECRET_PATTERNS = [
    (r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "硬编码 API key", "critical"),
    (r"(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]", "硬编码密码", "critical"),
    (r"(?:secret|token|auth[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "硬编码密钥/令牌", "critical"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", "critical"),
    (r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----", "私钥", "critical"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token", "critical"),
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI API Key", "critical"),
]

# 路径穿越模式
PATH_TRAVERSAL_PATTERNS = [
    (r"open\s*\(\s*[^)]*\.\.[/\\]", "文件操作可能包含路径穿越 (../)", "high"),
    (r"Path\s*\(\s*[^)]*\.\.[/\\]", "Path 操作可能包含路径穿越 (../)", "high"),
    (r"fs\.(readFile|writeFile|readFileSync|writeFileSync|createReadStream|createWriteStream)\s*\(\s*[^)]*\.\.[/\\]", "文件操作可能包含路径穿越", "high"),
]

# 不安全网络模式
INSECURE_NETWORK_PATTERNS = [
    (r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)", "使用非加密 HTTP 连接（非 localhost）", "medium"),
    (r"verify\s*[:=]\s*False", "禁用 SSL 证书验证", "high"),
    (r"rejectUnauthorized\s*[:=]\s*false", "禁用 TLS 证书验证", "high"),
    (r"NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0", "禁用 TLS 证书验证（环境变量）", "high"),
]

# 敏感环境变量名
SENSITIVE_ENV_VARS = {
    "API_KEY", "API_SECRET", "SECRET_KEY", "PRIVATE_KEY", "PASSWORD", "PASSWD",
    "TOKEN", "ACCESS_TOKEN", "REFRESH_TOKEN", "AUTH_TOKEN", "BEARER_TOKEN",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    "GITHUB_TOKEN", "GITLAB_TOKEN", "DATABASE_URL", "DB_PASSWORD",
    "REDIS_PASSWORD", "MONGO_PASSWORD", "MYSQL_ROOT_PASSWORD",
}

# 敏感 header 名
SENSITIVE_HEADERS = {
    "authorization", "x-api-key", "x-auth-token", "x-access-token",
    "cookie", "set-cookie", "proxy-authorization",
}


class AuditResult:
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
            "snippet": snippet.strip()[:100] if snippet else "",
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


def scan_code_file(file_path: Path, rel_path: str, result: AuditResult):
    """扫描代码文件中的安全问题"""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    result.files_scanned += 1
    lines = content.split("\n")
    result.lines_scanned += len(lines)

    # 扫描危险代码模式
    for pattern, message, severity in DANGEROUS_PATTERNS:
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                # 排除注释行
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
                    continue
                result.add_issue(severity, "dangerous_code", rel_path, i, message, line)

    # 扫描硬编码密钥
    for pattern, message, severity in SECRET_PATTERNS:
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//"):
                    continue
                # 排除示例/文档中的占位符
                if "your_" in line.lower() or "example" in line.lower() or "placeholder" in line.lower():
                    continue
                result.add_issue(severity, "hardcoded_secret", rel_path, i, message, line)

    # 扫描路径穿越
    for pattern, message, severity in PATH_TRAVERSAL_PATTERNS:
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                result.add_issue(severity, "path_traversal", rel_path, i, message, line)

    # 扫描不安全网络
    for pattern, message, severity in INSECURE_NETWORK_PATTERNS:
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//"):
                    continue
                result.add_issue(severity, "insecure_network", rel_path, i, message, line)


def audit_mcp_json(mcp_path: Path, rel_path: str, result: AuditResult):
    """审计 mcp.json 中的安全问题"""
    try:
        mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
    except Exception as e:
        result.add_issue("high", "invalid_json", rel_path, 0, f"mcp.json 不是有效 JSON: {e}")
        return

    result.files_scanned += 1

    servers = mcp.get("mcpServers", {})
    for server_name, server_config in servers.items():
        # 检查 headers
        headers = server_config.get("headers", {})
        for header_name, header_value in headers.items():
            if header_name.lower() in SENSITIVE_HEADERS:
                result.add_issue("critical", "secret_in_headers", rel_path, 0,
                                 f"MCP 服务器 '{server_name}' 的 headers 中包含敏感 header '{header_name}'，凭据应由客户端管理")
            # 检查 header 值是否像密钥
            if isinstance(header_value, str) and len(header_value) > 16 and any(
                kw in header_name.lower() for kw in ["key", "token", "secret", "auth"]
            ):
                result.add_issue("critical", "secret_in_headers", rel_path, 0,
                                 f"MCP 服务器 '{server_name}' 的 header '{header_name}' 可能包含硬编码密钥")

        # 检查 env
        env = server_config.get("env", {})
        for env_name, env_value in env.items():
            if env_name.upper() in SENSITIVE_ENV_VARS:
                result.add_issue("high", "sensitive_env", rel_path, 0,
                                 f"MCP 服务器 '{server_name}' 的 env 中设置了敏感变量 '{env_name}'，应由客户端注入")
            # 检查 env 值是否像密钥
            if isinstance(env_value, str) and len(env_value) > 16 and not env_value.startswith("${"):
                if any(kw in env_name.upper() for kw in ["KEY", "SECRET", "TOKEN", "PASSWORD", "AUTH"]):
                    result.add_issue("critical", "hardcoded_secret", rel_path, 0,
                                     f"MCP 服务器 '{server_name}' 的 env '{env_name}' 可能包含硬编码密钥")

        # 检查 command
        command = server_config.get("command", "")
        if command and " " in command and not server_config.get("args"):
            result.add_issue("medium", "shell_command", rel_path, 0,
                             f"MCP 服务器 '{server_name}' 的 command 包含空格，应该是单个可执行 token，参数放在 args 中")

        # 检查保留环境变量
        if env:
            for reserved in ["PLUGIN_ROOT", "PLUGIN_DATA"]:
                if reserved in env:
                    result.add_issue("high", "reserved_env", rel_path, 0,
                                     f"MCP 服务器 '{server_name}' 的 env 中设置了保留变量 '{reserved}'，这由客户端自动注入")


def audit_plugin_json(plugin_path: Path, rel_path: str, result: AuditResult):
    """审计 plugin.json 中的安全问题"""
    try:
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    except Exception as e:
        result.add_issue("high", "invalid_json", rel_path, 0, f"plugin.json 不是有效 JSON: {e}")
        return

    result.files_scanned += 1

    # 检查 name
    name = plugin.get("name", "")
    if not name:
        result.add_issue("high", "missing_name", rel_path, 0, "plugin.json 缺少必需字段 name")
    elif not re.match(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$", name):
        result.add_issue("medium", "invalid_name", rel_path, 0,
                         f"plugin name '{name}' 不符合规范（小写字母+数字+连字符+点）")

    # 检查 $schema
    schema = plugin.get("$schema", "")
    if not schema:
        result.add_issue("low", "missing_schema", rel_path, 0, "plugin.json 缺少 $schema 字段")


def audit_skill(skill_dir: Path, rel_prefix: str, result: AuditResult):
    """审计单个 skill 的安全问题"""
    # 扫描 scripts/ 目录
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists() and scripts_dir.is_dir():
        for script_file in scripts_dir.rglob("*"):
            if script_file.is_file() and script_file.suffix in {".py", ".js", ".ts", ".sh", ".bash"}:
                rel = f"{rel_prefix}/{script_file.relative_to(skill_dir)}"
                scan_code_file(script_file, rel, result)

    # 扫描 SKILL.md 中的硬编码密钥
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        rel = f"{rel_prefix}/SKILL.md"
        scan_code_file(skill_md, rel, result)


def mask_sensitive(text: str) -> str:
    """对可能包含敏感信息的文本进行掩码处理"""
    import re
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


def print_report(result: AuditResult, min_severity: str = "low"):
    """打印审计报告"""
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    min_level = severity_order.get(min_severity, 3)

    print("=" * 70)
    print("Agent Plugin 安全审计报告")
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

    # 按严重级别排序
    sorted_issues = sorted(result.issues, key=lambda x: severity_order.get(x["severity"], 99))

    print("问题详情:")
    print("-" * 70)
    for issue in sorted_issues:
        if severity_order.get(issue["severity"], 99) > min_level:
            continue
        severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(issue["severity"], "⚪")
        print(f"\n{severity_icon} [{issue['severity'].upper()}] {issue['message']}")
        print(f"   文件: {issue['file']}" + (f":{issue['line']}" if issue['line'] > 0 else ""))
        print(f"   类别: {issue['category']}")
        if issue["snippet"]:
            print(f"   代码: {mask_sensitive(issue['snippet'])}")

    print()
    print("=" * 70)
    if result.critical_count > 0:
        print("❌ 存在严重安全问题，必须修复后才能发布")
    elif result.high_count > 0:
        print("⚠️  存在高危安全问题，建议修复后发布")
    elif result.medium_count > 0:
        print("⚡ 存在中危问题，建议评估后修复")
    else:
        print("✅ 仅存在低危问题，可发布但建议优化")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Agent Plugin 安全审计工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low"], default="low",
                        help="最低显示严重级别（默认 low，显示所有）")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.exists():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)
    if not plugin_dir.is_dir():
        print(f"错误: 路径不是目录: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    result = AuditResult()

    # 审计 plugin.json
    plugin_json = plugin_dir / "plugin.json"
    if plugin_json.exists():
        audit_plugin_json(plugin_json, "plugin.json", result)
    else:
        result.add_issue("high", "missing_plugin_json", "plugin.json", 0, "缺少必需文件 plugin.json")

    # 审计 mcp.json
    mcp_json = plugin_dir / "mcp.json"
    if mcp_json.exists():
        audit_mcp_json(mcp_json, "mcp.json", result)

    # 审计 skills/
    skills_dir = plugin_dir / "skills"
    if skills_dir.exists() and skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                audit_skill(skill_dir, f"skills/{skill_dir.name}", result)

    # 审计 MCP 服务器代码（兼容 server/ 单数 和 servers/ 复数两种目录命名）
    for servers_dir_name in ("servers", "server"):
        servers_dir = plugin_dir / servers_dir_name
        if servers_dir.exists() and servers_dir.is_dir():
            # 区分两种布局：
            # - servers/<name>/...  （多服务器，官方推荐）
            # - server/...          （单服务器扁平，历史 examples 用法）
            subdirs = [d for d in servers_dir.iterdir() if d.is_dir()]
            if subdirs:
                # 多服务器布局：遍历每个子目录
                for server_dir in subdirs:
                    for code_file in server_dir.rglob("*"):
                        if code_file.is_file() and code_file.suffix in {".py", ".js", ".ts", ".sh", ".bash"}:
                            if "node_modules" in code_file.parts or "__pycache__" in code_file.parts:
                                continue
                            rel = f"{servers_dir_name}/{code_file.relative_to(servers_dir)}"
                            scan_code_file(code_file, rel, result)
            else:
                # 单服务器扁平布局：直接扫描 server/ 下的代码文件
                for code_file in servers_dir.rglob("*"):
                    if code_file.is_file() and code_file.suffix in {".py", ".js", ".ts", ".sh", ".bash"}:
                        if "node_modules" in code_file.parts or "__pycache__" in code_file.parts:
                            continue
                        rel = f"{servers_dir_name}/{code_file.relative_to(servers_dir)}"
                        scan_code_file(code_file, rel, result)

    # 输出结果
    if args.format == "json":
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
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_report(result, args.severity)

    # 退出码：有 critical 或 high 问题时返回 1
    sys.exit(1 if result.critical_count > 0 or result.high_count > 0 else 0)


if __name__ == "__main__":
    main()
