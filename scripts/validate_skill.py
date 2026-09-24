#!/usr/bin/env python3
"""
Agent Skill 验证器

验证逻辑来源：
  - 核心验证规则移植自 agentskills.io 官方 skills-ref 工具
    (https://github.com/agentskills/agentskills/tree/main/skills-ref)
  - 增强检查（body 长度、目录结构、脚本可执行性、触发场景提示）
    为 agent-plugin-creator 自包含实现，不依赖官方工具

用法:
    python3 validate_skill.py <skill目录路径>

官方验证检查项 (skills-ref 对齐):
    - SKILL.md 存在
    - frontmatter 字段白名单: name, description, license,
      allowed-tools, metadata, compatibility
    - name: 非空、<=64字符、小写、不以连字符开头/结尾、
      无连续连字符、仅 Unicode 字母+数字+连字符、与目录名一致
    - description: 非空、<=1024字符
    - compatibility: 字符串、<=500字符

增强检查项:
    - body 非空且 <=500 行
    - scripts/references/assets 目录结构合理性
    - 脚本可执行权限
    - description 触发场景提示
"""
import os
import sys
import unicodedata
from pathlib import Path

# ============================================================
# 官方验证常量 (对齐 skills-ref)
# ============================================================
MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500

# 官方允许的 frontmatter 字段
ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}


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
        lines.append("Agent Skill 验证报告")
        lines.append("核心规则对齐 agentskills.io 官方 skills-ref")
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
            lines.append("结论: Skill 验证通过")
        else:
            lines.append(f"结论: 验证失败，存在 {len(self.errors)} 个错误")
        lines.append("=" * 60)
        return "\n".join(lines)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 YAML frontmatter（简单解析，不依赖 PyYAML）"""
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


# ============================================================
# 官方验证函数 (移植自 skills-ref validator.py)
# ============================================================

def _validate_name_official(name: str, skill_dir: Path) -> list[str]:
    """官方 name 验证逻辑 (移植自 skills-ref)

    支持 i18n 字符 (Unicode 字母)，使用 NFKC 规范化。
    """
    errors = []
    if not name or not isinstance(name, str) or not name.strip():
        errors.append("Field 'name' must be a non-empty string")
        return errors
    name = unicodedata.normalize("NFKC", name.strip())
    if len(name) > MAX_SKILL_NAME_LENGTH:
        errors.append(
            f"Skill name '{name}' exceeds {MAX_SKILL_NAME_LENGTH} character limit "
            f"({len(name)} chars)"
        )
    if name != name.lower():
        errors.append(f"Skill name '{name}' must be lowercase")
    if name.startswith("-") or name.endswith("-"):
        errors.append("Skill name cannot start or end with a hyphen")
    if "--" in name:
        errors.append("Skill name cannot contain consecutive hyphens")
    if not all(c.isalnum() or c == "-" for c in name):
        errors.append(
            f"Skill name '{name}' contains invalid characters. "
            "Only letters, digits, and hyphens are allowed."
        )
    if skill_dir:
        dir_name = unicodedata.normalize("NFKC", skill_dir.name)
        if dir_name != name:
            errors.append(
                f"Directory name '{skill_dir.name}' must match skill name '{name}'"
            )
    return errors


def _validate_description_official(description: str) -> list[str]:
    """官方 description 验证逻辑 (移植自 skills-ref)"""
    errors = []
    if not description or not isinstance(description, str) or not description.strip():
        errors.append("Field 'description' must be a non-empty string")
        return errors
    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"Description exceeds {MAX_DESCRIPTION_LENGTH} character limit "
            f"({len(description)} chars)"
        )
    return errors


def _validate_compatibility_official(compatibility: str) -> list[str]:
    """官方 compatibility 验证逻辑 (移植自 skills-ref)"""
    errors = []
    if not isinstance(compatibility, str):
        errors.append("Field 'compatibility' must be a string")
        return errors
    if len(compatibility) > MAX_COMPATIBILITY_LENGTH:
        errors.append(
            f"Compatibility exceeds {MAX_COMPATIBILITY_LENGTH} character limit "
            f"({len(compatibility)} chars)"
        )
    return errors


def _validate_metadata_fields_official(metadata: dict) -> list[str]:
    """官方字段白名单验证 (移植自 skills-ref)"""
    errors = []
    extra_fields = set(metadata.keys()) - ALLOWED_FIELDS
    if extra_fields:
        errors.append(
            f"Unexpected fields in frontmatter: {', '.join(sorted(extra_fields))}. "
            f"Only {sorted(ALLOWED_FIELDS)} are allowed."
        )
    return errors


def validate_metadata_official(metadata: dict, skill_dir: Path = None) -> list[str]:
    """官方核心验证函数 (移植自 skills-ref validate_metadata)

    返回错误列表，空列表表示验证通过。
    """
    errors = []
    errors.extend(_validate_metadata_fields_official(metadata))
    if "name" not in metadata:
        errors.append("Missing required field in frontmatter: name")
    else:
        errors.extend(_validate_name_official(metadata["name"], skill_dir))
    if "description" not in metadata:
        errors.append("Missing required field in frontmatter: description")
    else:
        errors.extend(_validate_description_official(metadata["description"]))
    if "compatibility" in metadata:
        errors.extend(_validate_compatibility_official(metadata["compatibility"]))
    return errors


# ============================================================
# 增强验证 (agent-plugin-creator 自包含实现)
# ============================================================

def _validate_enhancements(skill_dir: Path, fm: dict, body: str, result: ValidationResult):
    """增强检查：body 长度、目录结构、脚本可执行性、触发场景提示"""
    # body 检查
    if not body.strip():
        result.warn("SKILL.md body 为空，建议添加工作流指令")
    else:
        body_lines = body.strip().split("\n")
        if len(body_lines) > 500:
            result.warn(
                f"SKILL.md body 超过 500 行 ({len(body_lines)} 行)\n"
                "   建议: 将详细参考材料移到 references/ 目录"
            )
        else:
            result.ok(f"SKILL.md body 长度合理 ({len(body_lines)} 行)")

    # description 触发场景提示
    if "description" in fm and isinstance(fm["description"], str):
        desc = fm["description"]
        desc_lower = desc.lower()
        has_trigger = any(
            kw in desc_lower
            for kw in ["use when", "when ", "if ", "for ", "trigger", "mentioned"]
        )
        if not has_trigger and len(desc) < 50:
            result.warn(
                "description 可能缺少触发场景说明\n"
                "   提示: description 应同时描述做什么和什么时候用，"
                "这是 agent 决定是否激活 skill 的依据"
            )

    # 目录结构检查
    for subdir in ["scripts", "references", "assets"]:
        d = skill_dir / subdir
        if d.exists() and not d.is_dir():
            result.error(f"{subdir}/ 存在但不是目录")

    # 脚本可执行性检查
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists() and scripts_dir.is_dir():
        for script in scripts_dir.iterdir():
            if script.is_file() and script.suffix in {".py", ".sh", ".js"}:
                if not os.access(script, os.X_OK):
                    result.warn(f"脚本 {script.name} 没有可执行权限（建议 chmod +x）")

    result.ok("增强检查完成（body 长度、目录结构、脚本权限、触发场景）")


# ============================================================
# 主验证入口
# ============================================================

def validate_skill(skill_path: str) -> ValidationResult:
    result = ValidationResult()
    skill_dir = Path(skill_path).resolve()

    if not skill_dir.exists():
        result.error(f"Skill 目录不存在: {skill_dir}")
        return result
    if not skill_dir.is_dir():
        result.error(f"路径不是目录: {skill_dir}")
        return result
    result.ok(f"Skill 目录存在: {skill_dir}")

    # 检查 SKILL.md
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result.error("缺少必需文件: SKILL.md")
        return result
    if not skill_md.is_file():
        result.error("SKILL.md 不是常规文件")
        return result
    result.ok("SKILL.md 存在")

    # 读取并解析
    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        result.error(f"无法读取 SKILL.md: {e}")
        return result

    if not content.startswith("---"):
        result.error("SKILL.md 必须以 YAML frontmatter 开头（以 --- 开始）")
        return result

    fm, body = parse_frontmatter(content)
    if not fm:
        result.error("无法解析 frontmatter 或 frontmatter 为空")
        return result
    result.ok("SKILL.md 包含有效的 YAML frontmatter")

    # ---- 官方验证 (对齐 skills-ref) ----
    official_errors = validate_metadata_official(fm, skill_dir)
    if official_errors:
        for e in official_errors:
            result.error(f"[官方规则] {e}")
    else:
        name = fm.get("name", "")
        result.ok(f"[官方规则] frontmatter 验证通过 (name={name})")

    # ---- 增强验证 ----
    _validate_enhancements(skill_dir, fm, body, result)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Agent Skill 规范验证器（对齐 agentskills.io 官方 skills-ref）",
        epilog="示例: python3 validate_skill.py ./my-skill",
    )
    parser.add_argument("skill_dir", help="Skill 目录路径")
    args = parser.parse_args()
    result = validate_skill(args.skill_dir)
    print(result.report())
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
