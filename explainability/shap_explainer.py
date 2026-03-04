"""
SHAP explanations for fraud model.
"""
from typing import Dict, List
import numpy as np

class ShapExplainer:
    def __init__(self, model, feature_names: List[str]):
        self.model = model
        self.feature_names = feature_names
        try:
            import shap  # type: ignore
            self._shap = shap
            self.explainer = shap.TreeExplainer(model)
        except Exception:
            self._shap = None
            self.explainer = None

    def top_reasons(self, features: Dict[str, float], k: int = 3) -> List[str]:
        if not self.explainer or not self.feature_names:
            return []
        x = np.array([[features.get(n, 0.0) for n in self.feature_names]], dtype=float)
        try:
            vals = self.explainer.shap_values(x)
            sv = vals[1][0] if isinstance(vals, list) else vals[0]
            pairs = list(zip(self.feature_names, sv))
            pairs.sort(key=lambda t: abs(t[1]), reverse=True)
            return [p[0] for p in pairs[:k]]
        except Exception:
            return []
