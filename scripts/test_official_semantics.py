#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
VALID=ROOT/'scripts/validate_plugin.py'
def run(d): return subprocess.run(['python3',str(VALID),str(d)],capture_output=True,text=True)
def main():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td)
        # plugin name 必须与目录名一致（验证器要求），所以用目录名
        plugin={'$schema':'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json','name':base.name}
        (base/'plugin.json').write_text(json.dumps(plugin)); (base/'bin').mkdir(); (base/'bin/server').write_text('#!/bin/sh\n')
        (base/'mcp.json').write_text(json.dumps({'$schema':'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json','mcpServers':{'s':{'type':'stdio','command':'./bin/server','args':['../opaque-value'],'cwd':'./'}}}))
        ok=run(base)
        assert ok.returncode==0, ok.stdout+ok.stderr
        mismatch=json.loads((base/'mcp.json').read_text()); mismatch['$schema']='https://agent-plugins.org/schemas/9.9.9/mcp.schema.json'; (base/'mcp.json').write_text(json.dumps(mismatch)); bad=run(base); assert bad.returncode!=0
        mismatch['$schema']='https://agent-plugins.org/schemas/1.0.0/mcp.schema.json'; mismatch['mcpServers']['s']['headers']={'Authorization':'x','authorization':'y'}; mismatch['mcpServers']['s']['type']='streamable-http'; mismatch['mcpServers']['s'].pop('command'); mismatch['mcpServers']['s'].pop('args'); mismatch['mcpServers']['s'].pop('cwd'); mismatch['mcpServers']['s']['url']='http://localhost:3000'; (base/'mcp.json').write_text(json.dumps(mismatch)); dup=run(base); assert dup.returncode!=0
    print('OFFICIAL_SEMANTICS_PASS')
if __name__=='__main__': main()
