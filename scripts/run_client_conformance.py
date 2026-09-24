#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, time
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--plugin',required=True)
    ap.add_argument('--client',required=True)
    ap.add_argument('--command',help='Optional client-specific smoke command; use {plugin} placeholder')
    ap.add_argument('--output',required=True)
    a=ap.parse_args(); plugin=Path(a.plugin).resolve(); out=Path(a.output)
    result={'client':a.client,'plugin':str(plugin),'status':'not-tested','evidence':[]}
    if not a.command:
        result['reason']='No real client command supplied; compatibility is unknown.'
    else:
        cmd=a.command.format(plugin=str(plugin))
        started=time.time()
        cmd_parts=shlex.split(cmd)
        p=subprocess.run(cmd_parts,shell=False,capture_output=True,text=True,timeout=180,env={**os.environ,'PLUGIN_ROOT':str(plugin)})
        result.update({'status':'pass' if p.returncode==0 else 'fail','command':cmd,'returncode':p.returncode,'duration_seconds':round(time.time()-started,3),'stdout':p.stdout[-10000:],'stderr':p.stderr[-10000:]})
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['status'] in {'pass','not-tested'} else 1
if __name__=='__main__': raise SystemExit(main())
