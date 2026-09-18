"""
Script điều phối chạy toàn bộ pipeline phát hiện giao dịch bất thường,
theo đúng thứ tự các giai đoạn trong kế hoạch (ke-hoach-phat-hien-giao-dich-bat-thuong.md):

  1-2. ETL: đọc dữ liệu (Spark), EDA, làm sạch, chuẩn hóa, time-based split
  3.   Xử lý mất cân bằng dữ liệu
  4.   Huấn luyện 3 mô hình (Logistic Regression, Random Forest, Isolation Forest)
  5.   Đánh giá & so sánh mô hình
  6.   Trực quan hóa

Yêu cầu trước khi chạy:
  - Java 8/11/17 đã cài đặt (bắt buộc cho PySpark)
  - pip install -r requirements.txt
  - data/raw/creditcard.csv đã tồn tại (tải từ Kaggle hoặc chạy
    `python src/generate_synthetic_data.py` để sinh dữ liệu giả lập)

Chạy: python run_pipeline.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from config import DATA_BACKEND, RAW_CSV_DATA_PATH, RAW_CSV_PATH  # noqa: E402


def _step(title, fn):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)
    start = time.time()
    fn()
    print(f"[OK] '{title}' hoàn tất trong {time.time() - start:.1f}s")


def main():
    if DATA_BACKEND == "hdfs":
        from hdfs_utils import file_status

        try:
            exists = file_status("/data/raw/creditcard.csv") is not None
        except Exception as e:
            print(f"[Lỗi] Không kết nối được tới HDFS ({e}). "
                  "Đảm bảo đã chạy 'docker compose -f docker-compose.hdfs.yml up -d'.")
            sys.exit(1)
        if not exists:
            print(f"[Lỗi] Không tìm thấy {RAW_CSV_DATA_PATH}. "
                  "Chạy 'python scripts/hdfs_bootstrap.py' để upload dữ liệu lên HDFS trước.")
            sys.exit(1)
    elif not RAW_CSV_PATH.exists():
        print(f"[Lỗi] Không tìm thấy dữ liệu thô tại {RAW_CSV_PATH}")
        print("Hãy tải creditcard.csv từ Kaggle vào data/raw/, hoặc chạy:")
        print("    python src/generate_synthetic_data.py")
        sys.exit(1)

    from spark_etl import run_etl
    from imbalance import run_imbalance_handling
    from train_models import run_training
    from evaluate import run_evaluation
    from visualize import run_visualization

    _step("Giai đoạn 1-2: ETL (đọc dữ liệu, EDA, làm sạch, chuẩn hóa, split)", run_etl)
    _step("Giai đoạn 3: Xử lý dữ liệu mất cân bằng", run_imbalance_handling)
    _step("Giai đoạn 4: Huấn luyện 3 mô hình", run_training)
    _step("Giai đoạn 5: Đánh giá & so sánh mô hình", run_evaluation)
    _step("Giai đoạn 6: Trực quan hóa", run_visualization)

    print("\nPipeline hoàn tất. Xem kết quả tại reports/metrics_comparison.csv "
          "và reports/figures/")


if __name__ == "__main__":
    main()
