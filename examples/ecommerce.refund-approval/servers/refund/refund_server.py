from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
from mcp.server.fastmcp import FastMCP
ROOT=Path(__file__).resolve().parents[1]
ORDERS=json.loads((ROOT/'data'/'orders.json').read_text())
AUDIT=ROOT/'data'/'audit.log'
PROCESSED=set()
mcp=FastMCP('ecommerce-refund-approval')
def _token(order_id, amount, reason): return hashlib.sha256(f"{order_id}|{amount:.2f}|{reason}".encode()).hexdigest()[:16]
@mcp.tool()
def get_order(order_id: str) -> dict:
    """Read order evidence. Does not modify state."""
    return ORDERS.get(order_id, {'error':'order_not_found','order_id':order_id})
@mcp.tool()
def prepare_refund(order_id: str, amount: float, reason: str) -> dict:
    """Create a refund preview and one-time confirmation token; does not execute a refund."""
    order=ORDERS.get(order_id)
    if not order: return {'eligible':False,'error':'order_not_found'}
    if amount<=0 or amount>order['paid_amount']-order['prior_refund']: return {'eligible':False,'error':'amount_out_of_bounds'}
    if not order['return_window_open']: return {'eligible':False,'error':'return_window_closed'}
    return {'eligible':True,'order_id':order_id,'amount':round(amount,2),'currency':order['currency'],'reason':reason,'confirmation_token':_token(order_id,amount,reason),'idempotency_key':f'{order_id}:{amount:.2f}:{reason}'}
@mcp.tool()
def execute_refund(order_id: str, amount: float, reason: str, confirmation_token: str, user_confirmed: bool) -> dict:
    """Execute a refund only with explicit confirmation and a valid token; writes an audit event."""
    expected=_token(order_id,amount,reason)
    idempotency_key=f'{order_id}:{amount:.2f}:{reason}'
    if idempotency_key in PROCESSED: return {'executed':False,'error':'duplicate_idempotency_key'}
    if not user_confirmed: return {'executed':False,'error':'explicit_confirmation_required'}
    if confirmation_token!=expected: return {'executed':False,'error':'invalid_confirmation_token'}
    order=ORDERS.get(order_id)
    if not order: return {'executed':False,'error':'order_not_found'}
    order['prior_refund']=round(order['prior_refund']+amount,2)
    PROCESSED.add(idempotency_key)
    audit_id=hashlib.sha256(f'{order_id}|{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:12]
    AUDIT.open('a',encoding='utf-8').write(json.dumps({'audit_id':audit_id,'order_id':order_id,'amount':amount,'reason':reason})+'\n')
    return {'executed':True,'audit_id':audit_id,'order_id':order_id,'amount':amount,'currency':order['currency']}
if __name__=='__main__': mcp.run(transport='stdio')
