#!/usr/bin/env python3
"""
国际化框架工具

为插件生成多语言支持，自动提取和管理翻译字符串。

用法:
    python3 scripts/i18n_helper.py init --plugin ./my-plugin --locales zh,en,ja
    python3 scripts/i18n_helper.py extract --plugin ./my-plugin
    python3 scripts/i18n_helper.py translate --plugin ./my-plugin --locale en
    python3 scripts/i18n_helper.py status --plugin ./my-plugin
    python3 scripts/i18n_helper.py --json
"""
import argparse
import json
import re
import sys
from pathlib import Path


def init_i18n(plugin_dir: Path, locales: list) -> dict:
    """初始化国际化支持"""
    i18n_dir = plugin_dir / "i18n"
    i18n_dir.mkdir(exist_ok=True)

    # 创建配置文件
    config = {
        "default_locale": "en",
        "supported_locales": locales,
        "fallback": "en",
        "directory": "i18n",
    }
    (i18n_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 为每个语言创建翻译文件
    created = []
    for locale in locales:
        locale_file = i18n_dir / f"{locale}.json"
        if not locale_file.exists():
            locale_file.write_text("{}\n", encoding="utf-8")
            created.append(str(locale_file.relative_to(plugin_dir)))

    return {
        "plugin": plugin_dir.name,
        "locales": locales,
        "created": created,
        "config": str((i18n_dir / "config.json").relative_to(plugin_dir)),
    }


def extract_strings(plugin_dir: Path) -> dict:
    """从插件代码中提取可翻译字符串"""
    strings = {}
    patterns = [
        # Python: _("string") 或 gettext("string")
        (r'_\s*\(\s*["\']([^"\']+)["\']\s*\)', "python"),
        (r'gettext\s*\(\s*["\']([^"\']+)["\']\s*\)', "python"),
        # JavaScript/TypeScript: t("string") 或 i18n.t("string")
        (r'\bt\s*\(\s*["\']([^"\']+)["\']\s*\)', "javascript"),
        (r'i18n\.t\s*\(\s*["\']([^"\']+)["\']\s*\)', "javascript"),
    ]

    for f in plugin_dir.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".ts") and "__pycache__" not in str(f):
            try:
                content = f.read_text(encoding="utf-8")
                rel_path = str(f.relative_to(plugin_dir))
                for pattern, lang in patterns:
                    for match in re.finditer(pattern, content):
                        text = match.group(1)
                        if text not in strings:
                            strings[text] = []
                        strings[text].append({"file": rel_path, "language": lang})
            except Exception:
                pass

    # 更新翻译文件
    i18n_dir = plugin_dir / "i18n"
    if i18n_dir.exists():
        for locale_file in i18n_dir.glob("*.json"):
            if locale_file.name == "config.json":
                continue
            try:
                translations = json.loads(locale_file.read_text(encoding="utf-8"))
                for text in strings:
                    if text not in translations:
                        translations[text] = ""  # 空翻译待填充
                locale_file.write_text(
                    json.dumps(translations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            except Exception:
                pass

    return {
        "plugin": plugin_dir.name,
        "total_strings": len(strings),
        "strings": {k: len(v) for k, v in strings.items()},
        "files_scanned": len(set(item["file"] for items in strings.values() for item in items)),
    }


def check_translation_status(plugin_dir: Path) -> dict:
    """检查翻译状态"""
    i18n_dir = plugin_dir / "i18n"
    if not i18n_dir.exists():
        return {"error": "i18n 目录不存在，请先运行 init"}

    result = {
        "plugin": plugin_dir.name,
        "locales": {},
        "overall_completion": 0,
    }

    all_strings = set()
    locale_stats = {}

    for locale_file in sorted(i18n_dir.glob("*.json")):
        if locale_file.name == "config.json":
            continue
        locale = locale_file.stem
        try:
            translations = json.loads(locale_file.read_text(encoding="utf-8"))
            total = len(translations)
            translated = sum(1 for v in translations.values() if v)
            completion = round(translated / total * 100, 1) if total > 0 else 0

            locale_stats[locale] = {
                "total": total,
                "translated": translated,
                "missing": total - translated,
                "completion": completion,
            }
            all_strings.update(translations.keys())
        except Exception:
            pass

    result["locales"] = locale_stats
    if locale_stats:
        result["overall_completion"] = round(
            sum(s["completion"] for s in locale_stats.values()) / len(locale_stats), 1
        )
    result["total_unique_strings"] = len(all_strings)

    return result


def generate_translation_template(plugin_dir: Path, output_file: Path) -> dict:
    """生成翻译模板"""
    i18n_dir = plugin_dir / "i18n"
    if not i18n_dir.exists():
        return {"error": "i18n 目录不存在"}

    # 合并所有语言的 key
    all_keys = set()
    for locale_file in i18n_dir.glob("*.json"):
        if locale_file.name == "config.json":
            continue
        try:
            translations = json.loads(locale_file.read_text(encoding="utf-8"))
            all_keys.update(translations.keys())
        except Exception:
            pass

    template = {key: "" for key in sorted(all_keys)}
    output_file.write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return {
        "template": str(output_file),
        "total_keys": len(all_keys),
    }


def main():
    parser = argparse.ArgumentParser(description="国际化框架工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # init
    init_parser = subparsers.add_parser("init", help="初始化国际化支持")
    init_parser.add_argument("--plugin", required=True, help="插件目录")
    init_parser.add_argument("--locales", default="en,zh", help="支持的语言（逗号分隔）")

    # extract
    extract_parser = subparsers.add_parser("extract", help="提取可翻译字符串")
    extract_parser.add_argument("--plugin", required=True, help="插件目录")

    # status
    status_parser = subparsers.add_parser("status", help="检查翻译状态")
    status_parser.add_argument("--plugin", required=True, help="插件目录")

    # template
    template_parser = subparsers.add_parser("template", help="生成翻译模板")
    template_parser.add_argument("--plugin", required=True, help="插件目录")
    template_parser.add_argument("--output", required=True, help="模板输出文件")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    plugin_dir = Path(args.plugin).resolve()

    if args.command == "init":
        locales = [l.strip() for l in args.locales.split(",")]
        result = init_i18n(plugin_dir, locales)
    elif args.command == "extract":
        result = extract_strings(plugin_dir)
    elif args.command == "status":
        result = check_translation_status(plugin_dir)
    elif args.command == "template":
        result = generate_translation_template(plugin_dir, Path(args.output))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
