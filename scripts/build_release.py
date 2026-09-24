#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys, zipfile
from pathlib import Path

def digest(path):
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()
def main():
    parser = argparse.ArgumentParser(description="构建发布包：生成 manifest 并打包为 zip，包含 SHA256 校验")
    parser.add_argument("skill_root", help="技能根目录路径")
    parser.add_argument("output_zip", help="输出 zip 文件路径")
    args = parser.parse_args()
    root=Path(args.skill_root).resolve(); out=Path(args.output_zip).resolve()
    files=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and not p.is_symlink() and p.name not in {'release-audit.json','build-manifest.json'}:
            files.append(p)
    manifest={'root':root.name,'files':[{'path':str(p.relative_to(root)),'sha256':digest(p),'size':p.stat().st_size} for p in files]}
    (root/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files+[root/'build-manifest.json']:
            rel=p.relative_to(root); info=zipfile.ZipInfo(str(Path(root.name)/rel).replace('\\','/'),date_time=(2020,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o644<<16; z.writestr(info,p.read_bytes())
    print(json.dumps({'output':str(out),'file_count':len(files)+1,'sha256':digest(out)},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
