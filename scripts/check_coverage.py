#!/usr/bin/env python3
"""
代码覆盖率检查工具

运行 pytest 覆盖率测试，生成报告，检查最低覆盖率门禁。

用法:
    python3 scripts/check_coverage.py
    python3 scripts/check_coverage.py --min-coverage 70
    python3 scripts/check_coverage.py --json
    python3 scripts/check_coverage.py --output coverage-report.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="代码覆盖率检查工具")
    parser.add_argument("--min-coverage", type=float, default=60.0, help="最低覆盖率百分比（默认60%%）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--output", help="输出覆盖率报告到文件")
    parser.add_argument("--skip-tests", action="store_true", help="跳过测试，只分析已有 coverage.xml")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]

    if not args.skip_tests:
        # 运行 pytest 覆盖率测试
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--cov=scripts",
             "--cov-report=term-missing", "--cov-report=xml:coverage.xml",
             "--no-cov-on-fail"],
            capture_output=True, text=True, cwd=str(skill_root), timeout=120,
        )
        test_passed = result.returncode == 0
        test_output = result.stdout + result.stderr
    else:
        test_passed = True
        test_output = ""

    # 解析 coverage.xml
    coverage_file = skill_root / "coverage.xml"
    coverage_data = {"total": 0, "files": []}

    if coverage_file.exists():
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(coverage_file)
            root = tree.getroot()

            # 总覆盖率
            total_coverage = float(root.get("line-rate", 0)) * 100
            coverage_data["total"] = round(total_coverage, 1)

            # 每个文件的覆盖率
            for package in root.findall(".//package"):
                for cls in package.findall(".//class"):
                    filename = cls.get("filename", "")
                    line_rate = float(cls.get("line-rate", 0)) * 100
                    lines = cls.findall(".//line")
                    missed = sum(1 for l in lines if l.get("hits", "0") == "0")
                    total_lines = len(lines)
                    coverage_data["files"].append({
                        "file": filename,
                        "coverage": round(line_rate, 1),
                        "total_lines": total_lines,
                        "missed_lines": missed,
                    })
        except Exception as e:
            coverage_data["error"] = str(e)

    # 按覆盖率排序
    coverage_data["files"].sort(key=lambda x: x["coverage"])

    # 判断是否通过门禁
    passed = coverage_data["total"] >= args.min_coverage and test_passed

    report = {
        "test_passed": test_passed,
        "total_coverage": coverage_data["total"],
        "min_coverage": args.min_coverage,
        "passed": passed,
        "files_count": len(coverage_data["files"]),
        "files": coverage_data["files"],
        "low_coverage_files": [f for f in coverage_data["files"] if f["coverage"] < args.min_coverage],
    }

    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("代码覆盖率报告")
        print("=" * 60)
        print(f"\n测试: {'✅ 通过' if test_passed else '❌ 失败'}")
        print(f"总覆盖率: {coverage_data['total']}%")
        print(f"门禁要求: ≥{args.min_coverage}%")
        print(f"状态: {'✅ 通过' if passed else '❌ 未通过'}")
        print(f"文件数: {len(coverage_data['files'])}")

        if coverage_data["files"]:
            print(f"\n低覆盖率文件 (<{args.min_coverage}%):")
            for f in report["low_coverage_files"][:10]:
                print(f"  {f['coverage']:5.1f}%  {f['file']} (缺失 {f['missed_lines']}/{f['total_lines']} 行)")

            print(f"\n覆盖率最高的 5 个文件:")
            for f in coverage_data["files"][-5:]:
                print(f"  {f['coverage']:5.1f}%  {f['file']}")

        print("\n" + "=" * 60)
        if not passed:
            print(f"❌ 覆盖率不足 {args.min_coverage}%，请补充测试")
        else:
            print("✅ 覆盖率达标")
        print("=" * 60)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
