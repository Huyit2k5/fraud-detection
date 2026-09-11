# Notebooks (tuỳ chọn)

Toàn bộ pipeline đã được hiện thực dưới dạng script chạy được trong `src/` (xem README ở gốc
dự án). Thư mục này dành cho notebook khám phá/trình bày thêm nếu cần cho báo cáo/demo, ví dụ:

- `01_eda.ipynb` — khám phá dữ liệu, minh hoạ lại các bước trong `src/spark_etl.py` (`explore_data`)
- `02_preprocessing_spark.ipynb` — minh hoạ làm sạch/chuẩn hoá/xử lý mất cân bằng
- `03_modeling.ipynb` — huấn luyện và so sánh 3 mô hình
- `04_evaluation_visualization.ipynb` — đánh giá và trực quan hoá

Có thể import trực tiếp các hàm từ `src/` (thêm `sys.path.insert(0, "../src")` ở đầu notebook)
thay vì viết lại logic.
