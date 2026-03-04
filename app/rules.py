from typing import Dict, Any, List, Tuple
import json

def compute_rules(txn: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []
    amount = float(txn.get("amount", 0.0))
    avg = float(profile.get("avg_amount", 0.0))
    std = float(profile.get("std_amount", 1.0))
    if amount > avg + 3 * std:
        score += 0.4
        reasons.append("amount_spike")
    frequent_locations = profile.get("frequent_locations", "[]")
    loc = str(txn.get("location", ""))
    if loc not in json.loads(frequent_locations):
        score += 0.2
        reasons.append("unusual_location")
    device_history = profile.get("device_history", "[]")
    device_id = str(txn.get("device_id", ""))
    if device_id not in json.loads(device_history):
        score += 0.2
        reasons.append("new_device")
    ts = str(txn.get("timestamp", "00:00"))
    try:
        h = int(ts.split(":")[0])
    except:
        h = 0
    if h < 5 or h > 23:
        score += 0.2
        reasons.append("odd_hour")
    merchant = str(txn.get("merchant", ""))
    if merchant.lower() in ["electronics", "luxury", "crypto"]:
        score += 0.2
        reasons.append("high_risk_merchant")
    if amount >= 100000:
        score += 0.5
        reasons.append("very_high_amount")
    return min(score, 1.0), reasons
