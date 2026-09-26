#!/usr/bin/env python3
"""
变异测试 + 属性测试框架

对核心验证函数进行变异测试（Mutation Testing），
验证测试用例的有效性（是否真的能抓到 bug）。

使用方法：
    python3 scripts/mutation_test.py
    python3 scripts/mutation_test.py --target validate_plugin
"""
import argparse
import json
import random
import subprocess
import sys
from pathlib import Path


# 变异算子列表
MUTATION_OPERATORS = [
    ("replace_equals", "==", "!="),
    ("replace_gt", ">", "<"),
    ("replace_ge", ">=", "<="),
    ("replace_and", "and", "or"),
    ("remove_not", "not ", ""),
]


def generate_mutations(source_file: Path, max_mutations: int = 20) -> list:
    """生成变异体"""
    content = source_file.read_text(encoding="utf-8")
    lines = content.split("\n")

    mutations = []
    for op_name, old, new in MUTATION_OPERATORS:
        for i, line in enumerate(lines):
            if old in line and not line.strip().startswith("#"):
                # 跳过注释和字符串中的替换
                if line.strip().startswith('"') or line.strip().startswith("'"):
                    continue
                mutations.append({
                    "operator": op_name,
                    "line": i + 1,
                    "old": old,
                    "new": new,
                    "original_line": line.strip(),
                })
                if len(mutations) >= max_mutations:
                    return mutations
    return mutations


def run_property_tests() -> dict:
    """属性测试：验证不变量"""
    sys.path.insert(0, str(Path(__file__).parent))

    results = {
        "property_tests": [],
        "passed": 0,
        "failed": 0,
    }

    # 属性 1: validate_plugin 对空目录应该失败
    try:
        from validate_plugin import validate_plugin
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_plugin(Path(tmpdir))
            results["property_tests"].append({
                "name": "空目录验证失败",
                "property": "validate_plugin(empty_dir) 必须返回错误",
                "passed": len(result.errors) > 0,
            })
            results["passed"] += 1 if len(result.errors) > 0 else 0
            results["failed"] += 0 if len(result.errors) > 0 else 1
    except Exception as e:
        results["property_tests"].append({
            "name": "空目录验证失败",
            "error": str(e),
            "passed": False,
        })
        results["failed"] += 1

    # 属性 2: validate_skill 对无效名称应该失败
    try:
        from validate_skill import _validate_name_official
        bad_names = ["", "UPPERCASE", "with space", "with.dot", "-startswith"]
        all_failed = True
        for name in bad_names:
            errors = _validate_name_official(name, None)
            if len(errors) == 0:
                all_failed = False
                break
        results["property_tests"].append({
            "name": "无效技能名称验证失败",
            "property": "_validate_name_official(bad_names) 必须返回错误",
            "passed": all_failed,
        })
        results["passed"] += 1 if all_failed else 0
        results["failed"] += 0 if all_failed else 1
    except Exception as e:
        results["property_tests"].append({
            "name": "无效技能名称验证失败",
            "error": str(e),
            "passed": False,
        })
        results["failed"] += 1

    # 属性 3: errors.format_error 对所有 ErrorCode 都应该输出
    try:
        from errors import ErrorCode, format_error
        all_format = True
        for code in ErrorCode:
            try:
                out = format_error(code, "test")
                if "E" not in out:
                    all_format = False
                    break
            except Exception:
                all_format = False
                break
        results["property_tests"].append({
            "name": "所有错误码可格式化",
            "property": "format_error(所有 ErrorCode) 不应该抛异常",
            "passed": all_format,
        })
        results["passed"] += 1 if all_format else 0
        results["failed"] += 0 if all_format else 1
    except Exception as e:
        results["property_tests"].append({
            "name": "所有错误码可格式化",
            "error": str(e),
            "passed": False,
        })
        results["failed"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="变异测试 + 属性测试")
    parser.add_argument("--target", help="目标脚本名称")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--mutations-only", action="store_true", help="只运行变异测试")
    parser.add_argument("--properties-only", action="store_true", help="只运行属性测试")
    args = parser.parse_args()

    results = {}

    if not args.properties_only:
        # 变异测试：分析代码中的可变异点
        scripts_dir = Path(__file__).parent
        target_script = args.target or "validate_plugin.py"
        target_path = scripts_dir / target_script

        if target_path.exists():
            mutations = generate_mutations(target_path, max_mutations=10)
            results["mutation_analysis"] = {
                "target": target_script,
                "total_mutations_found": len(mutations),
                "top_mutations": mutations[:5],
                "note": "变异测试需要完整的测试套件支持，这里只做静态分析",
            }

    if not args.mutations_only:
        # 属性测试
        results["property_tests"] = run_property_tests()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("变异测试 + 属性测试报告")
        print("=" * 60)

        if "mutation_analysis" in results:
            m = results["mutation_analysis"]
            print(f"\n🧬 变异分析: {m['target']}")
            print(f"   发现可变异点: {m['total_mutations_found']} 个")
            print(f"   说明: {m['note']}")

        if "property_tests" in results:
            p = results["property_tests"]
            print(f"\n🔍 属性测试:")
            for t in p["property_tests"]:
                icon = "✅" if t["passed"] else "❌"
                print(f"   {icon} {t['name']}")
                if not t["passed"] and "error" in t:
                    print(f"      错误: {t['error'][:80]}")

            print(f"\n   通过: {p['passed']} | 失败: {p['failed']}")

        print("=" * 60)

    sys.exit(0 if results.get("property_tests", {}).get("failed", 1) == 0 else 1)


if __name__ == "__main__":
    main()
