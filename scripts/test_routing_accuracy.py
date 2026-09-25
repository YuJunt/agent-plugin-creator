#!/usr/bin/env python3
"""
Agent Plugin Creator 路由触发专项测试

测试技能的 description 触发准确性：
- should-trigger: 应该触发本技能的场景
- should-not-trigger: 不应该触发的场景
- near-miss: 边界场景（容易误触发的）

用法:
    python3 scripts/test_routing_accuracy.py [--json]
"""
import argparse
import json
import sys
from pathlib import Path

# 应该触发的场景（用户提到这些时，应该使用 agent-plugin-creator）
SHOULD_TRIGGER = [
    {
        "prompt": "帮我创建一个 Agent Plugin",
        "keywords": ["创建", "Agent Plugin", "插件"],
        "reason": "明确要求创建 Agent Plugin"
    },
    {
        "prompt": "把这个 skill 和 MCP 服务器打包成可分发的插件",
        "keywords": ["打包", "skill", "MCP", "插件"],
        "reason": "要求将 Skill + MCP 打包成插件"
    },
    {
        "prompt": "为 Cursor 和 Claude Code 做插件适配",
        "keywords": ["Cursor", "Claude", "插件", "适配"],
        "reason": "多客户端插件适配"
    },
    {
        "prompt": "生成一个可运行的 MCP 服务器代码",
        "keywords": ["MCP", "服务器", "生成"],
        "reason": "MCP 服务器代码生成"
    },
    {
        "prompt": "插件安全审计",
        "keywords": ["插件", "安全审计"],
        "reason": "插件安全审计"
    },
    {
        "prompt": "把旧的 Claude 插件迁移到 Agent Plugins 标准",
        "keywords": ["迁移", "插件", "Agent Plugins"],
        "reason": "插件格式迁移"
    },
    {
        "prompt": "验证这个插件是否符合规范",
        "keywords": ["验证", "插件", "规范"],
        "reason": "插件规范验证"
    },
    {
        "prompt": "agent plugin creator",
        "keywords": ["agent plugin", "creator"],
        "reason": "英文触发词"
    },
    {
        "prompt": "portable plugin package",
        "keywords": ["portable", "plugin", "package"],
        "reason": "英文可移植插件打包"
    },
    {
        "prompt": "MCP server stdio transport",
        "keywords": ["MCP", "server", "stdio"],
        "reason": "MCP 服务器传输配置"
    },
]

# 不应该触发的场景（这些应该用其他技能）
SHOULD_NOT_TRIGGER = [
    {
        "prompt": "帮我写一篇文章",
        "keywords": ["写文章"],
        "reason": "内容创作，与插件无关"
    },
    {
        "prompt": "分析一下这只股票",
        "keywords": ["股票", "分析"],
        "reason": "金融分析，与插件无关"
    },
    {
        "prompt": "今天天气怎么样",
        "keywords": ["天气"],
        "reason": "日常查询，与插件无关"
    },
    {
        "prompt": "帮我翻译这段英文",
        "keywords": ["翻译"],
        "reason": "翻译任务，与插件无关"
    },
    {
        "prompt": "创建一个飞书文档",
        "keywords": ["飞书", "文档"],
        "reason": "飞书文档操作，应该用 lark-doc 技能"
    },
    {
        "prompt": "做一个 PPT",
        "keywords": ["PPT", "幻灯片"],
        "reason": "演示文稿，应该用 ppt 技能"
    },
    {
        "prompt": "处理这个 Excel 文件",
        "keywords": ["Excel", "表格"],
        "reason": "表格处理，应该用 sheet 技能"
    },
    {
        "prompt": "生成一张图片",
        "keywords": ["图片", "生成"],
        "reason": "图片生成，应该用 creative-design 技能"
    },
]

# 边界场景（容易误触发的，需要仔细判断）
NEAR_MISS = [
    {
        "prompt": "创建一个技能（skill）",
        "should_trigger": False,
        "reason": "只创建单个 Skill，应该用 skill-creator，不是插件创建"
    },
    {
        "prompt": "优化这个技能的 description",
        "should_trigger": False,
        "reason": "技能优化，应该用 skill-creator"
    },
    {
        "prompt": "这个 MCP 服务器连不上，帮我调试",
        "should_trigger": False,
        "reason": "MCP 调试，不是创建插件"
    },
    {
        "prompt": "帮我写一个 Python 脚本",
        "should_trigger": False,
        "reason": "通用编程，与插件无关"
    },
    {
        "prompt": "创建一个包含 MCP 的插件",
        "should_trigger": True,
        "reason": "明确要求创建包含 MCP 的插件"
    },
    {
        "prompt": "把插件反向封装成技能",
        "should_trigger": True,
        "reason": "反向封装是本技能的核心功能"
    },
    {
        "prompt": "插件打包成 zip",
        "should_trigger": True,
        "reason": "插件打包是本技能的功能"
    },
]


def analyze_prompt(prompt: str, skill_description: str) -> dict:
    """简单的关键词匹配分析（实际触发由平台 LLM 判断，这里做基线测试）"""
    # 提取技能 description 中的关键词
    trigger_keywords = [
        "agent plugin", "插件", "mcp", "portable", "可移植",
        "skill", "技能", "create", "创建", "package", "打包",
        "validate", "验证", "audit", "审计", "migrate", "迁移",
        "client", "客户端", "adapter", "适配"
    ]

    prompt_lower = prompt.lower()
    matched = [kw for kw in trigger_keywords if kw in prompt_lower]

    # 简单判断：匹配到 2 个以上关键词认为应该触发
    should_trigger = len(matched) >= 2

    return {
        "prompt": prompt,
        "matched_keywords": matched,
        "match_count": len(matched),
        "should_trigger": should_trigger,
    }


def main():
    parser = argparse.ArgumentParser(description="路由触发准确性测试")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
    skill_description = ""
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
        # 提取 frontmatter 的 description
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                frontmatter = content[3:end]
                for line in frontmatter.split("\n"):
                    if line.strip().startswith("description:"):
                        skill_description = line.split(":", 1)[1].strip()
                        break

    results = {
        "should_trigger": [],
        "should_not_trigger": [],
        "near_miss": [],
    }

    # 测试 should-trigger
    st_passed = 0
    for case in SHOULD_TRIGGER:
        analysis = analyze_prompt(case["prompt"], skill_description)
        passed = analysis["should_trigger"]
        if passed:
            st_passed += 1
        results["should_trigger"].append({
            **case,
            "analysis": analysis,
            "passed": passed,
        })

    # 测试 should-not-trigger
    snt_passed = 0
    for case in SHOULD_NOT_TRIGGER:
        analysis = analyze_prompt(case["prompt"], skill_description)
        # 不应该触发的，should_trigger 应该为 False
        passed = not analysis["should_trigger"]
        if passed:
            snt_passed += 1
        results["should_not_trigger"].append({
            **case,
            "analysis": analysis,
            "passed": passed,
        })

    # 测试 near-miss
    nm_passed = 0
    for case in NEAR_MISS:
        analysis = analyze_prompt(case["prompt"], skill_description)
        passed = analysis["should_trigger"] == case["should_trigger"]
        if passed:
            nm_passed += 1
        results["near_miss"].append({
            **case,
            "analysis": analysis,
            "passed": passed,
        })

    total = len(SHOULD_TRIGGER) + len(SHOULD_NOT_TRIGGER) + len(NEAR_MISS)
    passed_total = st_passed + snt_passed + nm_passed
    accuracy = passed_total / total if total > 0 else 0

    summary = {
        "total_cases": total,
        "passed": passed_total,
        "failed": total - passed_total,
        "accuracy": round(accuracy * 100, 1),
        "should_trigger": {"total": len(SHOULD_TRIGGER), "passed": st_passed},
        "should_not_trigger": {"total": len(SHOULD_NOT_TRIGGER), "passed": snt_passed},
        "near_miss": {"total": len(NEAR_MISS), "passed": nm_passed},
    }

    if args.json:
        print(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("路由触发准确性测试")
        print("=" * 60)
        print()
        print(f"总用例: {total}")
        print(f"通过: {passed_total}")
        print(f"失败: {total - passed_total}")
        print(f"准确率: {accuracy * 100:.1f}%")
        print()
        print(f"  应该触发: {st_passed}/{len(SHOULD_TRIGGER)} 通过")
        print(f"  不应触发: {snt_passed}/{len(SHOULD_NOT_TRIGGER)} 通过")
        print(f"  边界场景: {nm_passed}/{len(NEAR_MISS)} 通过")
        print()

        if passed_total < total:
            print("失败用例:")
            print("-" * 60)
            for category, cases in results.items():
                for case in cases:
                    if not case["passed"]:
                        print(f"  [{category}] {case['prompt']}")
                        print(f"    原因: {case['reason']}")
                        print(f"    匹配关键词: {case['analysis']['matched_keywords']}")
                        print()

        print("=" * 60)
        if accuracy >= 0.9:
            print("✅ 触发准确性优秀")
        elif accuracy >= 0.8:
            print("⚠️  触发准确性良好，建议优化")
        else:
            print("❌ 触发准确性不足，需要优化 description")
        print("=" * 60)

    return 0 if accuracy >= 0.8 else 1


if __name__ == "__main__":
    sys.exit(main())
