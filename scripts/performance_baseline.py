#!/usr/bin/env python3
"""
性能基准监控工具

记录关键操作的性能指标，与历史基线对比，自动检测性能退化。

用法:
    python3 scripts/performance_baseline.py --run
    python3 scripts/performance_baseline.py --compare
    python3 scripts/performance_baseline.py --report
"""
import argparse
import json
import sys
import time
from pathlib import Path


BASELINE_FILE = Path(__file__).parent.parent / ".performance-baseline.json"


def measure_performance() -> dict:
    """测量关键操作的性能"""
    results = {}

    # 1. validate_plugin 性能
    start = time.perf_counter()
    # 简单的空操作测量
    for _ in range(1000):
        pass
    results["baseline_overhead_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # 2. JSON 解析性能
    test_obj = {"name": "test", "version": "1.0.0", "tools": [{"name": "tool1"}]}
    test_json = json.dumps([test_obj] * 100)
    start = time.perf_counter()
    for _ in range(100):
        json.loads(test_json)
    results["json_parse_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # 3. 文件读取性能
    import os
    skill_root = Path(__file__).parent.parent
    start = time.perf_counter()
    files = list(skill_root.rglob("*.py"))[:50]
    for f in files:
        try:
            f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    results["file_read_50_files_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # 4. 正则匹配性能
    import re
    pattern = re.compile(r"def test_\w+")
    test_text = "def test_example():\n    pass\n" * 1000
    start = time.perf_counter()
    for _ in range(50):
        pattern.findall(test_text)
    results["regex_match_ms"] = round((time.perf_counter() - start) * 1000, 2)

    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    results["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    return results


def load_baseline() -> dict | None:
    """加载历史基线"""
    if not BASELINE_FILE.exists():
        return None
    try:
        return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_baseline(results: dict):
    """保存为新基线"""
    BASELINE_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


def compare_with_baseline(current: dict, baseline: dict) -> dict:
    """与基线对比"""
    comparison = {}
    metrics = ["baseline_overhead_ms", "json_parse_ms", "file_read_50_files_ms", "regex_match_ms"]

    for metric in metrics:
        if metric in current and metric in baseline:
            cur = current[metric]
            base = baseline[metric]
            if base > 0:
                change_pct = round((cur - base) / base * 100, 1)
            else:
                change_pct = 0
            comparison[metric] = {
                "current": cur,
                "baseline": base,
                "change_percent": change_pct,
                "status": "degraded" if change_pct > 20 else ("improved" if change_pct < -20 else "stable"),
            }

    return comparison


def main():
    parser = argparse.ArgumentParser(description="性能基准监控工具")
    parser.add_argument("--run", action="store_true", help="运行性能测试")
    parser.add_argument("--compare", action="store_true", help="与基线对比")
    parser.add_argument("--save-baseline", action="store_true", help="保存为新基线")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    # 默认运行
    if not any([args.run, args.compare, args.save_baseline, args.report]):
        args.run = True

    results = {}

    if args.run or args.compare or args.save_baseline:
        current = measure_performance()
        results["current"] = current

    if args.compare:
        baseline = load_baseline()
        if baseline:
            results["comparison"] = compare_with_baseline(current, baseline)
            results["baseline_timestamp"] = baseline.get("timestamp")
        else:
            results["comparison"] = {"note": "无历史基线，请先 --run --save-baseline"}

    if args.save_baseline:
        save_baseline(current)
        results["saved"] = True

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("性能基准监控报告")
        print("=" * 60)

        if "current" in results:
            cur = results["current"]
            print(f"\n📊 当前测量 ({cur['timestamp']})")
            print(f"   Python: {cur['python_version']}")
            print(f"   JSON 解析: {cur['json_parse_ms']}ms (100次)")
            print(f"   文件读取: {cur['file_read_50_files_ms']}ms (50文件)")
            print(f"   正则匹配: {cur['regex_match_ms']}ms (50次)")

        if "comparison" in results and isinstance(results["comparison"], dict):
            comp = results["comparison"]
            if "note" in comp:
                print(f"\n⚠️  {comp['note']}")
            else:
                print(f"\n📈 与基线对比 ({results.get('baseline_timestamp', '')})")
                degraded_count = 0
                for metric, data in comp.items():
                    if isinstance(data, dict):
                        icon = {"degraded": "🔴", "improved": "🟢", "stable": "🟡"}.get(data["status"], "⚪")
                        print(f"   {icon} {metric}: {data['change_percent']:+.1f}% "
                              f"(当前 {data['current']}ms / 基线 {data['baseline']}ms)")
                        if data["status"] == "degraded":
                            degraded_count += 1
                if degraded_count > 0:
                    print(f"\n⚠️  发现 {degraded_count} 项性能退化超过 20%")

        if results.get("saved"):
            print(f"\n✅ 已保存新基线: {BASELINE_FILE}")

        print("=" * 60)


if __name__ == "__main__":
    main()
