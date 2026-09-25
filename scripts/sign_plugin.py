#!/usr/bin/env python3
"""
插件包数字签名工具

使用 HMAC-SHA256 对插件包进行签名和验证，确保完整性和来源可信。

用法:
    python3 scripts/sign_plugin.py <插件目录> --sign --key your-secret-key
    python3 scripts/sign_plugin.py <插件目录> --verify --key your-secret-key
    python3 scripts/sign_plugin.py <插件目录> --sign --key-env PLUGIN_SIGNING_KEY
    python3 scripts/sign_plugin.py <插件目录> --json
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def calculate_manifest(plugin_dir: Path) -> dict:
    """计算插件文件清单（所有文件的哈希）"""
    manifest = {
        "plugin": plugin_dir.name,
        "generated_at": datetime.now().isoformat(),
        "files": {},
        "total_files": 0,
        "total_size": 0,
    }

    for f in sorted(plugin_dir.rglob("*")):
        if f.is_file() and "__pycache__" not in str(f) and ".git" not in str(f):
            if f.name in ("signature.json", "manifest.json"):
                continue
            rel_path = str(f.relative_to(plugin_dir))
            file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
            file_size = f.stat().st_size
            manifest["files"][rel_path] = {
                "sha256": file_hash,
                "size": file_size,
            }
            manifest["total_files"] += 1
            manifest["total_size"] += file_size

    return manifest


def sign_manifest(manifest: dict, key: str) -> dict:
    """对清单进行 HMAC-SHA256 签名"""
    manifest_json = json.dumps(manifest, sort_keys=True, ensure_ascii=False)
    signature = hmac.new(
        key.encode("utf-8"),
        manifest_json.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "algorithm": "HMAC-SHA256",
        "signature": signature,
        "signed_at": datetime.now().isoformat(),
        "key_hash": hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
    }


def verify_signature(plugin_dir: Path, key: str) -> dict:
    """验证插件签名"""
    sig_file = plugin_dir / "signature.json"
    if not sig_file.exists():
        return {"valid": False, "error": "signature.json 不存在"}

    try:
        sig_data = json.loads(sig_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"valid": False, "error": "signature.json 不是有效 JSON"}

    stored_manifest = sig_data.get("manifest", {})
    stored_signature = sig_data.get("signature", {})

    # 重新计算清单
    current_manifest = calculate_manifest(plugin_dir)

    # 比较文件清单
    mismatches = []
    for path, info in current_manifest["files"].items():
        if path not in stored_manifest["files"]:
            mismatches.append({"type": "added", "file": path})
        elif stored_manifest["files"][path]["sha256"] != info["sha256"]:
            mismatches.append({"type": "modified", "file": path})

    for path in stored_manifest["files"]:
        if path not in current_manifest["files"]:
            mismatches.append({"type": "removed", "file": path})

    # 验证签名
    manifest_json = json.dumps(stored_manifest, sort_keys=True, ensure_ascii=False)
    expected_signature = hmac.new(
        key.encode("utf-8"),
        manifest_json.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    signature_valid = expected_signature == stored_signature.get("signature", "")
    manifest_valid = len(mismatches) == 0

    return {
        "valid": signature_valid and manifest_valid,
        "signature_valid": signature_valid,
        "manifest_valid": manifest_valid,
        "mismatches": mismatches,
        "signed_at": stored_signature.get("signed_at", "unknown"),
        "total_files": current_manifest["total_files"],
    }


def main():
    parser = argparse.ArgumentParser(description="插件包数字签名工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--sign", action="store_true", help="签名插件")
    parser.add_argument("--verify", action="store_true", help="验证插件签名")
    parser.add_argument("--key", help="签名密钥")
    parser.add_argument("--key-env", help="从环境变量读取签名密钥")
    parser.add_argument("--output", help="签名文件输出路径（默认 signature.json）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    if not args.sign and not args.verify:
        print("错误: 必须指定 --sign 或 --verify", file=sys.stderr)
        sys.exit(1)

    # 获取密钥
    key = args.key
    if args.key_env:
        key = os.environ.get(args.key_env, "")
    if not key:
        print("错误: 必须提供 --key 或 --key-env", file=sys.stderr)
        sys.exit(1)

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    if args.sign:
        manifest = calculate_manifest(plugin_dir)
        signature = sign_manifest(manifest, key)

        sig_data = {
            "manifest": manifest,
            "signature": signature,
        }

        output_path = Path(args.output).resolve() if args.output else plugin_dir / "signature.json"
        output_path.write_text(json.dumps(sig_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        result = {
            "action": "sign",
            "plugin": plugin_dir.name,
            "total_files": manifest["total_files"],
            "total_size": manifest["total_size"],
            "signature": signature["signature"],
            "output": str(output_path),
        }

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("=" * 50)
            print("插件签名完成")
            print("=" * 50)
            print(f"插件: {plugin_dir.name}")
            print(f"文件数: {manifest['total_files']}")
            print(f"总大小: {manifest['total_size']} bytes")
            print(f"签名: {signature['signature'][:32]}...")
            print(f"已保存: {output_path}")
            print("=" * 50)

    elif args.verify:
        result = verify_signature(plugin_dir, key)
        result["action"] = "verify"
        result["plugin"] = plugin_dir.name

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("=" * 50)
            print("插件签名验证")
            print("=" * 50)
            print(f"插件: {plugin_dir.name}")
            print(f"签名时间: {result.get('signed_at', 'unknown')}")
            print(f"文件数: {result.get('total_files', 0)}")
            print()
            print(f"签名验证: {'✅ 通过' if result.get('signature_valid') else '❌ 失败'}")
            print(f"清单验证: {'✅ 通过' if result.get('manifest_valid') else '❌ 失败'}")

            if result.get("mismatches"):
                print(f"\n文件差异 ({len(result['mismatches'])} 个):")
                for m in result["mismatches"][:10]:
                    icon = {"added": "➕", "removed": "➖", "modified": "✏️"}.get(m["type"], "❓")
                    print(f"  {icon} [{m['type']}] {m['file']}")

            print()
            if result["valid"]:
                print("✅ 插件完整性验证通过")
            else:
                print("❌ 插件完整性验证失败，文件可能被篡改")
            print("=" * 50)

        sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
