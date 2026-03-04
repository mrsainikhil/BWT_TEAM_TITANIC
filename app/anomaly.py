from typing import Dict, Any, List, Tuple
import json

def compute_anomaly(txn: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []
    amount = float(txn.get("amount", 0.0))
    avg = float(profile.get("avg_amount", 0.0))
    std = float(profile.get("std_amount", 1.0))
    if std <= 0:
        std = 1.0
    if amount > avg * 3:
        score += 0.3
        reasons.append("amount_deviation")
    loc = str(txn.get("location", ""))
    frequent_locations = json.loads(profile.get("frequent_locations", "[]"))
    if loc not in frequent_locations:
        score += 0.2
        reasons.append("location_anomaly")
    device_id = str(txn.get("device_id", ""))
    device_history = json.loads(profile.get("device_history", "[]"))
    if device_id not in device_history:
        score += 0.2
        reasons.append("device_anomaly")
    ts = str(txn.get("timestamp", "00:00"))
    try:
        h = int(ts.split(":")[0])
    except:
        h = 0
    if h < 6 or h > 22:
        score += 0.1
        reasons.append("time_anomaly")
    return min(score, 1.0), reasons
