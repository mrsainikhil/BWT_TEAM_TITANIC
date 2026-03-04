import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT_MAX_PER_MIN = int(os.getenv("RATE_LIMIT_MAX_PER_MIN", "60"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
WS_CHANNEL = "fraud_ws_stream"
MODEL_FLAG_THRESHOLD = float(os.getenv("MODEL_FLAG_THRESHOLD", "0.6"))
GEO_DISTANCE_THRESHOLD_KM = float(os.getenv("GEO_DISTANCE_THRESHOLD_KM", "50"))
SMS_WEBHOOK_URL = os.getenv("SMS_WEBHOOK_URL", "")
SMS_SENDER = os.getenv("SMS_SENDER", "SentinelPay")
RISK_WEIGHTS = {
    "rule": float(os.getenv("RISK_WEIGHT_RULE", "0.25")),
    "ml": float(os.getenv("RISK_WEIGHT_ML", "0.45")),
    "anomaly": float(os.getenv("RISK_WEIGHT_ANOMALY", "0.2")),
    "graph": float(os.getenv("RISK_WEIGHT_GRAPH", "0.1")),
}
STREAM_TXN = os.getenv("STREAM_TXN", "stream:txn")
STREAM_DECISION = os.getenv("STREAM_DECISION", "stream:decision")
MODEL_PATH = os.getenv("MODEL_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml", "fraud_model.pkl")))
