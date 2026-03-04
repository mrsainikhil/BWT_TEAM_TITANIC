from typing import Dict, Any, List
import os
import joblib
import numpy as np
from app.config import MODEL_PATH

class FraudModel:
    def __init__(self):
        self.model = None
        self.feature_names: List[str] = []
        self._load()

    def _load(self):
        try:
            obj = joblib.load(MODEL_PATH)
            self.model = obj.get("model")
            self.feature_names = obj.get("features", [])
        except Exception:
            self.model = None
            self.feature_names = []

    def is_loaded(self) -> bool:
        return self.model is not None

    def predict_proba(self, features: Dict[str, float]) -> float:
        if not self.model or not self.feature_names:
            # fallback: simple heuristic using amount
            amt = float(features.get("amount", 0.0))
            return 1.0 / (1.0 + np.exp(-(amt / 100000.0 - 0.5)))
        x = np.array([[features.get(n, 0.0) for n in self.feature_names]], dtype=float)
        try:
            # LightGBM sklearn API predict_proba
            proba = self.model.predict_proba(x)
            return float(proba[0][1])
        except Exception:
            y = self.model.predict(x)
            return float(y[0])

model = FraudModel()
