#!/usr/bin/env python3
"""
MCP 服务器握手测试工具（支持双时代协议）

通过 stdio 启动 MCP 服务器，自动检测协议版本并执行对应握手流程：
  - 旧版（2024-11-05）：initialize → notifications/initialized → tools/list
  - 新版（2026-07-28）：无状态模式，直接 tools/list（无需 initialize）

用法:
    python3 test_mcp_handshake.py --command "npx tsx src/server.ts"
    python3 test_mcp_handshake.py --command "python server.py" --timeout 15
    python3 test_mcp_handshake.py --command "..." --mode legacy|stateless|auto
"""
import argparse
import json
import selectors
import shlex
import subprocess
import sys
import time


def send_message(proc, message: dict):
    """向 MCP 服务器发送 JSON-RPC 消息"""
    line = json.dumps(message) + "\n"
    try:
        proc.stdin.write(line)
        proc.stdin.flush()
    except (BrokenPipeError, ValueError, OSError):
        return {"_error": "无法写入服务器 stdin（进程可能已退出）"}


def read_response(proc, timeout: float = 10.0) -> dict:
    """读取 MCP 服务器的响应（单行 JSON），使用 selectors 实现真正的超时"""
    start = time.time()
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)

    while time.time() - start < timeout:
        if proc.poll() is not None:
            sel.close()
            return {"_error": f"服务器进程已退出，退出码: {proc.returncode}"}

        remaining = max(0, timeout - (time.time() - start))
        events = sel.select(timeout=min(remaining, 0.5))
        if not events:
            continue

        line = proc.stdout.readline()
        if not line:
            sel.close()
            return {"_error": "服务器 stdout 已关闭（进程可能已退出）"}

        line = line.strip()
        if not line:
            continue
        try:
            sel.close()
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    sel.close()
    return {"_error": f"等待响应超时（{timeout}秒）"}


def _try_legacy_handshake(proc, results: dict, timeout: int) -> bool:
    """旧版握手流程（2024-11-05 协议）"""
    # 1. initialize
    send_message(proc, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mcp-handshake-tester", "version": "1.0.0"},
        },
    })
    resp = read_response(proc, timeout)
    if "_error" in resp or "error" in resp:
        results["initialize"]["details"] = resp.get("_error", f"错误: {resp.get('error')}")
        return False
    if "result" in resp:
        result = resp["result"]
        results["server_info"] = result.get("serverInfo")
        capabilities = result.get("capabilities", {})
        results["initialize"]["passed"] = True
        results["initialize"]["details"] = (
            f"服务器: {result.get('serverInfo', {}).get('name', 'unknown')} "
            f"v{result.get('serverInfo', {}).get('version', 'unknown')}, "
            f"能力: {', '.join(capabilities.keys()) if capabilities else '无'}"
        )

    # 2. notifications/initialized
    send_message(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    # 3. tools/list
    send_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    resp = read_response(proc, timeout)
    if "_error" in resp or "error" in resp:
        results["tools_list"]["details"] = resp.get("_error", f"错误: {resp.get('error')}")
        return False
    if "result" in resp:
        tools = resp["result"].get("tools", [])
        results["tools"] = tools
        results["tools_list"]["passed"] = True
        results["tools_list"]["details"] = f"发现 {len(tools)} 个工具"
        return True
    return False


def _try_stateless_handshake(proc, results: dict, timeout: int) -> bool:
    """新版无状态模式（2026-07-28 协议，无需 initialize）"""
    results["initialize"] = {"passed": True, "details": "无状态模式（无需 initialize）"}
    send_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    resp = read_response(proc, timeout)
    if "_error" in resp or "error" in resp:
        results["tools_list"]["details"] = resp.get("_error", f"错误: {resp.get('error')}")
        return False
    if "result" in resp:
        tools = resp["result"].get("tools", [])
        results["tools"] = tools
        results["tools_list"]["passed"] = True
        results["tools_list"]["details"] = f"发现 {len(tools)} 个工具（无状态模式）"
        return True
    return False


def test_handshake(command: str, timeout: int = 10, check_resources: bool = True,
                   check_prompts: bool = True, cwd: str = None, mode: str = "auto") -> dict:
    """执行 MCP 握手测试（自动检测协议版本）

    mode:
        - "auto": 自动检测（先试旧版，失败则试新版）
        - "legacy": 强制旧版握手（2024-11-05）
        - "stateless": 强制新版无状态（2026-07-28）
    """
    results = {
        "protocol_mode": None,
        "initialize": {"passed": False, "details": ""},
        "tools_list": {"passed": False, "details": ""},
        "resources_list": {"passed": None, "details": "未检查"},
        "prompts_list": {"passed": None, "details": "未检查"},
        "server_info": None,
        "tools": [],
        "resources": [],
        "prompts": [],
        "errors": [],
    }

    cmd_parts = shlex.split(command)

    def start_server():
        return subprocess.Popen(
            cmd_parts, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1, cwd=cwd,
        )

    proc = None
    try:
        proc = start_server()

        if mode == "auto":
            legacy_ok = _try_legacy_handshake(proc, results, timeout)
            if legacy_ok:
                results["protocol_mode"] = "legacy (2024-11-05)"
            else:
                # 旧版失败，重启进程试新版
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                proc = start_server()
                stateless_ok = _try_stateless_handshake(proc, results, timeout)
                if stateless_ok:
                    results["protocol_mode"] = "stateless (2026-07-28)"
        elif mode == "legacy":
            results["protocol_mode"] = "legacy (2024-11-05)"
            _try_legacy_handshake(proc, results, timeout)
        elif mode == "stateless":
            results["protocol_mode"] = "stateless (2026-07-28)"
            _try_stateless_handshake(proc, results, timeout)

        # 可选：resources/list
        if check_resources and results["tools_list"]["passed"]:
            send_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "resources/list"})
            resp = read_response(proc, timeout)
            if "result" in resp:
                resources = resp["result"].get("resources", [])
                results["resources"] = resources
                results["resources_list"]["passed"] = True
                results["resources_list"]["details"] = f"发现 {len(resources)} 个资源"
            elif "error" in resp:
                err_msg = str(resp.get("error", ""))
                if "MethodNotFound" in err_msg or "-32601" in err_msg:
                    results["resources_list"]["passed"] = None
                    results["resources_list"]["details"] = "服务器不支持 resources 能力"
                else:
                    results["resources_list"]["passed"] = False
                    results["resources_list"]["details"] = f"错误: {resp['error']}"
            else:
                results["resources_list"]["passed"] = False
                results["resources_list"]["details"] = str(resp.get("_error", resp))

        # 可选：prompts/list
        if check_prompts and results["tools_list"]["passed"]:
            send_message(proc, {"jsonrpc": "2.0", "id": 4, "method": "prompts/list"})
            resp = read_response(proc, timeout)
            if "result" in resp:
                prompts = resp["result"].get("prompts", [])
                results["prompts"] = prompts
                results["prompts_list"]["passed"] = True
                results["prompts_list"]["details"] = f"发现 {len(prompts)} 个提示"
            elif "error" in resp:
                err_msg = str(resp.get("error", ""))
                if "MethodNotFound" in err_msg or "-32601" in err_msg:
                    results["prompts_list"]["passed"] = None
                    results["prompts_list"]["details"] = "服务器不支持 prompts 能力"
                else:
                    results["prompts_list"]["passed"] = False
                    results["prompts_list"]["details"] = f"错误: {resp['error']}"
            else:
                results["prompts_list"]["passed"] = False
                results["prompts_list"]["details"] = str(resp.get("_error", resp))

    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    return results


def print_results(results: dict):
    """打印测试结果"""
    print("=" * 60)
    print("MCP 服务器握手测试报告")
    if results.get("protocol_mode"):
        print(f"协议模式: {results['protocol_mode']}")
    print("=" * 60)

    checks = [
        ("initialize (初始化握手)", results["initialize"]),
        ("tools/list (工具列表)", results["tools_list"]),
        ("resources/list (资源列表)", results["resources_list"]),
        ("prompts/list (提示列表)", results["prompts_list"]),
    ]

    all_passed = True
    for name, check in checks:
        if check["passed"] is None:
            status = "⚪ 不支持" if "不支持" in check["details"] else "⚪ 跳过"
        elif check["passed"]:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
            all_passed = False
        print(f"\n{status}: {name}")
        print(f"   {check['details']}")

    if results["server_info"]:
        si = results["server_info"]
        print(f"\n📋 服务器信息: {si.get('name', 'unknown')} v{si.get('version', 'unknown')}")

    if results["tools"]:
        print(f"\n🔧 工具列表 ({len(results['tools'])}):")
        for t in results["tools"]:
            print(f"   - {t.get('name', '?')}: {t.get('description', '')[:60]}")

    if results["errors"]:
        print(f"\n❌ 错误 ({len(results['errors'])}):")
        for e in results["errors"]:
            print(f"   - {e}")

    print("\n" + "=" * 60)
    if all_passed:
        print("结论: 握手测试全部通过 ✅")
    else:
        print("结论: 握手测试存在失败项 ❌")
    print("=" * 60)
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="MCP 服务器握手测试工具（支持双时代协议）")
    parser.add_argument("--command", required=True, help="启动 MCP 服务器的命令")
    parser.add_argument("--timeout", type=int, default=10, help="响应超时秒数（默认 10）")
    parser.add_argument("--cwd", help="服务器工作目录")
    parser.add_argument("--mode", choices=["auto", "legacy", "stateless"], default="auto",
                        help="协议模式（默认 auto 自动检测）")
    parser.add_argument("--no-check-resources", action="store_true", help="跳过 resources/list 检查")
    parser.add_argument("--no-check-prompts", action="store_true", help="跳过 prompts/list 检查")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    args = parser.parse_args()

    results = test_handshake(
        command=args.command,
        timeout=args.timeout,
        check_resources=not args.no_check_resources,
        check_prompts=not args.no_check_prompts,
        cwd=args.cwd,
        mode=args.mode,
    )

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        sys.exit(0 if results["initialize"]["passed"] and results["tools_list"]["passed"] else 1)
    else:
        all_passed = print_results(results)
        sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
