"""Gói suy luận nhỏ, hợp lệ, dựng tay (không cần Spark) để kiểm thử backend."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from config import MODEL_FEATURE_COLS

AMOUNT_MEAN, AMOUNT_STD = 88.0, 250.0
I_AMOUNT = MODEL_FEATURE_COLS.index("Amount_scaled")
I_V14 = MODEL_FEATURE_COLS.index("V14")


def _tree(v_ll, v_lr, v_rl, v_rr, w=(40.0, 10.0, 30.0, 120.0)):
    """Cây độ sâu 2: V14 <= -1 ? (Amount_scaled <= 1 ? a : b) : (Amount_scaled <= 2 ? c : d)."""
    return {
        "children_left": [1, 2, -1, -1, 5, -1, -1],
        "children_right": [4, 3, -1, -1, 6, -1, -1],
        "features": [I_V14, I_AMOUNT, -1, -1, I_AMOUNT, -1, -1],
        "thresholds": [-1.0, 1.0, 0.0, 0.0, 2.0, 0.0, 0.0],
        "values": [0.3, 0.7, v_ll, v_lr, 0.05, v_rl, v_rr],
        "node_sample_weight": [sum(w), w[0] + w[1], w[0], w[1], w[2] + w[3], w[2], w[3]],
    }


TREES = [_tree(0.6, 0.95, 0.01, 0.3), _tree(0.7, 0.9, 0.02, 0.2), _tree(0.5, 0.99, 0.0, 0.4)]


def _frame(n: int, t0: float, rng) -> pd.DataFrame:
    time = np.sort(rng.uniform(t0, t0 + 40_000, n))
    hour_frac = (time % 86_400) / 3600
    amount = np.round(rng.exponential(80, n), 2)
    df = pd.DataFrame(rng.normal(size=(n, len(MODEL_FEATURE_COLS))), columns=MODEL_FEATURE_COLS)
    df["Hour_sin"] = np.sin(2 * np.pi * hour_frac / 24)
    df["Hour_cos"] = np.cos(2 * np.pi * hour_frac / 24)
    df["Amount_scaled"] = (amount - AMOUNT_MEAN) / AMOUNT_STD
    df.insert(0, "Class", (df["V14"] < -1.2).astype(int))
    df.insert(0, "Amount", amount)
    df.insert(0, "Hour", np.floor(hour_frac).astype(int))
    df.insert(0, "Time", time)
    df.insert(0, "tx_id", np.arange(n))
    return df


def write_fake_bundle(path: Path) -> Path:
    from export_inference import compute_rates

    rng = np.random.default_rng(7)
    train = _frame(200, 0, rng)
    test = _frame(50, 100_000, rng)
    path.mkdir(parents=True, exist_ok=True)
    meta = {
        "model_name": "Random Forest", "model_type": "random_forest", "features": MODEL_FEATURE_COLS,
        "threshold": 0.42, "pr_auc": 0.8, "selection_note": "kiểm thử",
        "amount_mean": AMOUNT_MEAN, "amount_std": AMOUNT_STD, "trees": TREES,
    }
    (path / "model.json").write_text(json.dumps(meta), encoding="utf-8")
    train.to_parquet(path / "train.parquet", index=False)
    test.to_parquet(path / "test.parquet", index=False)
    (path / "rates.json").write_text(json.dumps(compute_rates(train)), encoding="utf-8")
    return path
