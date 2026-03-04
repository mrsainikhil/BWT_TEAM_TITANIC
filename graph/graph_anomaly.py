"""
Compute graph-based risk signals.
"""
from typing import Dict, Any, Tuple, List
import networkx as nx

def compute_graph_anomaly(G: nx.Graph, txn: Dict[str, Any]) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []
    u = txn["user_id"]; p = str(txn.get("payee_id") or ""); d = str(txn.get("device_id") or "")
    if p and G.has_node(p):
        deg = G.degree(p)
        if deg > 5:
            score += 0.2
            reasons.append("mule_network_suspected")
    if d and G.has_node(d):
        degd = G.degree(d)
        if degd > 3:
            score += 0.2
            reasons.append("shared_device_high_risk")
    try:
        cl = nx.clustering(G, u)
        if cl > 0.5:
            score += 0.1
            reasons.append("suspicious_cluster")
    except Exception:
        pass
    return min(score, 1.0), reasons
