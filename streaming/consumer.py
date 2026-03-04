"""
Consumer worker that processes transactions from Redis Streams and emits decisions.
"""
import asyncio
import json
from typing import Dict, Any
from app.cache import init_redis, transaction_key, cache_set, get_user_profile, update_user_profile
from app.rules import compute_rules
from app.anomaly import compute_anomaly
from app.models import model
from app.aggregator import aggregate
from app.decision import decide
from app.config import STREAM_TXN, STREAM_DECISION, MODEL_FLAG_THRESHOLD
from graph.graph_builder import add_transaction_edge, build_graph
from graph.graph_anomaly import compute_graph_anomaly
from features.feature_pipeline import feature_pipeline

async def process_txn(txn: Dict[str, Any]) -> Dict[str, Any]:
    profile = await get_user_profile(txn["user_id"])
    rule_score, rule_reasons = compute_rules(txn, profile)
    txn["unusual_location_flag"] = "unusual_location" in rule_reasons
    txn["new_device_flag"] = "new_device" in rule_reasons
    feats = await feature_pipeline(txn, profile)
    ml_prob = model.predict_proba(feats)
    anomaly_score, anomaly_reasons = compute_anomaly(txn, profile)
    await add_transaction_edge(txn)
    G = await build_graph()
    graph_score, graph_reasons = compute_graph_anomaly(G, txn)
    agg = aggregate(rule_score, ml_prob, anomaly_score, graph_score)
    all_reasons = list(dict.fromkeys(rule_reasons + anomaly_reasons + graph_reasons))
    decision, explanation = decide(agg["risk_score"], all_reasons)
    flagged = agg["risk_score"] >= MODEL_FLAG_THRESHOLD
    resp = {"decision": decision, "explanation": {"risk_score": agg["risk_score"], "reasons": all_reasons}, "flagged": flagged}
    await cache_set(transaction_key(txn), resp)
    await update_user_profile(txn["user_id"], {"transaction_frequency": profile.get("transaction_frequency", 1) + 1})
    return resp

async def main():
    r = await init_redis()
    group = "fraud_workers"
    stream = STREAM_TXN
    try:
        await r.xgroup_create(stream, group, id="$", mkstream=True)
    except Exception:
        pass
    while True:
        try:
            msgs = await r.xreadgroup(groupname=group, consumername="worker1", streams={stream: ">"}, count=10, block=1000)
        except Exception:
            await asyncio.sleep(0.2)
            msgs = []
        for _, entries in msgs or []:
            for mid, fields in entries:
                try:
                    txn = json.loads(fields.get("data"))
                    resp = await process_txn(txn)
                    await r.xadd(STREAM_DECISION, {"data": json.dumps({"txn": txn, "resp": resp})})
                    await r.xack(stream, group, mid)
                except Exception:
                    pass
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    asyncio.run(main())
