#!/usr/bin/env python3
"""
版本迁移工具

支持 Agent Plugins 规范版本的自动迁移（1.0.0 → 1.1.0）。

用法:
    python3 scripts/migrate_version.py <插件目录> --from 1.0.0 --to 1.1.0
    python3 scripts/migrate_version.py <插件目录> --to 1.1.0
    python3 scripts/migrate_version.py <插件目录> --dry-run
    python3 scripts/migrate_version.py <插件目录> --json
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


SCHEMA_URLS = {
    "1.0.0": {
        "plugin": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "mcp": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
    },
    "1.1.0": {
        "plugin": "https://agent-plugins.org/schemas/1.1.0/plugin.schema.json",
        "mcp": "https://agent-plugins.org/schemas/1.1.0/mcp.schema.json",
    },
}

# 1.0 → 1.1 的变更说明
MIGRATION_NOTES = {
    "1.0.0->1.1.0": [
        "schema URL 版本号更新",
        "新增 extensions 字段支持（可选）",
        "mcpServers 配置结构优化",
        "新增 metadata 字段支持（可选）",
    ]
}


def detect_version(plugin_dir: Path) -> str:
    """检测插件当前规范版本"""
    plugin_json = plugin_dir / "plugin.json"
    if not plugin_json.exists():
        return "unknown"

    try:
        plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
        schema = plugin.get("$schema", "")
        for version in SCHEMA_URLS:
            if version in schema:
                return version
    except Exception:
        pass

    return "unknown"


def migrate_1_0_to_1_1(plugin_dir: Path, dry_run: bool = False) -> dict:
    """从 1.0.0 迁移到 1.1.0"""
    changes = []
    backup = {}

    # 1. 更新 plugin.json
    plugin_json = plugin_dir / "plugin.json"
    if plugin_json.exists():
        try:
            plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
            backup["plugin.json"] = plugin.copy()

            old_schema = plugin.get("$schema", "")
            new_schema = SCHEMA_URLS["1.1.0"]["plugin"]

            if old_schema != new_schema:
                plugin["$schema"] = new_schema
                changes.append({
                    "file": "plugin.json",
                    "field": "$schema",
                    "old": old_schema,
                    "new": new_schema,
                })

            # 1.1.0 新增 extensions 字段（如果不存在则添加空对象）
            if "extensions" not in plugin:
                plugin["extensions"] = {}
                changes.append({
                    "file": "plugin.json",
                    "field": "extensions",
                    "old": "(不存在)",
                    "new": "{}",
                })

            if not dry_run:
                plugin_json.write_text(
                    json.dumps(plugin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
        except Exception as e:
            changes.append({"file": "plugin.json", "error": str(e)})

    # 2. 更新 mcp.json
    mcp_json = plugin_dir / "mcp.json"
    if mcp_json.exists():
        try:
            mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
            backup["mcp.json"] = mcp.copy()

            old_schema = mcp.get("$schema", "")
            new_schema = SCHEMA_URLS["1.1.0"]["mcp"]

            if old_schema != new_schema:
                mcp["$schema"] = new_schema
                changes.append({
                    "file": "mcp.json",
                    "field": "$schema",
                    "old": old_schema,
                    "new": new_schema,
                })

            if not dry_run:
                mcp_json.write_text(
                    json.dumps(mcp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
        except Exception as e:
            changes.append({"file": "mcp.json", "error": str(e)})

    # 3. 创建迁移记录
    migration_record = {
        "migration": "1.0.0->1.1.0",
        "timestamp": datetime.now().isoformat(),
        "changes": changes,
        "notes": MIGRATION_NOTES["1.0.0->1.1.0"],
    }

    if not dry_run:
        (plugin_dir / "migration-log.json").write_text(
            json.dumps(migration_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return {
        "from": "1.0.0",
        "to": "1.1.0",
        "changes": changes,
        "change_count": len(changes),
        "dry_run": dry_run,
        "notes": MIGRATION_NOTES["1.0.0->1.1.0"],
    }


def main():
    parser = argparse.ArgumentParser(description="版本迁移工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--from", dest="from_version", help="源版本（默认自动检测）")
    parser.add_argument("--to", default="1.1.0", help="目标版本（默认 1.1.0）")
    parser.add_argument("--dry-run", action="store_true", help="只显示变更，不实际修改")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    # 检测当前版本
    current_version = args.from_version or detect_version(plugin_dir)
    if current_version == "unknown":
        print("错误: 无法检测插件版本，请使用 --from 指定", file=sys.stderr)
        sys.exit(1)

    if current_version == args.to:
        print(f"插件已经是 {args.to} 版本，无需迁移")
        sys.exit(0)

    # 执行迁移
    migration_key = f"{current_version}->{args.to}"

    if migration_key == "1.0.0->1.1.0":
        result = migrate_1_0_to_1_1(plugin_dir, dry_run=args.dry_run)
    else:
        print(f"错误: 不支持的迁移路径: {migration_key}", file=sys.stderr)
        print("支持的迁移: 1.0.0->1.1.0", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print(f"版本迁移: {result['from']} → {result['to']}")
        print("=" * 50)
        print(f"模式: {'预览（不修改）' if result['dry_run'] else '实际迁移'}")
        print(f"变更数: {result['change_count']}")
        print()

        if result["changes"]:
            print("变更详情:")
            for c in result["changes"]:
                if "error" in c:
                    print(f"  ❌ {c['file']}: {c['error']}")
                else:
                    print(f"  ✅ {c['file']}.{c['field']}")
                    print(f"     旧: {c['old']}")
                    print(f"     新: {c['new']}")
        else:
            print("无需变更")

        print()
        print("迁移说明:")
        for note in result["notes"]:
            print(f"  - {note}")

        print()
        if result["dry_run"]:
            print("⚠️  Dry-run 模式，未实际修改文件")
        else:
            print("✅ 迁移完成，迁移记录已保存到 migration-log.json")
        print("=" * 50)

    sys.exit(0)


if __name__ == "__main__":
    main()
