#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
RULES=[
 ('schema|manifest|name|plugin.json','structure','Fix manifest fields, canonical schema, name or closed-set violations. Re-run validate_plugin.py.'),
 ('skill|frontmatter|trigger|route|near-miss','skill-routing','Revise Skill metadata, ROUTE preflight and positive/negative trigger cases. Re-run selection and edge evaluations.'),
 ('mcp|tool|schema|transport|handshake','mcp-contract','Fix MCP transport, command, tool contract, structured output or handshake. Re-run MCP client smoke tests.'),
 ('timeout|latency|concurrency|limit|pagination','performance','Add bounded results, pagination, timeout, retry and concurrency tests; do not claim capacity before evidence.'),
 ('secret|credential|token|symlink|escape|shell|header','security','Block the artifact, remove secret or escape path, and add a negative fixture before retrying.'),
 ('client|compatible|installation|discovery','client-conformance','Collect a real client log or mark capability unknown; never convert not-tested to pass.'),
 ('license|provenance|hash|reproducible|build','release','Repair provenance, license, deterministic build, file manifest or SHA256 evidence.'),
]
def main():
    parser = argparse.ArgumentParser(description="根据评估报告生成修复计划：按7个类别分类，标注P0/P1优先级")
    parser.add_argument("input_report", help="输入的评估报告 JSON 文件")
    parser.add_argument("output_plan", help="输出的修复计划 JSON 文件")
    args = parser.parse_args()
    inp=Path(args.input_report); out=Path(args.output_plan); data=json.loads(inp.read_text(encoding='utf-8')); text=json.dumps(data,ensure_ascii=False).lower(); tasks=[]; covered=set()
    for pattern,category,action in RULES:
        import re
        hits=re.findall(pattern,text)
        if hits and category not in covered: tasks.append({'category':category,'evidence_terms':sorted(set(hits)),'priority':'P0' if category in {'structure','security','mcp-contract'} else 'P1','next_action':action}); covered.add(category)
    result={'source':str(inp),'status':'repair-required' if tasks else 'no-known-repair','tasks':tasks,'unclassified_failures':[]}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
