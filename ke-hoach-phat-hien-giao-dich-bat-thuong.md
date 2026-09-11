# Kế hoạch thực hiện đề tài: Phát hiện giao dịch tài chính bất thường

## 1. Mục tiêu và phạm vi đề tài

**Mục tiêu chính:** Xây dựng hệ thống phát hiện gian lận/giao dịch bất thường trong dữ liệu thẻ tín dụng hoặc ngân hàng, sử dụng hệ sinh thái Big Data (HDFS + Spark) kết hợp Machine Learning.

**Đầu ra dự kiến:**
- Pipeline xử lý dữ liệu lớn end-to-end (thu thập → lưu trữ → làm sạch → mô hình hóa → đánh giá → trực quan hóa)
- Báo cáo so sánh hiệu năng giữa 3 mô hình (Isolation Forest, Random Forest, Logistic Regression)
- Dashboard/biểu đồ trực quan các giao dịch nghi vấn

---

## 2. Kiến trúc hệ thống tổng thể

```
[Dataset gốc] → [HDFS lưu trữ] → [Spark: ETL & xử lý mất cân bằng]
        → [Spark MLlib / Python: huấn luyện mô hình]
        → [Đánh giá: Precision/Recall/F1] → [Trực quan hóa]
```

**Công nghệ đề xuất:**
- **Lưu trữ:** Hadoop HDFS (có thể dùng bản single-node hoặc pseudo-distributed cho đề tài học thuật)
- **Xử lý dữ liệu:** Apache Spark (PySpark) với Spark SQL, Spark MLlib
- **Mô hình:** Spark MLlib (Logistic Regression, Random Forest) + scikit-learn (Isolation Forest, vì MLlib không có sẵn thuật toán này)
- **Trực quan hóa:** Matplotlib/Seaborn, hoặc Plotly/Power BI nếu muốn dashboard tương tác
- **Môi trường:** Google Colab / máy cá nhân (Docker Hadoop-Spark) / cụm thật nếu có điều kiện

---

## 3. Lộ trình thực hiện (đề xuất 6-8 tuần)

### Giai đoạn 1: Chuẩn bị dữ liệu và môi trường (Tuần 1-2)
- Chọn bộ dữ liệu: phổ biến nhất là **Credit Card Fraud Detection Dataset (Kaggle - ULB)** với ~284,807 giao dịch, chỉ 0.17% là gian lận (rất mất cân bằng — phù hợp với đề tài)
- Cài đặt môi trường: Hadoop (HDFS), Spark, PySpark, Python libraries
- Đưa dữ liệu vào HDFS: `hdfs dfs -put transactions.csv /data/raw/`

### Giai đoạn 2: Khám phá và làm sạch dữ liệu (Tuần 2-3)
- Đọc dữ liệu từ HDFS bằng Spark DataFrame
- EDA (Exploratory Data Analysis): kiểm tra phân phối class, missing values, outliers, tương quan giữa các đặc trưng
- Làm sạch: xử lý missing/duplicate, chuẩn hóa (StandardScaler/MinMaxScaler) các cột như `Amount`, `Time`

### Giai đoạn 3: Xử lý dữ liệu mất cân bằng (Tuần 3-4)
Vì gian lận thường chiếm <1% dữ liệu, cần áp dụng kỹ thuật cân bằng:
- **Undersampling** lớp đa số (Normal)
- **Oversampling** lớp thiểu số: SMOTE (thường làm ở tầng Python/pandas vì Spark MLlib chưa hỗ trợ SMOTE trực tiếp — có thể dùng thư viện `imblearn` sau khi lấy mẫu từ Spark, hoặc dùng weighted class trong mô hình)
- Hoặc dùng **class weighting** trực tiếp trong Logistic Regression / Random Forest của Spark MLlib (`weightCol`)

### Giai đoạn 4: Xây dựng mô hình (Tuần 4-5)
Triển khai và huấn luyện 3 mô hình:

| Mô hình | Đặc điểm | Công cụ |
|---|---|---|
| Logistic Regression | Baseline, dễ giải thích | Spark MLlib |
| Random Forest | Xử lý tốt phi tuyến, dữ liệu mất cân bằng | Spark MLlib |
| Isolation Forest | Unsupervised, phù hợp phát hiện anomaly không cần nhãn | scikit-learn (train trên sample lấy từ Spark) |

- Chia tập train/test (thường 70/30 hoặc dùng time-based split vì dữ liệu giao dịch có yếu tố thời gian)
- Tinh chỉnh siêu tham số (Grid Search / Cross-validation)

### Giai đoạn 5: Đánh giá mô hình (Tuần 5-6)
Vì đây là bài toán mất cân bằng, **Accuracy không phù hợp** — tập trung vào:
- **Precision:** tỷ lệ giao dịch dự đoán gian lận đúng thực sự là gian lận
- **Recall:** tỷ lệ giao dịch gian lận thực tế được phát hiện
- **F1-score:** cân bằng giữa Precision và Recall
- **Confusion Matrix**, **ROC-AUC**, **Precision-Recall Curve** (quan trọng hơn ROC khi dữ liệu mất cân bằng)
- So sánh 3 mô hình bằng bảng tổng hợp

### Giai đoạn 6: Trực quan hóa và báo cáo (Tuần 6-7)
- Biểu đồ phân phối giao dịch bình thường vs gian lận
- Scatter plot/PCA 2D để minh họa vùng anomaly mà Isolation Forest phát hiện
- Confusion matrix heatmap cho từng mô hình
- Biểu đồ so sánh Precision/Recall/F1 giữa 3 mô hình (bar chart)
- Dashboard tổng hợp giao dịch nghi vấn theo thời gian/số tiền

### Giai đoạn 7: Hoàn thiện báo cáo (Tuần 7-8)
- Viết báo cáo: giới thiệu, cơ sở lý thuyết, kiến trúc hệ thống, kết quả thực nghiệm, kết luận & hướng phát triển
- Chuẩn bị slide thuyết trình + demo

---

## 4. Một số lưu ý kỹ thuật quan trọng

- **HDFS trong đề tài nhỏ:** nếu dữ liệu chỉ vài trăm MB, việc dùng HDFS chủ yếu mang tính minh họa kiến trúc Big Data; có thể dùng Hadoop pseudo-distributed mode trên 1 máy.
- **Isolation Forest không cần nhãn** để huấn luyện (unsupervised), nhưng vẫn cần nhãn thật để **đánh giá** kết quả — đây là điểm cần làm rõ trong báo cáo.
- Với dữ liệu mất cân bằng, nên báo cáo thêm **Precision-Recall AUC** thay vì chỉ ROC-AUC vì nó phản ánh đúng hơn hiệu năng trên lớp thiểu số.
- Cân nhắc dùng **time-based split** thay vì random split, vì trong thực tế mô hình phải dự đoán giao dịch tương lai dựa trên giao dịch quá khứ.

---

## 5. Cấu trúc thư mục dự án đề xuất

```
fraud-detection-project/
├── data/
│   ├── raw/              # dữ liệu gốc trên HDFS
│   └── processed/        # dữ liệu sau làm sạch
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_preprocessing_spark.ipynb
│   ├── 03_modeling.ipynb
│   └── 04_evaluation_visualization.ipynb
├── src/
│   ├── spark_etl.py
│   ├── train_models.py
│   └── evaluate.py
├── reports/
│   └── final_report.docx
└── README.md
```
