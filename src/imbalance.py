"""
Giai đoạn 3 của kế hoạch: Xử lý dữ liệu mất cân bằng.

Cung cấp 2 hướng tiếp cận như trong kế hoạch:
1. Class weighting trực tiếp trong Spark MLlib (weightCol) — dùng cho Logistic Regression /
   Random Forest, không cần rời khỏi Spark.
2. Oversampling bằng SMOTE (imblearn) — thực hiện ở tầng Python/pandas sau khi lấy mẫu từ Spark,
   vì Spark MLlib chưa hỗ trợ SMOTE trực tiếp.

Chạy độc lập: python src/imbalance.py
"""

import pandas as pd
from imblearn.over_sampling import SMOTE
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from config import (
    LABEL_COL,
    MODEL_FEATURE_COLS,
    RANDOM_SEED,
    TRAIN_BALANCED_PARQUET_PATH,
    TRAIN_PARQUET_PATH,
    TRAIN_WEIGHTED_PARQUET_PATH,
)
from spark_etl import get_spark_session


def add_class_weight_column(df: DataFrame, label_col: str = LABEL_COL,
                             weight_col: str = "class_weight") -> DataFrame:
    """Thêm cột trọng số lớp (class weight) tỉ lệ nghịch với tần suất lớp,
    để dùng trực tiếp với `weightCol` trong LogisticRegression/RandomForest của Spark MLlib.
    Không cần thay đổi số lượng dòng dữ liệu (khác với oversampling/undersampling)."""
    counts = df.groupBy(label_col).count().collect()
    total = sum(r["count"] for r in counts)
    n_classes = len(counts)
    weights = {r[label_col]: total / (n_classes * r["count"]) for r in counts}
    print(f"[Imbalance] Trọng số lớp (class weight): {weights}")

    weight_expr = F.when(F.col(label_col) == 1, float(weights.get(1, 1.0))).otherwise(
        float(weights.get(0, 1.0))
    )
    return df.withColumn(weight_col, weight_expr)


def smote_oversample(train_df: DataFrame, sampling_strategy: float = 0.1,
                      seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Lấy mẫu train từ Spark DataFrame về pandas rồi áp dụng SMOTE.
    sampling_strategy=0.1 nghĩa là sau khi oversample, lớp thiểu số (gian lận)
    sẽ bằng 10% số lượng lớp đa số (tránh oversample quá mức 1:1 với dữ liệu rất mất cân bằng)."""
    pdf = train_df.select(MODEL_FEATURE_COLS + [LABEL_COL]).toPandas()

    X = pdf[MODEL_FEATURE_COLS]
    y = pdf[LABEL_COL]

    print(f"[SMOTE] Trước oversample: {y.value_counts().to_dict()}")
    smote = SMOTE(sampling_strategy=sampling_strategy, random_state=seed)
    X_res, y_res = smote.fit_resample(X, y)
    print(f"[SMOTE] Sau oversample: {y_res.value_counts().to_dict()}")

    balanced = X_res.copy()
    balanced[LABEL_COL] = y_res
    return balanced


def run_imbalance_handling():
    spark = get_spark_session()
    try:
        # Đọc train gốc (từ giai đoạn ETL) - KHÔNG ghi đè lại chính file này khi đang đọc lazy
        # từ nó, vì Spark sẽ lỗi "file does not exist" (đọc/ghi cùng path). Ghi ra path khác.
        train_df = spark.read.parquet(str(TRAIN_PARQUET_PATH))

        # Cách 1: gắn class weight (dùng trực tiếp trong Spark MLlib, giữ nguyên toàn bộ dữ liệu)
        weighted_df = add_class_weight_column(train_df)
        weighted_df.write.mode("overwrite").parquet(str(TRAIN_WEIGHTED_PARQUET_PATH))
        print(f"[Imbalance] Đã lưu train (có class_weight) -> {TRAIN_WEIGHTED_PARQUET_PATH}")

        # Cách 2: SMOTE oversample (dùng cho các mô hình cần dữ liệu train cân bằng hơn,
        # ví dụ Isolation Forest muốn so sánh, hoặc thử nghiệm thêm)
        balanced_pdf = smote_oversample(train_df)
        balanced_spark_df = spark.createDataFrame(balanced_pdf)
        balanced_spark_df = add_class_weight_column(balanced_spark_df)
        balanced_spark_df.write.mode("overwrite").parquet(str(TRAIN_BALANCED_PARQUET_PATH))
        print(f"[Imbalance] Đã lưu train balanced (SMOTE) -> {TRAIN_BALANCED_PARQUET_PATH}")
    finally:
        spark.stop()


if __name__ == "__main__":
    run_imbalance_handling()
