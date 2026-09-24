#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def main():
    if len(sys.argv)!=2: print('usage: simulate_discovery.py <plugin-root>',file=sys.stderr); return 2
    root=Path(sys.argv[1]).resolve(); discovered={'skills':[],'invalid_skills':[],'mcp_servers':[],'invalid_mcp_servers':[]}
    skills=root/'skills'
    if skills.is_dir():
        for child in sorted(skills.iterdir()):
            if not child.is_dir(): continue
            md=child/'SKILL.md'
            if md.is_file() and not md.is_symlink(): discovered['skills'].append(child.name)
            else: discovered['invalid_skills'].append(child.name)
    mcp=root/'mcp.json'
    if mcp.is_file():
        try: data=json.loads(mcp.read_text()); servers=data.get('mcpServers',{})
        except Exception: servers={}
        for name,entry in servers.items():
            if isinstance(entry,dict) and entry.get('type') in {'stdio','streamable-http','sse'}: discovered['mcp_servers'].append(name)
            else: discovered['invalid_mcp_servers'].append(name)
    print(json.dumps(discovered,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
