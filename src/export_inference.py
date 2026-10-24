"""
Xuất "gói suy luận" cho giao diện web (models/inference/), chạy ở cuối bước đánh giá.

Backend web suy luận KHÔNG khởi động Spark (quá chậm cho thanh trượt "nếu… thì…" và chế độ giám sát
trực tiếp), nên mô hình tốt nhất được xuất sang dạng JSON để tính lại bằng numpy:
- model.json   : mô hình (cây Random Forest hoặc hệ số Logistic Regression), ngưỡng, tham số chuẩn hóa.
- train.parquet, test.parquet : các cột cần cho suy luận/giải thích (local, kể cả khi DATA_BACKEND=hdfs).
- rates.json   : tỉ lệ gian lận theo khoảng số tiền và theo giờ (tính trên tập train).
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from pyspark.ml.classification import LogisticRegressionModel, RandomForestClassificationModel
from pyspark.sql import DataFrame

from config import (
    AMOUNT_COL,
    HOUR_COL,
    INFERENCE_DIR,
    LABEL_COL,
    MODEL_FEATURE_COLS,
    MODELS_DIR,
    SCALER_PARAMS_PATH,
    TIME_COL,
    TRAIN_PARQUET_PATH,
    local_uri,
)

EXPORTABLE_MODELS = {"Random Forest": "random_forest", "Logistic Regression": "logistic_regression"}
AMOUNT_EDGES = [0, 1, 10, 50, 100, 500, 1000, None]
AMOUNT_LABELS = ["<1 €", "1–10 €", "10–50 €", "50–100 €", "100–500 €", "500–1.000 €", ">1.000 €"]
BUNDLE_COLS = ["tx_id", TIME_COL, HOUR_COL, AMOUNT_COL, LABEL_COL] + MODEL_FEATURE_COLS


def export_rf(model: RandomForestClassificationModel) -> list[dict]:
    """Duyệt cấu trúc từng cây (qua py4j) thành mảng phẳng kiểu scikit-learn/shap.

    - Nút nội bộ: đi trái khi x[feature] <= threshold (quy ước ContinuousSplit của Spark).
    - values: P(gian lận) tại nút = stats[1] / sum(stats) - Spark lấy trung bình giá trị này qua các cây.
    - node_sample_weight: sum(impurityStats.stats) - tổng trọng số mẫu tại nút (cần cho TreeSHAP)."""
    trees = []
    for tree in model.trees:
        left, right, feats, thrs, values, weights = [], [], [], [], [], []

        def assign(node) -> int:
            """Đánh số nút theo thứ tự duyệt trước (gốc = 0), trả về chỉ số của nút."""
            me = len(values)
            stats = [float(s) for s in node.impurityStats().stats()]
            total = sum(stats)
            left.append(-1)
            right.append(-1)
            feats.append(-1)
            thrs.append(0.0)
            values.append(stats[1] / total if total > 0 and len(stats) > 1 else 0.0)
            weights.append(total)
            if node.getClass().getSimpleName() == "InternalNode":
                split = node.split()
                feats[me] = int(split.featureIndex())
                thrs[me] = float(split.threshold())
                left[me] = assign(node.leftChild())
                right[me] = assign(node.rightChild())
            return me

        assign(tree._java_obj.rootNode())
        trees.append({"children_left": left, "children_right": right, "features": feats,
                      "thresholds": thrs, "values": values, "node_sample_weight": weights})
    return trees


def export_lr(model: LogisticRegressionModel, train_pdf: pd.DataFrame) -> dict:
    return {
        "coefficients": [float(c) for c in model.coefficients.toArray()],
        "intercept": float(model.intercept),
        "feature_means": [float(m) for m in train_pdf[MODEL_FEATURE_COLS].mean().to_numpy()],
    }


def choose_model(comparison_df: pd.DataFrame) -> tuple[str, str]:
    """Chọn mô hình có PR-AUC cao nhất trong số các mô hình xuất được (RF, LR)."""
    ranked = comparison_df.sort_values("pr_auc", ascending=False)
    candidates = ranked[ranked["model"].isin(EXPORTABLE_MODELS)]
    if candidates.empty:
        raise ValueError("Không có mô hình Random Forest/Logistic Regression trong bảng so sánh.")
    best = candidates.iloc[0]
    note = f"{best['model']} có PR-AUC cao nhất ({best['pr_auc']:.4f}) trên tập test"
    top = ranked.iloc[0]
    if top["model"] != best["model"]:
        note += (f"; {top['model']} có PR-AUC cao hơn ({top['pr_auc']:.4f}) nhưng không xuất được "
                 "cho giao diện")
    return best["model"], note


def compute_rates(train_pdf: pd.DataFrame) -> dict:
    """Tỉ lệ gian lận (0-1) theo khoảng số tiền (lo <= Amount < hi) và theo giờ trong ngày."""
    buckets = []
    for i, label in enumerate(AMOUNT_LABELS):
        lo, hi = AMOUNT_EDGES[i], AMOUNT_EDGES[i + 1]
        mask = train_pdf[AMOUNT_COL] >= lo
        if hi is not None:
            mask &= train_pdf[AMOUNT_COL] < hi
        n, fraud = int(mask.sum()), int(train_pdf.loc[mask, LABEL_COL].sum())
        buckets.append({"label": label, "lo": lo, "hi": hi, "n": n, "fraud": fraud,
                        "rate": fraud / n if n else 0.0})
    hours = []
    for h in range(24):
        mask = train_pdf[HOUR_COL] == h
        n, fraud = int(mask.sum()), int(train_pdf.loc[mask, LABEL_COL].sum())
        hours.append({"hour": h, "n": n, "fraud": fraud, "rate": fraud / n if n else 0.0})
    return {"overall_rate": float(train_pdf[LABEL_COL].mean()), "amount_buckets": buckets, "hours": hours}


def _to_bundle_pdf(df: DataFrame) -> pd.DataFrame:
    pdf = df.select([TIME_COL, HOUR_COL, AMOUNT_COL, LABEL_COL] + MODEL_FEATURE_COLS).toPandas()
    pdf = pdf.sort_values(TIME_COL, kind="stable").reset_index(drop=True)
    pdf.insert(0, "tx_id", np.arange(len(pdf)))
    return pdf[BUNDLE_COLS]


def export_inference_bundle(spark, test_df: DataFrame, comparison_df: pd.DataFrame,
                            thresholds: dict) -> Path:
    model_name, note = choose_model(comparison_df)
    key = EXPORTABLE_MODELS[model_name]
    train_pdf = _to_bundle_pdf(spark.read.parquet(str(TRAIN_PARQUET_PATH)))
    test_pdf = _to_bundle_pdf(test_df)
    scaler = json.loads(Path(SCALER_PARAMS_PATH).read_text(encoding="utf-8"))
    pr_auc = float(comparison_df.set_index("model").loc[model_name, "pr_auc"])

    meta = {
        "model_name": model_name, "model_type": key, "features": MODEL_FEATURE_COLS,
        "threshold": float(thresholds.get(key, {}).get("threshold", 0.5)), "pr_auc": pr_auc,
        "selection_note": note, "amount_mean": scaler["amount_mean"], "amount_std": scaler["amount_std"],
    }
    if key == "random_forest":
        meta["trees"] = export_rf(RandomForestClassificationModel.load(local_uri(MODELS_DIR / key)))
    else:
        meta.update(export_lr(LogisticRegressionModel.load(local_uri(MODELS_DIR / key)), train_pdf))

    # Ghi ra thư mục tạm rồi đổi tên: không bao giờ để lại gói dở dang cho backend đọc.
    tmp = INFERENCE_DIR.with_name(INFERENCE_DIR.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "model.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    train_pdf.to_parquet(tmp / "train.parquet", index=False)
    test_pdf.to_parquet(tmp / "test.parquet", index=False)
    (tmp / "rates.json").write_text(json.dumps(compute_rates(train_pdf), ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    shutil.rmtree(INFERENCE_DIR, ignore_errors=True)
    tmp.rename(INFERENCE_DIR)
    print(f"[Export] Đã xuất gói suy luận ({model_name}) -> {INFERENCE_DIR}")
    return INFERENCE_DIR
