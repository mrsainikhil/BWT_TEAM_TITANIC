from typing import Dict, Any, List, Tuple
import json
import math
from .config import GEO_DISTANCE_THRESHOLD_KM

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
    try:
        lat = float(txn.get("upi_lat")) if txn.get("upi_lat") is not None else None
        lon = float(txn.get("upi_lon")) if txn.get("upi_lon") is not None else None
    except:
        lat = None
        lon = None
    if lat is not None and lon is not None:
        try:
            gl = json.loads(profile.get("frequent_geo_locations", "[]"))
        except:
            gl = []
        def _hav(a):
            return a * math.pi / 180.0
        def _dist(a1, b1, a2, b2):
            dlat = _hav(a2 - a1)
            dlon = _hav(b2 - b1)
            sa = math.sin(dlat / 2.0) ** 2 + math.cos(_hav(a1)) * math.cos(_hav(a2)) * math.sin(dlon / 2.0) ** 2
            c = 2.0 * math.atan2(math.sqrt(sa), math.sqrt(1.0 - sa))
            return 6371.0 * c
        md = None
        for it in gl:
            try:
                d = _dist(lat, lon, float(it.get("lat")), float(it.get("lon")))
            except:
                d = None
            if d is not None:
                if md is None or d < md:
                    md = d
        if md is not None and md > GEO_DISTANCE_THRESHOLD_KM:
            score += 0.2
            if "unusual_location" not in reasons:
                reasons.append("unusual_location")
    return min(score, 1.0), reasons
