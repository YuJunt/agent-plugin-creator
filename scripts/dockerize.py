#!/usr/bin/env python3
"""
Docker 镜像生成工具

为 MCP 服务器自动生成 Dockerfile 和 docker-compose.yml，支持 streamable-http 部署。

用法:
    python3 scripts/dockerize.py <插件目录> --server <服务器名>
    python3 scripts/dockerize.py <插件目录> --all
    python3 scripts/dockerize.py <插件目录> --output ./docker
    python3 scripts/dockerize.py <插件目录> --port 8080 --json
"""
import argparse
import json
import sys
from pathlib import Path


def generate_python_dockerfile(server_name: str, port: int) -> str:
    """生成 Python MCP 服务器的 Dockerfile"""
    return f"""# MCP Server: {server_name}
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY servers/{server_name}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

# 复制服务器代码
COPY servers/{server_name}/ ./

# 暴露 streamable-http 端口
EXPOSE {port}

# 启动服务器
CMD ["python3", "server.py", "--port", "{port}"]
"""


def generate_typescript_dockerfile(server_name: str, port: int) -> str:
    """生成 TypeScript MCP 服务器的 Dockerfile"""
    return f"""# MCP Server: {server_name}
FROM node:20-alpine

WORKDIR /app

# 安装依赖
COPY servers/{server_name}/package.json ./
RUN npm install --production

# 复制服务器代码
COPY servers/{server_name}/ ./

# 编译 TypeScript
RUN npm run build || true

# 暴露 streamable-http 端口
EXPOSE {port}

# 启动服务器
CMD ["node", "dist/server.js", "--port", "{port}"]
"""


def generate_docker_compose(plugin_name: str, servers: list, base_port: int) -> str:
    """生成 docker-compose.yml"""
    services = {}
    for i, server in enumerate(servers):
        port = base_port + i
        services[server["name"]] = {
            "build": {
                "context": ".",
                "dockerfile": f"docker/Dockerfile.{server['name']}",
            },
            "ports": [f"{port}:{port}"],
            "environment": {
                "PORT": str(port),
                "MCP_TRANSPORT": "streamable-http",
            },
            "restart": "unless-stopped",
        }

    compose = {
        "version": "3.8",
        "services": services,
    }

    lines = ["version: '3.8'", "", "services:"]
    for name, svc in services.items():
        lines.append(f"  {name}:")
        lines.append(f"    build:")
        lines.append(f"      context: .")
        lines.append(f"      dockerfile: docker/Dockerfile.{name}")
        lines.append(f"    ports:")
        for p in svc["ports"]:
            lines.append(f"      - \"{p}\"")
        lines.append(f"    environment:")
        for k, v in svc["environment"].items():
            lines.append(f"      {k}: \"{v}\"")
        lines.append(f"    restart: {svc['restart']}")
        lines.append("")

    return "\n".join(lines)


def generate_dockerignore() -> str:
    """生成 .dockerignore"""
    return """__pycache__
*.pyc
*.pyo
node_modules
.git
.gitignore
*.md
!README.md
tests/
evals/
examples/
.dockerignore
Dockerfile
docker-compose.yml
"""


def main():
    parser = argparse.ArgumentParser(description="Docker 镜像生成工具")
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--server", help="指定服务器名称（默认所有）")
    parser.add_argument("--all", action="store_true", help="为所有服务器生成 Dockerfile")
    parser.add_argument("--output", default="docker", help="输出目录（默认 docker/）")
    parser.add_argument("--port", type=int, default=8080, help="基础端口号（默认8080）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--force", action="store_true", help="覆盖已有文件")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误: 插件目录不存在: {plugin_dir}", file=sys.stderr)
        sys.exit(1)

    mcp_json = plugin_dir / "mcp.json"
    if not mcp_json.exists():
        print("错误: 插件没有 mcp.json，无法生成 Docker 镜像", file=sys.stderr)
        sys.exit(1)

    try:
        mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"错误: mcp.json 不是有效 JSON: {e}", file=sys.stderr)
        sys.exit(1)

    servers = []
    for name, config in mcp.get("mcpServers", {}).items():
        if args.server and name != args.server:
            continue
        command = config.get("command", "")
        language = "typescript" if "node" in command else "python"
        servers.append({"name": name, "language": language, "config": config})

    if not servers:
        print("错误: 未找到匹配的 MCP 服务器", file=sys.stderr)
        sys.exit(1)

    output_dir = plugin_dir / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = []

    # 为每个服务器生成 Dockerfile
    for i, server in enumerate(servers):
        port = args.port + i
        dockerfile_path = output_dir / f"Dockerfile.{server['name']}"

        if dockerfile_path.exists() and not args.force:
            print(f"⚠️  已存在: {dockerfile_path}（使用 --force 覆盖）", file=sys.stderr)
            continue

        if server["language"] == "python":
            content = generate_python_dockerfile(server["name"], port)
        else:
            content = generate_typescript_dockerfile(server["name"], port)

        dockerfile_path.write_text(content, encoding="utf-8")
        generated.append(str(dockerfile_path.relative_to(plugin_dir)))

    # 生成 docker-compose.yml
    if len(servers) > 1 or args.all:
        compose_path = plugin_dir / "docker-compose.yml"
        if not compose_path.exists() or args.force:
            compose_content = generate_docker_compose(plugin_dir.name, servers, args.port)
            compose_path.write_text(compose_content, encoding="utf-8")
            generated.append("docker-compose.yml")

    # 生成 .dockerignore
    dockerignore_path = plugin_dir / ".dockerignore"
    if not dockerignore_path.exists() or args.force:
        dockerignore_path.write_text(generate_dockerignore(), encoding="utf-8")
        generated.append(".dockerignore")

    result = {
        "plugin": plugin_dir.name,
        "servers": [s["name"] for s in servers],
        "generated": generated,
        "output_dir": str(output_dir.relative_to(plugin_dir)),
        "base_port": args.port,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("Docker 镜像生成完成")
        print("=" * 50)
        print(f"插件: {plugin_dir.name}")
        print(f"服务器: {', '.join(s['name'] for s in servers)}")
        print(f"输出目录: {args.output}/")
        print(f"基础端口: {args.port}")
        print()
        print("生成的文件:")
        for f in generated:
            print(f"  ✅ {f}")
        print()
        print("使用方法:")
        print(f"  cd {plugin_dir}")
        print(f"  docker compose up -d")
        print(f"  # 或单个服务器:")
        for s in servers:
            print(f"  docker build -f docker/Dockerfile.{s['name']} -t {s['name']} .")
        print("=" * 50)

    sys.exit(0)


if __name__ == "__main__":
    main()
