#!/usr/bin/env python3
"""
MCP 工具真实调用测试

不只是握手测试，而是实际调用每个工具并验证输出结构。

用法:
    python3 scripts/test_mcp_tools.py --command "python3 servers/my-server/server.py"
    python3 scripts/test_mcp_tools.py --command "python3 server.py" --timeout 15
    python3 scripts/test_mcp_tools.py --command "python3 server.py" --json
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def send_message(proc, message: dict):
    """向 MCP 服务器发送 JSON-RPC 消息"""
    line = json.dumps(message) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()


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
                continue
        time.sleep(0.05)
    return {"_error": f"等待响应超时（{timeout}秒）"}


def generate_test_args(tool: dict) -> dict:
    """根据工具的 inputSchema 自动生成测试参数"""
    args = {}
    properties = tool.get("inputSchema", {}).get("properties", {})
    required = tool.get("inputSchema", {}).get("required", [])

    for param_name, param_schema in properties.items():
        param_type = param_schema.get("type", "string")
        # 只给必填参数生成测试值，可选参数留空
        if param_name not in required:
            continue

        if param_type == "string":
            if "enum" in param_schema:
                args[param_name] = param_schema["enum"][0]
            elif param_name in ("url", "link", "endpoint"):
                args[param_name] = "https://example.com"
            elif param_name in ("path", "file", "filename"):
                args[param_name] = "/tmp/test.txt"
            elif param_name in ("query", "search", "keyword", "q"):
                args[param_name] = "test"
            else:
                args[param_name] = "test_value"
        elif param_type == "integer":
            args[param_name] = 1
        elif param_type == "number":
            args[param_name] = 1.0
        elif param_type == "boolean":
            args[param_name] = True
        elif param_type == "array":
            args[param_name] = []
        elif param_type == "object":
            args[param_name] = {}

    return args


def test_tool_call(proc, tool: dict, msg_id: int, timeout: int) -> dict:
    """测试单个工具调用"""
    tool_name = tool.get("name", "unknown")
    test_args = generate_test_args(tool)

    call_msg = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": test_args,
        },
    }

    start = time.time()
    send_message(proc, call_msg)
    response = read_response(proc, timeout=timeout)
    duration = round((time.time() - start) * 1000, 1)

    result = {
        "tool": tool_name,
        "test_arguments": test_args,
        "duration_ms": duration,
        "passed": False,
        "error": None,
        "output_preview": None,
    }

    if "_error" in response:
        result["error"] = response["_error"]
        return result

    if "error" in response:
        result["error"] = f"JSON-RPC error: {response['error'].get('message', 'unknown')}"
        return result

    if "result" not in response:
        result["error"] = "响应中缺少 result 字段"
        return result

    content = response["result"].get("content", [])
    if not content:
        result["error"] = "工具返回空 content"
        return result

    # 提取文本内容
    text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
    result["output_preview"] = "\n".join(text_parts)[:500]
    result["passed"] = True
    result["content_count"] = len(content)
    result["is_error"] = response["result"].get("isError", False)

    return result


def main():
    parser = argparse.ArgumentParser(description="MCP 工具真实调用测试")
    parser.add_argument("--command", required=True, help="MCP 服务器启动命令")
    parser.add_argument("--args", nargs="*", default=[], help="命令参数")
    parser.add_argument("--timeout", type=int, default=10, help="单次响应超时（秒）")
    parser.add_argument("--cwd", help="工作目录")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--skip-tools", nargs="*", default=[], help="跳过测试的工具名")
    args = parser.parse_args()

    # 启动服务器
    cmd = [args.command] + args.args
    cwd = args.cwd or str(Path(args.command).parent if Path(args.command).parent != Path(".") else ".")

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd if cwd != "." else None,
        )
    except FileNotFoundError:
        print(f"错误: 命令不存在: {args.command}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 启动服务器失败: {e}", file=sys.stderr)
        sys.exit(1)

    results = {
        "handshake": None,
        "tools_list": None,
        "tool_tests": [],
        "summary": {},
    }

    msg_id = 1

    # 1. 握手 initialize
    init_msg = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "agent-plugin-creator-test", "version": "1.0.0"},
        },
    }
    msg_id += 1
    send_message(proc, init_msg)
    init_resp = read_response(proc, timeout=args.timeout)

    if "_error" in init_resp:
        results["handshake"] = {"passed": False, "error": init_resp["_error"]}
        proc.terminate()
        _output(results, args.json)
        sys.exit(1)

    if "error" in init_resp:
        results["handshake"] = {"passed": False, "error": init_resp["error"].get("message", "unknown")}
        proc.terminate()
        _output(results, args.json)
        sys.exit(1)

    results["handshake"] = {
        "passed": True,
        "protocol_version": init_resp.get("result", {}).get("protocolVersion", "unknown"),
        "server_info": init_resp.get("result", {}).get("serverInfo", {}),
    }

    # 2. 发送 initialized 通知
    send_message(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    # 3. 列出工具
    list_msg = {"jsonrpc": "2.0", "id": msg_id, "method": "tools/list"}
    msg_id += 1
    send_message(proc, list_msg)
    list_resp = read_response(proc, timeout=args.timeout)

    if "_error" in list_resp or "error" in list_resp:
        results["tools_list"] = {"passed": False, "error": list_resp.get("_error") or list_resp.get("error", {}).get("message")}
        proc.terminate()
        _output(results, args.json)
        sys.exit(1)

    tools = list_resp.get("result", {}).get("tools", [])
    results["tools_list"] = {"passed": True, "count": len(tools), "tools": [t.get("name") for t in tools]}

    # 4. 逐个调用工具
    for tool in tools:
        tool_name = tool.get("name", "")
        if tool_name in args.skip_tools:
            results["tool_tests"].append({
                "tool": tool_name,
                "passed": True,
                "skipped": True,
                "error": None,
            })
            continue

        test_result = test_tool_call(proc, tool, msg_id, args.timeout)
        msg_id += 1
        results["tool_tests"].append(test_result)

    # 5. 关闭服务器
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    # 汇总
    passed = sum(1 for t in results["tool_tests"] if t.get("passed") and not t.get("skipped"))
    failed = sum(1 for t in results["tool_tests"] if not t.get("passed") and not t.get("skipped"))
    skipped = sum(1 for t in results["tool_tests"] if t.get("skipped"))
    total = len(results["tool_tests"])

    results["summary"] = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round(passed / (total - skipped) * 100, 1) if (total - skipped) > 0 else 0,
    }

    _output(results, args.json)
    sys.exit(0 if failed == 0 else 1)


def _output(results: dict, as_json: bool):
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print("=" * 60)
    print("MCP 工具真实调用测试")
    print("=" * 60)

    # 握手
    hs = results["handshake"]
    if hs and hs.get("passed"):
        print(f"\n✅ 握手通过: {hs.get('server_info', {}).get('name', 'unknown')} v{hs.get('server_info', {}).get('version', '?')}")
    else:
        print(f"\n❌ 握手失败: {hs.get('error', 'unknown') if hs else 'no result'}")

    # 工具列表
    tl = results["tools_list"]
    if tl and tl.get("passed"):
        print(f"✅ 工具列表: {tl['count']} 个工具")
    else:
        print(f"❌ 工具列表获取失败: {tl.get('error') if tl else 'no result'}")

    # 逐个工具
    print("\n工具调用测试:")
    print("-" * 60)
    for t in results["tool_tests"]:
        if t.get("skipped"):
            print(f"  ⏭️  {t['tool']} (跳过)")
        elif t.get("passed"):
            status = "❌(isError)" if t.get("is_error") else "✅"
            print(f"  {status} {t['tool']} ({t['duration_ms']}ms)")
        else:
            print(f"  ❌ {t['tool']}: {t.get('error', 'unknown')}")

    # 汇总
    s = results["summary"]
    print("\n" + "=" * 60)
    print(f"汇总: {s['passed']}/{s['total'] - s['skipped']} 通过 "
          f"({s['pass_rate']}%), 失败 {s['failed']}, 跳过 {s['skipped']}")
    if s["failed"] == 0:
        print("✅ 所有工具调用测试通过")
    else:
        print("❌ 存在工具调用失败")
    print("=" * 60)


if __name__ == "__main__":
    main()
