#!/usr/bin/env python3
"""
MCP 服务器安全检查清单（对照 OWASP MCP Security Cheat Sheet）

逐项检查 MCP 服务器的 12 项安全控制，输出合规报告。

用法:
    python3 mcp_security_check.py <插件目录路径>
    python3 mcp_security_check.py ./my-plugin --format json

参考:
    OWASP MCP Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html
    MCP Security Standard: https://mcp-security-standard.org/
"""
import argparse
import json
import re
import sys
from pathlib import Path


# OWASP MCP 12 项安全控制
SECURITY_CHECKS = [
    {
        "id": "AUTH-01",
        "name": "认证与授权",
        "description": "生产环境必须要求认证，禁止匿名访问",
        "severity": "critical",
        "check": lambda root: _check_authentication(root),
    },
    {
        "id": "NET-02",
        "name": "传输安全",
        "description": "远程 MCP 必须使用 HTTPS/TLS，禁止明文 HTTP",
        "severity": "high",
        "check": lambda root: _check_transport_security(root),
    },
    {
        "id": "INPUT-03",
        "name": "输入验证",
        "description": "所有工具参数必须验证类型和范围（Strict JSON Schema）",
        "severity": "high",
        "check": lambda root: _check_input_validation(root),
    },
    {
        "id": "TIMEOUT-04",
        "name": "超时设置",
        "description": "所有外部调用必须设置超时，防止挂起",
        "severity": "medium",
        "check": lambda root: _check_timeout(root),
    },
    {
        "id": "LOG-05",
        "name": "日志规范",
        "description": "日志输出到 stderr，stdout 只用于 JSON-RPC",
        "severity": "medium",
        "check": lambda root: _check_logging(root),
    },
    {
        "id": "SECRETS-06",
        "name": "敏感数据保护",
        "description": "禁止在日志或响应中打印密钥/密码，使用环境变量注入",
        "severity": "critical",
        "check": lambda root: _check_secrets(root),
    },
    {
        "id": "ERROR-07",
        "name": "错误处理",
        "description": "捕获所有异常，返回通用错误信息，不泄露内部细节",
        "severity": "medium",
        "check": lambda root: _check_error_handling(root),
    },
    {
        "id": "CONFIRM-08",
        "name": "工具确认",
        "description": "高风险操作必须要求用户确认（HITL）",
        "severity": "high",
        "check": lambda root: _check_user_confirmation(root),
    },
    {
        "id": "SUPPLY-09",
        "name": "供应链安全",
        "description": "依赖包版本锁定，定期更新，SBOM 生成",
        "severity": "high",
        "check": lambda root: _check_supply_chain(root),
    },
    {
        "id": "AUDIT-10",
        "name": "审计日志",
        "description": "记录所有工具调用用于审计",
        "severity": "medium",
        "check": lambda root: _check_audit_logging(root),
    },
    {
        "id": "POISON-11",
        "name": "工具描述投毒检测",
        "description": "工具描述中不包含恶意指令（忽略之前指令等）",
        "severity": "critical",
        "check": lambda root: _check_tool_poisoning(root),
    },
    {
        "id": "ISOLATE-12",
        "name": "隔离与沙箱",
        "description": "MCP 服务器进程与主机环境隔离，限制文件系统访问",
        "severity": "medium",
        "check": lambda root: _check_isolation(root),
    },
    # ===== OWASP MCP Top 10 模型层安全（2026 新增）=====
    {
        "id": "MCP01-MISBIND",
        "owasp_id": "MCP01",
        "name": "模型误绑定（Model Misbinding）",
        "description": "工具描述必须明确指定使用场景，避免被模型错误调用到不相关场景",
        "severity": "high",
        "check": lambda root: _check_model_misbinding(root),
    },
    {
        "id": "MCP02-SPOOF",
        "owasp_id": "MCP02",
        "name": "上下文欺骗（Context Spoofing）",
        "description": "工具输出不能伪装成系统指令或开发者消息，防止上下文欺骗",
        "severity": "high",
        "check": lambda root: _check_context_spoofing(root),
    },
    {
        "id": "MCP03-STATE",
        "owasp_id": "MCP03",
        "name": "提示状态操纵（Prompt-State Manipulation）",
        "description": "工具描述中不包含修改对话历史、系统提示或会话状态的指令",
        "severity": "critical",
        "check": lambda root: _check_prompt_state_manipulation(root),
    },
    {
        "id": "MCP07-COVERTC",
        "owasp_id": "MCP07",
        "name": "隐蔽通道滥用（Covert Channel Abuse）",
        "description": "工具输出不包含隐藏的指令或数据（如 Unicode 零宽字符、base64 编码指令）",
        "severity": "high",
        "check": lambda root: _check_covert_channel(root),
    },
    {
        "id": "MCP08-PRIVESC",
        "owasp_id": "MCP08",
        "name": "权限提升（Privilege Escalation）",
        "description": "高风险工具必须有明确的权限边界标注，防止权限提升",
        "severity": "high",
        "check": lambda root: _check_privilege_escalation(root),
    },
]


def _find_server_files(root: Path) -> list:
    """查找所有 MCP 服务器文件"""
    files = []
    for ext in ("*.py", "*.ts", "*.js"):
        for p in root.rglob(ext):
            if any(skip in str(p) for skip in ["__pycache__", "node_modules", ".git", "official"]):
                continue
            # 只检查 servers/ 目录下的文件，或包含 mcp/server 的文件
            if "servers" in str(p) or "mcp" in p.name.lower() or "server" in p.name.lower():
                files.append(p)
    return files


def _check_authentication(root: Path) -> dict:
    """检查认证要求"""
    servers = _find_server_files(root)
    has_auth = False
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if any(kw in content.lower() for kw in ["auth", "token", "api_key", "apikey", "oauth", "bearer"]):
            has_auth = True
            break
    return {
        "status": "pass" if has_auth else "warning",
        "detail": "服务器代码中检测到认证相关关键词" if has_auth else "未检测到认证机制（生产环境必须配置）",
        "servers_checked": len(servers),
    }


def _check_transport_security(root: Path) -> dict:
    """检查传输安全"""
    mcp_json = root / "mcp.json"
    if not mcp_json.exists():
        return {"status": "not-applicable", "detail": "无 mcp.json（纯 Skill 插件）"}
    try:
        mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "fail", "detail": "mcp.json 解析失败"}
    has_remote = False
    has_https = True
    for name, cfg in mcp.get("mcpServers", {}).items():
        if cfg.get("type") == "streamable-http" or "url" in cfg:
            has_remote = True
            url = cfg.get("url", "")
            if url.startswith("http://") and "localhost" not in url and "127.0.0.1" not in url:
                has_https = False
    if not has_remote:
        return {"status": "pass", "detail": "仅使用 stdio 传输（本地进程通信，无需 TLS）"}
    return {
        "status": "pass" if has_https else "fail",
        "detail": "远程 MCP 使用 HTTPS" if has_https else "远程 MCP 使用明文 HTTP",
    }


def _check_input_validation(root: Path) -> dict:
    """检查输入验证（Strict JSON Schema）"""
    servers = _find_server_files(root)
    has_strict = False
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if any(kw in content for kw in ["additionalProperties: false", "extra='forbid'", "extra=\"forbid\"", "model_config"]):
            has_strict = True
            break
    return {
        "status": "pass" if has_strict else "warning",
        "detail": "检测到 Strict Mode 配置" if has_strict else "未检测到 Strict JSON Schema（建议添加 additionalProperties: false）",
    }


def _check_timeout(root: Path) -> dict:
    """检查超时设置"""
    servers = _find_server_files(root)
    has_timeout = False
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if any(kw in content for kw in ["timeout", "Timeout", "TIMEOUT"]):
            has_timeout = True
            break
    return {
        "status": "pass" if has_timeout else "warning",
        "detail": "检测到超时相关代码" if has_timeout else "未检测到超时设置（建议外部调用都加 timeout）",
    }


def _check_logging(root: Path) -> dict:
    """检查日志规范"""
    servers = _find_server_files(root)
    has_stderr = False
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if "sys.stderr" in content or "console.error" in content or "process.stderr" in content:
            has_stderr = True
            break
    return {
        "status": "pass" if has_stderr else "warning",
        "detail": "检测到 stderr 日志输出" if has_stderr else "未检测到 stderr 日志（stdio 服务器不要打印到 stdout）",
    }


def _check_secrets(root: Path) -> dict:
    """检查敏感数据保护"""
    servers = _find_server_files(root)
    has_hardcoded = False
    patterns = [
        r'api[_-]?key\s*[:=]\s*[\'\"][A-Za-z0-9]{16,}[\'\"]',
        r'password\s*[:=]\s*[\'\"][^\'\"]{6,}[\'\"]',
        r'token\s*[:=]\s*[\'\"][A-Za-z0-9]{16,}[\'\"]',
    ]
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            if re.search(pat, content, re.IGNORECASE):
                if "your_" not in content.lower() and "example" not in content.lower():
                    has_hardcoded = True
                    break
    return {
        "status": "fail" if has_hardcoded else "pass",
        "detail": "检测到硬编码密钥" if has_hardcoded else "未检测到硬编码密钥",
    }


def _check_error_handling(root: Path) -> dict:
    """检查错误处理"""
    servers = _find_server_files(root)
    has_try_except = False
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if "try:" in content or "try {" in content or "catch" in content:
            has_try_except = True
            break
    return {
        "status": "pass" if has_try_except else "warning",
        "detail": "检测到异常处理代码" if has_try_except else "未检测到异常处理（建议添加 try-catch）",
    }


def _check_user_confirmation(root: Path) -> dict:
    """检查用户确认机制"""
    servers = _find_server_files(root)
    has_confirmation = False
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if any(kw in content.lower() for kw in ["confirm", "requires_confirmation", "user_approval", "hittl", "human-in-the-loop"]):
            has_confirmation = True
            break
    return {
        "status": "pass" if has_confirmation else "warning",
        "detail": "检测到用户确认机制" if has_confirmation else "未检测到 HITL 机制（高风险操作建议要求用户确认）",
    }


def _check_supply_chain(root: Path) -> dict:
    """检查供应链安全"""
    has_sbom = (root / "sbom.json").exists() or (root / "sbom.xml").exists()
    has_lock = (root / "package-lock.json").exists() or (root / "requirements-lock.txt").exists() or (root / "poetry.lock").exists()
    issues = []
    if not has_sbom:
        issues.append("缺少 SBOM 文件")
    if not has_lock:
        issues.append("缺少依赖锁定文件")
    status = "pass" if not issues else "warning"
    return {"status": status, "detail": "; ".join(issues) if issues else "SBOM 和依赖锁定文件齐全"}


def _check_audit_logging(root: Path) -> dict:
    """检查审计日志"""
    servers = _find_server_files(root)
    has_audit = False
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if any(kw in content.lower() for kw in ["audit", "log_tool_call", "log_request", "logging.info"]):
            has_audit = True
            break
    return {
        "status": "pass" if has_audit else "warning",
        "detail": "检测到审计日志代码" if has_audit else "未检测到审计日志（建议记录所有工具调用）",
    }


def _check_tool_poisoning(root: Path) -> dict:
    """检查工具描述投毒"""
    poisoning_patterns = [
        r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?",
        r"forget\s+(?:all\s+)?previous\s+instructions?",
        r"you\s+(?:are\s+now|must\s+now)\s+(?:act|be|pretend)",
    ]
    servers = _find_server_files(root)
    found = []
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pat in poisoning_patterns:
            if re.search(pat, content, re.IGNORECASE):
                found.append(f.name)
                break
    return {
        "status": "fail" if found else "pass",
        "detail": f"检测到投毒模式: {', '.join(found)}" if found else "未检测到工具描述投毒",
    }


def _check_isolation(root: Path) -> dict:
    """检查隔离与沙箱"""
    # 检查是否有 Docker 配置
    has_docker = (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists()
    return {
        "status": "pass" if has_docker else "info",
        "detail": "有 Docker 隔离配置" if has_docker else "无 Docker 隔离配置（生产环境建议容器化部署）",
    }


# ===== OWASP MCP Top 10 模型层安全检查函数 =====

def _check_model_misbinding(root: Path) -> dict:
    """MCP01: 检查工具描述是否明确指定使用场景"""
    servers = _find_server_files(root)
    vague_tools = []
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        # 检查工具描述是否过于模糊
        vague_patterns = [
            r'description:\s*["\']?(do something|handle stuff|process data|utility)',
            r'description:\s*["\']?(tool|function|action)\s*["\']?\s*$',
        ]
        for pat in vague_patterns:
            if re.search(pat, content, re.IGNORECASE | re.MULTILINE):
                vague_tools.append(f.name)
                break

    if vague_tools:
        return {
            "status": "fail",
            "detail": f"发现描述模糊的工具: {', '.join(set(vague_tools))}（容易被模型误绑定到错误场景）",
        }
    return {
        "status": "pass",
        "detail": "所有工具描述都明确了使用场景",
    }


def _check_context_spoofing(root: Path) -> dict:
    """MCP02: 检查工具输出是否可能伪装成系统指令"""
    servers = _find_server_files(root)
    spoof_patterns = [
        r'system\s*:',
        r'developer\s*message',
        r'you\s+must\s+now',
        r'ignore\s+(all\s+)?previous',
        r'new\s+instructions?\s*:',
    ]
    risky_files = []
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        # 只检查返回的文本内容中是否有这些模式
        for pat in spoof_patterns:
            if re.search(pat, content, re.IGNORECASE):
                risky_files.append(f.name)
                break

    if risky_files:
        return {
            "status": "warning",
            "detail": f"以下文件包含可能被误解为系统指令的文本: {', '.join(set(risky_files))}",
        }
    return {
        "status": "pass",
        "detail": "未发现上下文欺骗风险",
    }


def _check_prompt_state_manipulation(root: Path) -> dict:
    """MCP03: 检查工具描述中是否有修改对话历史的指令"""
    servers = _find_server_files(root)
    manipulation_patterns = [
        r'ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|messages?|context)',
        r'forget\s+everything',
        r'new\s+persona',
        r'you\s+are\s+now\s+(a|an)\s+(different|new)',
        r'rewrite\s+(the\s+)?(system|prompt|instructions?)',
    ]
    risky_files = []
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pat in manipulation_patterns:
            if re.search(pat, content, re.IGNORECASE):
                risky_files.append(f.name)
                break

    if risky_files:
        return {
            "status": "fail",
            "detail": f"发现提示状态操纵风险: {', '.join(set(risky_files))}",
        }
    return {
        "status": "pass",
        "detail": "未发现提示状态操纵风险",
    }


def _check_covert_channel(root: Path) -> dict:
    """MCP07: 检查是否有隐蔽通道风险"""
    servers = _find_server_files(root)
    covert_patterns = [
        r'[​-‍]',  # Unicode 零宽字符
        r'base64\.b64encode',
        r'\\u00[0-9a-fA-F]{2}\\u00[0-9a-fA-F]{2}',  # 连续 Unicode 转义
    ]
    risky_files = []
    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pat in covert_patterns:
            if re.search(pat, content):
                risky_files.append(f.name)
                break

    if risky_files:
        return {
            "status": "warning",
            "detail": f"发现隐蔽通道风险: {', '.join(set(risky_files))}（可能包含隐藏指令）",
        }
    return {
        "status": "pass",
        "detail": "未发现隐蔽通道风险",
    }


def _check_privilege_escalation(root: Path) -> dict:
    """MCP08: 检查高风险工具是否有权限标注"""
    servers = _find_server_files(root)
    has_risk_labels = False
    total_tools = 0

    for f in servers:
        content = f.read_text(encoding="utf-8", errors="ignore")
        # 统计工具数量
        tool_count = len(re.findall(r'@mcp\.tool\(\)|server\.tool\(', content))
        total_tools += tool_count
        # 检查是否有风险标注
        if re.search(r'RISK_LEVEL|risk_level|read-only|destructive|irreversible', content, re.IGNORECASE):
            has_risk_labels = True

    if total_tools == 0:
        return {"status": "info", "detail": "未发现工具定义"}

    if not has_risk_labels:
        return {
            "status": "warning",
            "detail": f"发现 {total_tools} 个工具，但缺少风险等级标注（建议添加 read-only/reversible/destructive 标签）",
        }
    return {
        "status": "pass",
        "detail": f"发现 {total_tools} 个工具，已有风险等级标注",
    }


def main():
    parser = argparse.ArgumentParser(description="MCP 服务器安全检查清单（对照 OWASP）")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    args = parser.parse_args()

    root = Path(args.plugin_dir).resolve()
    if not root.exists():
        print(f"错误: 目录不存在: {root}", file=sys.stderr)
        return 2

    results = []
    for check in SECURITY_CHECKS:
        try:
            result = check["check"](root)
        except Exception as e:
            result = {"status": "error", "detail": f"检查执行失败: {e}"}
        results.append({
            "id": check["id"],
            "name": check["name"],
            "severity": check["severity"],
            "description": check["description"],
            **result,
        })

    # 统计
    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    if args.format == "json":
        output = {
            "plugin": str(root),
            "total_checks": len(results),
            "summary": status_counts,
            "checks": results,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0 if status_counts.get("fail", 0) == 0 else 1

    # 文本输出
    print("=" * 70)
    print("MCP 服务器安全检查清单（对照 OWASP MCP Security Cheat Sheet）")
    print("=" * 70)
    print()

    status_icon = {
        "pass": "✅",
        "warning": "⚠️",
        "fail": "❌",
        "error": "💥",
        "info": "ℹ️",
        "not-applicable": "⚪",
    }

    for r in results:
        icon = status_icon.get(r["status"], "?")
        print(f"{icon} [{r['id']}] {r['name']}")
        print(f"   级别: {r['severity']} | 状态: {r['status']}")
        print(f"   {r['detail']}")
        print()

    print("-" * 70)
    print("汇总:")
    for status, count in sorted(status_counts.items()):
        icon = status_icon.get(status, "?")
        print(f"  {icon} {status}: {count} 项")
    print()

    return 0 if status_counts.get("fail", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
