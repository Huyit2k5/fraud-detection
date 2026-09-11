# Notebooks

4 notebook minh họa từng giai đoạn của kế hoạch, gọi trực tiếp các hàm trong `src/`
(không viết lại logic) - đã chạy thử thành công trên dữ liệu thật (`creditcard.csv`, Kaggle ULB):

- `01_eda.ipynb` — khám phá dữ liệu (Giai đoạn 1-2): đọc dữ liệu qua Spark, phân phối class,
  missing values, thống kê Amount, tương quan giữa các đặc trưng PCA và nhãn Class
- `02_preprocessing_spark.ipynb` — làm sạch, chuẩn hóa, time-based split, xử lý mất cân bằng
  (Giai đoạn 2-3): class weighting + SMOTE
- `03_modeling.ipynb` — huấn luyện 3 mô hình (Giai đoạn 4): Logistic Regression, Random Forest
  (kèm feature importance), Isolation Forest
- `04_evaluation_visualization.ipynb` — đánh giá & trực quan hóa (Giai đoạn 5-6): bảng so sánh
  Precision/Recall/F1/ROC-AUC/PR-AUC và 5 biểu đồ

## Yêu cầu trước khi chạy

- Đã cài `jupyter`/`nbclient`/`ipykernel` trong venv:
  `pip install nbclient ipykernel jupyter`
- Đã có `data/raw/creditcard.csv` (xem README ở gốc dự án)
- Notebook 02-04 cần chạy `01`/`02` trước để có `data/processed/*.parquet` và `models/*`
  (hoặc chạy `python run_pipeline.py` một lần trước, sau đó mở notebook để xem lại/trình bày)
- Mỗi notebook tự set `JAVA_HOME`/`HADOOP_HOME` ở cell đầu tiên - chỉnh lại đường dẫn cho đúng
  máy của bạn nếu khác với mặc định trong file

## Chạy trong Jupyter

```bash
cd notebooks
jupyter notebook
```

Hoặc chạy không cần mở giao diện (headless), ví dụ notebook 04:

```bash
python -c "
import nbformat
from nbclient import NotebookClient
nb = nbformat.read('04_evaluation_visualization.ipynb', as_version=4)
NotebookClient(nb, timeout=300, kernel_name='python3').execute()
nbformat.write(nb, '04_evaluation_visualization.ipynb')
"
```
