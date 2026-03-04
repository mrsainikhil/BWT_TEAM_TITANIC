"""
Runtime feature pipeline for transaction scoring.
"""
from typing import Dict, Any
import time
import json
import math
from app.cache import init_redis

async def _now() -> float:
    return time.time()

async def feature_pipeline(txn: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, float]:
    r = await init_redis()
    uid = txn["user_id"]
    ts_key = f"user:{uid}:timestamps"
    fail_key = f"user:{uid}:failures"
    now = await _now()
    try:
        # Redis memory fallback supports get/set only; emulate lists via hash fields
        raw = await r.get(ts_key)
        arr = json.loads(raw) if raw else []
        arr.append(now)
        arr = [t for t in arr if now - t <= 3600]
        await r.set(ts_key, json.dumps(arr), ex=3600)
    except Exception:
        arr = [now]
    c_1m = len([t for t in arr if now - t <= 60])
    c_5m = len([t for t in arr if now - t <= 300])
    c_1h = len(arr)
    avg = float(profile.get("avg_amount", 500.0))
    std = float(profile.get("std_amount", 200.0)) or 1.0
    amount = float(txn.get("amount", 0.0))
    amount_z = (amount - avg) / std
    try:
        gl = json.loads(profile.get("frequent_geo_locations", "[]"))
    except Exception:
        gl = []
    def _hav(a): return a * math.pi / 180.0
    def _dist(a1, b1, a2, b2):
        dlat = _hav(a2 - a1); dlon = _hav(b2 - b1)
        sa = math.sin(dlat/2.0)**2 + math.cos(_hav(a1)) * math.cos(_hav(a2)) * math.sin(dlon/2.0)**2
        c = 2.0 * math.atan2(math.sqrt(sa), math.sqrt(1.0 - sa))
        return 6371.0 * c
    lat = txn.get("upi_lat"); lon = txn.get("upi_lon")
    md = None
    if lat is not None and lon is not None and gl:
        for it in gl:
            try:
                d = _dist(float(lat), float(lon), float(it.get("lat")), float(it.get("lon")))
                if md is None or d < md: md = d
            except Exception:
                pass
    dist_last = md or 0.0
    device_risk = 0.5 if txn.get("new_device_flag") else 0.0
    m = str(txn.get("merchant", "")).lower()
    merchant_risk = 0.3 if m in ["electronics", "luxury", "crypto"] else 0.0
    # failures
    try:
        rawf = await r.get(fail_key)
        fa = json.loads(rawf) if rawf else []
        fa = [t for t in fa if now - t <= 3600]
        await r.set(fail_key, json.dumps(fa), ex=3600)
    except Exception:
        fa = []
    account_age_days = 365
    feats = {
        "transaction_velocity_1min": float(c_1m),
        "transaction_velocity_5min": float(c_5m),
        "transaction_velocity_1hr": float(c_1h),
        "amount_zscore": float(amount_z),
        "distance_from_last_transaction": float(dist_last),
        "device_risk_score": float(device_risk),
        "merchant_risk_score": float(merchant_risk),
        "account_age_days": float(account_age_days),
        "failed_transactions_last_hour": float(len(fa)),
        "amount": amount,
    }
    return feats
