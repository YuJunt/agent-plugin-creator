#!/usr/bin/env python3
from __future__ import annotations
import argparse, asyncio, json, statistics, time
from pathlib import Path

async def main_async(a):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params=StdioServerParameters(command=a.command,args=[str(a.server)],cwd=str(a.cwd or a.server.parent))
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as s:
            await s.initialize(); await s.list_tools(); sem=asyncio.Semaphore(a.concurrency); lat=[]; failures=0; sizes=[]
            async def one(i):
                nonlocal failures
                async with sem:
                    t=time.perf_counter()
                    try:
                        r=await s.call_tool(a.tool,json.loads(a.arguments)); text=''.join(getattr(x,'text','') for x in (r.content or [])); sizes.append(len(text)); lat.append((time.perf_counter()-t)*1000)
                    except Exception: failures+=1
            await asyncio.gather(*(one(i) for i in range(a.requests)))
            lat.sort(); p95=lat[min(len(lat)-1,max(0,int(len(lat)*.95)-1))] if lat else None
            return {'requests':a.requests,'concurrency':a.concurrency,'successes':len(lat),'failures':failures,'failure_rate':failures/a.requests if a.requests else 0,'latency_ms':{'min':min(lat) if lat else None,'median':statistics.median(lat) if lat else None,'p95':p95,'max':max(lat) if lat else None},'result_size_bytes':{'max':max(sizes) if sizes else None,'median':statistics.median(sizes) if sizes else None}}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--server',type=Path,required=True); ap.add_argument('--cwd',type=Path); ap.add_argument('--command',default='python3'); ap.add_argument('--tool',required=True); ap.add_argument('--arguments',required=True); ap.add_argument('--requests',type=int,default=10); ap.add_argument('--concurrency',type=int,default=2); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); result=asyncio.run(main_async(a)); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['failure_rate']==0 else 1
if __name__=='__main__': raise SystemExit(main())
