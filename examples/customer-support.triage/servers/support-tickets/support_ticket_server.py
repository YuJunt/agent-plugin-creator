from datetime import datetime, timezone
from pathlib import Path
import csv
from mcp.server.fastmcp import FastMCP
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data'/'tickets.csv'
mcp=FastMCP('customer-support-triage')
def rows():
    with DATA.open(encoding='utf-8', newline='') as f: return list(csv.DictReader(f))
@mcp.tool()
def list_tickets(status: str|None=None, severity: str|None=None, limit: int=50) -> list[dict]:
    """List support tickets without modifying them."""
    out=rows()
    if status: out=[r for r in out if r['status'].lower()==status.lower()]
    if severity: out=[r for r in out if r['severity'].lower()==severity.lower()]
    return out[:max(1,min(limit,200))]
@mcp.tool()
def find_sla_risks(limit: int=50) -> list[dict]:
    """Find open tickets whose age exceeds or approaches the stated SLA."""
    now=datetime(2026,8,17,12,0,tzinfo=timezone.utc)
    out=[]
    for r in rows():
        if r['status']!='open': continue
        age=(now-datetime.fromisoformat(r['created_date']).replace(tzinfo=timezone.utc)).total_seconds()/3600
        if age >= float(r['sla_hours'])*0.75:
            x=dict(r); x['age_hours']=round(age,1); x['risk']='breach' if age>=float(r['sla_hours']) else 'near_breach'; out.append(x)
    return out[:max(1,min(limit,200))]
if __name__=='__main__': mcp.run(transport='stdio')
