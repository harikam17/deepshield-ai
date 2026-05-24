import json
import os
from typing import List, Dict, Any

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
MAX_HISTORY = 500  # Cap to prevent unbounded growth


def load_history() -> List[Dict[str, Any]]:
    """Load prediction history from JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except (json.JSONDecodeError, IOError):
        return []


def save_history_entry(entry: Dict[str, Any]) -> None:
    """Append a new prediction entry to history."""
    history = load_history()
    history.insert(0, entry)  # Newest first

    # Cap history size
    if len(history) > MAX_HISTORY:
        history = history[:MAX_HISTORY]

    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except IOError as e:
        print(f"[Utils] Warning: Could not save history: {e}")


def compute_stats(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate statistics from prediction history."""
    total = len(history)

    if total == 0:
        return {
            "total_scans": 0,
            "fake_count": 0,
            "real_count": 0,
            "uncertain_count": 0,
            "fake_rate": 0.0,
            "real_rate": 0.0,
            "avg_confidence": 0.0,
            "avg_risk_score": 0.0,
            "high_risk_count": 0,
        }

    fake_count = sum(1 for h in history if h.get("result") == "FAKE")
    real_count = sum(1 for h in history if h.get("result") == "REAL")
    uncertain_count = sum(1 for h in history if h.get("result") == "UNCERTAIN")

    confidences = [h["confidence"] for h in history if "confidence" in h]
    risks = [h["risk_score"] for h in history if "risk_score" in h]

    avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0.0
    avg_risk = round(sum(risks) / len(risks), 1) if risks else 0.0

    high_risk_count = sum(1 for r in risks if r >= 60)

    return {
        "total_scans": total,
        "fake_count": fake_count,
        "real_count": real_count,
        "uncertain_count": uncertain_count,
        "fake_rate": round(fake_count / total * 100, 1),
        "real_rate": round(real_count / total * 100, 1),
        "avg_confidence": avg_confidence,
        "avg_risk_score": avg_risk,
        "high_risk_count": high_risk_count,
    }

