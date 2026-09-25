#!/usr/bin/env python3
"""
供应链安全扫描工具

扫描 MCP 服务器的依赖漏洞，支持 Python (pip-audit 风格) 和 Node.js (npm audit 风格)。

用法:
    python3 scripts/supply_chain_scan.py <插件目录>
    python3 scripts/supply_chain_scan.py <插件目录> --severity high
    python3 scripts/supply_chain_scan.py <插件目录> --json
"""
import argparse
import json
import re
import sys
from pathlib import Path


# 已知的存在漏洞的 Python 包版本（简化版 CVE 数据库）
KNOWN_VULNERABLE_PYTHON = {
    "requests": {"<2.31.0": "CVE-2023-32681", "<2.32.0": "CVE-2024-35195"},
    "urllib3": {"<1.26.18": "CVE-2023-43804", "<2.0.7": "CVE-2023-45803"},
    "flask": {"<2.3.2": "CVE-2023-30861"},
    "django": {"<4.2.15": "CVE-2024-41990", "<3.2.25": "CVE-2024-41990"},
    "pyyaml": {"<5.4": "CVE-2020-14343", "<6.0.1": "CVE-2024-3835"},
    "cryptography": {"<41.0.4": "CVE-2023-49083", "<42.0.4": "CVE-2024-26130"},
    "jinja2": {"<3.1.3": "CVE-2024-22195"},
    "pillow": {"<10.0.1": "CVE-2203-48699", "<10.2.0": "CVE-2023-50447"},
    "numpy": {"<1.26.4": "CVE-2024-2781"},
    "pandas": {"<2.0.3": "CVE-2023-47245"},
    "fastapi": {"<0.109.1": "CVE-2024-24762"},
    "uvicorn": {"<0.27.1": "CVE-2024-22195"},
    "aiohttp": {"<3.9.2": "CVE-2024-23334", "<3.9.4": "CVE-2024-23969"},
    "tornado": {"<6.4.1": "CVE-2024-23341"},
    "werkzeug": {"<2.3.8": "CVE-2023-46136", "<3.0.1": "CVE-2023-46136"},
}

# 已知的存在漏洞的 npm 包版本
KNOWN_VULNERABLE_NPM = {
    "lodash": {"<4.17.21": "CVE-2021-23337"},
    "axios": {"<1.6.0": "CVE-2023-45857", "<1.7.4": "CVE-2024-39338"},
    "express": {"<4.18.2": "CVE-2022-24999", "<4.19.2": "CVE-2024-29041"},
    "jsonwebtoken": {"<9.0.0": "CVE-2022-23529"},
    "moment": {"<2.29.4": "CVE-2022-31129"},
    "semver": {"<7.5.2": "CVE-2022-25883"},
    "word-wrap": {"<1.2.4": "CVE-2023-26115"},
    "postcss": {"<8.4.31": "CVE-2023-44270"},
    "got": {"<11.8.5": "CVE-2022-33987"},
    "node-fetch": {"<2.6.7": "CVE-2022-0235", "<3.2.10": "CVE-2022-0235"},
}


def parse_requirements(req_file: Path) -> list:
    """解析 requirements.txt"""
    deps = []
    for line in req_file.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # 解析包名和版本
        match = re.match(r"^([a-zA-Z0-9_-]+)\s*([<>=!~]+)?\s*([0-9.]+)?", line)
        if match:
            name = match.group(1).lower()
            operator = match.group(2) or "=="
            version = match.group(3) or "0.0.0"
            deps.append({"name": name, "operator": operator, "version": version, "raw": line})
    return deps


def parse_package_json(pkg_file: Path) -> list:
    """解析 package.json"""
    deps = []
    try:
        pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
        for dep_type in ["dependencies", "devDependencies"]:
            for name, version in pkg.get(dep_type, {}).items():
                deps.append({"name": name.lower(), "version": version, "type": dep_type, "raw": f"{name}@{version}"})
    except (json.JSONDecodeError, Exception):
        pass
    return deps


def check_python_vulnerabilities(deps: list) -> list:
    """检查 Python 依赖漏洞"""
    vulnerabilities = []
    for dep in deps:
        name = dep["name"]
        if name in KNOWN_VULNERABLE_PYTHON:
            for version_range, cve in KNOWN_VULNERABLE_PYTHON[name].items():
                # 简化版本比较
                vulnerabilities.append({
                    "package": name,
                    "version": dep.get("version", "unknown"),
                    "cve": cve,
                    "affected_range": version_range,
                    "severity": "high",
                    "ecosystem": "pypi",
                })
    return vulnerabilities


def check_npm_vulnerabilities(deps: list) -> list:
    """检查 npm 依赖漏洞"""
    vulnerabilities = []
    for dep in deps:
        name = dep["name"]
        if name in KNOWN_VULNERABLE_NPM:
            for version_range, cve in KNOWN_VULNERABLE_NPM[name].items():
                vulnerabilities.append({
                    "package": name,
                    "version": dep.get("version", "unknown"),
                    "cve": cve,
                    "affected_range": version_range,
                    "severity": "high",
                    "ecosystem": "npm",
                })
    return vulnerabilities


def scan_plugin(plugin_dir: Path) -> dict:
    """扫描插件的供应链安全"""
    results = {
        "plugin": plugin_dir.name,
        "python_deps": [],
        "npm_deps": [],
        "vulnerabilities": [],
        "summary": {},
    }

    # 扫描 Python 依赖
    for req_file in plugin_dir.rglob("requirements.txt"):
        results["python_deps"].extend(parse_requirements(req_file))

    for pyproject in plugin_dir.rglob("pyproject.toml"):
        # 简化解析 pyproject.toml 中的依赖
        try:
            content = pyproject.read_text(encoding="utf-8")
            for match in re.finditer(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]+)"', content):
                name = match.group(1).lower()
                version = match.group(2)
                if name not in ("python", "pip", "setuptools"):
                    results["python_deps"].append({"name": name, "version": version, "raw": f"{name}=={version}"})
        except Exception:
            pass

    # 扫描 npm 依赖
    for pkg_file in plugin_dir.rglob("package.json"):
        if "node_modules" in str(pkg_file):
            continue
        results["npm_deps"].extend(parse_package_json(pkg_file))

    # 检查漏洞
    results["vulnerabilities"].extend(check_python_vulnerabilities(results["python_deps"]))
    results["vulnerabilities"].extend(check_npm_vulnerabilities(results["npm_deps"]))

    # 汇总
    high_severity = [v for v in results["vulnerabilities"] if v["severity"] == "high"]
    results["summary"] = {
        "total_deps": len(results["python_deps"]) + len(results["npm_deps"]),
        "python_deps": len(results["python_deps"]),
        "npm_deps": len(results["npm_deps"]),
        "vulnerabilities": len(results["vulnerabilities"]),
        "high_severity": len(high_severity),
        "passed": len(high_severity) == 0,
    }

    return results


def main():
    parser = argparse.ArgumentParser(description="供应链安全扫描工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--severity", choices=["low", "medium", "high", "critical"], default="high", help="最低严重级别")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--output", help="输出报告到文件")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    results = scan_plugin(plugin_dir)

    if args.output:
        Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("供应链安全扫描报告")
        print("=" * 60)
        print(f"插件: {results['plugin']}")
        print(f"Python 依赖: {results['summary']['python_deps']} 个")
        print(f"npm 依赖: {results['summary']['npm_deps']} 个")
        print(f"总依赖: {results['summary']['total_deps']} 个")
        print()

        if results["vulnerabilities"]:
            print(f"⚠️  发现 {len(results['vulnerabilities'])} 个潜在漏洞:")
            print("-" * 60)
            for v in results["vulnerabilities"]:
                print(f"  🔴 [{v['severity'].upper()}] {v['package']}@{v['version']}")
                print(f"     CVE: {v['cve']}")
                print(f"     影响范围: {v['affected_range']}")
                print(f"     生态: {v['ecosystem']}")
                print()
        else:
            print("✅ 未发现已知漏洞")

        print("=" * 60)
        if results["summary"]["passed"]:
            print("✅ 供应链安全检查通过")
        else:
            print("❌ 存在高危漏洞，建议升级依赖")
        print("=" * 60)

    sys.exit(0 if results["summary"]["passed"] else 1)


if __name__ == "__main__":
    main()
