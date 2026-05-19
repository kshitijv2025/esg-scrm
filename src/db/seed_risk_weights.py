"""
Seed default risk prediction weights to data/risk_weights.json.

Run once: python -m src.db.seed_risk_weights
"""
import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_WEIGHTS_PATH = _DATA_DIR / "risk_weights.json"

DEFAULT_WEIGHTS = {
    "risk_tier": 0.30,
    "risk_flags": 0.25,
    "certifications": 0.15,
    "questionnaire": 0.15,
    "country": 0.15,
}


def seed_risk_weights() -> None:
    """Write default risk weights if the file does not already exist."""
    if _WEIGHTS_PATH.exists():
        print(f"risk_weights.json already exists at {_WEIGHTS_PATH} — skipping")
        return

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_WEIGHTS_PATH, "w") as f:
        json.dump(DEFAULT_WEIGHTS, f, indent=2)

    print(f"Seeded default risk weights to {_WEIGHTS_PATH}")


if __name__ == "__main__":
    seed_risk_weights()
