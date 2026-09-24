#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, time, uuid
from pathlib import Path
from urllib.parse import urlparse
import requests

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--url',required=True); ap.add_argument('--output',required=True); ap.add_argument('--header-env',action='append',default=[],help='HEADER_NAME=ENV_VAR_NAME')
    a=ap.parse_args(); parsed=urlparse(a.url); out={'url':a.url,'status':'not-tested','checks':[]}
    if parsed.scheme not in {'http','https'} or parsed.username or parsed.fragment: out.update(status='blocked',reason='Invalid URL: absolute HTTP(S) without userinfo or fragment required')
    elif parsed.hostname not in {'localhost','127.0.0.1','::1'} and parsed.scheme!='https': out.update(status='blocked',reason='Non-loopback remote MCP must use HTTPS')
    else:
        headers={'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
        for item in a.header_env:
            name,sep,env=item.partition('=')
            if not sep or not os.environ.get(env): out.update(status='blocked',reason=f'Missing header environment variable: {env}'); break
            headers[name]=os.environ[env]
        if out['status']=='not-tested':
            body={'jsonrpc':'2.0','id':str(uuid.uuid4()),'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'agent-plugin-creator-probe','version':'0.1.0'}}}
            try:
                t=time.time(); r=requests.post(a.url,headers=headers,json=body,timeout=20,allow_redirects=False); out.update(status='pass' if r.status_code<400 else 'fail',http_status=r.status_code,duration_seconds=round(time.time()-t,3),response_preview=r.text[:2000],redirect=bool(r.is_redirect)); out['checks']=['url-policy','initialize-http']
                if r.is_redirect: out.update(status='blocked',reason='Redirect not followed for credential safety')
            except Exception as e: out.update(status='fail',error=type(e).__name__+': '+str(e))
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(out,ensure_ascii=False,indent=2)); return 0 if out['status'] in {'pass','not-tested'} else 1
if __name__=='__main__': raise SystemExit(main())
