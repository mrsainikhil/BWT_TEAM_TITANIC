"""
Synthetic fraud data generator.
"""
import random
import argparse
import pandas as pd
from datetime import datetime, timedelta

def generate(n_normal: int, n_fraud: int) -> pd.DataFrame:
    rows = []
    base_time = datetime.now()
    users = [f"user_{i}" for i in range(50)]
    devices = [f"device_{i}" for i in range(100)]
    merchants = ["Grocery", "Electronics", "Luxury", "Crypto", "Travel", "Dining"]
    for _ in range(n_normal):
        u = random.choice(users)
        t = base_time + timedelta(seconds=random.randint(0, 3600))
        amt = random.uniform(50, 500)
        rows.append({
            "user_id": u,
            "amount": amt,
            "timestamp": t.isoformat(),
            "distance": random.uniform(0, 5),
            "device_risk_score": 0.0,
            "merchant_risk_score": 0.1,
            "account_created_at": (t - timedelta(days=random.randint(30, 1000))).isoformat(),
            "failed": 0,
            "device_id": random.choice(devices),
            "merchant": random.choice(merchants),
            "label": 0,
        })
    for _ in range(n_fraud):
        u = random.choice(users)
        t = base_time + timedelta(seconds=random.randint(0, 3600))
        amt = random.uniform(1000, 150000)
        rows.append({
            "user_id": u,
            "amount": amt,
            "timestamp": t.isoformat(),
            "distance": random.uniform(20, 500),
            "device_risk_score": 0.7,
            "merchant_risk_score": 0.6,
            "account_created_at": (t - timedelta(days=random.randint(1, 200))).isoformat(),
            "failed": random.choice([0,1]),
            "device_id": random.choice(devices),
            "merchant": random.choice(["Electronics", "Luxury", "Crypto"]),
            "label": 1,
        })
    return pd.DataFrame(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--normal", type=int, default=5000)
    ap.add_argument("--fraud", type=int, default=1000)
    ap.add_argument("--out", default="fraud_dataset.csv")
    args = ap.parse_args()
    df = generate(args.normal, args.fraud)
    df.to_csv(args.out, index=False)
    print(f"Wrote {args.out} with {len(df)} rows")

if __name__ == "__main__":
    main()
