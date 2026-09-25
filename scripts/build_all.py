#!/usr/bin/env python3
"""
一键全流程构建命令

从配置到发布一键完成：创建→验证→审计→打包→多客户端适配→质量评分。

用法:
    python3 scripts/build_all.py --config config.json --output ./dist
    python3 scripts/build_all.py --config config.json --output ./dist --skip-tests
    python3 scripts/build_all.py --config config.json --output ./dist --clients claude,cursor
    python3 scripts/build_all.py --config config.json --output ./dist --json
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


class ProgressBar:
    """简单进度条"""
    def __init__(self, total: int, prefix: str = ""):
        self.total = total
        self.current = 0
        self.prefix = prefix
        self.width = 40

    def update(self, step: str = ""):
        self.current += 1
        pct = self.current / self.total
        filled = int(self.width * pct)
        bar = "█" * filled + "░" * (self.width - filled)
        print(f"\r{self.prefix} [{bar}] {self.current}/{self.total} {step}", end="", flush=True)
        if self.current == self.total:
            print()

    def done(self):
        if self.current < self.total:
            self.current = self.total
            filled = self.width
            bar = "█" * filled
            print(f"\r{self.prefix} [{bar}] {self.current}/{self.total} 完成", flush=True)


def run_step(name: str, script: Path, args: list, cwd: Path = None, timeout: int = 60) -> dict:
    """运行一个构建步骤"""
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script)] + args,
            capture_output=True, text=True, cwd=str(cwd) if cwd else None,
            timeout=timeout,
        )
        duration = round(time.time() - start, 1)
        return {
            "name": name,
            "passed": result.returncode == 0,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"name": name, "passed": False, "duration": timeout, "error": "超时", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"name": name, "passed": False, "duration": 0, "error": str(e), "stdout": "", "stderr": ""}


def main():
    parser = argparse.ArgumentParser(description="一键全流程构建命令")
    parser.add_argument("--config", required=True, help="插件配置文件路径（JSON）")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--name", help="插件名称（覆盖配置文件）")
    parser.add_argument("--clients", default="all", help="客户端适配列表（逗号分隔，或 all）")
    parser.add_argument("--skip-tests", action="store_true", help="跳过 MCP 握手测试")
    parser.add_argument("--skip-audit", action="store_true", help="跳过安全审计")
    parser.add_argument("--skip-package", action="store_true", help="跳过打包")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config).resolve()

    if not config_path.exists():
        print(f"错误: 配置文件不存在: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    plugin_name = args.name or config.get("name", "my-plugin")
    output_dir = Path(args.output).resolve()
    plugin_dir = output_dir / plugin_name

    # 构建步骤
    steps = []

    # 步骤1: 生成插件
    steps.append({
        "name": "生成插件",
        "script": skill_root / "scripts" / "wizard.py",
        "args": ["--config", str(config_path), "--output", str(plugin_dir)],
        "enabled": True,
    })

    # 步骤2: 验证插件
    steps.append({
        "name": "规范验证",
        "script": skill_root / "scripts" / "validate_plugin.py",
        "args": [str(plugin_dir)],
        "enabled": True,
    })

    # 步骤3: 自动修复（如果验证失败）
    steps.append({
        "name": "自动修复",
        "script": skill_root / "scripts" / "auto_fix.py",
        "args": [str(plugin_dir)],
        "enabled": True,
        "conditional": True,  # 只在验证失败时运行
    })

    # 步骤4: MCP 握手测试
    if not args.skip_tests and (plugin_dir / "mcp.json").exists():
        # 需要从 mcp.json 读取命令
        steps.append({
            "name": "MCP 握手测试",
            "script": skill_root / "scripts" / "test_mcp_handshake.py",
            "args": ["--command", "python3", "--timeout", "10"],
            "enabled": True,
            "needs_mcp_config": True,
        })

    # 步骤5: 安全审计
    if not args.skip_audit:
        steps.append({
            "name": "安全审计",
            "script": skill_root / "scripts" / "audit_plugin.py",
            "args": [str(plugin_dir)],
            "enabled": True,
        })

    # 步骤6: 质量评分
    steps.append({
        "name": "质量评分",
        "script": skill_root / "scripts" / "score_plugin.py",
        "args": [str(plugin_dir)],
        "enabled": True,
    })

    # 步骤7: 生成文档
    steps.append({
        "name": "生成文档",
        "script": skill_root / "scripts" / "generate_docs.py",
        "args": [str(plugin_dir), "--output", str(plugin_dir / "README.md"), "--force"],
        "enabled": True,
    })

    # 步骤8: 多客户端适配
    if args.clients:
        client_args = ["--generate", "--force"]
        if args.clients != "all":
            client_args.extend(["--clients", args.clients])
        steps.append({
            "name": "多客户端适配",
            "script": skill_root / "scripts" / "client_adapter.py",
            "args": [str(plugin_dir)] + client_args,
            "enabled": True,
        })

    # 步骤9: 打包
    if not args.skip_package:
        steps.append({
            "name": "打包发布",
            "script": skill_root / "scripts" / "package_plugin.py",
            "args": [str(plugin_dir), "--output", str(output_dir)],
            "enabled": True,
        })

    # 执行步骤
    enabled_steps = [s for s in steps if s["enabled"]]
    progress = ProgressBar(len(enabled_steps), prefix="构建进度")
    results = []
    failed = False

    if not args.json:
        print(f"🚀 开始构建: {plugin_name}")
        print(f"   输出目录: {output_dir}")
        print(f"   步骤数: {len(enabled_steps)}")
        print()

    for step in enabled_steps:
        if failed and step.get("conditional"):
            # 条件步骤：只在前面失败时运行，这里跳过
            progress.update(f"跳过 {step['name']}")
            results.append({"name": step["name"], "passed": True, "skipped": True})
            continue

        progress.update(step["name"])

        # 处理需要动态参数的步骤
        step_args = step["args"]
        if step.get("needs_mcp_config"):
            mcp_json = plugin_dir / "mcp.json"
            if mcp_json.exists():
                try:
                    mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
                    first_server = list(mcp.get("mcpServers", {}).values())[0]
                    if first_server.get("type") == "stdio":
                        cmd = first_server.get("command", "python3")
                        server_args = first_server.get("args", [])
                        # 找到服务器文件
                        server_file = None
                        for a in server_args:
                            if a.endswith(".py") or a.endswith(".js"):
                                server_file = plugin_dir / a.lstrip("./")
                                break
                        if server_file and server_file.exists():
                            step_args = ["--command", cmd, str(server_file), "--timeout", "10"]
                except Exception:
                    pass

        result = run_step(step["name"], step["script"], step_args, timeout=120)
        results.append(result)

        if not result["passed"] and not step.get("conditional"):
            # 非条件步骤失败，标记但继续（自动修复可能修复）
            if step["name"] != "规范验证":  # 验证失败时继续到自动修复
                pass

        if step["name"] == "规范验证" and not result["passed"]:
            # 验证失败，继续到自动修复
            pass
        elif not result["passed"] and step["name"] != "自动修复":
            # 其他步骤失败，记录但继续（打包等步骤可能仍有价值）
            pass

    progress.done()

    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    failed_count = total - passed

    summary = {
        "plugin": plugin_name,
        "output": str(output_dir),
        "total_steps": total,
        "passed": passed,
        "failed": failed_count,
        "success_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "steps": results,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    else:
        print()
        print("=" * 50)
        print(f"构建完成: {plugin_name}")
        print("=" * 50)
        print(f"总步骤: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed_count}")
        print(f"成功率: {summary['success_rate']}%")
        print()

        for r in results:
            if r.get("skipped"):
                icon = "⏭️"
            elif r.get("passed"):
                icon = "✅"
            else:
                icon = "❌"
            duration = r.get("duration", 0)
            print(f"  {icon} {r['name']} ({duration}s)")
            if not r.get("passed") and not r.get("skipped"):
                error = r.get("error") or r.get("stderr", "")[:100]
                if error:
                    print(f"     错误: {error}")

        print()
        if failed_count == 0:
            print("🎉 构建全部通过！")
        else:
            print(f"⚠️  {failed_count} 个步骤失败，请检查上方详情")

        print(f"\n📦 产物位置: {output_dir}")
        print("=" * 50)

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
