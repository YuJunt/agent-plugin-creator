#!/usr/bin/env python3
"""
性能基准持续监控工具

记录核心脚本的性能数据，对比历史结果，检测性能退化。

用法:
    python3 scripts/benchmark_monitor.py --run
    python3 scripts/benchmark_monitor.py --history
    python3 scripts/benchmark_monitor.py --compare baseline.json
    python3 scripts/benchmark_monitor.py --threshold 10 --json
"""
import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


# 基准测试项：(名称, 脚本, 参数)
BENCHMARKS = [
    ("validate_plugin_minimal", "validate_plugin.py", ["examples/minimal-skill-only"]),
    ("validate_skill_self", "validate_skill.py", ["."]),
    ("security_check_self", "security_check.py", [".", "--severity", "high"]),
    ("audit_plugin_example", "audit_plugin.py", ["examples/customer-support.triage"]),
    ("release_audit_self", "release_audit.py", ["."]),
    ("score_plugin_example", "score_plugin.py", ["examples/minimal-skill-only"]),
    ("fuzz_test_quick", "fuzz_test.py", ["--target", "validate_plugin", "--iterations", "10"]),
]


def run_benchmark(skill_root: Path, name: str, script: str, args: list, warmup: int = 1, runs: int = 3) -> dict:
    """运行单个基准测试"""
    script_path = skill_root / "scripts" / script
    if not script_path.exists():
        return {"name": name, "error": "script not found"}

    latencies = []

    # 预热
    for _ in range(warmup):
        try:
            subprocess.run(
                [sys.executable, str(script_path)] + args,
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            pass

    # 正式测试
    for _ in range(runs):
        start = time.perf_counter()
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)] + args,
                capture_output=True, text=True, timeout=30,
            )
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
        except subprocess.TimeoutExpired:
            latencies.append(30000)  # 超时记为 30s
        except Exception as e:
            return {"name": name, "error": str(e)}

    return {
        "name": name,
        "script": script,
        "runs": len(latencies),
        "min_ms": round(min(latencies), 1),
        "median_ms": round(statistics.median(latencies), 1),
        "mean_ms": round(statistics.mean(latencies), 1),
        "max_ms": round(max(latencies), 1),
        "stdev_ms": round(statistics.stdev(latencies), 1) if len(latencies) > 1 else 0,
        "latencies": [round(l, 1) for l in latencies],
    }


def load_history(history_file: Path) -> list:
    """加载历史基准数据"""
    if history_file.exists():
        try:
            return json.loads(history_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            return []
    return []


def save_history(history_file: Path, history: list):
    """保存历史基准数据"""
    # 只保留最近 50 条记录
    history = history[-50:]
    history_file.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compare_results(current: dict, baseline: dict, threshold: float) -> list:
    """对比基准结果，检测性能退化"""
    regressions = []

    current_benchmarks = {b["name"]: b for b in current.get("benchmarks", [])}
    baseline_benchmarks = {b["name"]: b for b in baseline.get("benchmarks", [])}

    for name, curr in current_benchmarks.items():
        if name in baseline_benchmarks and "median_ms" in curr and "median_ms" in baseline_benchmarks[name]:
            curr_median = curr["median_ms"]
            base_median = baseline_benchmarks[name]["median_ms"]
            if base_median > 0:
                change_pct = (curr_median - base_median) / base_median * 100
                if change_pct > threshold:
                    regressions.append({
                        "name": name,
                        "baseline_ms": base_median,
                        "current_ms": curr_median,
                        "change_pct": round(change_pct, 1),
                        "severity": "high" if change_pct > 50 else "medium",
                    })

    return regressions


def main():
    parser = argparse.ArgumentParser(description="性能基准持续监控工具")
    parser.add_argument("--run", action="store_true", help="运行基准测试")
    parser.add_argument("--history", action="store_true", help="查看历史记录")
    parser.add_argument("--compare", help="与指定的基准文件对比")
    parser.add_argument("--threshold", type=float, default=10.0, help="性能退化告警阈值（百分比，默认10%%）")
    parser.add_argument("--runs", type=int, default=3, help="每个测试运行次数")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    history_file = skill_root / "benchmark-history.json"

    if args.history:
        history = load_history(history_file)
        if args.json:
            print(json.dumps(history, ensure_ascii=False, indent=2))
        else:
            print(f"历史记录: {len(history)} 条")
            for record in history[-10:]:
                print(f"  {record.get('timestamp', '?')}: 平均 {record.get('avg_median_ms', '?')}ms")
        return

    if not args.run and not args.compare:
        args.run = True  # 默认运行

    if args.run:
        if not args.json:
            print(f"🔍 运行性能基准测试 ({len(BENCHMARKS)} 项, 每项 {args.runs} 次)")
            print()

        results = []
        for name, script, script_args in BENCHMARKS:
            if not args.json:
                print(f"  测试 {name}...", end=" ", flush=True)
            result = run_benchmark(skill_root, name, script, script_args, runs=args.runs)
            results.append(result)
            if not args.json:
                if "error" in result:
                    print(f"❌ {result['error']}")
                else:
                    print(f"{result['median_ms']}ms (中位数)")

        # 计算总体统计
        valid_results = [r for r in results if "median_ms" in r]
        avg_median = round(statistics.mean([r["median_ms"] for r in valid_results]), 1) if valid_results else 0

        current = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": results,
            "avg_median_ms": avg_median,
            "total_tests": len(results),
            "passed_tests": len(valid_results),
        }

        # 保存到历史
        history = load_history(history_file)
        history.append(current)
        save_history(history_file, history)

        # 与上一次对比
        regressions = []
        if len(history) >= 2:
            regressions = compare_results(current, history[-2], args.threshold)

        if args.json:
            print(json.dumps({**current, "regressions": regressions}, ensure_ascii=False, indent=2))
        else:
            print()
            print("=" * 50)
            print("性能基准结果")
            print("=" * 50)
            print(f"总平均中位数: {avg_median}ms")
            print(f"通过测试: {len(valid_results)}/{len(results)}")
            print()

            for r in results:
                if "error" in r:
                    print(f"  ❌ {r['name']}: {r['error']}")
                else:
                    print(f"  {r['name']}: {r['median_ms']}ms (min:{r['min_ms']} max:{r['max_ms']})")

            if regressions:
                print(f"\n⚠️  检测到 {len(regressions)} 项性能退化 (>{args.threshold}%):")
                for r in regressions:
                    icon = "🔴" if r["severity"] == "high" else "🟡"
                    print(f"  {icon} {r['name']}: {r['baseline_ms']}ms → {r['current_ms']}ms (+{r['change_pct']}%)")
            else:
                print("\n✅ 无性能退化")

            print(f"\n历史记录已保存: {history_file} ({len(history)} 条)")
            print("=" * 50)

        sys.exit(1 if regressions else 0)

    if args.compare:
        baseline_file = Path(args.compare)
        if not baseline_file.exists():
            print(f"错误: 基准文件不存在: {baseline_file}", file=sys.stderr)
            sys.exit(1)

        baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
        history = load_history(history_file)
        if not history:
            print("错误: 没有当前基准数据，请先运行 --run", file=sys.stderr)
            sys.exit(1)

        current = history[-1]
        regressions = compare_results(current, baseline, args.threshold)

        if args.json:
            print(json.dumps({"regressions": regressions, "current": current, "baseline": baseline}, ensure_ascii=False, indent=2))
        else:
            print(f"对比: 当前 vs {baseline_file.name}")
            print(f"性能退化: {len(regressions)} 项")
            for r in regressions:
                print(f"  {r['name']}: +{r['change_pct']}%")

        sys.exit(1 if regressions else 0)


if __name__ == "__main__":
    main()
