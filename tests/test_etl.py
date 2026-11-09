import json

import pytest

import spark_etl
from config import MODEL_FEATURE_COLS, PCA_COLS
from spark_etl import fit_amount_time_scaler, save_scaler_params


def test_model_feature_cols():
    # Mô hình chỉ dùng số tiền đã chuẩn hóa + 28 thành phần PCA; không dùng thông tin thời gian.
    assert MODEL_FEATURE_COLS == ["Amount_scaled"] + PCA_COLS
    assert not any(c.startswith(("Hour", "Time")) for c in MODEL_FEATURE_COLS)


def test_no_hour_feature_in_etl():
    assert not hasattr(spark_etl, "add_hour_features")


def test_save_scaler_params(spark, tmp_path):
    df = spark.createDataFrame([(0.0, 0.0), (10.0, 100.0), (20.0, 200.0)], ["Amount", "Time"])
    path = tmp_path / "scaler.json"
    save_scaler_params(fit_amount_time_scaler(df), path)
    p = json.loads(path.read_text(encoding="utf-8"))

    # Spark dùng độ lệch chuẩn mẫu: std của [0, 10, 20] = 10.
    assert p["amount_mean"] == pytest.approx(10.0)
    assert p["amount_std"] == pytest.approx(10.0)
