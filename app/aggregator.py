from typing import Dict, Any, List

def aggregate(rule_score: float, ml_prob: float, anomaly_score: float) -> Dict[str, Any]:
    risk = 0.2 * rule_score + 0.5 * ml_prob + 0.3 * anomaly_score
    return {"risk_score": min(max(risk, 0.0), 1.0)}
