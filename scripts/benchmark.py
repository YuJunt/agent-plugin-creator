#!/usr/bin/env python3
"""
性能基准测试脚本。

测量关键操作的执行时间，建立性能基线。

用法:
    python3 scripts/benchmark.py [--iterations N] [--output FILE] [--json]

测试项:
    1. validate_skill - 技能验证
    2. validate_plugin - 插件验证
    3. audit_plugin - 安全审计
    4. init_skill - Skill 脚手架生成
    5. plugin_to_skill - 反向封装
    6. client_adapter --check - 客户端兼容性检查
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from statistics import mean, median, stdev


ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd: list, cwd: Path = None, timeout: int = 30) -> tuple[float, int, str]:
    """运行命令并返回执行时间（秒）、退出码、输出。"""
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.perf_counter() - start
        return elapsed, result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return elapsed, -1, "TIMEOUT"


def benchmark(name: str, cmd: list, iterations: int = 5, cwd: Path = None) -> dict:
    """运行基准测试。"""
    times = []
    exit_codes = []

    for i in range(iterations):
        elapsed, code, output = run_command(cmd, cwd)
        times.append(elapsed)
        exit_codes.append(code)

    success_rate = sum(1 for c in exit_codes if c == 0) / len(exit_codes) * 100

    return {
        "name": name,
        "iterations": iterations,
        "success_rate": round(success_rate, 1),
        "min_ms": round(min(times) * 1000, 2),
        "max_ms": round(max(times) * 1000, 2),
        "mean_ms": round(mean(times) * 1000, 2),
        "median_ms": round(median(times) * 1000, 2),
        "stddev_ms": round(stdev(times) * 1000, 2) if len(times) > 1 else 0,
        "exit_codes": exit_codes,
    }


def main():
    parser = argparse.ArgumentParser(description="性能基准测试脚本")
    parser.add_argument("--iterations", type=int, default=5, help="每个测试的迭代次数（默认5）")
    parser.add_argument("--output", help="输出 JSON 结果文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--quick", action="store_true", help="快速模式（3次迭代，跳过慢测试）")
    args = parser.parse_args()

    iterations = 3 if args.quick else args.iterations

    print("=" * 70)
    print("Agent Plugin Creator 性能基准测试")
    print("=" * 70)
    print(f"迭代次数: {iterations}")
    print(f"技能根目录: {ROOT}")
    print()

    results = []

    # 测试1: validate_skill
    print("[1/6] 测试 validate_skill...")
    results.append(benchmark(
        "validate_skill",
        ["python3", str(ROOT / "scripts/validate_skill.py"), str(ROOT)],
        iterations,
    ))

    # 测试2: validate_plugin (minimal-skill-only)
    print("[2/6] 测试 validate_plugin (minimal)...")
    results.append(benchmark(
        "validate_plugin_minimal",
        ["python3", str(ROOT / "scripts/validate_plugin.py"),
         str(ROOT / "examples/minimal-skill-only")],
        iterations,
    ))

    # 测试3: validate_plugin (complex)
    print("[3/6] 测试 validate_plugin (complex)...")
    results.append(benchmark(
        "validate_plugin_complex",
        ["python3", str(ROOT / "scripts/validate_plugin.py"),
         str(ROOT / "examples/ecommerce.refund-approval")],
        iterations,
    ))

    # 测试4: audit_plugin
    print("[4/6] 测试 audit_plugin...")
    results.append(benchmark(
        "audit_plugin",
        ["python3", str(ROOT / "scripts/audit_plugin.py"),
         str(ROOT / "examples/customer-support.triage"), "--severity", "low"],
        iterations,
    ))

    # 测试5: init_skill (在临时目录中)
    print("[5/6] 测试 init_skill...")
    with tempfile.TemporaryDirectory() as td:
        results.append(benchmark(
            "init_skill",
            ["python3", str(ROOT / "scripts/init_skill.py"), "bench-test-skill",
             "--path", td, "--force"],
            iterations,
        ))

    # 测试6: client_adapter --check
    if not args.quick:
        print("[6/6] 测试 client_adapter --check...")
        results.append(benchmark(
            "client_adapter_check",
            ["python3", str(ROOT / "scripts/client_adapter.py"),
             str(ROOT / "examples/minimal-skill-only"), "--check"],
            iterations,
        ))
    else:
        print("[6/6] 跳过 client_adapter (快速模式)")

    print()
    print("=" * 70)
    print("基准测试结果")
    print("=" * 70)
    print()

    # 表格输出
    header = f"{'测试项':<30} {'平均(ms)':<10} {'最小(ms)':<10} {'最大(ms)':<10} {'成功率':<8}"
    print(header)
    print("-" * 70)

    for r in results:
        status = "✅" if r["success_rate"] == 100 else "❌"
        print(f"{r['name']:<30} {r['mean_ms']:<10} {r['min_ms']:<10} {r['max_ms']:<10} {r['success_rate']:<8} {status}")

    print()
    print("=" * 70)

    # 性能评级
    total_mean = sum(r["mean_ms"] for r in results) / len(results)
    print(f"总体平均: {total_mean:.2f} ms")
    if total_mean < 100:
        print("性能评级: ⭐⭐⭐⭐⭐ 优秀（<100ms）")
    elif total_mean < 300:
        print("性能评级: ⭐⭐⭐⭐ 良好（<300ms）")
    elif total_mean < 1000:
        print("性能评级: ⭐⭐⭐ 一般（<1s）")
    else:
        print("性能评级: ⭐⭐ 需优化（>1s）")
    print("=" * 70)

    # 输出 JSON
    if args.json or args.output:
        output = {
            "benchmark_version": "1.0",
            "iterations": iterations,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
            "summary": {
                "total_mean_ms": round(total_mean, 2),
                "all_passed": all(r["success_rate"] == 100 for r in results),
            },
        }
        json_str = json.dumps(output, ensure_ascii=False, indent=2)

        if args.output:
            Path(args.output).write_text(json_str, encoding="utf-8")
            print(f"\n结果已保存到: {args.output}")

        if args.json:
            print(json_str)

    # 退出码
    if all(r["success_rate"] == 100 for r in results):
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
