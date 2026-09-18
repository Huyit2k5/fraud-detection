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
│   ├── metrics_comparison.csv
│   ├── generate_report.py  # Giai đoạn 7: sinh báo cáo học thuật (Word)
│   └── final_report.docx   # báo cáo học thuật hoàn chỉnh (sinh ra bởi generate_report.py)
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
   **Nếu máy có nhiều JDK cài song song** (ví dụ vừa có JDK 11 vừa có JDK 17) và biến `JAVA_HOME`
   cấp hệ thống (System/User Environment Variables) đang trỏ nhầm vào JDK 11, PySpark sẽ báo lỗi
   `UnsupportedClassVersionError` / `LinkageError khi loading main class org.apache.spark.launcher.Main`
   dù bạn đã set `JAVA_HOME` đúng ở bước trên trong terminal hiện tại — vì biến hệ thống chỉ mất tác
   dụng ở phiên đang mở, các terminal/tiến trình mới (kể cả `streamlit run dashboard/app.py`) vẫn kế
   thừa giá trị sai đó nếu bạn không set lại trong đúng terminal đó. Kiểm tra nhanh:
   `java -version` (bản đang chạy) và
   `[Environment]::GetEnvironmentVariable("JAVA_HOME","Machine")` (PowerShell, xem biến hệ thống).
   Cách sửa triệt để: đổi biến `JAVA_HOME` hệ thống (Windows Settings → Environment Variables) trỏ
   thẳng vào JDK 17. Dashboard (`dashboard/app.py`) đã tự động dò và ưu tiên JDK 17 cho các subprocess
   nó chạy (ETL/pipeline) nên không cần sửa gì thêm nếu chỉ dùng qua dashboard — nhưng khi chạy trực
   tiếp `python run_pipeline.py`/`python src/spark_etl.py` từ terminal, bạn vẫn cần tự set đúng
   `JAVA_HOME` như trên.
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

## 5. Sinh báo cáo học thuật (Giai đoạn 7)

Sau khi đã có `reports/metrics_comparison.csv` và `reports/figures/*.png` (chạy `run_pipeline.py`,
khuyến nghị chạy thêm `tune_models.py` trước), sinh báo cáo Word hoàn chỉnh bằng:

```bash
python reports/generate_report.py
```

Script tự động đọc số liệu/biểu đồ MỚI NHẤT và ghi ra `reports/final_report.docx`, gồm đầy đủ:
giới thiệu, cơ sở lý thuyết (Big Data/Spark, 3 thuật toán, các chỉ số đánh giá), kiến trúc hệ
thống, kết quả thực nghiệm (bảng + biểu đồ + phân tích), kết luận & hướng phát triển, tài liệu
tham khảo. Chạy lại script này bất cứ khi nào số liệu thay đổi (ví dụ sau khi tinh chỉnh mô hình
lại) để cập nhật báo cáo.

## 6. HDFS pseudo-cluster (tùy chọn) + Web dashboard

Mặc định pipeline chạy ở chế độ `DATA_BACKEND=local` (dữ liệu nằm ở `data/` trên đĩa, như mục 3-4 ở
trên). Nếu muốn dữ liệu thực sự nằm trên HDFS (namenode + datanode, single-node pseudo-cluster) thay vì
chỉ mô phỏng, làm theo các bước sau (cần Docker Desktop đang chạy):

1. Khởi động HDFS pseudo-cluster:
   ```bash
   docker compose -f docker-compose.hdfs.yml up -d
   ```
   Kiểm tra NameNode Web UI tại http://localhost:9870 (mục "Live Nodes" phải là 1).

2. **Chỉ trên Windows**: thêm 2 dòng sau vào file hosts (`C:\Windows\System32\drivers\etc\hosts`, cần
   quyền Admin để sửa) để Spark (chạy trên host) resolve được hostname của container:
   ```
   127.0.0.1 namenode
   127.0.0.1 datanode
   ```

3. Upload dữ liệu thô lên HDFS:
   ```bash
   python scripts/hdfs_bootstrap.py
   ```
   Xem file vừa upload tại http://localhost:9870/explorer.html#/data/raw

4. Bật chế độ HDFS rồi chạy pipeline như bình thường:
   ```bash
   set DATA_BACKEND=hdfs
   python run_pipeline.py
   ```
   Dữ liệu đã xử lý (`cleaned.parquet`, `train.parquet`, `test.parquet`...) sẽ được ghi vào
   `/data/processed/` trên HDFS thay vì `data/processed/` local. Bỏ biến `DATA_BACKEND` (hoặc set về
   `local`) để quay lại chế độ cũ.

5. Xem web dashboard trực quan hóa toàn bộ pipeline (dữ liệu trên HDFS, log ETL, so sánh mô hình,
   biểu đồ):
   ```bash
   streamlit run dashboard/app.py
   ```

Dừng cluster: `docker compose -f docker-compose.hdfs.yml down` (thêm `-v` nếu muốn xóa luôn dữ liệu
HDFS đã lưu trong volume).

## 7. Ghi chú kỹ thuật

- Mặc định (`DATA_BACKEND=local`) HDFS được mô phỏng bằng thư mục `data/` cục bộ. Xem mục 6 để chạy
  với HDFS pseudo-cluster thật (Docker) bằng cách set `DATA_BACKEND=hdfs`.
- `notebooks/01_eda.ipynb` và `notebooks/02_preprocessing_spark.ipynb` đọc dữ liệu qua
  `RAW_CSV_DATA_PATH` (tôn trọng `DATA_BACKEND`, giống `src/spark_etl.py`), không phải `RAW_CSV_PATH`
  (luôn là đường dẫn local) — nếu tự viết notebook/script mới đọc dữ liệu thô, dùng
  `RAW_CSV_DATA_PATH` để không vô tình bỏ qua chế độ HDFS.
- Khi `DATA_BACKEND=hdfs`, `run_pipeline.py` kiểm tra dữ liệu thô đã có trên HDFS trước khi chạy
  (qua WebHDFS) và báo lỗi rõ ràng ngay nếu chưa `hdfs_bootstrap.py` hoặc cluster chưa lên — thay vì
  để Spark khởi động xong rồi mới crash giữa chừng với stack trace Java khó hiểu.
- `dashboard/app.py` tự động dò và luôn ưu tiên JDK 17 cài trên máy (không phụ thuộc biến `JAVA_HOME`
  hệ thống, kể cả khi biến đó trỏ sai sang JDK khác) cho các subprocess ETL/pipeline nó chạy — nhưng
  khi chạy trực tiếp `python run_pipeline.py`/`python src/spark_etl.py` từ terminal (không qua
  dashboard), bạn vẫn cần tự set đúng `JAVA_HOME` như hướng dẫn ở mục 2.
- Isolation Forest là mô hình unsupervised, không dùng nhãn khi huấn luyện nhưng vẫn dùng nhãn thật
  (`Class`) để đánh giá.
- Vì dữ liệu mất cân bằng nặng, ưu tiên Precision/Recall/F1/PR-AUC hơn Accuracy/ROC-AUC.
- Dùng time-based split (theo cột `Time`) thay vì random split để mô phỏng dự đoán giao dịch tương lai.
- **Isolation Forest có Precision/PR-AUC thấp hơn hẳn 2 mô hình supervised** (Precision ~5% so với
  80-95%) - đây KHÔNG phải lỗi, mà là hạn chế đã biết của phương pháp unsupervised: nó xác định
  "bất thường" dựa trên việc bị cô lập trong toàn bộ không gian đặc trưng, không nhất thiết trùng
  với các giao dịch gian lận thật (nhiều giao dịch hợp lệ nhưng có giá trị lớn/hiếm cũng bị coi là
  bất thường). Đây là điểm quan trọng cần nêu khi so sánh trong báo cáo.
- **Kết quả sau khi tinh chỉnh** (`tune_models.py`, xem mục 4): Grid Search chọn
  Logistic Regression (regParam=0.1, elasticNetParam=0.5), Random Forest (numTrees=50, maxDepth=10);
  cả 2 đều giữ chiến lược class-weight (tốt hơn SMOTE một chút trên PR-AUC nội bộ); ngưỡng phân loại
  tối ưu: LR=0.759, RF=0.559 (thay vì mặc định 0.5) → Precision của Logistic Regression tăng từ
  0.11 lên 0.80, Random Forest đạt Precision 0.95/Recall 0.70/F1 0.81 trên tập test.
