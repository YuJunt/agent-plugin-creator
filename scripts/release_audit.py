#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

def sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="发布前审计：检查必需文件、官方资源、版本一致性、符号链接等")
    parser.add_argument("skill_root", help="技能根目录路径")
    args = parser.parse_args()
    root=Path(args.skill_root).resolve(); errors=[]; warnings=[]; evidence=[]
    required=['SKILL.md','references/evaluation-protocol.md','assets/schemas/1.0.0/plugin.schema.json','assets/schemas/1.0.0/mcp.schema.json','scripts/validate_plugin.py','scripts/quality_report.py','scripts/run_trigger_eval.py','scripts/judge_trigger_eval.py','scripts/run_edge_eval.py','scripts/build_release.py','references/mcp-tool-contract.json','references/permission-matrix.md','references/official-conformance-matrix.md','references/client-conformance.md','scripts/test_official_semantics.py','scripts/run_client_conformance.py','scripts/probe_remote_mcp.py','scripts/simulate_discovery.py','scripts/test_failure_boundaries.py','scripts/validate_tool_contract.py','scripts/generate_repair_plan.py','scripts/benchmark_mcp.py','scripts/release_decision.py']
    for rel in required:
        p=root/rel
        if not p.is_file(): errors.append(f'missing required release file: {rel}')
    vendor=root/'official'
    for rel in ['skill-creator/SKILL.md','mcp-builder/SKILL.md']:
        if not (vendor/rel).is_file(): errors.append(f'missing embedded official resource: {rel}')
    examples=list((root/'examples').iterdir()) if (root/'examples').is_dir() else []
    if len(examples)<4: warnings.append('fewer than four bundled regression examples')
    for p in root.rglob('*'):
        if p.is_symlink(): errors.append(f'symlink found in release tree: {p.relative_to(root)}')
    if not (root/'CHANGELOG.md').is_file(): warnings.append('CHANGELOG.md missing')
    if not (root/'provenance.json').is_file(): warnings.append('provenance.json missing')
    if not (root/'evals').is_dir(): errors.append('evals directory missing')
    # 版本一致性检查：SKILL.md 头部版本号必须与 provenance.json 一致
    import re as _re
    skill_md = (root/'SKILL.md').read_text(encoding='utf-8')
    pv = _re.search(r'>\s*\*\*版本\*\*:\s*v?([\d.]+)', skill_md)
    prov = json.loads((root/'provenance.json').read_text(encoding='utf-8'))
    if pv and prov.get('version'):
        if pv.group(1) != prov['version']:
            errors.append(f'版本不一致: SKILL.md 为 v{pv.group(1)}, provenance.json 为 v{prov["version"]}')
    # CHANGELOG.md 最新条目版本号必须与 provenance.json 一致
    changelog = root/'CHANGELOG.md'
    if changelog.is_file():
        cl_text = changelog.read_text(encoding='utf-8')
        cl_ver = _re.search(r'##\s*\[([\d.]+)\]', cl_text)
        if cl_ver and prov.get('version'):
            if cl_ver.group(1) != prov['version']:
                errors.append(f'版本不一致: CHANGELOG.md 最新为 v{cl_ver.group(1)}, provenance.json 为 v{prov["version"]}')
    checks={'required_files':len(required),'examples':len(examples),'vendor_files':sum(1 for _ in vendor.rglob('*')) if vendor.is_dir() else 0,'errors':len(errors),'warnings':len(warnings)}
    report={'status':'BLOCKED' if errors else ('WARNING' if warnings else 'PASS'),'checks':checks,'errors':errors,'warnings':warnings,'sha256':{str(p.relative_to(root)):sha256(p) for p in [root/'SKILL.md',root/'LICENSE.txt'] if p.is_file()}}
    (root/'release-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if errors else 0
if __name__=='__main__': raise SystemExit(main())
