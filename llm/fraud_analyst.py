"""
LLM-style analyst that formats reasons into natural language insights.
"""
from typing import List, Dict

def explain_natural(decision: str, risk_score: float, reasons: List[str], context: Dict[str, str] | None = None) -> str:
    parts = []
    if "new_device" in reasons or "device_anomaly" in reasons:
        parts.append("made from a new or unusual device")
    if "location_anomaly" in reasons or "unusual_location" in reasons:
        parts.append("originated from a different city or location than usual")
    if "odd_hour" in reasons or "time_anomaly" in reasons:
        parts.append("occurred at an unusual hour")
    if "amount_spike" in reasons or "amount_deviation" in reasons:
        parts.append("has an amount significantly higher than normal")
    if "mule_network_suspected" in reasons or "suspicious_cluster" in reasons:
        parts.append("involves connections associated with mule networks")
    base = "This transaction appears suspicious because it " + ", ".join(parts) + "."
    tail = f" Decision: {decision}. Risk: {int(risk_score*100)}%."
    return base + tail
