import asyncio
import time
import json
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from .cache import init_redis, transaction_key, cache_get, cache_set, get_user_profile, update_user_profile, rate_limit_allow
from .rules import compute_rules
from .anomaly import compute_anomaly
from .models import model
from .aggregator import aggregate
from .decision import decide

app = FastAPI()

class Transaction(BaseModel):
    user_id: str
    amount: float
    location: str
    device_id: str
    merchant: str
    timestamp: str

class Connections:
    def __init__(self):
        self.clients = set()
    async def add(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)
    def remove(self, ws: WebSocket):
        self.clients.discard(ws)
    async def broadcast(self, message: Dict[str, Any]):
        data = json.dumps(message)
        for ws in list(self.clients):
            try:
                await ws.send_text(data)
            except WebSocketDisconnect:
                self.remove(ws)

connections = Connections()

metrics = {
    "request_count": 0,
    "avg_response_ms": 0.0,
    "cache_hit_ratio": 0.0,
    "cache_hits": 0,
    "cache_misses": 0,
    "blocks": 0,
    "otp_verifications": 0,
    "approvals": 0,
}

@app.on_event("startup")
async def startup():
    await init_redis()

@app.post("/transaction")
async def process_transaction(txn: Transaction, request: Request):
    t0 = time.perf_counter()
    metrics["request_count"] += 1
    if not await rate_limit_allow(txn.user_id):
        raise HTTPException(status_code=429, detail="rate_limited")
    payload = txn.model_dump()
    key = transaction_key(payload)
    cached = await cache_get(key)
    if cached:
        metrics["cache_hits"] += 1
        resp = cached
    else:
        metrics["cache_misses"] += 1
        profile = await get_user_profile(txn.user_id)
        rule_score, rule_reasons = compute_rules(payload, profile)
        unusual_location_flag = "unusual_location" in rule_reasons
        new_device_flag = "new_device" in rule_reasons
        payload["unusual_location_flag"] = unusual_location_flag
        payload["new_device_flag"] = new_device_flag
        ml_prob = model.predict_proba(payload)
        anomaly_score, anomaly_reasons = compute_anomaly(payload, profile)
        agg = aggregate(rule_score, ml_prob, anomaly_score)
        all_reasons = list(dict.fromkeys(rule_reasons + anomaly_reasons))
        decision, explanation = decide(agg["risk_score"], all_reasons)
        resp = {"decision": decision, "explanation": explanation}
        await cache_set(key, resp)
        await update_user_profile(txn.user_id, {"transaction_frequency": profile.get("transaction_frequency", 1) + 1})
    await connections.broadcast({"type": "risk", "user_id": txn.user_id, "decision": resp["decision"], "risk": resp["explanation"]["risk_score"]})
    if resp["decision"] == "BLOCK":
        metrics["blocks"] += 1
    elif resp["decision"] == "OTP_VERIFICATION":
        metrics["otp_verifications"] += 1
    else:
        metrics["approvals"] += 1
    dt = (time.perf_counter() - t0) * 1000
    metrics["avg_response_ms"] = ((metrics["avg_response_ms"] * (metrics["request_count"] - 1)) + dt) / metrics["request_count"]
    total = metrics["cache_hits"] + metrics["cache_misses"]
    metrics["cache_hit_ratio"] = (metrics["cache_hits"] / total) if total > 0 else 0.0
    return JSONResponse(resp)

@app.get("/metrics")
async def get_metrics():
    return JSONResponse(metrics)

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await connections.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        connections.remove(ws)

dashboard_html = """
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>Fraud Monitor</title>
<style>
body { font-family: system-ui, sans-serif; margin: 16px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { border: 1px solid #ddd; padding: 12px; border-radius: 8px; }
.pill { display: inline-block; padding: 4px 8px; border-radius: 999px; }
.approve { background: #e6ffed; }
.block { background: #ffe6e6; }
.otp { background: #fff6db; }
</style>
</head>
<body>
<h2>Live Fraud Monitoring</h2>
<div class="grid">
  <div class="card">
    <h3>Metrics</h3>
    <div id="metrics"></div>
  </div>
  <div class="card">
    <h3>Stream</h3>
    <div id="stream"></div>
  </div>
</div>
<script>
async function loadMetrics() {
  const r = await fetch('/metrics');
  const m = await r.json();
  const el = document.getElementById('metrics');
  el.innerHTML = 'Requests: ' + m.request_count + '<br>' +
                 'Avg response: ' + m.avg_response_ms.toFixed(1) + ' ms<br>' +
                 'Cache hit ratio: ' + (m.cache_hit_ratio*100).toFixed(1) + '%<br>' +
                 'Approvals: ' + m.approvals + ', OTP: ' + m.otp_verifications + ', Blocks: ' + m.blocks;
}
setInterval(loadMetrics, 1000); loadMetrics();
const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.type === 'risk') {
    const s = document.getElementById('stream');
    const d = document.createElement('div');
    let cls = 'pill approve';
    if (msg.decision === 'BLOCK') cls = 'pill block';
    else if (msg.decision === 'OTP_VERIFICATION') cls = 'pill otp';
    d.innerHTML = '<span class=\"' + cls + '\">' + msg.decision + '</span> user=' + msg.user_id + ' risk=' + (msg.risk*100).toFixed(1) + '%';
    s.prepend(d);
  }
};
</script>
</body>
</html>
"""

@app.get("/")
async def dashboard():
    return HTMLResponse(dashboard_html)
