"""Đọc và kiểm tra gói suy luận (models/inference/) do bước đánh giá xuất ra."""

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from backend.runtime import LRRuntime, ModelRuntime, RFRuntime
from config import INFERENCE_DIR, MODEL_FEATURE_COLS

REQUIRED_FILES = ("model.json", "train.parquet", "test.parquet", "rates.json")
MODEL_PAYLOAD_KEYS = ("trees", "coefficients", "intercept", "feature_means")


class BundleError(Exception):
    """Gói suy luận thiếu hoặc không dùng được (thông báo tiếng Việt cho người dùng)."""


@dataclass
class Bundle:
    meta: dict
    runtime: ModelRuntime
    train: pd.DataFrame
    test: pd.DataFrame
    rates: dict


def load_bundle(path: Path = INFERENCE_DIR) -> Bundle:
    path = Path(path)
    if not all((path / f).exists() for f in REQUIRED_FILES):
        raise BundleError("Chưa có mô hình, hãy chạy pipeline (Huấn luyện & Đánh giá) trước.")
    model = json.loads((path / "model.json").read_text(encoding="utf-8"))
    if model.get("features") != MODEL_FEATURE_COLS:
        raise BundleError("Mô hình được huấn luyện với bộ đặc trưng cũ, hãy chạy lại pipeline.")

    if model["model_type"] == "random_forest":
        runtime = RFRuntime(model["trees"], model["features"])
    else:
        runtime = LRRuntime(model["coefficients"], model["intercept"], model["feature_means"], model["features"])
    meta = {k: v for k, v in model.items() if k not in MODEL_PAYLOAD_KEYS}
    return Bundle(
        meta=meta,
        runtime=runtime,
        train=pd.read_parquet(path / "train.parquet"),
        test=pd.read_parquet(path / "test.parquet"),
        rates=json.loads((path / "rates.json").read_text(encoding="utf-8")),
    )
