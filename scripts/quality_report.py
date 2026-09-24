#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def gate(name, status, evidence): return {"gate":name,"status":status,"evidence":evidence}

def main():
    parser = argparse.ArgumentParser(description="生成插件质量报告：8大门禁检查（业务契约/skill质量/MCP质量/运行时/密钥等）")
    parser.add_argument("plugin_root", help="插件根目录路径")
    args = parser.parse_args()
    root=Path(args.plugin_root).resolve(); gates=[]
    gates.append(gate('business-contract','passed' if (root/'README.md').exists() else 'warning','README.md present' if (root/'README.md').exists() else 'missing README.md'))
    skills=list((root/'skills').glob('*/SKILL.md')) if (root/'skills').is_dir() else []
    gates.append(gate('skill-quality','passed' if skills else 'blocked',f'{len(skills)} immediate-child Skill(s) found'))
    mcp=root/'mcp.json'
    if mcp.exists():
        has_eval=any((root/'evals').glob('*')) if (root/'evals').is_dir() else False
        has_runtime=root.joinpath('server').is_dir() or root.joinpath('bin').is_dir()
        gates.append(gate('mcp-quality','passed' if has_eval else 'warning','evaluation files present' if has_eval else 'missing MCP evaluation files'))
        gates.append(gate('runtime-evidence','passed' if has_runtime else 'warning','server/bin directory present' if has_runtime else 'no bundled runtime detected'))
    else:
        gates.append(gate('mcp-quality','passed','MCP not required for this Skill-only plugin'))
    secret_terms=[]
    for p in root.rglob('*'):
        if p.is_file() and p.name not in {'quality.json','quality.md'}:
            text=p.read_text(encoding='utf-8',errors='ignore')
            for term in ['BEGIN PRIVATE KEY','AKIA','api_key=','password=']:
                if term.lower() in text.lower(): secret_terms.append(f'{p}:{term}')
    gates.append(gate('secrets','blocked' if secret_terms else 'passed','; '.join(secret_terms) if secret_terms else 'no high-confidence secret markers'))
    statuses={x['status'] for x in gates}
    overall='blocked' if 'blocked' in statuses else ('warning' if 'warning' in statuses else 'passed')
    report={'plugin':str(root),'overall':overall,'gates':gates}
    print(json.dumps(report,indent=2,ensure_ascii=False))
    (root/'quality.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return 1 if overall=='blocked' else 0
if __name__=='__main__': raise SystemExit(main())
