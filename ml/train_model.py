"""
Train fraud detection model using LightGBM and save as joblib.
"""
from typing import List
import argparse
import os
import joblib
import pandas as pd
from lightgbm import LGBMClassifier
from .feature_engineering import build_training_features, REQUIRED_FEATURES

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, help="Path to CSV dataset with columns: user_id, amount, timestamp, distance, device_risk_score, merchant_risk_score, account_created_at, failed, label")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "fraud_model.pkl"))
    args = ap.parse_args()

    df = pd.read_csv(args.dataset)
    df = build_training_features(df)
    features = [c for c in REQUIRED_FEATURES if c in df.columns]
    X = df[features]
    y = df["label"]
    model = LGBMClassifier(n_estimators=200, learning_rate=0.05, max_depth=-1, n_jobs=-1)
    model.fit(X, y)
    # simple evaluation
    acc = float((model.predict(X) == y).mean())
    obj = {"model": model, "features": features, "metrics": {"train_accuracy": acc}}
    joblib.dump(obj, args.out)
    print(f"Saved model to {args.out} with features={features} train_accuracy={acc:.3f}")

if __name__ == "__main__":
    main()
