#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

def score(root: Path):
    dimensions={k:0 for k in ['trigger','portable_structure','skill_quality','mcp_quality','safety','verification','handoff']}
    evidence=[]
    manifest=root/'plugin.json'; skills=list((root/'skills').glob('*/SKILL.md')) if (root/'skills').is_dir() else []
    readme=root/'README.md'; mcp=root/'mcp.json'; evals=root/'evals'
    if skills: dimensions['trigger']=2; evidence.append('Skill description and immediate-child layout found')
    if manifest.exists() and skills and (not mcp.exists() or mcp.is_file()): dimensions['portable_structure']=2
    if skills:
        texts='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for p in skills)
        required=['Use when','step','Do not','Return']
        dimensions['skill_quality']=2 if all(x.lower() in texts.lower() for x in required) else 1
    if not mcp.exists(): dimensions['mcp_quality']=2
    elif (root/'server').is_dir() or (root/'bin').is_dir():
        dimensions['mcp_quality']=2; evidence.append('Bundled runtime directory found')
    else: dimensions['mcp_quality']=1; evidence.append('MCP config exists but no bundled runtime evidence')
    all_text=''.join(p.read_text(encoding='utf-8',errors='ignore') for p in root.rglob('*') if p.is_file() and p.suffix in {'.md','.json','.py','.txt'})
    dimensions['safety']=2 if not any(x.lower() in all_text.lower() for x in ['BEGIN PRIVATE KEY','api_key=','password=']) else 0
    proc=subprocess.run(['python3',str(Path(__file__).with_name('validate_plugin.py')),str(root)],capture_output=True,text=True)
    dimensions['verification']=2 if proc.returncode==0 else 0
    dimensions['handoff']=2 if readme.exists() and evals.exists() else 1
    total=sum(dimensions.values()); max_score=14
    status='strong pass' if total>=12 else ('pass with warnings' if total>=9 else 'fail')
    return {'plugin':str(root),'score':total,'max_score':max_score,'status':status,'dimensions':dimensions,'evidence':evidence,'validator_output':proc.stdout}

def main():
    parser = argparse.ArgumentParser(description="评估插件产物质量：7维度评分（触发/结构/skill/MCP/安全/验证/交接）")
    parser.add_argument("plugin_roots", nargs="+", help="一个或多个插件根目录路径")
    args = parser.parse_args()
    reports=[score(Path(x).resolve()) for x in args.plugin_roots]
    print(json.dumps(reports,indent=2,ensure_ascii=False))
    return 0 if all(r['status']!='fail' for r in reports) else 1
if __name__=='__main__': raise SystemExit(main())
