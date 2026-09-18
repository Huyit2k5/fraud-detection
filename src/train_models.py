"""
Giai đoạn 4 của kế hoạch: Xây dựng và huấn luyện mô hình.

3 mô hình theo kế hoạch:
- Logistic Regression (Spark MLlib) — baseline, dễ giải thích, dùng class_weight
- Random Forest (Spark MLlib) — xử lý tốt phi tuyến, dùng class_weight
- Isolation Forest (scikit-learn) — unsupervised, không cần nhãn khi train,
  train trên sample dữ liệu lấy từ Spark, chỉ dùng nhãn thật khi đánh giá.

Chạy độc lập: python src/train_models.py
"""

import joblib
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.feature import VectorAssembler
from pyspark.sql import DataFrame
from sklearn.ensemble import IsolationForest

from config import (
    LABEL_COL,
    MODEL_FEATURE_COLS,
    MODELS_DIR,
    RANDOM_SEED,
    TEST_PARQUET_PATH,
    TRAIN_WEIGHTED_PARQUET_PATH,
    local_uri,
)
from spark_etl import get_spark_session


def assemble_features(df: DataFrame, features_col: str = "features") -> DataFrame:
    assembler = VectorAssembler(inputCols=MODEL_FEATURE_COLS, outputCol=features_col)
    return assembler.transform(df)


def train_logistic_regression(train_df: DataFrame):
    print("[Train] Huấn luyện Logistic Regression (Spark MLlib)...")
    lr = LogisticRegression(
        featuresCol="features", labelCol=LABEL_COL, weightCol="class_weight",
        maxIter=100, regParam=0.01,
    )
    model = lr.fit(train_df)
    return model


def train_random_forest(train_df: DataFrame):
    print("[Train] Huấn luyện Random Forest (Spark MLlib)...")
    rf = RandomForestClassifier(
        featuresCol="features", labelCol=LABEL_COL, weightCol="class_weight",
        numTrees=100, maxDepth=8, seed=RANDOM_SEED,
    )
    model = rf.fit(train_df)
    return model


def train_isolation_forest(train_df: DataFrame, contamination: float = 0.01,
                            sample_size: int = 50_000):
    """Isolation Forest là unsupervised: KHÔNG dùng cột Class khi huấn luyện.
    Lấy sample từ Spark DataFrame về pandas/numpy để train bằng scikit-learn.

    Lưu ý về `contamination`: đặt đúng bằng tỉ lệ gian lận thật (~0.0017) sẽ khiến ngưỡng
    bất thường quá hẹp, dễ không trùng với các điểm gian lận thật (Precision/Recall gần 0),
    vì Isolation Forest coi "bất thường" là điểm bị cô lập trong TOÀN BỘ không gian đặc trưng,
    không nhất thiết trùng với đặc điểm gian lận. Nới contamination lên ~1% cho recall có ý
    nghĩa hơn (đánh đổi: precision thấp hơn) - đây là hạn chế đã biết của phương pháp
    unsupervised so với các mô hình supervised (Logistic Regression, Random Forest), nên được
    nêu rõ khi so sánh trong báo cáo."""
    print("[Train] Huấn luyện Isolation Forest (scikit-learn, unsupervised)...")
    pdf = train_df.select(MODEL_FEATURE_COLS).limit(sample_size).toPandas()

    iso = IsolationForest(
        n_estimators=200,
        contamination=contamination,  # tỉ lệ gian lận ước lượng, dùng để đặt ngưỡng
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    iso.fit(pdf[MODEL_FEATURE_COLS])
    return iso


def run_training():
    spark = get_spark_session()
    try:
        train_df = spark.read.parquet(str(TRAIN_WEIGHTED_PARQUET_PATH))
        train_df = assemble_features(train_df)
        train_df.cache()

        lr_model = train_logistic_regression(train_df)
        rf_model = train_random_forest(train_df)
        iso_model = train_isolation_forest(train_df)

        lr_path = MODELS_DIR / "logistic_regression"
        rf_path = MODELS_DIR / "random_forest"
        iso_path = MODELS_DIR / "isolation_forest.joblib"

        lr_model.write().overwrite().save(local_uri(lr_path))
        rf_model.write().overwrite().save(local_uri(rf_path))
        joblib.dump(iso_model, iso_path)

        print(f"[Train] Đã lưu Logistic Regression -> {lr_path}")
        print(f"[Train] Đã lưu Random Forest -> {rf_path}")
        print(f"[Train] Đã lưu Isolation Forest -> {iso_path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    run_training()
