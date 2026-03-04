"""
Producer that enqueues transactions to Redis Streams.
"""
from typing import Dict, Any
import json
from app.cache import init_redis
from app.config import STREAM_TXN

async def enqueue_transaction(txn: Dict[str, Any]) -> str:
    r = await init_redis()
    data = json.dumps(txn)
    try:
        xid = await r.xadd(STREAM_TXN, {"data": data})
    except Exception:
        xid = "mem:" + data
    return xid
