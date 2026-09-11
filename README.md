# Phát hiện giao dịch tài chính bất thường (Fraud Detection)

Dự án Big Data + Machine Learning phát hiện gian lận thẻ tín dụng, dựa trên
[Credit Card Fraud Detection Dataset (Kaggle - ULB)](https://www.kaggle.com/mlg-ulb/creditcardfraud).

Xem chi tiết kế hoạch tại [ke-hoach-phat-hien-giao-dich-bat-thuong.md](ke-hoach-phat-hien-giao-dich-bat-thuong.md).

## 1. Cấu trúc dự án

```
fraud-detection/
├── data/
│   ├── raw/              # dữ liệu gốc (đặt creditcard.csv vào đây), mô phỏng HDFS /data/raw/
│   └── processed/        # dữ liệu sau làm sạch/tiền xử lý (parquet)
├── notebooks/            # notebook khám phá (tuỳ chọn)
├── src/
│   ├── config.py         # đường dẫn, hằng số dùng chung
│   ├── spark_etl.py       # Giai đoạn 1-2: đọc HDFS/CSV bằng Spark, EDA, làm sạch, chuẩn hóa
│   ├── imbalance.py       # Giai đoạn 3: xử lý mất cân bằng (class weight / SMOTE)
│   ├── train_models.py    # Giai đoạn 4: huấn luyện Logistic Regression, Random Forest (Spark MLlib) + Isolation Forest (sklearn)
│   ├── evaluate.py         # Giai đoạn 5: Precision/Recall/F1/ROC-AUC/PR-AUC, so sánh 3 mô hình
│   └── visualize.py        # Giai đoạn 6: biểu đồ trực quan
├── reports/
│   ├── figures/            # biểu đồ xuất ra
│   └── metrics_comparison.csv
├── run_pipeline.py         # script điều phối chạy toàn bộ pipeline
├── requirements.txt
└── README.md
```

## 2. Cài đặt môi trường

Yêu cầu: Python 3.10+, Java 8/11/17 (bắt buộc cho PySpark).

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Kiểm tra Java (PySpark cần JVM):
```bash
java -version
```
Nếu chưa có, cài OpenJDK 17, ví dụ qua winget: `winget install EclipseAdoptium.Temurin.17.JDK`

### Lưu ý riêng cho Windows (đã kiểm chứng khi build dự án này)

1. **winutils.exe**: Spark trên Windows cần `winutils.exe`/`hadoop.dll` để ghi file cục bộ
   (Parquet), nếu không sẽ lỗi `HADOOP_HOME and hadoop.home.dir are unset`. Tải về và đặt vào
   `hadoop/bin/` (đã có sẵn thư mục `hadoop/bin/winutils.exe` trong dự án này, tải từ
   [cdarlint/winutils](https://github.com/cdarlint/winutils), bản hadoop-3.3.6), rồi set biến môi trường
   trước khi chạy:
   ```bash
   set JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot
   set HADOOP_HOME=D:\fraud-detection\hadoop
   set PATH=%JAVA_HOME%\bin;%HADOOP_HOME%\bin;%PATH%
   ```
2. **Phiên bản pandas**: nếu dùng Python rất mới (3.13+/3.14), `pip install pandas` có thể cài
   pandas >= 3.0, hiện PySpark **chưa hỗ trợ đầy đủ pandas 3.x** (dễ gây lỗi crash Python worker khi
   `toPandas()`/UDF). Dự án này đã test ổn định với **pandas 2.3.3** — nếu gặp lỗi tương tự, chạy:
   `pip install "pandas==2.3.3"`.
3. Nếu Python 3.14 không có sẵn wheel cho một số gói (ví dụ pandas bản cũ cố build từ source và lỗi
   thiếu Visual Studio/meson), dùng: `pip install --only-binary=:all: <package>` để chỉ lấy bản wheel
   dựng sẵn.

## 3. Dữ liệu

Tải `creditcard.csv` từ Kaggle và đặt vào `data/raw/creditcard.csv`.
Nếu chưa có dữ liệu thật, chạy script sinh dữ liệu giả lập (synthetic) để test toàn bộ pipeline:

```bash
python src/generate_synthetic_data.py
```

Script này tạo `data/raw/creditcard.csv` với cấu trúc giống dataset gốc
(cột `Time`, `V1`-`V28`, `Amount`, `Class`) và tỉ lệ gian lận ~0.17%.

## 4. Chạy toàn bộ pipeline

```bash
python run_pipeline.py
```

Pipeline sẽ lần lượt:
1. Đọc `data/raw/creditcard.csv` bằng Spark (`spark_etl.py`), EDA, làm sạch, chuẩn hóa, lưu ra `data/processed/`.
2. Xử lý mất cân bằng dữ liệu (`imbalance.py`) → `data/processed/train_weighted.parquet` (dùng cho bước 3).
3. Huấn luyện 3 mô hình: Logistic Regression, Random Forest (Spark MLlib), Isolation Forest (scikit-learn) (`train_models.py`).
4. Đánh giá và so sánh (`evaluate.py`) → `reports/metrics_comparison.csv`.
5. Vẽ biểu đồ trực quan (`visualize.py`) → `reports/figures/`.

Có thể chạy từng bước riêng lẻ bằng cách gọi trực tiếp từng file trong `src/`.

### Tinh chỉnh mô hình (tùy chọn, khuyến nghị chạy trước khi viết báo cáo cuối)

Sau khi đã chạy `run_pipeline.py` ít nhất 1 lần (có `data/processed/train_weighted.parquet` và
`train_balanced.parquet`), chạy thêm:

```bash
python src/tune_models.py
```

Script này sẽ:
- Grid Search + 3-fold Cross-Validation cho Logistic Regression (regParam, elasticNetParam) và
  Random Forest (numTrees, maxDepth), chọn bộ tham số có PR-AUC trung bình cao nhất.
- So sánh chiến lược xử lý mất cân bằng: class weighting vs SMOTE, chọn chiến lược tốt hơn.
- Tối ưu ngưỡng phân loại (threshold) tối đa hóa F1-score trên một tập validation tách riêng
  từ train (time-based), thay vì dùng mặc định 0.5 - lưu vào `models/thresholds.json`.
- Ghi đè mô hình đã tinh chỉnh vào `models/logistic_regression`, `models/random_forest`.

Sau đó chạy lại `python src/evaluate.py` và `python src/visualize.py` để cập nhật kết quả/biểu đồ
với mô hình đã tinh chỉnh (evaluate.py tự động dùng ngưỡng trong `models/thresholds.json` nếu có).

## 5. Ghi chú kỹ thuật

- HDFS được mô phỏng bằng thư mục `data/raw` cục bộ; nếu chạy trên cluster thật, thay đường dẫn
  trong `src/config.py` bằng `hdfs://<namenode>:8020/data/raw/creditcard.csv`.
- Isolation Forest là mô hình unsupervised, không dùng nhãn khi huấn luyện nhưng vẫn dùng nhãn thật
  (`Class`) để đánh giá.
- Vì dữ liệu mất cân bằng nặng, ưu tiên Precision/Recall/F1/PR-AUC hơn Accuracy/ROC-AUC.
- Dùng time-based split (theo cột `Time`) thay vì random split để mô phỏng dự đoán giao dịch tương lai.
