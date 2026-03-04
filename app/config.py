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
