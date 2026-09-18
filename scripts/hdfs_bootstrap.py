"""Upload dữ liệu thô lên HDFS pseudo-cluster (chạy 1 lần sau khi
`docker compose -f docker-compose.hdfs.yml up -d`, trước khi chạy pipeline với DATA_BACKEND=hdfs).

Chạy: python scripts/hdfs_bootstrap.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import RAW_CSV_PATH  # noqa: E402
from hdfs_utils import mkdirs, upload_file  # noqa: E402


def main():
    if not RAW_CSV_PATH.exists():
        print(f"[Lỗi] Không tìm thấy {RAW_CSV_PATH}. Chạy 'python src/generate_synthetic_data.py' "
              "hoặc tải creditcard.csv từ Kaggle trước.")
        sys.exit(1)

    print("[HDFS] Tạo thư mục /data/raw, /data/processed...")
    mkdirs("/data/raw")
    mkdirs("/data/processed")

    print(f"[HDFS] Upload {RAW_CSV_PATH} -> /data/raw/creditcard.csv ...")
    upload_file(RAW_CSV_PATH, "/data/raw/creditcard.csv")
    print("[HDFS] Hoàn tất. Xem tại NameNode UI: http://localhost:9870/explorer.html#/data/raw")


if __name__ == "__main__":
    main()
