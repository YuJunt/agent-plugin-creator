#!/usr/bin/env python3
"""
Agent Plugins 1.0.0 规范验证脚本（集成 Skill 和 MCP 验证）

用法:
    python3 validate_plugin.py <插件目录路径>

检查项:
    - plugin.json 存在且为有效 JSON
    - 必需字段 $schema 和 name 存在且值正确
    - name 符合命名规则且与目录名一致
    - 无未知顶层字段
    - skills/ 下每个直接子目录含 SKILL.md
    - 每个 skill 的 frontmatter 符合 agentskills.io 官方规范
    - mcp.json（如存在）格式正确且版本与 plugin.json 一致
    - MCP 服务器配置符合传输类型要求
    - MCP env 中不含保留变量名 PLUGIN_ROOT / PLUGIN_DATA
    - ${PLUGIN_ROOT} 引用的文件真实存在
    - 插件内路径不逃逸出根目录
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# 规范常量（支持 1.0.0 稳定版与 1.1.0 working draft，校验规则一致）
PLUGIN_SCHEMAS = {
    "1.0.0": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
    "1.1.0": "https://agent-plugins.org/schemas/1.1.0/plugin.schema.json",
}
MCP_SCHEMAS = {
    "1.0.0": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
    "1.1.0": "https://agent-plugins.org/schemas/1.1.0/mcp.schema.json",
}
# 当前推荐生成使用的稳定版本
DEFAULT_SCHEMA_VERSION = "1.0.0"


def _schema_version(schema_url: str) -> Optional[str]:
    """从 schema URL 提取版本号，如 .../1.0.0/plugin.schema.json -> '1.0.0'"""
    for ver in PLUGIN_SCHEMAS:
        if ver in schema_url:
            return ver
    return None

# plugin.json 允许的顶层字段
ALLOWED_PLUGIN_FIELDS = {
    "$schema", "name", "version", "description", "author",
    "homepage", "repository", "license", "keywords", "extensions"
}

# author 对象允许的字段
ALLOWED_AUTHOR_FIELDS = {"name", "email", "url"}

# Agent Plugins plugin name 规范（允许点，仅 ASCII — 包名/目录名兼容性）
PLUGIN_NAME_PATTERN = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")

# agentskills.io skill name 规范（不允许点，支持 Unicode 字母 — 与 validate_skill.py 对齐）
import unicodedata as _unicodedata

def validate_skill_name(name: str) -> tuple[bool, str]:
    """验证 skill name 是否符合 agentskills.io 规范（支持 Unicode 字母）。

    与 validate_skill.py 的 _validate_name_official 逻辑一致：
    - NFKC 规范化
    - 非空、<=64 字符
    - 全小写
    - 不以连字符开头/结尾，无连续连字符
    - 仅 Unicode 字母数字 + 连字符
    """
    if not name or not isinstance(name, str) or not name.strip():
        return False, "name must be a non-empty string"
    name = _unicodedata.normalize("NFKC", name.strip())
    if len(name) > 64:
        return False, f"name exceeds 64 character limit ({len(name)} chars)"
    if name != name.lower():
        return False, f"name '{name}' must be lowercase"
    if name.startswith("-") or name.endswith("-"):
        return False, "name cannot start or end with a hyphen"
    if "--" in name:
        return False, "name cannot contain consecutive hyphens"
    if "." in name:
        return False, "skill name cannot contain dots (use hyphens)"
    if not all(c.isalnum() or c == "-" for c in name):
        return False, f"name '{name}' contains invalid characters (only Unicode letters, digits, and hyphens)"
    return True, ""

# MCP 传输类型
MCP_TRANSPORTS = {"stdio", "streamable-http", "sse"}

# 保留环境变量名
RESERVED_ENV_VARS = {"PLUGIN_ROOT", "PLUGIN_DATA"}


class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def ok(self, msg):
        self.passed.append(msg)

    @property
    def success(self):
        return len(self.errors) == 0

    def report(self):
        lines = []
        lines.append("=" * 60)
        lines.append("Agent Plugins 1.0.0 验证报告")
        lines.append("=" * 60)

        if self.passed:
            lines.append(f"\n✅ 通过 ({len(self.passed)} 项):")
            for p in self.passed:
                lines.append(f"   - {p}")

        if self.warnings:
            lines.append(f"\n⚠️  警告 ({len(self.warnings)} 项):")
            for w in self.warnings:
                lines.append(f"   - {w}")

        if self.errors:
            lines.append(f"\n❌ 错误 ({len(self.errors)} 项):")
            for e in self.errors:
                lines.append(f"   - {e}")

        lines.append("\n" + "=" * 60)
        if self.success:
            lines.append("结论: 插件符合 Agent Plugins 1.0.0 规范")
        else:
            lines.append(f"结论: 验证失败，存在 {len(self.errors)} 个错误")
        lines.append("=" * 60)
        return "\n".join(lines)


def parse_frontmatter(content: str) -> tuple:
    """简单解析 YAML frontmatter"""
    if not content.startswith("---"):
        return {}, content

    lines = content.split("\n")
    if len(lines) < 2 or lines[0].strip() != "---":
        return {}, content

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, content

    frontmatter_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1:])

    fm = {}
    current_key = None
    current_dict = None

    for line in frontmatter_lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith("  ") and current_key and current_dict is not None:
            stripped = line.strip()
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                current_dict[k.strip()] = v.strip().strip('"').strip("'")
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                current_key = key
                current_dict = {}
                fm[key] = current_dict
            else:
                current_key = None
                current_dict = None
                fm[key] = value.strip('"').strip("'")

    return fm, body


def validate_skill_frontmatter(skill_dir: Path, result: ValidationResult):
    """验证单个 skill 的 frontmatter（agentskills.io 官方规范）"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result.error(f"skills/{skill_dir.name}/ 缺少 SKILL.md")
        return

    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        result.error(f"skills/{skill_dir.name}/SKILL.md 无法读取: {e}")
        return

    if not content.startswith("---"):
        result.error(f"skills/{skill_dir.name}/SKILL.md 必须以 YAML frontmatter 开头")
        return

    fm, body = parse_frontmatter(content)
    if not fm:
        result.error(f"skills/{skill_dir.name}/SKILL.md frontmatter 解析失败或为空")
        return

    # 验证 name
    if "name" not in fm:
        result.error(f"skills/{skill_dir.name}/SKILL.md 缺少必需字段: name")
    else:
        sname = fm["name"]
        if not isinstance(sname, str) or not sname:
            result.error(f"skills/{skill_dir.name}: name 必须是非空字符串")
        else:
            if len(sname) > 64:
                result.error(f"skills/{skill_dir.name}: name 超过 64 字符")
            valid, reason = validate_skill_name(sname)
            if not valid:
                result.error(
                    f"skills/{skill_dir.name}: name 不符合 agentskills.io 官方规范\n"
                    f"   值: '{sname}'\n"
                    f"   原因: {reason}\n"
                    f"   规则: Unicode 小写字母+数字+连字符（不允许点），不以连字符开头/结尾，无连续连字符"
                )
            if sname != skill_dir.name:
                result.error(
                    f"skills/{skill_dir.name}: SKILL.md 的 name 与目录名不一致\n"
                    f"   name: {sname}, 目录名: {skill_dir.name}"
                )

    # 验证 description
    if "description" not in fm:
        result.error(f"skills/{skill_dir.name}/SKILL.md 缺少必需字段: description")
    else:
        desc = fm["description"]
        if not isinstance(desc, str) or not desc:
            result.error(f"skills/{skill_dir.name}: description 必须是非空字符串")
        elif len(desc) > 1024:
            result.error(f"skills/{skill_dir.name}: description 超过 1024 字符 ({len(desc)})")

    # 检查 body
    if not body.strip():
        result.warn(f"skills/{skill_dir.name}/SKILL.md body 为空")


def check_plugin_root_refs(value: str, plugin_root: Path, context: str, result: ValidationResult):
    """检查 ${PLUGIN_ROOT} 引用的文件是否存在"""
    if "${PLUGIN_ROOT}" not in value:
        return

    # 提取 ${PLUGIN_ROOT}/path 形式的路径
    pattern = re.compile(r"\$\{PLUGIN_ROOT\}(/[^\s\"'`,]*)?")
    for match in pattern.finditer(value):
        rel_path = match.group(1) or ""
        if rel_path:
            # 去掉末尾的标点
            rel_path = rel_path.rstrip(".,;:!?")
            target = (plugin_root / rel_path.lstrip("/")).resolve()
            if not target.exists():
                result.warn(
                    f"{context}: ${{PLUGIN_ROOT}}{rel_path} 引用的文件/目录不存在\n"
                    f"   解析为: {target}"
                )


def validate_plugin(plugin_path: str) -> ValidationResult:
    result = ValidationResult()
    root = Path(plugin_path).resolve()

    if not root.exists():
        result.error(f"插件目录不存在: {root}")
        return result
    if not root.is_dir():
        result.error(f"路径不是目录: {root}")
        return result

    result.ok(f"插件目录存在: {root}")

    # === 1. 验证 plugin.json ===
    plugin_json_path = root / "plugin.json"
    if not plugin_json_path.exists():
        result.error("缺少必需文件: plugin.json")
        return result
    if not plugin_json_path.is_file():
        result.error("plugin.json 不是常规文件")
        return result

    result.ok("plugin.json 存在")

    try:
        with open(plugin_json_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        result.error(f"plugin.json 不是有效 JSON: {e}")
        return result

    if not isinstance(manifest, dict):
        result.error("plugin.json 顶层必须是对象")
        return result

    result.ok("plugin.json 是有效 JSON 对象")

    # 检查必需字段
    if "$schema" not in manifest:
        result.error("plugin.json 缺少必需字段: $schema")
    else:
        schema_val = manifest["$schema"]
        if not isinstance(schema_val, str):
            result.error("$schema 必须是字符串")
        elif schema_val not in PLUGIN_SCHEMAS.values():
            result.error(
                f"$schema 值不正确\n   期望之一: {', '.join(PLUGIN_SCHEMAS.values())}\n   实际: {schema_val}"
            )
        else:
            ver = _schema_version(schema_val)
            result.ok(f"$schema 值正确（规范版本 {ver}）")

    if "name" not in manifest:
        result.error("plugin.json 缺少必需字段: name")
    else:
        name_val = manifest["name"]
        if not isinstance(name_val, str) or not name_val:
            result.error("name 必须是非空字符串")
        else:
            if len(name_val) > 64:
                result.error(f"name 长度超过 64 字符: {len(name_val)}")
            if not PLUGIN_NAME_PATTERN.match(name_val):
                result.error(
                    f"name 不符合命名规则: '{name_val}'\n"
                    f"   规则: 1-64字符，小写字母/数字/连字符/点，以字母数字开头结尾，禁止连续 -- 或 .."
                )
            if name_val != root.name:
                result.error(f"name 与目录名不一致\n   name: {name_val}\n   目录名: {root.name}")
            else:
                result.ok(f"name 符合规则且与目录名一致: {name_val}")

    # 检查未知顶层字段
    # 注意：官方规范 §5.2 说 clients "report and ignore" 未知字段（非致命），
    # 但本验证器作为作者侧发布前检查，选择更严格——提前发现拼写错误和误用。
    unknown_fields = set(manifest.keys()) - ALLOWED_PLUGIN_FIELDS
    if unknown_fields:
        result.error(
            f"plugin.json 包含未知顶层字段: {', '.join(sorted(unknown_fields))}\n"
            f"   允许的字段: {', '.join(sorted(ALLOWED_PLUGIN_FIELDS))}\n"
            f"   提示: 客户端专属数据应放在 extensions 字段下（如 \"extensions\": {{\"com.acme.client\": {{...}}}}）\n"
            f"   说明: 官方运行时会忽略未知字段，但发布前检查选择严格以提前发现拼写错误"
        )
    else:
        result.ok("plugin.json 无未知顶层字段")

    # 检查 author 对象
    if "author" in manifest:
        author = manifest["author"]
        if not isinstance(author, dict):
            result.error("author 必须是对象")
        else:
            unknown_author = set(author.keys()) - ALLOWED_AUTHOR_FIELDS
            if unknown_author:
                result.error(f"author 对象包含未知字段: {', '.join(sorted(unknown_author))}")
            else:
                result.ok("author 对象字段合法")

    # JSON 类型检查（规范 §5.4: metadata fields validated by JSON types）
    if "version" in manifest and not isinstance(manifest["version"], str):
        result.error(f"plugin.json 的 version 字段必须是字符串，当前是 {type(manifest['version']).__name__}")
    elif "version" in manifest:
        import re as _re
        if not _re.match(r'^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$', manifest["version"]):
            result.warn(
                f"plugin.json 的 version '{manifest['version']}' 不符合 semver 格式\n"
                f"   建议格式: MAJOR.MINOR.PATCH（如 1.0.0）"
            )
    if "keywords" in manifest:
        kws = manifest["keywords"]
        if not isinstance(kws, list) or not all(isinstance(k, str) for k in kws):
            result.error(f"plugin.json 的 keywords 字段必须是字符串数组（string[]）")
    if "description" in manifest and not isinstance(manifest["description"], str):
        result.error(f"plugin.json 的 description 字段必须是字符串")
    if "license" in manifest and not isinstance(manifest["license"], str):
        result.error(f"plugin.json 的 license 字段必须是字符串")
    if "homepage" in manifest and not isinstance(manifest["homepage"], str):
        result.error(f"plugin.json 的 homepage 字段必须是字符串")

    # 推荐字段警告
    for field in ["version", "description", "license"]:
        if field not in manifest:
            result.warn(f"缺少推荐字段: {field}")

    # === 2. 验证 skills/ ===
    skills_dir = root / "skills"
    if skills_dir.exists():
        if not skills_dir.is_dir():
            result.error("skills 存在但不是目录")
        else:
            skill_count = 0
            for entry in sorted(skills_dir.iterdir()):
                if entry.is_dir():
                    skill_md = entry / "SKILL.md"
                    if not skill_md.exists():
                        result.error(
                            f"skills/{entry.name}/ 缺少 SKILL.md 文件\n"
                            f"   提示: 只有包含 SKILL.md 的直接子目录才会被识别为 skill"
                        )
                    else:
                        validate_skill_frontmatter(entry, result)
                        skill_count += 1
                elif entry.is_file():
                    result.warn(f"skills/ 下有文件 {entry.name}（skills 目录应只包含子目录）")
            result.ok(f"发现 {skill_count} 个 skill 目录")
    else:
        result.ok("无 skills/ 目录（纯 MCP 插件或空插件）")

    # === 3. 验证 mcp.json ===
    mcp_json_path = root / "mcp.json"
    if mcp_json_path.exists():
        if not mcp_json_path.is_file():
            result.error("mcp.json 不是常规文件")
        else:
            result.ok("mcp.json 存在")

            try:
                with open(mcp_json_path, "r", encoding="utf-8") as f:
                    mcp_config = json.load(f)
            except json.JSONDecodeError as e:
                result.error(f"mcp.json 不是有效 JSON: {e}")
                mcp_config = None

            if mcp_config is not None:
                if not isinstance(mcp_config, dict):
                    result.error("mcp.json 顶层必须是对象")
                else:
                    # 检查必需字段
                    if "$schema" not in mcp_config:
                        result.error("mcp.json 缺少必需字段: $schema")
                    else:
                        mcp_schema = mcp_config["$schema"]
                        if mcp_schema not in MCP_SCHEMAS.values():
                            result.error(
                                f"mcp.json 的 $schema 值不正确\n   期望之一: {', '.join(MCP_SCHEMAS.values())}\n   实际: {mcp_schema}"
                            )
                        else:
                            mcp_ver = _schema_version(mcp_schema)
                            result.ok(f"mcp.json 的 $schema 值正确（规范版本 {mcp_ver}）")

                    if "mcpServers" not in mcp_config:
                        result.error("mcp.json 缺少必需字段: mcpServers")
                    else:
                        servers = mcp_config["mcpServers"]
                        if not isinstance(servers, dict):
                            result.error("mcpServers 必须是对象")
                        else:
                            result.ok(f"mcpServers 包含 {len(servers)} 个服务器配置")
                            for srv_name, srv_config in servers.items():
                                validate_mcp_server(srv_name, srv_config, root, result)

                    # 检查未知顶层字段
                    unknown_mcp = set(mcp_config.keys()) - {"$schema", "mcpServers"}
                    if unknown_mcp:
                        result.error(f"mcp.json 包含未知顶层字段: {', '.join(sorted(unknown_mcp))}")

                    # 版本一致性：plugin.json 与 mcp.json 必须指向同一规范版本
                    plugin_ver = _schema_version(manifest.get("$schema", ""))
                    mcp_ver = _schema_version(mcp_config.get("$schema", ""))
                    if plugin_ver and mcp_ver and plugin_ver == mcp_ver:
                        result.ok(f"plugin.json 与 mcp.json 的规范版本一致（均为 {plugin_ver}）")
                    elif plugin_ver and mcp_ver:
                        result.error(
                            f"plugin.json 与 mcp.json 的规范版本不一致\n"
                            f"   plugin.json: {plugin_ver}\n   mcp.json:     {mcp_ver}"
                        )
    else:
        result.ok("无 mcp.json（纯 Skills 插件）")

    # === 4. 检查路径安全 ===
    check_path_safety(root, result)

    return result


def validate_mcp_server(name: str, config, root: Path, result: ValidationResult):
    """验证单个 MCP 服务器配置"""
    if not isinstance(config, dict):
        result.error(f"MCP 服务器 '{name}' 配置不是对象")
        return

    if "type" not in config:
        result.error(f"MCP 服务器 '{name}' 缺少必需字段: type")
        return

    srv_type = config["type"]
    if srv_type not in MCP_TRANSPORTS:
        result.error(
            f"MCP 服务器 '{name}' 的 type 不支持: '{srv_type}'\n"
            f"   支持的类型: {', '.join(sorted(MCP_TRANSPORTS))}"
        )
        return

    if srv_type == "stdio":
        validate_stdio_server(name, config, root, result)
    elif srv_type in ("streamable-http", "sse"):
        validate_http_server(name, config, result)


def validate_stdio_server(name: str, config: dict, root: Path, result: ValidationResult):
    """验证 stdio 类型 MCP 服务器"""
    if "command" not in config:
        result.error(f"stdio 服务器 '{name}' 缺少必需字段: command")
        return

    command = config["command"]
    if not isinstance(command, str) or not command:
        result.error(f"stdio 服务器 '{name}' 的 command 必须是非空字符串")
        return

    if " " in command.strip():
        result.error(
            f"stdio 服务器 '{name}' 的 command 包含空格\n"
            f"   值: '{command}'\n"
            f"   提示: command 必须是单个可执行 token，参数应放在 args 数组中"
        )

    # 规范 §7.2.1: command 必须是 bare executable name（不含路径分隔符）
    # 或以 ./ 开头的 plugin-relative path。其他含 / 的形式（如 ../xxx、/abs/path）非法。
    if "/" in command and not command.startswith("./"):
        result.error(
            f"stdio 服务器 '{name}' 的 command 含路径但未以 ./ 开头\n"
            f"   值: '{command}'\n"
            f"   提示: 插件内可执行文件必须以 ./ 开头（如 ./bin/server）；"
            f"系统命令用 bare name（如 python3、node），不要写绝对路径或 ../"
        )

    # 检查插件相对路径
    if command.startswith("./"):
        cmd_path = (root / command[2:]).resolve()
        if not str(cmd_path).startswith(str(root)):
            result.error(f"stdio 服务器 '{name}' 的 command 路径逃逸出插件根目录")
        elif not cmd_path.exists():
            result.warn(
                f"stdio 服务器 '{name}' 的 command 指向的文件不存在\n"
                f"   路径: {command}（解析为: {cmd_path}）"
            )

    # 检查 args
    if "args" in config:
        args = config["args"]
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            result.error(f"stdio 服务器 '{name}' 的 args 必须是字符串数组")
        else:
            # 检查 ${PLUGIN_ROOT} 引用
            for i, arg in enumerate(args):
                check_plugin_root_refs(arg, root, f"stdio 服务器 '{name}' args[{i}]", result)

    # 检查 env
    if "env" in config:
        env = config["env"]
        if not isinstance(env, dict):
            result.error(f"stdio 服务器 '{name}' 的 env 必须是对象")
        else:
            for key in env:
                if key in RESERVED_ENV_VARS:
                    result.error(
                        f"stdio 服务器 '{name}' 的 env 包含保留变量名: {key}\n"
                        f"   提示: PLUGIN_ROOT 和 PLUGIN_DATA 由客户端注入，不能在配置中设置"
                    )
                if not isinstance(env[key], str):
                    result.error(f"stdio 服务器 '{name}' 的 env['{key}'] 必须是字符串")
                else:
                    check_plugin_root_refs(env[key], root, f"stdio 服务器 '{name}' env['{key}']", result)

    # 检查 cwd
    if "cwd" in config:
        cwd = config["cwd"]
        if not isinstance(cwd, str):
            result.error(f"stdio 服务器 '{name}' 的 cwd 必须是字符串")
        else:
            valid_cwd = (
                cwd.startswith("./")
                or cwd == "${PLUGIN_ROOT}"
                or cwd.startswith("${PLUGIN_ROOT}/")
                or cwd == "${PLUGIN_DATA}"
                or cwd.startswith("${PLUGIN_DATA}/")
            )
            if not valid_cwd:
                result.error(
                    f"stdio 服务器 '{name}' 的 cwd 格式不合法\n"
                    f"   值: '{cwd}'\n"
                    f"   允许的形式: ./相对路径, ${{PLUGIN_ROOT}}, ${{PLUGIN_ROOT}}/..., ${{PLUGIN_DATA}}, ${{PLUGIN_DATA}}/..."
                )
            elif ".." in cwd.split("/"):
                result.error(
                    f"stdio 服务器 '{name}' 的 cwd 包含路径段 '..'（逃逸出插件目录）\n"
                    f"   值: '{cwd}'"
                )


def validate_http_server(name: str, config: dict, result: ValidationResult):
    """验证 streamable-http / sse 类型 MCP 服务器"""
    if "url" not in config:
        result.error(f"HTTP 服务器 '{name}' 缺少必需字段: url")
        return

    url = config["url"]
    if not isinstance(url, str) or not url:
        result.error(f"HTTP 服务器 '{name}' 的 url 必须是非空字符串")
        return

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            result.error(f"HTTP 服务器 '{name}' 的 url 必须是 http 或 https")
        if not parsed.netloc:
            result.error(f"HTTP 服务器 '{name}' 的 url 缺少主机名")
        if parsed.username or parsed.password:
            result.error(f"HTTP 服务器 '{name}' 的 url 包含用户信息（user:pass@）")
        if parsed.fragment:
            result.error(f"HTTP 服务器 '{name}' 的 url 包含 fragment（#...）")

        host = parsed.hostname or ""
        is_localhost = (
            host == "localhost"
            or host.startswith("127.")
            or host == "::1"
            or host == "[::1]"
        )
        if parsed.scheme == "http" and not is_localhost:
            result.error(f"HTTP 服务器 '{name}' 的非 localhost 端点必须使用 HTTPS\n   URL: {url}")
    except Exception:
        result.error(f"HTTP 服务器 '{name}' 的 url 无法解析: {url}")

    # 检查 headers
    if "headers" in config:
        headers = config["headers"]
        if not isinstance(headers, dict):
            result.error(f"HTTP 服务器 '{name}' 的 headers 必须是对象")
        else:
            seen = {}
            secret_patterns = ["authorization", "api-key", "apikey", "token", "secret", "x-api-key"]
            for key in headers:
                lower_key = key.lower()
                if lower_key in seen:
                    result.error(
                        f"HTTP 服务器 '{name}' 的 headers 包含重复头名（不区分大小写）\n"
                        f"   '{seen[lower_key]}' 和 '{key}'"
                    )
                seen[lower_key] = key
                if not isinstance(headers[key], str):
                    result.error(f"HTTP 服务器 '{name}' 的 headers['{key}'] 必须是字符串")
                if any(p in lower_key for p in secret_patterns):
                    result.warn(
                        f"HTTP 服务器 '{name}' 的 headers 中可能包含凭据: '{key}'\n"
                        f"   提示: headers 是公开的包数据，不应嵌入密钥。凭据应由客户端的授权机制管理。"
                    )


def check_path_safety(root: Path, result: ValidationResult):
    """检查插件目录中是否有逃逸出根目录的符号链接"""
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            for name in dirnames + filenames:
                full_path = Path(dirpath) / name
                if full_path.is_symlink():
                    resolved = full_path.resolve()
                    if not str(resolved).startswith(str(root)):
                        result.error(
                            f"发现逃逸出插件根目录的符号链接\n"
                            f"   链接: {full_path.relative_to(root)}\n"
                            f"   目标: {resolved}"
                        )
    except PermissionError:
        result.warn("路径安全检查时遇到权限错误，部分目录未检查")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Agent Plugins 规范验证器（支持 1.0.0 与 1.1.0 working draft）",
        epilog="示例: python3 validate_plugin.py ./my-plugin",
    )
    parser.add_argument("plugin_dir", help="插件目录路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    args = parser.parse_args()

    result = validate_plugin(args.plugin_dir)
    if args.json:
        print(result.to_json() if hasattr(result, "to_json") else json.dumps({
            "success": result.success,
            "errors": [e.message for e in result.errors],
            "warnings": [w.message for w in result.warnings],
        }, ensure_ascii=False, indent=2))
    else:
        print(result.report())
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
