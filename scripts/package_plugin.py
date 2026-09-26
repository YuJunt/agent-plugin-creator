#!/usr/bin/env python3
"""
Agent Plugin 打包发布工具

将符合 Agent Plugins 1.0 标准的插件打包为可分发的格式，生成：
  1. zip 压缩包（可直接分发）
  2. marketplace.json（各平台市场配置）
  3. MANIFEST.json（发布清单，含文件哈希和元数据）
  4. 发布说明（RELEASE_NOTES.md 模板）

用法:
    python3 package_plugin.py <插件目录> --output dist
    python3 package_plugin.py ./my-plugin --output dist --version 1.0.0
    python3 package_plugin.py ./my-plugin --output dist --platforms claude,copilot
    python3 package_plugin.py ./my-plugin --output dist --skip-validation
"""
import argparse
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from _common import load_plugin_json



def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """计算文件哈希"""
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def collect_plugin_files(plugin_dir: Path) -> list:
    """收集插件中的所有文件（排除缓存、临时文件等）"""
    exclude_dirs = {"__pycache__", ".git", "node_modules", ".DS_Store", "dist", "build", "tests", "htmlcov", ".pytest_cache", ".github", "docs"}
    exclude_extensions = {".pyc", ".pyo", ".swp", ".swo", "~"}

    files = []
    for root, dirs, filenames in os.walk(plugin_dir):
        # 排除目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for filename in filenames:
            file_path = Path(root) / filename
            if file_path.suffix in exclude_extensions:
                continue
            rel_path = file_path.relative_to(plugin_dir)
            files.append({
                "path": str(rel_path),
                "absolute_path": str(file_path),
                "size": file_path.stat().st_size,
            })
    return files


def generate_manifest(plugin: dict, files: list, version: str) -> dict:
    """生成发布清单 MANIFEST.json"""
    manifest = {
        "manifest_version": "1.0",
        "plugin": {
            "name": plugin.get("name", ""),
            "version": version,
            "description": plugin.get("description", ""),
            "author": plugin.get("author", {}),
            "license": plugin.get("license", "MIT"),
            "keywords": plugin.get("keywords", []),
        },
        "packaged_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
        "total_size": 0,
        "file_count": len(files),
    }

    total_size = 0
    for f in files:
        file_hash = calculate_file_hash(Path(f["absolute_path"]))
        manifest["files"].append({
            "path": f["path"],
            "size": f["size"],
            "sha256": file_hash,
        })
        total_size += f["size"]

    manifest["total_size"] = total_size
    return manifest


def generate_marketplace_config(plugin: dict, version: str, platforms: list) -> dict:
    """生成各平台 marketplace 配置"""
    config = {
        "name": plugin.get("name", ""),
        "version": version,
        "description": plugin.get("description", ""),
        "author": plugin.get("author", {}).get("name", ""),
        "license": plugin.get("license", "MIT"),
        "platforms": {},
    }

    # Claude Code marketplace
    if "claude" in platforms:
        config["platforms"]["claude"] = {
            "marketplace": {
                "name": plugin.get("name", ""),
                "description": plugin.get("description", ""),
                "plugins": [
                    {
                        "name": plugin.get("name", ""),
                        "path": ".",
                        "description": plugin.get("description", ""),
                        "version": version,
                    }
                ],
            },
            "install_command": f"/plugin install {plugin.get('name', '')}",
        }

    # GitHub Copilot / VS Code marketplace
    if "copilot" in platforms:
        config["platforms"]["copilot"] = {
            "extension": {
                "name": plugin.get("name", ""),
                "displayName": plugin.get("name", "").replace("-", " ").title(),
                "description": plugin.get("description", ""),
                "version": version,
                "publisher": plugin.get("author", {}).get("name", "unknown"),
                "license": plugin.get("license", "MIT"),
                "engines": {"vscode": "^1.80.0"},
                "categories": ["AI", "Other"],
            },
            "install_method": "VS Code extension marketplace",
        }

    # OpenAI Codex marketplace
    if "codex" in platforms:
        config["platforms"]["codex"] = {
            "plugin": {
                "name": plugin.get("name", ""),
                "version": version,
                "description": plugin.get("description", ""),
            },
            "install_command": f"codex plugin install {plugin.get('name', '')}",
        }

    # Cursor marketplace
    if "cursor" in platforms:
        config["platforms"]["cursor"] = {
            "rules": {
                "name": plugin.get("name", ""),
                "version": version,
                "description": plugin.get("description", ""),
            },
            "install_method": "Copy .cursor/rules/ to project",
        }

    # Google Gemini
    if "gemini" in platforms:
        config["platforms"]["gemini"] = {
            "extension": {
                "name": plugin.get("name", ""),
                "version": version,
                "description": plugin.get("description", ""),
            },
            "install_method": "Gemini extension manager",
        }

    return config


def create_zip_package(plugin_dir: Path, zip_path: Path, files: list):
    """创建 zip 压缩包"""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f["absolute_path"], arcname=f["path"])
    return zip_path.stat().st_size


def generate_release_notes(plugin: dict, version: str) -> str:
    """生成发布说明模板"""
    name = plugin.get("name", "my-plugin")
    lines = []
    lines.append(f"# {name} v{version}")
    lines.append("")
    lines.append(f"> {plugin.get('description', '')}")
    lines.append("")
    lines.append("## 发布说明")
    lines.append("")
    lines.append("### 新增功能")
    lines.append("- 初始版本发布")
    lines.append("")
    lines.append("### 修复问题")
    lines.append("- 无")
    lines.append("")
    lines.append("### 已知限制")
    lines.append("- 无")
    lines.append("")
    lines.append("## 安装")
    lines.append("")
    lines.append("### Claude Code")
    lines.append("```bash")
    lines.append(f"/plugin install {name}")
    lines.append("```")
    lines.append("")
    lines.append("### 手动安装")
    lines.append(f"1. 下载 `{name}-v{version}.zip`")
    lines.append("2. 解压到插件目录")
    lines.append("3. 在客户端中启用插件")
    lines.append("")
    lines.append("## 兼容性")
    lines.append("")
    lines.append("- ✅ Claude Code")
    lines.append("- ✅ Cursor")
    lines.append("- ✅ VS Code (GitHub Copilot)")
    lines.append("- ✅ OpenAI Codex")
    lines.append("")
    lines.append("## 验证")
    lines.append("")
    lines.append("安装后运行：")
    lines.append("```bash")
    lines.append(f"python3 scripts/validate_plugin.py /path/to/{name}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Agent Plugin 打包发布工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--output", default="dist", help="输出目录（默认 dist）")
    parser.add_argument("--version", help="版本号（默认从 plugin.json 读取）")
    parser.add_argument("--platforms", default="claude,codex,copilot,cursor,gemini",
                        help="目标平台，逗号分隔（默认所有平台）")
    parser.add_argument("--skip-validation", action="store_true", help="跳过插件结构验证")
    parser.add_argument("--no-zip", action="store_true", help="不生成 zip 包")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.exists():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    # 加载插件信息
    plugin = load_plugin_json(plugin_dir)
    name = plugin.get("name", "my-plugin")
    version = args.version or plugin.get("version", "0.1.0")

    # 版本一致性检查：--version 与 plugin.json 不一致时警告
    if args.version and plugin.get("version") and args.version != plugin["version"]:
        print(f"⚠️  版本号不一致: --version={args.version}, plugin.json={plugin['version']}")
        print(f"   将使用 --version 的值: {args.version}")

    print(f"📦 打包插件: {name} v{version}")
    print(f"   源目录: {plugin_dir}")

    # 验证插件结构
    if not args.skip_validation:
        print("   验证插件结构...")
        # 简单验证：检查必需文件
        if not (plugin_dir / "plugin.json").exists():
            print("错误: 缺少 plugin.json", file=sys.stderr)
            sys.exit(1)
        # 检查 skills 目录结构
        skills_dir = plugin_dir / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir() and not (skill_dir / "SKILL.md").exists():
                    print(f"警告: skill 目录缺少 SKILL.md: {skill_dir.name}", file=sys.stderr)
        print("   ✅ 验证通过")

    # 收集文件
    files = collect_plugin_files(plugin_dir)
    print(f"   收集文件: {len(files)} 个")

    # 创建输出目录
    output_dir = Path(args.output).resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        print(f"错误: 输出目录已存在且非空: {output_dir}", file=sys.stderr)
        print("提示: 使用 --output 指定其他目录，或手动删除已有内容", file=sys.stderr)
        sys.exit(1)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成发布清单
    print("   生成发布清单...")
    manifest = generate_manifest(plugin, files, version)
    manifest_path = output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 生成 marketplace 配置
    print("   生成 marketplace 配置...")
    platforms = [p.strip() for p in args.platforms.split(",")]
    marketplace_config = generate_marketplace_config(plugin, version, platforms)
    marketplace_path = output_dir / "marketplace.json"
    marketplace_path.write_text(json.dumps(marketplace_config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 生成发布说明
    print("   生成发布说明...")
    release_notes = generate_release_notes(plugin, version)
    release_notes_path = output_dir / "RELEASE_NOTES.md"
    release_notes_path.write_text(release_notes, encoding="utf-8")

    # 创建 zip 包
    zip_size = 0
    if not args.no_zip:
        print("   创建 zip 压缩包...")
        zip_path = output_dir / f"{name}-v{version}.zip"
        zip_size = create_zip_package(plugin_dir, zip_path, files)
        # 计算 zip 哈希
        zip_hash = calculate_file_hash(zip_path)
        print(f"   zip 包: {zip_path.name} ({zip_size / 1024:.1f} KB, sha256: {zip_hash[:16]}...)")

    print()
    print("=" * 60)
    print(f"✅ 打包完成: {name} v{version}")
    print("=" * 60)
    print(f"输出目录: {output_dir}")
    print(f"文件数量: {len(files)} 个源文件")
    print(f"总大小: {manifest['total_size'] / 1024:.1f} KB (源文件)")
    if not args.no_zip:
        print(f"zip 包: {zip_size / 1024:.1f} KB")
    print()
    print("生成的文件:")
    print(f"  - MANIFEST.json      发布清单（含文件哈希）")
    print(f"  - marketplace.json   各平台市场配置")
    print(f"  - RELEASE_NOTES.md  发布说明模板")
    if not args.no_zip:
        print(f"  - {name}-v{version}.zip  可分发压缩包")
    print()
    print("目标平台:")
    for p in platforms:
        print(f"  - {p}")
    print()
    print("下一步:")
    print("  1. 编辑 RELEASE_NOTES.md，填写实际发布说明")
    print("  2. 验证 zip 包可正常解压和加载")
    print("  3. 上传到各平台 marketplace 或分发 zip 包")


if __name__ == "__main__":
    main()
