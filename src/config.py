"""Cấu hình đường dẫn và hằng số dùng chung cho toàn bộ pipeline."""

import sys
from pathlib import Path

# Đảm bảo in được tiếng Việt có dấu trên console Windows (mặc định cp1252/cp1258)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Thư mục gốc của dự án (một cấp trên thư mục src/)
ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = ROOT_DIR / "models"

# Đường dẫn dữ liệu.
# Trong môi trường học thuật, đây là thư mục cục bộ mô phỏng HDFS.
# Khi chạy trên cluster thật, đổi thành "hdfs://<namenode>:8020/data/raw/creditcard.csv".
RAW_CSV_PATH = RAW_DIR / "creditcard.csv"
CLEANED_PARQUET_PATH = PROCESSED_DIR / "cleaned.parquet"
TRAIN_PARQUET_PATH = PROCESSED_DIR / "train.parquet"
TEST_PARQUET_PATH = PROCESSED_DIR / "test.parquet"
# Train + cột class_weight (cùng số dòng với TRAIN_PARQUET_PATH), dùng cho Spark MLlib weightCol
TRAIN_WEIGHTED_PARQUET_PATH = PROCESSED_DIR / "train_weighted.parquet"
# Train sau khi oversample bằng SMOTE (nhiều dòng hơn), lựa chọn thay thế để thử nghiệm
TRAIN_BALANCED_PARQUET_PATH = PROCESSED_DIR / "train_balanced.parquet"

# Cột đặc trưng của dataset Credit Card Fraud Detection (Kaggle - ULB):
# Time, V1..V28 (PCA components), Amount, Class (0 = bình thường, 1 = gian lận)
LABEL_COL = "Class"
AMOUNT_COL = "Amount"
TIME_COL = "Time"
PCA_COLS = [f"V{i}" for i in range(1, 29)]

# FEATURE_COLS: dùng cho EDA/trực quan hóa (Time, Amount ở thang đo GỐC, dễ đọc/diễn giải)
FEATURE_COLS = [TIME_COL, AMOUNT_COL] + PCA_COLS

# MODEL_FEATURE_COLS: dùng để HUẤN LUYỆN mô hình. Time/Amount đã chuẩn hóa (StandardScaler)
# thành Time_scaled/Amount_scaled để cùng thang đo với V1..V28 (~N(0,1)) - quan trọng với
# Isolation Forest và Logistic Regression, nếu không Time/Amount (biên độ lớn) sẽ lấn át tín hiệu
# của các thành phần PCA.
TIME_SCALED_COL = "Time_scaled"
AMOUNT_SCALED_COL = "Amount_scaled"
MODEL_FEATURE_COLS = [TIME_SCALED_COL, AMOUNT_SCALED_COL] + PCA_COLS

# Tỉ lệ chia tập train/test theo thời gian (time-based split)
TRAIN_RATIO = 0.7

RANDOM_SEED = 42

for d in (DATA_DIR, RAW_DIR, PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR, MODELS_DIR):
    d.mkdir(parents=True, exist_ok=True)
