import asyncio
import time
import json
import os
import sys
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config import MODEL_FLAG_THRESHOLD
from app.cache import init_redis, transaction_key, cache_get, cache_set, get_user_profile, update_user_profile, rate_limit_allow, set_callback, get_callback, pending_set, pending_get, pending_clear, set_mobile, get_mobile
from app.rules import compute_rules
from app.anomaly import compute_anomaly
from app.models import model
from app.aggregator import aggregate
from app.decision import decide

app = FastAPI()

class Transaction(BaseModel):
    user_id: str
    amount: float
    location: str
    device_id: str
    merchant: str
    timestamp: str
    upi_app: str | None = None
    upi_lat: float | None = None
    upi_lon: float | None = None

class CallbackRegistration(BaseModel):
    user_id: str
    url: str
    secret: str

class ConfirmRequest(BaseModel):
    txn_hash: str
    approve: bool

class MobileRegistration(BaseModel):
    user_id: str
    url: str
    phone: str

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
    "flags": 0,
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
        flagged = agg["risk_score"] >= MODEL_FLAG_THRESHOLD
        resp = {"decision": decision, "explanation": explanation, "flagged": flagged}
        await cache_set(key, resp)
        await update_user_profile(txn.user_id, {"transaction_frequency": profile.get("transaction_frequency", 1) + 1})
    await connections.broadcast({"type": "risk", "user_id": txn.user_id, "decision": resp["decision"], "risk": resp["explanation"]["risk_score"], "flagged": resp.get("flagged", False)})
    if resp["decision"] == "BLOCK":
        metrics["blocks"] += 1
    elif resp["decision"] == "OTP_VERIFICATION":
        metrics["otp_verifications"] += 1
    else:
        metrics["approvals"] += 1
    if resp.get("flagged"):
        metrics["flags"] += 1
    dt = (time.perf_counter() - t0) * 1000
    metrics["avg_response_ms"] = ((metrics["avg_response_ms"] * (metrics["request_count"] - 1)) + dt) / metrics["request_count"]
    total = metrics["cache_hits"] + metrics["cache_misses"]
    metrics["cache_hit_ratio"] = (metrics["cache_hits"] / total) if total > 0 else 0.0
    return JSONResponse(resp)

@app.post("/precheck")
async def precheck(txn: Transaction):
    payload = txn.model_dump()
    key = transaction_key(payload)
    profile = await get_user_profile(txn.user_id)
    rule_score, rule_reasons = compute_rules(payload, profile)
    payload["unusual_location_flag"] = "unusual_location" in rule_reasons
    payload["new_device_flag"] = "new_device" in rule_reasons
    ml_prob = model.predict_proba(payload)
    anomaly_score, anomaly_reasons = compute_anomaly(payload, profile)
    agg = aggregate(rule_score, ml_prob, anomaly_score)
    reasons = list(dict.fromkeys(rule_reasons + anomaly_reasons))
    flagged = agg["risk_score"] >= MODEL_FLAG_THRESHOLD
    resp = {"txn_hash": key, "flagged": flagged, "decision_preview": decide(agg["risk_score"], reasons)[0], "explanation": {"risk_score": agg["risk_score"], "reasons": reasons}}
    if flagged:
        await pending_set(key, resp)
        cb = await get_callback(txn.user_id)
        url = cb.get("url")
        if url:
            async def notify():
                import requests
                try:
                    requests.post(url, json={"event":"risk_precheck","user_id":txn.user_id,"txn_hash":key,"risk":agg["risk_score"],"reasons":reasons}, timeout=2)
                except Exception:
                    pass
            asyncio.create_task(notify())
        mob = await get_mobile(txn.user_id)
        murl = mob.get("url")
        phone = mob.get("phone")
        if murl and phone:
            async def notify_mobile():
                import requests
                try:
                    text = f"Risk alert {int(agg['risk_score']*100)}% {txn.merchant} {txn.amount} at {txn.location}"
                    requests.post(murl, json={"phone": phone, "text": text}, timeout=2)
                except Exception:
                    pass
            asyncio.create_task(notify_mobile())
        await connections.broadcast({"type":"precheck","user_id":txn.user_id,"txn_hash":key,"risk":agg["risk_score"],"reasons":reasons})
    return JSONResponse(resp)

@app.post("/confirm")
async def confirm(req: ConfirmRequest):
    pend = await pending_get(req.txn_hash)
    if not pend:
        raise HTTPException(status_code=404, detail="not_found_or_expired")
    await pending_clear(req.txn_hash)
    if not req.approve:
        decision, explanation = "BLOCK", {"risk_score": pend["explanation"]["risk_score"], "reasons": pend["explanation"]["reasons"] + ["user_declined"]}
        return JSONResponse({"decision": decision, "explanation": explanation})
    return JSONResponse({"decision": "APPROVE", "explanation": pend["explanation"]})

@app.post("/register_callback")
async def register_callback(reg: CallbackRegistration):
    await set_callback(reg.user_id, reg.url, reg.secret)
    return JSONResponse({"status":"ok"})

@app.post("/register_mobile")
async def register_mobile(reg: MobileRegistration):
    await set_mobile(reg.user_id, reg.url, reg.phone)
    return JSONResponse({"status":"ok"})
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
<title>SentinelPay • Real-Time Fraud Monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root { --bg:#0f172a; --fg:#e5e7eb; --muted:#94a3b8; --card:#111827; --accent:#38bdf8; --ok:#22c55e; --warn:#f59e0b; --bad:#ef4444; }
* { box-sizing: border-box; }
body { font-family: ui-sans-serif, system-ui, -apple-system; margin:0; background:linear-gradient(180deg,#0b1220,#0f172a); color:var(--fg); }
.nav { display:flex; align-items:center; justify-content:space-between; padding:14px 20px; border-bottom:1px solid #1f2937; position:sticky; top:0; backdrop-filter:saturate(180%) blur(8px); background:#0f172aDD; }
.brand { font-weight:700; letter-spacing:0.3px; }
.grid { display:grid; grid-template-columns: 1.2fr 1fr; gap:16px; padding:20px; }
.card { background:var(--card); border:1px solid #1f2937; padding:14px; border-radius:12px; }
.metrics { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; }
.metric { background:#0b1328; border:1px solid #1e293b; border-radius:10px; padding:12px; }
.k { font-size:12px; color:var(--muted); }
.v { font-size:22px; font-weight:700; }
.pill { display:inline-block; padding:4px 8px; border-radius:999px; font-weight:600; font-size:12px; }
.approve { background: #052e1a; color: var(--ok); border:1px solid #134e4a; }
.block { background: #3c0d0d; color: var(--bad); border:1px solid #7f1d1d; }
.otp { background: #3b2a06; color: var(--warn); border:1px solid #713f12; }
.flag { background: #0a2433; color: var(--accent); border:1px solid #0ea5e9; }
.stream div { padding:6px 0; border-bottom:1px dashed #1f2937; }
.form-row { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:8px; }
.btn { background:var(--accent); color:#00111a; border:none; border-radius:8px; padding:10px 14px; font-weight:700; cursor:pointer; }
.btn:active { transform:translateY(1px); }
.footer { padding:12px 20px; color:var(--muted); }
</style>
</head>
<body>
<div class="nav">
  <div class="brand">SentinelPay</div>
  <div style="color:var(--muted)">Real-time AI Fraud Interception</div>
</div>
<div class="grid">
  <div class="card">
    <h3 style="margin:0 0 8px 0">Metrics</h3>
    <div class="metrics">
      <div class="metric"><div class="k">Requests</div><div class="v" id="m_req">0</div></div>
      <div class="metric"><div class="k">Avg response (ms)</div><div class="v" id="m_rt">0</div></div>
      <div class="metric"><div class="k">Cache hit (%)</div><div class="v" id="m_hit">0</div></div>
      <div class="metric"><div class="k">Approvals / OTP / Blocks</div><div class="v" id="m_counts">0 / 0 / 0</div></div>
    </div>
    <canvas id="rtChart" height="120" style="margin-top:12px;"></canvas>
  </div>
  <div class="card">
    <h3 style="margin:0 0 8px 0">Live Stream</h3>
    <div id="stream" class="stream"></div>
  </div>
</div>
<div class="grid" style="grid-template-columns: 1fr;">
  <div class="card">
    <h3 style="margin:0 0 8px 0">Quick Simulate</h3>
    <div class="form-row">
      <input id="f_user" placeholder="user_id" value="user_42" />
      <input id="f_amount" placeholder="amount" type="number" value="25000" />
      <input id="f_location" placeholder="location" value="Delhi" />
    </div>
    <div class="form-row">
      <input id="f_device" placeholder="device_id" value="device_78" />
      <input id="f_merchant" placeholder="merchant" value="Electronics" />
      <input id="f_time" placeholder="timestamp (HH:MM)" value="23:12" />
    </div>
    <button class="btn" id="btnSend">Send Transaction</button>
    <div id="lastResp" style="margin-top:8px;color:var(--muted)"></div>
  </div>
</div>
<div class="footer">Engine uses rules + ML + anomaly, cached decisions, and WebSocket streaming.</div>
<script>
let rtData = [];
const ctx = document.getElementById('rtChart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: { labels: [], datasets: [{ label: 'Response ms', data: rtData, borderColor: '#38bdf8', tension: 0.25 }] },
  options: { scales: { x: { display: false }, y: { beginAtZero: true } }, plugins:{legend:{display:false}} }
});
async function loadMetrics() {
  const r = await fetch('/metrics');
  const m = await r.json();
  document.getElementById('m_req').innerText = m.request_count;
  document.getElementById('m_rt').innerText = m.avg_response_ms.toFixed(1);
  document.getElementById('m_hit').innerText = (m.cache_hit_ratio*100).toFixed(1);
  document.getElementById('m_counts').innerText = `${m.approvals} / ${m.otp_verifications} / ${m.blocks}`;
}
setInterval(loadMetrics, 1000); loadMetrics();
const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.type === 'risk') {
    const s = document.getElementById('stream');
    const d = document.createElement('div');
    let cls = 'pill approve', tag='APPROVE';
    if (msg.decision === 'BLOCK') { cls = 'pill block'; tag='BLOCK'; }
    else if (msg.decision === 'OTP_VERIFICATION') { cls = 'pill otp'; tag='OTP'; }
    const flag = msg.flagged ? '<span class=\"pill flag\">FLAG</span> ' : '';
    d.innerHTML = flag + '<span class=\"' + cls + '\">' + tag + '</span> ' +
                  'user=' + msg.user_id + ' risk=' + (msg.risk*100).toFixed(1) + '%';
    s.prepend(d);
    const now = new Date();
    chart.data.labels.push('');
    chart.data.datasets[0].data.push(Math.round(msg.risk*100)); 
    if (chart.data.labels.length > 60) { chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
    chart.update('none');
  }
  if (msg.type === 'precheck') {
    const s = document.getElementById('stream');
    const d = document.createElement('div');
    d.innerHTML = '<span class=\"pill flag\">FLAG</span> user=' + msg.user_id + ' risk=' + (msg.risk*100).toFixed(1) + '% ' +
      '<button class=\"btn\" id=\"btnApprove\">Approve</button> ' +
      '<button class=\"btn\" id=\"btnBlock\" style=\"background:#ef4444;color:white\">Block</button>';
    s.prepend(d);
    document.getElementById('btnApprove').onclick = async () => {
      const r = await fetch('/confirm', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ txn_hash: msg.txn_hash, approve: true }) });
      await r.json();
    };
    document.getElementById('btnBlock').onclick = async () => {
      const r = await fetch('/confirm', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ txn_hash: msg.txn_hash, approve: false }) });
      await r.json();
    };
  }
};
document.getElementById('btnSend').onclick = async () => {
  const payload = {
    user_id: document.getElementById('f_user').value || 'user_42',
    amount: parseFloat(document.getElementById('f_amount').value || '25000'),
    location: document.getElementById('f_location').value || 'Delhi',
    device_id: document.getElementById('f_device').value || 'device_78',
    merchant: document.getElementById('f_merchant').value || 'Electronics',
    timestamp: document.getElementById('f_time').value || '23:12'
  };
  const r = await fetch('/precheck', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const j = await r.json();
  if (!j.flagged) {
    const r2 = await fetch('/transaction', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const j2 = await r2.json();
    document.getElementById('lastResp').innerText = 'Decision: ' + j2.decision + ' • Risk: ' + (j2.explanation.risk_score*100).toFixed(1) + '%';
  } else {
    document.getElementById('lastResp').innerText = 'Flagged: risk ' + (j.explanation.risk_score*100).toFixed(1) + '%';
  }
};
</script>
</body>
</html>
"""

@app.get("/")
async def dashboard():
    return HTMLResponse(dashboard_html)
