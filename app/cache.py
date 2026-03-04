import hashlib
import json
from typing import Any, Dict, Optional
from redis.asyncio import Redis
from .config import REDIS_URL, CACHE_TTL_SECONDS, RATE_LIMIT_MAX_PER_MIN

redis: Optional[Redis] = None

class _Mem:
    def __init__(self):
        self.kv: Dict[str, str] = {}
        self.h: Dict[str, Dict[str, str]] = {}
        self.counters: Dict[str, int] = {}
    async def get(self, k: str):
        return self.kv.get(k)
    async def set(self, k: str, v: str, ex: Optional[int] = None):
        self.kv[k] = v
    async def hgetall(self, k: str):
        return self.h.get(k, {})
    async def hset(self, k: str, mapping: Dict[str, str]):
        self.h.setdefault(k, {}).update(mapping)
    async def incr(self, k: str):
        v = self.counters.get(k, 0) + 1
        self.counters[k] = v
        return v
    async def expire(self, k: str, sec: int):
        return True

async def init_redis() -> Redis:
    global redis
    if redis is None:
        try:
            r = Redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
            try:
                await r.ping()
                redis = r
            except Exception:
                redis = _Mem()
        except Exception:
            redis = _Mem()
    return redis

def transaction_key(payload: Dict[str, Any]) -> str:
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "txn:" + hashlib.sha256(s.encode()).hexdigest()

async def cache_get(key: str) -> Optional[Dict[str, Any]]:
    r = await init_redis()
    v = await r.get(key)
    if v is None:
        return None
    return json.loads(v)

async def cache_set(key: str, value: Dict[str, Any], ttl: int = CACHE_TTL_SECONDS) -> None:
    r = await init_redis()
    await r.set(key, json.dumps(value), ex=ttl)

async def get_user_profile(user_id: str) -> Dict[str, Any]:
    r = await init_redis()
    key = f"user:{user_id}:profile"
    v = await r.hgetall(key)
    if not v:
        return {
            "avg_amount": 500.0,
            "std_amount": 200.0,
            "frequent_locations": json.dumps(["Delhi"]),
            "frequent_geo_locations": json.dumps([{"lat": 28.6139, "lon": 77.2090}]),
            "device_history": json.dumps([]),
            "transaction_frequency": 1,
        }
    return {
        "avg_amount": float(v.get("avg_amount", 500.0)),
        "std_amount": float(v.get("std_amount", 200.0)),
        "frequent_locations": v.get("frequent_locations", json.dumps(["Delhi"])),
        "frequent_geo_locations": v.get("frequent_geo_locations", json.dumps([{"lat": 28.6139, "lon": 77.2090}])),
        "device_history": v.get("device_history", json.dumps([])),
        "transaction_frequency": int(v.get("transaction_frequency", 1)),
    }

async def update_user_profile(user_id: str, fields: Dict[str, Any]) -> None:
    r = await init_redis()
    key = f"user:{user_id}:profile"
    await r.hset(key, mapping={k: str(v) for k, v in fields.items()})

async def rate_limit_allow(user_id: str) -> bool:
    r = await init_redis()
    key = f"ratelimit:{user_id}"
    v = await r.incr(key)
    if v == 1:
        await r.expire(key, 60)
    return v <= RATE_LIMIT_MAX_PER_MIN

async def set_callback(user_id: str, url: str, secret: str) -> None:
    r = await init_redis()
    key = f"user:{user_id}:callback"
    await r.hset(key, mapping={"url": url, "secret": secret})

async def get_callback(user_id: str) -> Dict[str, Any]:
    r = await init_redis()
    key = f"user:{user_id}:callback"
    v = await r.hgetall(key)
    return v or {}

async def pending_set(txn_hash: str, data: Dict[str, Any], ttl: int = 120) -> None:
    r = await init_redis()
    key = f"pending:{txn_hash}"
    await r.set(key, json.dumps(data), ex=ttl)

async def pending_get(txn_hash: str) -> Optional[Dict[str, Any]]:
    r = await init_redis()
    key = f"pending:{txn_hash}"
    v = await r.get(key)
    return json.loads(v) if v else None

async def pending_clear(txn_hash: str) -> None:
    r = await init_redis()
    key = f"pending:{txn_hash}"
    await r.set(key, "", ex=1)

async def set_mobile(user_id: str, url: str, phone: str) -> None:
    r = await init_redis()
    key = f"user:{user_id}:mobile"
    await r.hset(key, mapping={"url": url, "phone": phone})

async def get_mobile(user_id: str) -> Dict[str, Any]:
    r = await init_redis()
    key = f"user:{user_id}:mobile"
    v = await r.hgetall(key)
    return v or {}
