"""
Giai đoạn 5 của kế hoạch: Đánh giá và so sánh mô hình.

Vì dữ liệu mất cân bằng, KHÔNG dùng Accuracy. Tập trung vào:
- Precision, Recall, F1-score
- Confusion Matrix
- ROC-AUC và đặc biệt Precision-Recall AUC (quan trọng hơn ROC-AUC với dữ liệu mất cân bằng)

So sánh 3 mô hình: Logistic Regression, Random Forest, Isolation Forest.

Nếu đã chạy `tune_models.py`, file `models/thresholds.json` chứa ngưỡng phân loại đã tối ưu
(tối đa hóa F1 trên tập validation, KHÔNG phải test) cho Logistic Regression/Random Forest -
evaluate.py sẽ ưu tiên dùng ngưỡng này thay vì mặc định 0.5 của Spark MLlib. Nếu chưa chạy
tune_models.py, tự động dùng ngưỡng mặc định 0.5.

Chạy độc lập: python src/evaluate.py
"""

import json

import joblib
import numpy as np
import pandas as pd
from pyspark.ml.classification import LogisticRegressionModel, RandomForestClassificationModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql.functions import col
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from config import LABEL_COL, MODEL_FEATURE_COLS, MODELS_DIR, REPORTS_DIR, TEST_PARQUET_PATH, local_uri
from spark_etl import get_spark_session
from train_models import assemble_features


def load_thresholds() -> dict:
    """Đọc ngưỡng phân loại đã tối ưu từ tune_models.py, nếu có. Mặc định 0.5 nếu chưa tinh chỉnh."""
    path = MODELS_DIR / "thresholds.json"
    if not path.exists():
        return {"logistic_regression": {"threshold": 0.5}, "random_forest": {"threshold": 0.5}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute_metrics(y_true, y_pred, y_score, model_name: str) -> dict:
    """Tính bộ chỉ số chuẩn: Precision, Recall, F1, ROC-AUC, PR-AUC + confusion matrix."""
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_true, y_score) if len(set(y_true)) > 1 else float("nan")
    pr_auc = average_precision_score(y_true, y_score) if len(set(y_true)) > 1 else float("nan")

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    print(f"\n=== {model_name} ===")
    print(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")
    print(f"ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f}")
    print(f"Confusion matrix -> TN={tn} FP={fp} FN={fn} TP={tp}")

    return {
        "model": model_name,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def evaluate_spark_model(model, test_df, model_name: str, threshold: float = 0.5) -> dict:
    """Dùng vector_to_array (hàm built-in Spark, không phải Python UDF) để lấy xác suất
    lớp dương (1 = gian lận) từ cột probability - tránh lỗi Python worker crash khi
    toPandas() trên tập dữ liệu lớn.

    `threshold`: ngưỡng phân loại (score >= threshold -> dự đoán gian lận). Nếu đã chạy
    tune_models.py, đây là ngưỡng tối ưu hóa F1 trên tập validation; mặc định 0.5 nếu chưa
    tinh chỉnh - KHÔNG dùng cột "prediction" có sẵn của Spark (luôn cố định ở ngưỡng 0.5)."""
    predictions = model.transform(test_df).withColumn(
        "score", vector_to_array(col("probability"))[1]
    )

    pdf = predictions.select(LABEL_COL, "score").toPandas()
    y_true = pdf[LABEL_COL].values
    y_score = pdf["score"].values
    y_pred = (y_score >= threshold).astype(int)
    print(f"[Evaluate] {model_name}: ngưỡng phân loại = {threshold:.4f}")
    return compute_metrics(y_true, y_pred, y_score, model_name)


def evaluate_isolation_forest(iso_model, test_pdf: pd.DataFrame) -> dict:
    """Isolation Forest: decision_function càng âm càng bất thường.
    predict() trả -1 (anomaly) / 1 (normal) -> quy đổi về 1/0 để so sánh với nhãn thật."""
    X_test = test_pdf[MODEL_FEATURE_COLS]
    y_true = test_pdf[LABEL_COL].values

    raw_pred = iso_model.predict(X_test)          # -1 = anomaly, 1 = normal
    y_pred = np.where(raw_pred == -1, 1, 0)

    # score_samples càng cao càng "bình thường" -> đảo dấu để score cao = càng bất thường/gian lận
    y_score = -iso_model.score_samples(X_test)

    return compute_metrics(y_true, y_pred, y_score, "Isolation Forest")


def run_evaluation():
    spark = get_spark_session()
    try:
        test_df = spark.read.parquet(str(TEST_PARQUET_PATH))
        test_df = assemble_features(test_df)
        test_df.cache()

        lr_model = LogisticRegressionModel.load(local_uri(MODELS_DIR / "logistic_regression"))
        rf_model = RandomForestClassificationModel.load(local_uri(MODELS_DIR / "random_forest"))
        iso_model = joblib.load(MODELS_DIR / "isolation_forest.joblib")
        thresholds = load_thresholds()

        results = []
        results.append(evaluate_spark_model(
            lr_model, test_df, "Logistic Regression",
            threshold=thresholds["logistic_regression"]["threshold"],
        ))
        results.append(evaluate_spark_model(
            rf_model, test_df, "Random Forest",
            threshold=thresholds["random_forest"]["threshold"],
        ))

        test_pdf = test_df.select(MODEL_FEATURE_COLS + [LABEL_COL]).toPandas()
        results.append(evaluate_isolation_forest(iso_model, test_pdf))

        comparison_df = pd.DataFrame(results)
        out_path = REPORTS_DIR / "metrics_comparison.csv"
        comparison_df.to_csv(out_path, index=False)
        print(f"\n[Evaluate] Bảng so sánh 3 mô hình đã lưu -> {out_path}")
        print(comparison_df.to_string(index=False))

        return comparison_df
    finally:
        spark.stop()


if __name__ == "__main__":
    run_evaluation()
