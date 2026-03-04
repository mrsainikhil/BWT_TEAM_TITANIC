from typing import Dict, Any
import math

class RiskModel:
    def __init__(self):
        self.weights = {
            "amount": 0.00001,
            "merchant_electronics": 0.2,
            "merchant_luxury": 0.25,
            "merchant_crypto": 0.3,
            "odd_hour": 0.15,
            "new_device": 0.2,
            "unusual_location": 0.2,
        }
        self.bias = -2.0

    def predict_proba(self, txn: Dict[str, Any]) -> float:
        x = 0.0
        x += self.weights["amount"] * float(txn.get("amount", 0.0))
        m = str(txn.get("merchant", "")).lower()
        if m == "electronics":
            x += self.weights["merchant_electronics"]
        if m == "luxury":
            x += self.weights["merchant_luxury"]
        if m == "crypto":
            x += self.weights["merchant_crypto"]
        ts = str(txn.get("timestamp", "00:00"))
        try:
            h = int(ts.split(":")[0])
        except:
            h = 0
        if h < 6 or h > 22:
            x += self.weights["odd_hour"]
        if txn.get("new_device_flag"):
            x += self.weights["new_device"]
        if txn.get("unusual_location_flag"):
            x += self.weights["unusual_location"]
        x += self.bias
        return 1.0 / (1.0 + math.exp(-x))

model = RiskModel()
