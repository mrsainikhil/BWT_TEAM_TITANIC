"""
Weighted risk aggregation.
"""
from typing import Dict
from app.config import RISK_WEIGHTS

def aggregate_scores(rule_score: float, ml_score: float, anomaly_score: float, graph_score: float) -> Dict[str, float]:
    w = RISK_WEIGHTS
    risk = w["rule"] * rule_score + w["ml"] * ml_score + w["anomaly"] * anomaly_score + w["graph"] * graph_score
    return {"risk_score": max(0.0, min(1.0, risk))}
