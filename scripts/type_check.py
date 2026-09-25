#!/usr/bin/env python3
"""
类型注解检查工具

检查脚本的类型注解覆盖率，生成类型质量报告。

用法:
    python3 scripts/type_check.py
    python3 scripts/type_check.py --target scripts/validate_plugin.py
    python3 scripts/type_check.py --min-coverage 80
    python3 scripts/type_check.py --json
"""
import argparse
import ast
import json
import sys
from pathlib import Path


def analyze_file(file_path: Path) -> dict:
    """分析单个文件的类型注解覆盖率"""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return {"file": str(file_path), "error": "parse failed"}

    total_funcs = 0
    typed_funcs = 0
    total_args = 0
    typed_args = 0
    has_return_annotation = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total_funcs += 1

            # 检查返回类型注解
            if node.returns:
                has_return_annotation += 1

            # 检查参数注解
            all_args = node.args.args + node.args.kwonlyargs
            func_typed = True
            for arg in all_args:
                if arg.arg in ("self", "cls"):
                    continue
                total_args += 1
                if arg.annotation:
                    typed_args += 1
                else:
                    func_typed = False

            # 如果有参数且所有参数都有注解，且有返回类型，则算完全注解
            if all_args and func_typed and node.returns:
                typed_funcs += 1
            elif not all_args and node.returns:
                typed_funcs += 1

    func_coverage = (typed_funcs / total_funcs * 100) if total_funcs > 0 else 100
    arg_coverage = (typed_args / total_args * 100) if total_args > 0 else 100

    return {
        "file": str(file_path),
        "total_functions": total_funcs,
        "typed_functions": typed_funcs,
        "function_coverage": round(func_coverage, 1),
        "total_args": total_args,
        "typed_args": typed_args,
        "arg_coverage": round(arg_coverage, 1),
        "has_return_annotations": has_return_annotation,
    }


def main():
    parser = argparse.ArgumentParser(description="类型注解检查工具")
    parser.add_argument("--target", help="指定检查的文件或目录（默认 scripts/）")
    parser.add_argument("--min-coverage", type=float, default=50.0, help="最低覆盖率要求")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    target = Path(args.target).resolve() if args.target else skill_root / "scripts"

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.glob("*.py"))
    else:
        print(f"错误: 目标不存在: {target}", file=sys.stderr)
        sys.exit(1)

    results = []
    for f in files:
        if f.name == "__init__.py":
            continue
        result = analyze_file(f)
        results.append(result)

    # 汇总
    total_funcs = sum(r.get("total_functions", 0) for r in results)
    typed_funcs = sum(r.get("typed_functions", 0) for r in results)
    total_args = sum(r.get("total_args", 0) for r in results)
    typed_args = sum(r.get("typed_args", 0) for r in results)

    overall_func_coverage = (typed_funcs / total_funcs * 100) if total_funcs > 0 else 100
    overall_arg_coverage = (typed_args / total_args * 100) if total_args > 0 else 100
    overall = (overall_func_coverage + overall_arg_coverage) / 2

    passed = overall >= args.min_coverage

    report = {
        "target": str(target),
        "files_checked": len(results),
        "total_functions": total_funcs,
        "typed_functions": typed_funcs,
        "function_coverage": round(overall_func_coverage, 1),
        "total_args": total_args,
        "typed_args": typed_args,
        "arg_coverage": round(overall_arg_coverage, 1),
        "overall_coverage": round(overall, 1),
        "min_coverage": args.min_coverage,
        "passed": passed,
        "files": results,
        "low_coverage_files": [r for r in results if r.get("function_coverage", 100) < args.min_coverage],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("类型注解覆盖率报告")
        print("=" * 60)
        print(f"目标: {target}")
        print(f"文件数: {len(results)}")
        print(f"函数总数: {total_funcs}")
        print(f"已注解函数: {typed_funcs}")
        print(f"函数覆盖率: {overall_func_coverage:.1f}%")
        print(f"参数总数: {total_args}")
        print(f"已注解参数: {typed_args}")
        print(f"参数覆盖率: {overall_arg_coverage:.1f}%")
        print(f"综合覆盖率: {overall:.1f}%")
        print(f"最低要求: {args.min_coverage}%")
        print(f"状态: {'✅ 通过' if passed else '❌ 未通过'}")

        if report["low_coverage_files"]:
            print(f"\n低覆盖率文件 (<{args.min_coverage}%):")
            for f in report["low_coverage_files"][:10]:
                print(f"  {f['function_coverage']:5.1f}%  {Path(f['file']).name} "
                      f"({f['typed_functions']}/{f['total_functions']} 函数)")

        print("\n" + "=" * 60)
        if not passed:
            print(f"❌ 覆盖率不足 {args.min_coverage}%，建议添加类型注解")
        else:
            print("✅ 类型注解覆盖率达标")
        print("=" * 60)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
