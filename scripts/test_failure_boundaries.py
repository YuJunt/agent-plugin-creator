#!/usr/bin/env python3
"""失败边界测试：验证 simulate_discovery.py 对有效/无效 Skill 和 MCP 的分类。"""
from pathlib import Path
import argparse, json, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser = argparse.ArgumentParser(description="失败边界测试")
    parser.parse_args()
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); (root/'skills/valid').mkdir(parents=True); (root/'skills/valid/SKILL.md').write_text('---\nname: valid\ndescription: Valid test skill. Use for boundary tests.\n---\n\nDo the test.\n'); (root/'skills/invalid').mkdir(parents=True); (root/'skills/invalid/SKILL.md').write_text('not frontmatter')
        (root/'plugin.json').write_text(json.dumps({'$schema':'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json','name':'boundary-test'}))
        (root/'mcp.json').write_text(json.dumps({'$schema':'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json','mcpServers':{'good':{'type':'stdio','command':'python3'},'bad':{'type':'unknown','command':'x'}}}))
        p=subprocess.run(['python3',str(ROOT/'scripts/simulate_discovery.py'),str(root)],capture_output=True,text=True,check=True); data=json.loads(p.stdout)
        assert data['skills']==['invalid','valid'] or set(data['skills'])=={'valid','invalid'}
        assert 'good' in data['mcp_servers'] and 'bad' in data['invalid_mcp_servers']
    print('FAILURE_BOUNDARIES_PASS')
if __name__=='__main__': main()
