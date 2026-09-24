#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="验证 MCP 工具契约：检查工具分类、副作用、幂等性、审计要求等高风险工具约束")
    parser.add_argument("plugin_root", help="插件根目录路径")
    parser.add_argument("contract_json", help="工具契约 JSON 文件路径")
    args = parser.parse_args()
    root=Path(args.plugin_root).resolve(); data=json.loads(Path(args.contract_json).read_text(encoding='utf-8')); errors=[]
    tools=data.get('tools')
    if not isinstance(tools,list) or not tools: errors.append('contract.tools must be a non-empty array')
    seen=set()
    for t in tools or []:
        name=t.get('name'); cls=t.get('classification');
        if not isinstance(name,str) or not name: errors.append('tool name is required')
        if name in seen: errors.append(f'duplicate tool: {name}')
        seen.add(name)
        if cls not in {'read-only','prepare','reversible-write','irreversible-write','destructive-admin'}: errors.append(f'{name}: invalid classification')
        if cls in {'irreversible-write','destructive-admin'}:
            if t.get('side_effects') is not True: errors.append(f'{name}: high-risk tool must declare side_effects=true')
            if t.get('requires_user_confirmation') is not True: errors.append(f'{name}: high-risk tool must require confirmation')
            if not (t.get('idempotency') or {}).get('required'): errors.append(f'{name}: high-risk tool must require idempotency')
            if not t.get('audit'): errors.append(f'{name}: high-risk tool must declare audit')
        if cls=='prepare' and t.get('side_effects') is True: errors.append(f'{name}: prepare must not have side effects')
        if not t.get('errors'): errors.append(f'{name}: errors must be declared')
    if not (root/'mcp.json').is_file(): errors.append('plugin has no mcp.json')
    result={'status':'PASS' if not errors else 'BLOCKED','tool_count':len(tools or []),'errors':errors}
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 1 if errors else 0
if __name__=='__main__': raise SystemExit(main())
