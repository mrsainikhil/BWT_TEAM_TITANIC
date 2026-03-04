"""
Feature engineering utilities for fraud model training.
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np

REQUIRED_FEATURES = [
    "transaction_velocity_1min",
    "transaction_velocity_5min",
    "transaction_velocity_1hr",
    "amount_zscore",
    "distance_from_last_transaction",
    "device_risk_score",
    "merchant_risk_score",
    "account_age_days",
    "failed_transactions_last_hour",
    "amount",
]

def build_training_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["user_id", "timestamp"])
    g = df.groupby("user_id")
    df["ts_sec"] = df["timestamp"].astype("int64") // 10**9
    # compute velocity as count of txns in prior windows by per-user
    v1 = []; v5 = []; v60 = []
    for uid, group in df.groupby("user_id"):
        secs = group["ts_sec"].tolist()
        idxs = group.index.tolist()
        for i, t in enumerate(secs):
            def count_in(win): return sum(1 for j in range(max(0, i-1000), i+1) if t - secs[j] <= win)
            v1.append((idxs[i], float(count_in(60))))
            v5.append((idxs[i], float(count_in(300))))
            v60.append((idxs[i], float(count_in(3600))))
    df["transaction_velocity_1min"] = 0.0
    df["transaction_velocity_5min"] = 0.0
    df["transaction_velocity_1hr"] = 0.0
    for idx, val in v1: df.at[idx, "transaction_velocity_1min"] = val
    for idx, val in v5: df.at[idx, "transaction_velocity_5min"] = val
    for idx, val in v60: df.at[idx, "transaction_velocity_1hr"] = val
    g_amt = g["amount"]
    mu = g_amt.transform("mean")
    sig = g_amt.transform("std").fillna(1.0)
    df["amount_zscore"] = (df["amount"] - mu) / sig
    df["distance_from_last_transaction"] = g["distance"].shift(1).fillna(0.0) if "distance" in df.columns else 0.0
    df["device_risk_score"] = df["device_risk_score"] if "device_risk_score" in df.columns else 0.0
    df["merchant_risk_score"] = df["merchant_risk_score"] if "merchant_risk_score" in df.columns else 0.0
    df["account_age_days"] = (df["timestamp"] - pd.to_datetime(df["account_created_at"])).dt.days if "account_created_at" in df.columns else 0
    if "failed" in df.columns:
        fh = []
        for uid, group in df.groupby("user_id"):
            secs = group["ts_sec"].tolist()
            fails = group["failed"].tolist()
            idxs = group.index.tolist()
            for i, t in enumerate(secs):
                cnt = 0
                for j in range(max(0, i-1000), i+1):
                    if t - secs[j] <= 3600 and fails[j]:
                        cnt += 1
                fh.append((idxs[i], float(cnt)))
        df["failed_transactions_last_hour"] = 0.0
        for idx, val in fh: df.at[idx, "failed_transactions_last_hour"] = val
    else:
        df["failed_transactions_last_hour"] = 0.0
    return df
