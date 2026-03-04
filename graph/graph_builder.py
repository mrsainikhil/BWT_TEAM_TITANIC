"""
Build and persist transaction relationship graph using NetworkX.
"""
from typing import Dict, Any
import networkx as nx
import json
from app.cache import init_redis

GRAPH_KEY = "graph:relationships"

async def add_transaction_edge(txn: Dict[str, Any]) -> None:
    r = await init_redis()
    try:
        raw = await r.get(GRAPH_KEY)
        data = json.loads(raw) if raw else {"nodes": [], "edges": []}
    except Exception:
        data = {"nodes": [], "edges": []}
    u = txn["user_id"]; p = str(txn.get("payee_id") or ""); m = str(txn.get("merchant") or ""); d = str(txn.get("device_id") or "")
    for n in [u, p, m, d]:
        if n and n not in data["nodes"]:
            data["nodes"].append(n)
    edges = [(u, p, "user_payee"), (p, m, "payee_merchant"), (u, d, "user_device"), (d, m, "device_merchant")]
    for a, b, t in edges:
        if a and b:
            data["edges"].append({"a": a, "b": b, "t": t})
    await r.set(GRAPH_KEY, json.dumps(data), ex=3600)

async def build_graph() -> nx.Graph:
    r = await init_redis()
    G = nx.Graph()
    try:
        raw = await r.get(GRAPH_KEY)
        data = json.loads(raw) if raw else {"nodes": [], "edges": []}
    except Exception:
        data = {"nodes": [], "edges": []}
    for n in data["nodes"]:
        G.add_node(n)
    for e in data["edges"]:
        G.add_edge(e["a"], e["b"], kind=e["t"])
    return G
