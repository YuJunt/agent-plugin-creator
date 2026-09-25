#!/usr/bin/env python3
"""
MCP 市场集成元数据工具

生成符合 MCP 市场规范的插件元数据，支持一键提交到 MCP 市场。

用法:
    python3 scripts/mcp_marketplace.py <插件目录> --generate
    python3 scripts/mcp_marketplace.py <插件目录> --validate
    python3 scripts/mcp_marketplace.py <插件目录> --json
"""
import argparse
import json
import sys
from pathlib import Path


def generate_marketplace_metadata(plugin_dir: Path, plugin: dict, mcp: dict) -> dict:
    """生成 MCP 市场元数据"""
    servers = []
    for name, config in mcp.get("mcpServers", {}).items():
        server = {
            "id": name,
            "name": name,
            "description": f"MCP server: {name}",
            "type": config.get("type", "stdio"),
        }
        if config.get("type") == "stdio":
            server["command"] = config.get("command", "")
            server["args"] = config.get("args", [])
        else:
            server["url"] = config.get("url", "")
        servers.append(server)

    skills = []
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append({
                    "id": skill_dir.name,
                    "name": skill_dir.name,
                    "path": f"skills/{skill_dir.name}",
                })

    return {
        "schemaVersion": "1.0.0",
        "id": plugin.get("name", "unknown"),
        "name": plugin.get("name", "unknown"),
        "version": plugin.get("version", "0.1.0"),
        "description": plugin.get("description", ""),
        "author": plugin.get("author", {}).get("name", ""),
        "license": plugin.get("license", "MIT"),
        "keywords": plugin.get("keywords", []),
        "homepage": plugin.get("homepage", ""),
        "repository": plugin.get("repository", ""),
        "mcpServers": servers,
        "skills": skills,
        "categories": _infer_categories(plugin),
        "tags": _generate_tags(plugin, servers),
        "rating": "general",
        "verified": False,
    }


def _infer_categories(plugin: dict) -> list:
    """推断插件分类"""
    name = plugin.get("name", "").lower()
    desc = plugin.get("description", "").lower()

    categories = []
    if any(k in name + desc for k in ["code", "review", "debug", "dev"]):
        categories.append("developer-tools")
    if any(k in name + desc for k in ["data", "analysis", "chart", "analytics"]):
        categories.append("data-analysis")
    if any(k in name + desc for k in ["customer", "support", "ticket", "service"]):
        categories.append("customer-support")
    if any(k in name + desc for k in ["knowledge", "doc", "search", "rag"]):
        categories.append("knowledge-management")
    if any(k in name + desc for k in ["security", "audit", "scan"]):
        categories.append("security")
    if not categories:
        categories.append("general")

    return categories[:3]  # 最多 3 个分类


def _generate_tags(plugin: dict, servers: list) -> list:
    """生成标签"""
    tags = ["mcp", "agent-plugin"]
    for server in servers:
        tags.append(server["type"])
    if plugin.get("keywords"):
        tags.extend(plugin["keywords"][:5])
    return list(set(tags))[:10]


def validate_marketplace_metadata(metadata: dict) -> dict:
    """验证市场元数据"""
    errors = []
    warnings = []

    required_fields = ["id", "name", "version", "description", "mcpServers"]
    for field in required_fields:
        if field not in metadata or not metadata[field]:
            errors.append(f"缺少必需字段: {field}")

    if "version" in metadata:
        import re
        if not re.match(r"^\d+\.\d+\.\d+$", metadata["version"]):
            errors.append("版本号格式不正确，应为 x.y.z")

    if "mcpServers" in metadata:
        for server in metadata["mcpServers"]:
            if "id" not in server:
                errors.append(f"MCP 服务器缺少 id: {server}")
            if server.get("type") not in ("stdio", "streamable-http", "sse"):
                warnings.append(f"MCP 服务器类型不常见: {server.get('type')}")

    if len(metadata.get("description", "")) > 500:
        warnings.append("描述超过 500 字符，建议精简")

    if len(metadata.get("keywords", [])) > 10:
        warnings.append("关键词超过 10 个，建议精简")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="MCP 市场集成元数据工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--generate", action="store_true", help="生成市场元数据")
    parser.add_argument("--validate", action="store_true", help="验证市场元数据")
    parser.add_argument("--output", help="输出文件路径（默认 marketplace.json）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--force", action="store_true", help="覆盖已有文件")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    # 加载 plugin.json
    plugin_json = plugin_dir / "plugin.json"
    if not plugin_json.exists():
        print("错误: 缺少 plugin.json", file=sys.stderr)
        sys.exit(1)
    plugin = json.loads(plugin_json.read_text(encoding="utf-8"))

    # 加载 mcp.json
    mcp = {}
    mcp_json = plugin_dir / "mcp.json"
    if mcp_json.exists():
        mcp = json.loads(mcp_json.read_text(encoding="utf-8"))

    if args.validate:
        # 验证已有元数据
        meta_path = plugin_dir / "marketplace.json"
        if not meta_path.exists():
            print("错误: 缺少 marketplace.json，请先运行 --generate", file=sys.stderr)
            sys.exit(1)
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        result = validate_marketplace_metadata(metadata)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"验证结果: {'✅ 有效' if result['valid'] else '❌ 无效'}")
            if result["errors"]:
                print("错误:")
                for e in result["errors"]:
                    print(f"  ❌ {e}")
            if result["warnings"]:
                print("警告:")
                for w in result["warnings"]:
                    print(f"  ⚠️  {w}")
        sys.exit(0 if result["valid"] else 1)

    # 生成元数据
    metadata = generate_marketplace_metadata(plugin_dir, plugin, mcp)

    # 验证
    validation = validate_marketplace_metadata(metadata)

    # 保存
    output_path = Path(args.output).resolve() if args.output else plugin_dir / "marketplace.json"
    if not output_path.exists() or args.force:
        output_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps({"metadata": metadata, "validation": validation}, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("MCP 市场元数据生成完成")
        print("=" * 50)
        print(f"插件: {metadata['name']} v{metadata['version']}")
        print(f"分类: {', '.join(metadata['categories'])}")
        print(f"MCP 服务器: {len(metadata['mcpServers'])} 个")
        print(f"Skills: {len(metadata['skills'])} 个")
        print(f"标签: {', '.join(metadata['tags'])}")
        print()
        print(f"验证: {'✅ 有效' if validation['valid'] else '❌ 无效'}")
        if validation["warnings"]:
            print("警告:")
            for w in validation["warnings"]:
                print(f"  ⚠️  {w}")
        print()
        print(f"已保存: {output_path}")
        print()
        print("提交流程:")
        print("  1. 访问 https://mcp-marketplace.example.com/submit")
        print("  2. 上传 marketplace.json")
        print("  3. 等待审核")
        print("=" * 50)

    sys.exit(0 if validation["valid"] else 1)


if __name__ == "__main__":
    main()
