#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def load(p):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception: return None
def main():
    parser = argparse.ArgumentParser(description="发布决策：综合审计/评估/一致性/性能等证据，给出 BLOCKED/WARNING/PASS 决策")
    parser.add_argument("skill_root", help="技能根目录路径")
    parser.add_argument("evidence_dir", help="证据目录路径（包含各评估结果 JSON）")
    args = parser.parse_args()
    root=Path(args.skill_root); ev=Path(args.evidence_dir); gates=[]; blocked=[]; warnings=[]
    audit=load(root/'release-audit.json') or load(ev/'release-audit.json')
    if not audit: blocked.append('missing release audit evidence')
    elif audit.get('errors'): blocked.append('release audit has errors')
    else: gates.append({'gate':'release-audit','status':'pass'})
    for name,label in [('selection_eval_results.json','skill-selection'),('trigger_eval_judged.json','skill-activation'),('client-conformance.json','client-conformance'),('remote-mcp.json','remote-mcp'),('benchmark.json','performance')]:
        p=ev/name; d=load(p)
        if not d: warnings.append(f'{label}: not-tested')
        elif label=='remote-mcp' and d.get('status')=='blocked' and 'must use HTTPS' in d.get('reason',''):
            warnings.append('remote-mcp: negative URL policy fixture passed; real endpoint not-tested')
            gates.append({'gate':label,'status':'negative-policy-pass'})
        elif d.get('status') in {'blocked','fail'}: blocked.append(f'{label}: {d.get("status")}')
        else: gates.append({'gate':label,'status':d.get('status','evidence')})
    result={'decision':'BLOCKED' if blocked else ('WARNING' if warnings else 'PASS'),'gates':gates,'blocked':blocked,'warnings':warnings,'release_candidate':not bool(blocked)}
    out=ev/'release-decision.json'; out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(result,ensure_ascii=False,indent=2)); return 1 if blocked else 0
if __name__=='__main__': raise SystemExit(main())
