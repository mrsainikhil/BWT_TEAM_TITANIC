from typing import Dict, Any, List, Tuple

def decide(risk_score: float, reasons: List[str]) -> Tuple[str, Dict[str, Any]]:
    if risk_score < 0.35:
        return "APPROVE", {"risk_score": risk_score, "reasons": reasons}
    if risk_score < 0.65:
        return "OTP_VERIFICATION", {"risk_score": risk_score, "reasons": reasons}
    return "BLOCK", {"risk_score": risk_score, "reasons": reasons}
