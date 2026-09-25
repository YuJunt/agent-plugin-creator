#!/usr/bin/env python3
"""
SBOM 软件物料清单生成工具

生成 CycloneDX 和 SPDX 格式的软件物料清单。

用法:
    python3 scripts/generate_sbom.py <插件目录> --format cyclonedx
    python3 scripts/generate_sbom.py <插件目录> --format spdx
    python3 scripts/generate_sbom.py <插件目录> --output sbom.json
    python3 scripts/generate_sbom.py <插件目录> --json
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def sha256_file(file_path: Path) -> str:
    """计算文件 SHA256"""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_components(plugin_dir: Path) -> list:
    """收集插件的所有组件"""
    components = []

    # 收集文件
    for f in plugin_dir.rglob("*"):
        if f.is_file() and "__pycache__" not in str(f) and ".git" not in str(f):
            rel_path = str(f.relative_to(plugin_dir))
            components.append({
                "type": "file",
                "name": rel_path,
                "version": "0.0.0",
                "path": rel_path,
                "hashes": {"SHA-256": sha256_file(f)},
                "size": f.stat().st_size,
            })

    # 收集 Python 依赖
    for req_file in plugin_dir.rglob("requirements.txt"):
        for line in req_file.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                match = re.match(r"^([a-zA-Z0-9_-]+)\s*([<>=!~]+)?\s*([0-9.]+)?", line)
                if match:
                    components.append({
                        "type": "library",
                        "name": match.group(1),
                        "version": match.group(3) or "unknown",
                        "purl": f"pkg:pypi/{match.group(1)}@{match.group(3) or 'unknown'}",
                        "ecosystem": "pypi",
                    })

    # 收集 npm 依赖
    for pkg_file in plugin_dir.rglob("package.json"):
        if "node_modules" in str(pkg_file):
            continue
        try:
            pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
            for dep_type in ["dependencies", "devDependencies"]:
                for name, version in pkg.get(dep_type, {}).items():
                    components.append({
                        "type": "library",
                        "name": name,
                        "version": version.replace("^", "").replace("~", ""),
                        "purl": f"pkg:npm/{name}@{version.replace('^', '').replace('~', '')}",
                        "ecosystem": "npm",
                    })
        except Exception:
            pass

    return components


def generate_cyclonedx(plugin_dir: Path, plugin: dict, components: list) -> dict:
    """生成 CycloneDX 格式 SBOM"""
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{plugin.get('name', 'plugin')}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "tools": [{"vendor": "agent-plugin-creator", "name": "generate_sbom", "version": "1.0.0"}],
            "component": {
                "type": "application",
                "name": plugin.get("name", "unknown"),
                "version": plugin.get("version", "0.1.0"),
                "description": plugin.get("description", ""),
            },
        },
        "components": [
            {
                "type": c.get("type", "library"),
                "name": c["name"],
                "version": c.get("version", "0.0.0"),
                "purl": c.get("purl", ""),
                "hashes": [{"alg": "SHA-256", "content": c["hashes"]["SHA-256"]}] if "hashes" in c else [],
            }
            for c in components if c["type"] == "library"
        ],
        "dependencies": [
            {"ref": f"pkg:pypi/{c['name']}@{c.get('version', 'unknown')}", "dependsOn": []}
            for c in components if c["type"] == "library" and c.get("ecosystem") == "pypi"
        ],
    }


def generate_spdx(plugin_dir: Path, plugin: dict, components: list) -> dict:
    """生成 SPDX 格式 SBOM"""
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{plugin.get('name', 'plugin')}-sbom",
        "documentNamespace": f"https://example.com/{plugin.get('name', 'plugin')}/sbom",
        "creationInfo": {
            "created": datetime.now().isoformat(),
            "creators": ["Tool: agent-plugin-creator-generate_sbom-1.0.0"],
        },
        "packages": [
            {
                "SPDXID": f"SPDXRef-Package-{i}",
                "name": c["name"],
                "versionInfo": c.get("version", "0.0.0"),
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "checksums": [{"algorithm": "SHA256", "checksumValue": c["hashes"]["SHA-256"]}] if "hashes" in c else [],
                "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl", "referenceLocator": c.get("purl", "")}] if c.get("purl") else [],
            }
            for i, c in enumerate(components) if c["type"] == "library"
        ],
        "relationships": [
            {"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": "SPDXRef-Package-0"}
        ] if components else [],
    }


def main():
    parser = argparse.ArgumentParser(description="SBOM 软件物料清单生成工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--format", choices=["cyclonedx", "spdx", "both"], default="cyclonedx", help="SBOM 格式")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    plugin_json = plugin_dir / "plugin.json"
    plugin = {}
    if plugin_json.exists():
        try:
            plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    components = collect_components(plugin_dir)
    libraries = [c for c in components if c["type"] == "library"]
    files = [c for c in components if c["type"] == "file"]

    results = {}

    if args.format in ("cyclonedx", "both"):
        cyclonedx = generate_cyclonedx(plugin_dir, plugin, components)
        results["cyclonedx"] = cyclonedx
        if args.output:
            out_path = Path(args.output)
            if args.format == "both":
                out_path = out_path.with_suffix(".cyclonedx.json")
            out_path.write_text(json.dumps(cyclonedx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.format in ("spdx", "both"):
        spdx = generate_spdx(plugin_dir, plugin, components)
        results["spdx"] = spdx
        if args.output:
            out_path = Path(args.output)
            if args.format == "both":
                out_path = out_path.with_suffix(".spdx.json")
            out_path.write_text(json.dumps(spdx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("SBOM 生成完成")
        print("=" * 60)
        print(f"插件: {plugin.get('name', 'unknown')} v{plugin.get('version', '?')}")
        print(f"格式: {args.format}")
        print(f"组件总数: {len(components)}")
        print(f"  依赖库: {len(libraries)}")
        print(f"  文件: {len(files)}")
        print()

        if libraries:
            print("依赖列表:")
            for lib in libraries[:20]:
                eco = lib.get("ecosystem", "unknown")
                print(f"  [{eco}] {lib['name']}@{lib.get('version', '?')}")
            if len(libraries) > 20:
                print(f"  ... 还有 {len(libraries) - 20} 个")

        if args.output:
            print(f"\n已保存: {args.output}")
        print("=" * 60)

    sys.exit(0)


if __name__ == "__main__":
    main()
