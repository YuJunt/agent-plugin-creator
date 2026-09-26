#!/usr/bin/env python3
"""MCP 服务器性能基准测试（自研 JSON-RPC 客户端，无外部依赖）。

与 test_mcp_handshake.py 使用相同的 JSON-RPC over stdio 实现，
兼容 fastmcp / TypeScript SDK / 任何标准 MCP stdio 服务器。

用法:
    python3 benchmark_mcp.py --server server.py --tool add --arguments '{"a":1,"b":2}' --requests 10 --output result.json
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
import statistics
from pathlib import Path


def send_message(proc, message: dict):
    """向 MCP 服务器发送 JSON-RPC 消息（单行 JSON + 换行）"""
    line = json.dumps(message) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()


def read_response(proc, timeout: float = 10.0) -> dict:
    """读取 MCP 服务器的响应（单行 JSON），跳过非 JSON 行"""
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
                # 可能是 stderr 重定向或其他非 JSON 行，继续读取
                continue
        time.sleep(0.01)
    return {"_error": f"等待响应超时（{timeout}秒）"}


def run_benchmark(command: str, args: list, tool: str, arguments: dict,
                  requests: int, concurrency: int, timeout: int = 10) -> dict:
    """执行性能基准测试"""
    latencies = []
    failures = 0
    result_sizes = []

    # 启动服务器
    proc = subprocess.Popen(
        [command] + args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # 1. initialize 握手
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "agent-plugin-creator-benchmark", "version": "1.0.0"}
            }
        })
        resp = read_response(proc, timeout)
        if "_error" in resp:
            return {"error": f"initialize 失败: {resp['_error']}", "requests": requests, "successes": 0, "failures": requests}

        # 2. initialized 通知
        send_message(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # 3. tools/list（确认工具存在）
        send_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        resp = read_response(proc, timeout)
        if "_error" in resp:
            return {"error": f"tools/list 失败: {resp['_error']}", "requests": requests, "successes": 0, "failures": requests}

        # 4. 循环调用工具（注意：stdio 是串行的，concurrency 仅用于统计参考）
        for i in range(requests):
            t_start = time.perf_counter()
            try:
                send_message(proc, {
                    "jsonrpc": "2.0",
                    "id": 100 + i,
                    "method": "tools/call",
                    "params": {"name": tool, "arguments": arguments}
                })
                resp = read_response(proc, timeout)
                elapsed = (time.perf_counter() - t_start) * 1000

                if "_error" in resp or "error" in resp:
                    failures += 1
                else:
                    latencies.append(elapsed)
                    # 计算结果大小
                    result_text = json.dumps(resp.get("result", {}), ensure_ascii=False)
                    result_sizes.append(len(result_text))
            except Exception:
                failures += 1

    finally:
        # 关闭服务器
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    latencies.sort()
    p95 = latencies[min(len(latencies) - 1, max(0, int(len(latencies) * 0.95) - 1))] if latencies else None

    return {
        "requests": requests,
        "concurrency": concurrency,
        "successes": len(latencies),
        "failures": failures,
        "failure_rate": failures / requests if requests else 0,
        "latency_ms": {
            "min": min(latencies) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "p95": p95,
            "max": max(latencies) if latencies else None,
        },
        "result_size_bytes": {
            "max": max(result_sizes) if result_sizes else None,
            "median": statistics.median(result_sizes) if result_sizes else None,
        },
    }


def main():
    ap = argparse.ArgumentParser(description="MCP 服务器性能基准测试（自研 JSON-RPC 客户端，无外部依赖）")
    ap.add_argument("--server", type=Path, required=True, help="MCP 服务器脚本路径")
    ap.add_argument("--cwd", type=Path, help="工作目录（默认服务器所在目录）")
    ap.add_argument("--command", default="python3", help="启动命令（默认 python3）")
    ap.add_argument("--tool", required=True, help="要调用的工具名")
    ap.add_argument("--arguments", required=True, help="工具参数（JSON 字符串）")
    ap.add_argument("--requests", type=int, default=10, help="请求次数（默认 10）")
    ap.add_argument("--concurrency", type=int, default=1, help="并发数（stdio 为串行，仅统计参考）")
    ap.add_argument("--timeout", type=int, default=10, help="单次响应超时秒数（默认 10）")
    ap.add_argument("--output", type=Path, required=True, help="结果输出 JSON 文件路径")
    a = ap.parse_args()

    # 解析参数
    try:
        arguments = json.loads(a.arguments)
    except json.JSONDecodeError as e:
        print(f"错误: --arguments 不是有效 JSON: {e}", file=sys.stderr)
        sys.exit(1)

    cwd = str(a.cwd or a.server.parent)
    result = run_benchmark(a.command, [str(a.server)], a.tool, arguments,
                           a.requests, a.concurrency, a.timeout)

    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("failure_rate", 1) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
