#!/usr/bin/env python3
"""
MCP 服务器握手测试工具

通过 stdio 启动 MCP 服务器，执行标准握手流程：
  1. initialize 请求 → 验证 serverInfo 和 capabilities
  2. notifications/initialized 通知
  3. tools/list 请求 → 验证工具列表
  4. resources/list 请求 → 验证资源列表（服务器不支持则标记为不支持）
  5. prompts/list 请求 → 验证提示列表（服务器不支持则标记为不支持）

用法:
    python3 test_mcp_handshake.py --command "npx tsx src/server.ts"
    python3 test_mcp_handshake.py --command "python server.py" --timeout 15
    python3 test_mcp_handshake.py --command "..." --no-check-resources --no-check-prompts
"""
import argparse
import json
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
        # 服务器进程已退出或 stdin 已关闭
        return {"_error": "无法写入服务器 stdin（进程可能已退出）"}


def read_response(proc, timeout: float = 10.0) -> dict:
    """读取 MCP 服务器的响应（单行 JSON）"""
    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            return {"_error": f"服务器进程已退出，退出码: {proc.returncode}"}
        line = proc.stdout.readline()
        if line:
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                # 可能是 stderr 输出或其他非 JSON 行，继续读取
                continue
        time.sleep(0.05)
    return {"_error": f"等待响应超时（{timeout}秒）"}


def test_handshake(command: str, timeout: int = 10, check_resources: bool = True,
                   check_prompts: bool = True, cwd: str = None) -> dict:
    """执行完整的 MCP 握手测试（默认检查 tools/resources/prompts 全部）"""
    results = {
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

    try:
        # 使用 shlex.split 安全拆分命令，避免 shell=True 的命令注入风险
        cmd_parts = shlex.split(command)
        proc = subprocess.Popen(
            cmd_parts,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd,
        )
    except Exception as e:
        results["errors"].append(f"无法启动服务器: {e}")
        return results

    try:
        # 1. initialize
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcp-handshake-tester", "version": "1.0.0"},
            },
        })
        resp = read_response(proc, timeout)
        if "_error" in resp:
            results["initialize"]["details"] = resp["_error"]
            results["errors"].append(f"initialize 失败: {resp['_error']}")
        elif "error" in resp:
            results["initialize"]["details"] = f"服务器返回错误: {resp['error']}"
            results["errors"].append(f"initialize 错误: {resp['error']}")
        elif "result" in resp:
            result = resp["result"]
            results["server_info"] = result.get("serverInfo")
            capabilities = result.get("capabilities", {})
            results["initialize"]["passed"] = True
            results["initialize"]["details"] = (
                f"服务器: {result.get('serverInfo', {}).get('name', 'unknown')} "
                f"v{result.get('serverInfo', {}).get('version', 'unknown')}, "
                f"能力: {', '.join(capabilities.keys()) if capabilities else '无'}"
            )
        else:
            results["initialize"]["details"] = f"未知响应格式: {resp}"
            results["errors"].append(f"initialize 未知响应: {resp}")

        # 2. notifications/initialized
        send_message(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # 3. tools/list
        send_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        resp = read_response(proc, timeout)
        if "_error" in resp:
            results["tools_list"]["details"] = resp["_error"]
            results["errors"].append(f"tools/list 失败: {resp['_error']}")
        elif "error" in resp:
            results["tools_list"]["details"] = f"服务器返回错误: {resp['error']}"
        elif "result" in resp:
            tools = resp["result"].get("tools", [])
            results["tools"] = tools
            results["tools_list"]["passed"] = True
            results["tools_list"]["details"] = f"发现 {len(tools)} 个工具"
        else:
            results["tools_list"]["details"] = f"未知响应格式: {resp}"

        # 4. resources/list（默认检查，服务器不支持则标记为不支持）
        if check_resources:
            send_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "resources/list"})
            resp = read_response(proc, timeout)
            if "result" in resp:
                resources = resp["result"].get("resources", [])
                results["resources"] = resources
                results["resources_list"]["passed"] = True
                results["resources_list"]["details"] = f"发现 {len(resources)} 个资源"
            elif "error" in resp:
                err_msg = str(resp.get("error", ""))
                if "MethodNotFound" in err_msg or "method not found" in err_msg.lower() or "-32601" in err_msg:
                    results["resources_list"]["passed"] = None
                    results["resources_list"]["details"] = "服务器不支持 resources 能力"
                else:
                    results["resources_list"]["passed"] = False
                    results["resources_list"]["details"] = f"错误: {resp['error']}"
            else:
                results["resources_list"]["passed"] = False
                results["resources_list"]["details"] = str(resp.get("_error", resp))

        # 5. prompts/list（默认检查，服务器不支持则标记为不支持）
        if check_prompts:
            send_message(proc, {"jsonrpc": "2.0", "id": 4, "method": "prompts/list"})
            resp = read_response(proc, timeout)
            if "result" in resp:
                prompts = resp["result"].get("prompts", [])
                results["prompts"] = prompts
                results["prompts_list"]["passed"] = True
                results["prompts_list"]["details"] = f"发现 {len(prompts)} 个提示"
            elif "error" in resp:
                err_msg = str(resp.get("error", ""))
                if "MethodNotFound" in err_msg or "method not found" in err_msg.lower() or "-32601" in err_msg:
                    results["prompts_list"]["passed"] = None
                    results["prompts_list"]["details"] = "服务器不支持 prompts 能力"
                else:
                    results["prompts_list"]["passed"] = False
                    results["prompts_list"]["details"] = f"错误: {resp['error']}"
            else:
                results["prompts_list"]["passed"] = False
                results["prompts_list"]["details"] = str(resp.get("_error", resp))

    finally:
        # 终止服务器进程
        if proc.poll() is None:
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
            if "不支持" in check["details"]:
                status = "⚪ 不支持"
            else:
                status = "⚪ 跳过"
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

    if results["resources"]:
        print(f"\n📦 资源列表 ({len(results['resources'])}):")
        for r in results["resources"]:
            print(f"   - {r.get('name', '?')}: {r.get('uri', '')}")

    if results["prompts"]:
        print(f"\n💬 提示列表 ({len(results['prompts'])}):")
        for p in results["prompts"]:
            print(f"   - {p.get('name', '?')}: {p.get('description', '')[:60]}")

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
    parser = argparse.ArgumentParser(description="MCP 服务器握手测试工具（默认检查 tools/resources/prompts 全部）")
    parser.add_argument("--command", required=True, help="启动 MCP 服务器的命令（如 'npx tsx src/server.ts'）")
    parser.add_argument("--timeout", type=int, default=10, help="响应超时秒数（默认 10）")
    parser.add_argument("--cwd", help="服务器工作目录（默认当前目录）")
    parser.add_argument("--no-check-resources", action="store_true", help="跳过 resources/list 检查")
    parser.add_argument("--no-check-prompts", action="store_true", help="跳过 prompts/list 检查")
    parser.add_argument("--check-resources", action="store_true", help="（已默认启用，保留用于向后兼容）")
    parser.add_argument("--check-prompts", action="store_true", help="（已默认启用，保留用于向后兼容）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    args = parser.parse_args()

    results = test_handshake(
        command=args.command,
        timeout=args.timeout,
        check_resources=not args.no_check_resources,
        check_prompts=not args.no_check_prompts,
        cwd=args.cwd,
    )

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        sys.exit(0 if results["initialize"]["passed"] and results["tools_list"]["passed"] else 1)
    else:
        all_passed = print_results(results)
        sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
