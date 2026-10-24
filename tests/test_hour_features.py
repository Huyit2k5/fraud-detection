import json
import math

import pytest

from config import MODEL_FEATURE_COLS
from spark_etl import add_hour_features, fit_amount_time_scaler, save_scaler_params


def test_add_hour_features(spark):
    df = spark.createDataFrame([(float(t),) for t in (0, 10800, 82800, 97200, 5400)], ["Time"])
    rows = {r["Time"]: r for r in add_hour_features(df).collect()}

    assert [rows[t]["Hour"] for t in (0, 10800, 82800, 97200, 5400)] == [0, 3, 23, 3, 1]
    assert rows[0]["Hour_sin"] == pytest.approx(0.0, abs=1e-9)
    assert rows[0]["Hour_cos"] == pytest.approx(1.0)
    assert rows[10800]["Hour_sin"] == pytest.approx(0.70710678)
    assert rows[10800]["Hour_cos"] == pytest.approx(0.70710678)
    assert rows[97200]["Hour_sin"] == pytest.approx(rows[10800]["Hour_sin"])  # 3h ngày 2 == 3h ngày 1
    assert rows[82800]["Hour_cos"] == pytest.approx(0.96592583)  # 23h sát 0h
    assert rows[5400]["Hour_sin"] == pytest.approx(math.sin(2 * math.pi * 1.5 / 24))  # giờ có phần lẻ


def test_model_feature_cols():
    assert MODEL_FEATURE_COLS[:3] == ["Hour_sin", "Hour_cos", "Amount_scaled"]
    assert len(MODEL_FEATURE_COLS) == 31
    assert "Time_scaled" not in MODEL_FEATURE_COLS


def test_save_scaler_params(spark, tmp_path):
    df = spark.createDataFrame([(0.0, 0.0), (10.0, 100.0), (20.0, 200.0)], ["Amount", "Time"])
    path = tmp_path / "scaler.json"
    save_scaler_params(fit_amount_time_scaler(df), path)
    p = json.loads(path.read_text(encoding="utf-8"))

    # Spark dùng độ lệch chuẩn mẫu: std của [0, 10, 20] = 10.
    assert p["amount_mean"] == pytest.approx(10.0)
    assert p["amount_std"] == pytest.approx(10.0)
    assert p["time_mean"] == pytest.approx(100.0)
