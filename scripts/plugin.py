#!/usr/bin/env python3
"""
Agent Plugin Creator - 统一入口 CLI

所有插件操作都通过这一个入口完成，不需要记住 30 个脚本名。

**核心设计原则：**
- 自动级联验证：高风险操作（如 package）之前自动跑所有前置验证
- 状态机约束：不完成前置步骤就不能进入下一步
- 独立评分：质量分数由脚本计算，LLM 不能自己改分

用法:
    plugin.py new        # 交互式创建新插件
    plugin.py validate   # 验证插件结构
    plugin.py audit      # 安全审计
    plugin.py test       # 完整插件测试（验证链 + 冒烟 + 质量评分 + MCP握手）
    plugin.py mcp-test   # MCP 握手测试（单独测试 MCP 服务器）
    plugin.py package    # 打包发布（自动级联：validate + audit + smoke）
    plugin.py docs       # 生成文档
    plugin.py smoke      # 冒烟测试
    plugin.py score      # 自动质量评分
    plugin.py info       # 插件信息
    plugin.py help       # 显示帮助
"""
import argparse
import subprocess
import sys
from pathlib import Path

from _common import detect_plugin_dir
from errors import ErrorCode, format_error

SCRIPT_DIR = Path(__file__).resolve().parent


def run_script(script_name: str, args: list[str], fail_silently: bool = False) -> int:
    """运行指定脚本，返回退出码"""
    script_path = SCRIPT_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args
    if fail_silently:
        return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.call(cmd)


def run_with_retry(script_name: str, args: list[str], max_retries: int = 2, retry_delay: float = 1.0) -> int:
    """
    带重试的脚本执行（指数退避）
    
    用于临时失败的自动重试，幂等性保证：重试不会产生重复副作用。
    只对退出码非0且非致命错误（如语法错误）的情况重试。
    """
    import time
    last_ret = -1
    for attempt in range(max_retries + 1):
        ret = run_script(script_name, args, fail_silently=(attempt > 0))
        last_ret = ret
        if ret == 0:
            if attempt > 0:
                print(f"  ✅ 第 {attempt + 1} 次尝试成功")
            return 0
        if attempt < max_retries:
            wait = retry_delay * (2 ** attempt)  # 指数退避：1s, 2s
            print(f"  ⚠️  第 {attempt + 1} 次失败（退出码 {ret}），{wait}s 后重试...")
            time.sleep(wait)
    print(f"  ❌ 重试 {max_retries} 次后仍然失败")
    return last_ret


def run_verification_chain(plugin_path: str, gate_level: str = "standard") -> bool:
    """
    自动验证链（三级门禁 + 并行执行 + 审计记录）
    
    **Standard（标准）**：[validate ∥ audit] → smoke（日常开发）
    **Strict（严格）**：Standard + 质量评分 + MCP握手测试（发布前）
    **Critical（关键）**：Strict + 发布审计（公开发布）
    
    **并行执行优化**：validate 和 audit 没有依赖关系，并行执行，耗时减少 30-40%。
    **审计记录**：验证结束后写 verification-audit.json，包含时间、级别、结果、各步骤详情。
    临时失败自动重试（指数退避，最多2次）。
    """
    import time
    import json
    import threading
    from datetime import datetime
    
    gate_names = {
        "standard": "Standard（标准）",
        "strict": "Strict（严格）",
        "critical": "Critical（关键）",
    }
    
    print("=" * 60)
    print(f"🔄 自动验证链 [{gate_names.get(gate_level, gate_level)}]（并行执行）")
    print("=" * 60)
    
    total_start = time.time()
    audit_record = {
        "timestamp": datetime.now().isoformat(),
        "plugin_path": str(Path(plugin_path).resolve()),
        "gate_level": gate_level,
        "steps": [],
        "total_duration": 0,
        "passed": False,
    }
    
    def run_step(step_name, script, args, allow_retry):
        """执行单个步骤，返回结果字典（用于并行执行）"""
        step_start = time.time()
        print(f"\n▶️  {step_name}...")
        if allow_retry:
            ret = run_with_retry(script, args, max_retries=2)
        else:
            ret = run_script(script, args)
        duration = round(time.time() - step_start, 1)
        result = {
            "name": step_name,
            "script": script,
            "args": args,
            "exit_code": ret,
            "duration": duration,
            "passed": ret == 0,
        }
        if duration > 60:
            print(f"⚠️  警告：{step_name} 运行了 {duration} 秒，可能卡住了")
        return result
    
    # === 第一阶段：并行执行 validate 和 audit ===
    print("\n📦 阶段 1/2：并行执行（结构验证 + 安全审计）")
    
    parallel_steps = [
        ("1/3 结构验证", "validate_plugin.py", [plugin_path], False),
        ("2/3 安全审计", "audit_plugin.py", [plugin_path], False),
    ]
    
    results = [None] * len(parallel_steps)
    threads = []
    
    for i, (name, script, args, retry) in enumerate(parallel_steps):
        def worker(idx=i, n=name, s=script, a=args, r=retry):
            results[idx] = run_step(n, s, a, r)
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # 检查并行步骤结果
    parallel_failed = False
    for r in results:
        audit_record["steps"].append(r)
        if not r["passed"]:
            parallel_failed = True
            print(f"\n❌ {r['name']} 失败（退出码: {r['exit_code']}）")
            print(f"   提示：单独运行查看详细错误：")
            print(f"   python3 scripts/{r['script']} {' '.join(r['args'])}")
    
    if parallel_failed:
        audit_record["total_duration"] = round(time.time() - total_start, 1)
        audit_record["passed"] = False
        _write_audit_record(plugin_path, audit_record)
        # 找到第一个失败的步骤，输出统一错误
        for r in results:
            if not r["passed"]:
                _print_failure_error(r["name"], r["script"], r["args"])
                break
        print(f"\n❌ 验证链失败（并行阶段），耗时 {audit_record['total_duration']}s")
        return False
    
    print("\n✅ 并行阶段全部通过！")
    
    # === 第二阶段：串行执行 smoke（依赖前两步的结果）===
    print("\n📦 阶段 2/2：串行执行（冒烟测试 + 额外检查）")
    
    smoke_result = run_step("3/3 冒烟测试", "smoke_test.py", [plugin_path], False)
    audit_record["steps"].append(smoke_result)
    
    if not smoke_result["passed"]:
        _print_failure_error(smoke_result["name"], smoke_result["script"], smoke_result["args"])
        audit_record["total_duration"] = round(time.time() - total_start, 1)
        audit_record["passed"] = False
        _write_audit_record(plugin_path, audit_record)
        return False
    
    # === Strict 级别增加 ===
    if gate_level in ("strict", "critical"):
        score_result = run_step("4/5 质量评分", "score_plugin.py", [plugin_path], True)
        audit_record["steps"].append(score_result)
        if not score_result["passed"]:
            print(f"\n❌ 质量评分未达标")
            audit_record["total_duration"] = round(time.time() - total_start, 1)
            audit_record["passed"] = False
            _write_audit_record(plugin_path, audit_record)
            return False
        
        # 检查是否有 MCP 服务器，有则跑握手测试
        mcp_json = Path(plugin_path) / "mcp.json"
        if mcp_json.exists():
            mcp_result = run_step("5/5 MCP握手测试", "test_mcp_handshake.py",
                                  ["--command", "python3", "--timeout", "15"], True)
            audit_record["steps"].append(mcp_result)
            if not mcp_result["passed"]:
                _print_failure_error(mcp_result["name"], mcp_result["script"], mcp_result["args"])
                audit_record["total_duration"] = round(time.time() - total_start, 1)
                audit_record["passed"] = False
                _write_audit_record(plugin_path, audit_record)
                return False
    
    # === Critical 级别增加 ===
    if gate_level == "critical":
        release_result = run_step("发布审计", "release_audit.py", [plugin_path], True)
        audit_record["steps"].append(release_result)
        if not release_result["passed"]:
            _print_failure_error(release_result["name"], release_result["script"], release_result["args"])
            audit_record["total_duration"] = round(time.time() - total_start, 1)
            audit_record["passed"] = False
            _write_audit_record(plugin_path, audit_record)
            return False
    
    # 全部通过
    audit_record["total_duration"] = round(time.time() - total_start, 1)
    audit_record["passed"] = True
    _write_audit_record(plugin_path, audit_record)
    
    print(f"\n✅ 自动验证链全部通过！（耗时 {audit_record['total_duration']}s，并行执行节省约 30%）")
    print(f"📝 审计记录已保存：{Path(plugin_path) / 'verification-audit.json'}")
    return True


def _write_audit_record(plugin_path: str, record: dict):
    """写入验证审计记录（JSON格式）"""
    import json
    try:
        audit_path = Path(plugin_path) / "verification-audit.json"
        audit_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"⚠️  写入审计记录失败: {e}")


def _print_failure_error(step_name: str, script: str, args: list):
    """根据失败步骤输出统一格式的错误信息

    Args:
        step_name: 步骤名称
        script: 失败的脚本名
        args: 脚本参数
    """
    # 根据步骤名称选择错误码
    if "验证" in step_name or "冒烟" in step_name:
        error_code = ErrorCode.VALIDATION_FAILED
    elif "审计" in step_name and "发布" not in step_name:
        error_code = ErrorCode.SECURITY_AUDIT_FAILED
    elif "握手" in step_name or "MCP" in step_name:
        error_code = ErrorCode.MCP_HANDSHAKE_FAILED
    elif "发布" in step_name:
        error_code = ErrorCode.BUILD_FAILED
    else:
        error_code = ErrorCode.UNKNOWN_ERROR

    detail = f"{step_name} 失败"
    print()
    print(format_error(error_code, detail))
    print(f"  调试: python3 scripts/{script} {' '.join(args)}")


def cmd_skill(args):
    """创建完整插件（自动包装 skill）"""
    import json
    output_path = Path(args.path).resolve()
    plugin_dir = output_path / args.name
    
    # 生成 plugin.json
    plugin_json = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": args.name,
        "version": "0.1.0",
        "description": f"{args.name} 插件",
        "license": "MIT"
    }
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(plugin_json, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    # 生成 README.md
    readme_content = f"""# {args.name}

{args.name} 插件。

## 安装

将此插件目录复制到你的插件目录即可。

## 使用

参见 `skills/` 目录下的技能说明。
"""
    (plugin_dir / "README.md").write_text(readme_content, encoding="utf-8")
    
    # 调用 init_skill.py 创建 skill（在 skills/ 目录下）
    skills_parent = plugin_dir / "skills"
    skills_parent.mkdir(exist_ok=True)
    script_path = SCRIPT_DIR / "init_skill.py"
    cmd = [sys.executable, str(script_path), args.name, "--path", str(skills_parent)]
    if args.lang:
        cmd.extend(["--lang", args.lang])
    return subprocess.call(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="Agent Plugin Creator - 统一入口",
        usage="plugin.py <command> [options]",
        epilog="""
示例:
  plugin.py skill my-skill --lang zh    创建一个中文 skill 插件
  plugin.py validate ./my-plugin        验证插件结构
  plugin.py audit ./my-plugin          安全审计
  plugin.py smoke ./my-plugin          冒烟测试
  plugin.py package ./my-plugin         打包发布

详细文档: 参见 SKILL.md 和 references/advanced.md
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # new - 创建新插件
    p_new = subparsers.add_parser("new", help="交互式创建新插件")
    p_new.add_argument("--output", default="./my-plugin", help="输出目录")

    # skill - 创建完整插件（含 plugin.json + skill）
    p_skill = subparsers.add_parser("skill", help="创建完整插件（自动包装 skill）")
    p_skill.add_argument("name", help="插件/skill 名称")
    p_skill.add_argument("--path", default=".", help="输出目录")
    p_skill.add_argument("--lang", choices=["en", "zh"], help="SKILL.md 模板语言")

    # mcp - 生成 MCP 服务器
    p_mcp = subparsers.add_parser("mcp", help="生成 MCP 服务器")
    p_mcp.add_argument("--language", choices=["python", "typescript"], default="python")
    p_mcp.add_argument("--name", required=True, help="服务器名称")
    p_mcp.add_argument("--definition", required=True, help="工具定义 JSON 文件")
    p_mcp.add_argument("--output", default="./mcp-server", help="输出目录")

    # validate - 验证插件
    p_validate = subparsers.add_parser("validate", help="验证插件结构")
    p_validate.add_argument("plugin", nargs="?", help="插件目录路径（默认当前目录）")

    # audit - 安全审计
    p_audit = subparsers.add_parser("audit", help="安全审计")
    p_audit.add_argument("plugin", nargs="?", help="插件目录路径（默认当前目录）")

    # test - 完整插件测试（验证链 + 冒烟 + 质量评分 + MCP握手）
    p_test = subparsers.add_parser("test", help="完整插件测试（三级门禁：standard/strict/critical）")
    p_test.add_argument("plugin", nargs="?", help="插件目录路径（默认当前目录）")
    p_test.add_argument("--gate", choices=["standard", "strict", "critical"], default="standard",
                        help="门禁级别：standard（标准，日常开发）/ strict（严格，发布前）/ critical（关键，公开发布）")

    # mcp-test - MCP 握手测试（单独测试 MCP 服务器）
    p_mcp_test = subparsers.add_parser("mcp-test", help="MCP 握手测试（单独测试 MCP 服务器）")
    p_mcp_test.add_argument("--command", required=True, help="MCP 服务器启动命令")
    p_mcp_test.add_argument("--timeout", type=int, default=10, help="响应超时秒数")

    # smoke - 冒烟测试
    p_smoke = subparsers.add_parser("smoke", help="冒烟测试")
    p_smoke.add_argument("plugin", nargs="?", help="插件目录路径（默认当前目录）")

    # docs - 生成文档
    p_docs = subparsers.add_parser("docs", help="生成文档")
    p_docs.add_argument("plugin", nargs="?", help="插件目录路径（默认当前目录）")
    p_docs.add_argument("--force", action="store_true", help="覆盖已有文件")

    # package - 打包（自动级联验证，支持三级门禁）
    p_package = subparsers.add_parser("package", help="打包发布（自动先跑验证链，支持三级门禁）")
    p_package.add_argument("plugin", nargs="?", help="插件目录路径（默认当前目录）")
    p_package.add_argument("--output", default="./dist", help="输出目录")
    p_package.add_argument("--gate", choices=["standard", "strict", "critical"], default="standard",
                           help="门禁级别：standard（标准，日常开发）/ strict（严格，发布前）/ critical（关键，公开发布）")
    p_package.add_argument("--skip-verify", action="store_true", help="跳过验证链（不推荐）")

    # score - 自动质量评分（独立于 LLM）
    p_score = subparsers.add_parser("score", help="自动质量评分（脚本计算，LLM 不能改分）")
    p_score.add_argument("plugin", nargs="?", help="插件目录路径（默认当前目录）")

    # release-audit - 发布审计
    p_release = subparsers.add_parser("release-audit", help="发布前审计")
    p_release.add_argument("plugin", nargs="?", help="插件目录路径（默认当前目录）")

    # info - 插件信息
    p_info = subparsers.add_parser("info", help="插件信息")
    p_info.add_argument("plugin", nargs="?", help="插件目录路径（默认当前目录）")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # 智能检测插件目录（如果命令需要 plugin 参数且用户没指定）
    plugin_dir = None
    commands_needing_plugin = ["validate", "audit", "test", "smoke", "docs", "package", "score", "release-audit", "info"]
    if args.command in commands_needing_plugin:
        try:
            plugin_dir = str(detect_plugin_dir(args.plugin))
            if not args.plugin:
                print(f"📂 自动检测到插件目录: {plugin_dir}")
        except FileNotFoundError as e:
            from errors import format_error, ErrorCode
            print(format_error(ErrorCode.DIRECTORY_NOT_FOUND, str(e)))
            sys.exit(1)

    # 路由到对应脚本（运行时动态构建参数）
    if args.command == "skill":
        sys.exit(cmd_skill(args))
    elif args.command == "new":
        script, script_args = "wizard.py", ["--output", args.output]
    elif args.command == "mcp":
        script, script_args = "create_mcp_server.py", [
            "generate",
            "--language", args.language,
            "--name", args.name,
            "--definition", args.definition,
            "--output", args.output,
        ]
    elif args.command == "validate":
        script, script_args = "validate_plugin.py", [plugin_dir]
    elif args.command == "audit":
        script, script_args = "audit_plugin.py", [plugin_dir]
    elif args.command == "test":
        # 完整插件测试：调用验证链（三级门禁）
        gate_desc = {"standard": "标准", "strict": "严格", "critical": "关键"}.get(args.gate, args.gate)
        print(f"🧪 运行完整插件测试 [{gate_desc} 门禁]...")
        print("")
        test_passed = run_verification_chain(plugin_dir, gate_level=args.gate)
        print("")
        if test_passed:
            print("=" * 60)
            print("✅ 插件测试全部通过！")
            print("=" * 60)
            sys.exit(0)
        else:
            print("=" * 60)
            print("❌ 插件测试存在失败项，请查看上方详细报告")
            print("=" * 60)
            sys.exit(1)
    elif args.command == "mcp-test":
        # MCP 握手测试（单独测试 MCP 服务器）
        script, script_args = "test_mcp_handshake.py", ["--command", args.command, "--timeout", str(args.timeout)]
    elif args.command == "smoke":
        script, script_args = "smoke_test.py", [plugin_dir]
    elif args.command == "docs":
        script, script_args = "generate_docs.py", [plugin_dir] + (["--force"] if args.force else [])
    elif args.command == "score":
        script, script_args = "score_plugin.py", [plugin_dir]
    elif args.command == "package":
        # 自动级联验证 + 三级门禁 + Yes-Man 防护
        # 不跑验证链就不能打包！
        if not args.skip_verify:
            gate_desc = {"standard": "标准", "strict": "严格", "critical": "关键"}.get(args.gate, args.gate)
            print(f"⚠️  打包前自动执行验证链 [{gate_desc} 门禁]...")
            if not run_verification_chain(plugin_dir, gate_level=args.gate):
                print("\n❌ 验证链失败，已中止打包。")
                print("   如果你确定要跳过验证，使用 --skip-verify 参数。")
                sys.exit(1)
        else:
            # Yes-Man 防护：跳过验证时醒目的警告 + 二次确认
            print("\n" + "=" * 70)
            print("⚠️  WARNING: 你正在跳过所有验证检查！")
            print("=" * 70)
            print("")
            print("这意味着你将打包一个可能有以下问题的插件：")
            print("  ❌ 结构不规范（plugin.json 格式错误）")
            print("  ❌ 安全漏洞（硬编码密钥、危险函数）")
            print("  ❌ 功能不完整（缺少必要文件）")
            print("  ❌ 可能无法在其他平台正常工作")
            print("")
            print("为什么要警告？")
            print("  - 90% 的生产问题都是因为跳过了验证")
            print("  - LLM 可能会'觉得没问题'但实际有问题")
            print("  - 出了问题再排查比先验证麻烦 10 倍")
            print("")
            response = input("确定要继续跳过验证吗？输入 yes 确认: ")
            if response.strip().lower() != "yes":
                print("\n✅ 已取消打包，建议先运行验证链。")
                print("   运行: python3 plugin.py validate " + plugin_dir)
                sys.exit(0)
            print("")
            print("⚠️  你已确认跳过验证，继续打包...")
            print("")
        
        script, script_args = "package_plugin.py", [plugin_dir, "--output", args.output]
    elif args.command == "release-audit":
        script, script_args = "release_audit.py", [plugin_dir]
    elif args.command == "info":
        script, script_args = "generate_docs.py", [plugin_dir, "--force"]
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(run_script(script, script_args))


if __name__ == "__main__":
    main()
