"""Cấu hình đường dẫn và hằng số dùng chung cho toàn bộ pipeline."""

import os
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

# Backend lưu trữ dữ liệu: "local" (mặc định, thư mục data/ trên đĩa) hoặc "hdfs"
# (HDFS pseudo-cluster chạy bằng docker-compose.hdfs.yml — xem README).
DATA_BACKEND = os.environ.get("DATA_BACKEND", "local").strip().lower()
# Số luồng Spark (local[N]) - mặc định 4 để máy laptop vẫn chạy mượt khi demo.
SPARK_CORES = int(os.environ.get("SPARK_CORES", "4"))
HDFS_NAMENODE_URI = os.environ.get("HDFS_NAMENODE_URI", "hdfs://localhost:9000")
HDFS_WEBHDFS_URL = os.environ.get("HDFS_WEBHDFS_URL", "http://localhost:9870")


def data_path(name: str) -> str:
    """Trả về đường dẫn đọc/ghi dữ liệu theo DATA_BACKEND hiện tại.

    - "local": đường dẫn tuyệt đối tới data/<name> trên đĩa.
    - "hdfs": URI hdfs://<namenode>/data/<name> (Spark tự hiểu scheme này).
    """
    if DATA_BACKEND == "hdfs":
        return f"{HDFS_NAMENODE_URI}/data/{name}"
    return str(DATA_DIR / name)


def local_uri(path: Path) -> str:
    """URI file:// tường minh cho 1 đường dẫn local, để dùng khi Spark đọc/ghi qua
    ml.util.MLWriter/MLReader (model Spark MLlib) — các model LUÔN lưu local trong models/,
    kể cả khi DATA_BACKEND=hdfs (fs.defaultFS trỏ sang HDFS). Không ép rõ scheme này thì Spark
    sẽ diễn giải đường dẫn Windows tuyệt đối (vd. "D:\\...") là đường dẫn HDFS -> lỗi
    InvalidPathException.
    """
    return path.as_uri()


# Đường dẫn dữ liệu, tự động trỏ tới local hoặc HDFS theo DATA_BACKEND.
RAW_CSV_PATH = RAW_DIR / "creditcard.csv"  # dùng riêng cho các check filesystem local (xem run_pipeline.py)
RAW_CSV_DATA_PATH = data_path("raw/creditcard.csv")
CLEANED_PARQUET_PATH = data_path("processed/cleaned.parquet")
TRAIN_PARQUET_PATH = data_path("processed/train.parquet")
TEST_PARQUET_PATH = data_path("processed/test.parquet")
# Train + cột class_weight (cùng số dòng với TRAIN_PARQUET_PATH), dùng cho Spark MLlib weightCol
TRAIN_WEIGHTED_PARQUET_PATH = data_path("processed/train_weighted.parquet")
# Train sau khi oversample bằng SMOTE (nhiều dòng hơn), lựa chọn thay thế để thử nghiệm
TRAIN_BALANCED_PARQUET_PATH = data_path("processed/train_balanced.parquet")

# Cột đặc trưng của dataset Credit Card Fraud Detection (Kaggle - ULB):
# Time, V1..V28 (PCA components), Amount, Class (0 = bình thường, 1 = gian lận)
LABEL_COL = "Class"
AMOUNT_COL = "Amount"
TIME_COL = "Time"
PCA_COLS = [f"V{i}" for i in range(1, 29)]

# FEATURE_COLS: dùng cho EDA/trực quan hóa (Time, Amount ở thang đo GỐC, dễ đọc/diễn giải)
FEATURE_COLS = [TIME_COL, AMOUNT_COL] + PCA_COLS

# Đặc trưng giờ trong ngày, tạo từ cột Time (số giây kể từ giao dịch đầu tiên, dữ liệu kéo dài
# 48 giờ) với giả định giao dịch đầu tiên diễn ra lúc 0h:
# - Hour (0-23): chỉ dùng để hiển thị/vẽ biểu đồ.
# - Hour_sin/Hour_cos: mã hóa giờ theo vòng tròn (vị trí kim đồng hồ) để 23h và 0h nằm sát nhau,
#   giúp cả Logistic Regression học được quy luật "ban đêm rủi ro cao" (không đơn điệu theo giờ).
SECONDS_PER_DAY = 86_400
HOUR_COL = "Hour"
HOUR_SIN_COL = "Hour_sin"
HOUR_COS_COL = "Hour_cos"

# MODEL_FEATURE_COLS: dùng để HUẤN LUYỆN mô hình. Amount đã chuẩn hóa (StandardScaler) thành
# Amount_scaled để cùng thang đo với V1..V28 (~N(0,1)) - quan trọng với Isolation Forest và
# Logistic Regression, nếu không Amount (biên độ lớn) sẽ lấn át tín hiệu của các thành phần PCA.
# KHÔNG dùng Time_scaled: Time chỉ tăng dần và vì chia train/test theo thời gian, mọi giá trị Time
# của tập test đều nằm ngoài khoảng giá trị của tập train -> đặc trưng này gây nhiễu. Thông tin
# thời gian được đưa vào qua Hour_sin/Hour_cos.
TIME_SCALED_COL = "Time_scaled"
AMOUNT_SCALED_COL = "Amount_scaled"
MODEL_FEATURE_COLS = [HOUR_SIN_COL, HOUR_COS_COL, AMOUNT_SCALED_COL] + PCA_COLS

# Tham số StandardScaler (mean/std của Amount, Time) học được ở bước ETL - dùng lại khi suy luận.
SCALER_PARAMS_PATH = MODELS_DIR / "feature_scaler.json"
# Gói suy luận (mô hình dạng JSON + dữ liệu) cho giao diện web, xuất ở bước đánh giá.
INFERENCE_DIR = MODELS_DIR / "inference"

# Tỉ lệ chia tập train/test theo thời gian (time-based split)
TRAIN_RATIO = 0.7

RANDOM_SEED = 42

for d in (DATA_DIR, RAW_DIR, PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR, MODELS_DIR):
    d.mkdir(parents=True, exist_ok=True)
