#!/usr/bin/env python3
"""
npm/pypi 包发布配置工具

为 MCP 服务器生成 npm package.json 或 pypi pyproject.toml 发布配置。

用法:
    python3 scripts/publish_config.py <服务器目录> --type pypi
    python3 scripts/publish_config.py <服务器目录> --type npm
    python3 scripts/publish_config.py <服务器目录> --type both --name my-mcp-server
    python3 scripts/publish_config.py <服务器目录> --json
"""
import argparse
import json
import sys
from pathlib import Path


def generate_pyproject_toml(server_name: str, version: str, description: str, author: str) -> str:
    """生成 pyproject.toml（Poetry 格式）"""
    return f"""[tool.poetry]
name = "{server_name}"
version = "{version}"
description = "{description}"
authors = ["{author}"]
readme = "README.md"
license = "MIT"
packages = [{{include = "{server_name.replace('-', '_')}"}}]
keywords = ["mcp", "server", "agent"]

[tool.poetry.dependencies]
python = "^3.10"
fastmcp = "^2.0"

[tool.poetry.scripts]
{server_name} = "{server_name.replace('-', '_')}.server:main"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
"""


def generate_package_json(server_name: str, version: str, description: str, author: str) -> str:
    """生成 package.json（npm 格式）"""
    pkg = {
        "name": server_name,
        "version": version,
        "description": description,
        "main": "dist/server.js",
        "types": "dist/server.d.ts",
        "bin": {
            server_name: "./dist/server.js"
        },
        "scripts": {
            "build": "tsc",
            "start": "node dist/server.js",
            "dev": "tsx src/server.ts",
            "test": "jest",
            "prepublishOnly": "npm run build"
        },
        "keywords": ["mcp", "server", "agent"],
        "author": author,
        "license": "MIT",
        "dependencies": {
            "@modelcontextprotocol/sdk": "^1.0.0"
        },
        "devDependencies": {
            "typescript": "^5.0.0",
            "@types/node": "^20.0.0",
            "tsx": "^4.0.0"
        },
        "engines": {
            "node": ">=18.0.0"
        },
        "files": ["dist/", "README.md", "LICENSE"],
        "repository": {
            "type": "git",
            "url": f"https://github.com/your-username/{server_name}.git"
        }
    }
    return json.dumps(pkg, indent=2, ensure_ascii=False) + "\n"


def generate_publish_yml(server_name: str, package_type: str) -> str:
    """生成 GitHub Actions 发布工作流"""
    if package_type == "pypi":
        return f"""name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install Poetry
        run: pip install poetry
      - name: Build
        run: poetry build
      - name: Publish
        env:
          POETRY_PYPI_TOKEN: ${{{{ secrets.PYPI_TOKEN }}}}
        run: poetry publish
"""
    else:
        return f"""name: Publish to npm

on:
  release:
    types: [created]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
      - name: Install
        run: npm ci
      - name: Build
        run: npm run build
      - name: Publish
        env:
          NODE_AUTH_TOKEN: ${{{{ secrets.NPM_TOKEN }}}}
        run: npm publish --access public
"""


def main():
    parser = argparse.ArgumentParser(description="npm/pypi 包发布配置工具")
    parser.add_argument("server_dir", help="MCP 服务器目录路径")
    parser.add_argument("--type", choices=["pypi", "npm", "both"], default="pypi", help="包类型")
    parser.add_argument("--name", help="包名称（默认使用目录名）")
    parser.add_argument("--version", default="0.1.0", help="版本号")
    parser.add_argument("--description", default="MCP Server", help="包描述")
    parser.add_argument("--author", default="Your Name <your@email.com>", help="作者")
    parser.add_argument("--github-actions", action="store_true", help="生成 GitHub Actions 发布工作流")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--force", action="store_true", help="覆盖已有文件")
    args = parser.parse_args()

    server_dir = Path(args.server_dir).resolve()
    if not server_dir.is_dir():
        print(f"错误: 目录不存在: {server_dir}", file=sys.stderr)
        sys.exit(1)

    server_name = args.name or server_dir.name
    generated = []

    # 生成配置文件
    if args.type in ("pypi", "both"):
        pyproject = server_dir / "pyproject.toml"
        if not pyproject.exists() or args.force:
            pyproject.write_text(generate_pyproject_toml(server_name, args.version, args.description, args.author), encoding="utf-8")
            generated.append("pyproject.toml")

    if args.type in ("npm", "both"):
        pkg_json = server_dir / "package.json"
        if not pkg_json.exists() or args.force:
            pkg_json.write_text(generate_package_json(server_name, args.version, args.description, args.author), encoding="utf-8")
            generated.append("package.json")

    # 生成 GitHub Actions
    if args.github_actions:
        workflows_dir = server_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        if args.type in ("pypi", "both"):
            yml = workflows_dir / "publish-pypi.yml"
            if not yml.exists() or args.force:
                yml.write_text(generate_publish_yml(server_name, "pypi"), encoding="utf-8")
                generated.append(".github/workflows/publish-pypi.yml")

        if args.type in ("npm", "both"):
            yml = workflows_dir / "publish-npm.yml"
            if not yml.exists() or args.force:
                yml.write_text(generate_publish_yml(server_name, "npm"), encoding="utf-8")
                generated.append(".github/workflows/publish-npm.yml")

    result = {
        "server": server_name,
        "type": args.type,
        "version": args.version,
        "generated": generated,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("发布配置生成完成")
        print("=" * 50)
        print(f"服务器: {server_name}")
        print(f"类型: {args.type}")
        print(f"版本: {args.version}")
        print()
        print("生成的文件:")
        for f in generated:
            print(f"  ✅ {f}")
        print()
        if args.type in ("pypi", "both"):
            print("PyPI 发布步骤:")
            print("  1. poetry install")
            print("  2. poetry build")
            print("  3. poetry publish")
            print()
        if args.type in ("npm", "both"):
            print("npm 发布步骤:")
            print("  1. npm install")
            print("  2. npm run build")
            print("  3. npm publish --access public")
        print("=" * 50)

    sys.exit(0)


if __name__ == "__main__":
    main()
