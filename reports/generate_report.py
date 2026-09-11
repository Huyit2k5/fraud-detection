"""
Sinh báo cáo học thuật hoàn chỉnh (Giai đoạn 7 của kế hoạch) dưới dạng file Word (.docx),
tự động nhúng bảng số liệu (reports/metrics_comparison.csv) và biểu đồ (reports/figures/*.png)
đã được tạo ra từ pipeline thật (data thật từ Kaggle - ULB).

Chạy: python reports/generate_report.py
(yêu cầu đã chạy run_pipeline.py và tune_models.py trước đó để có đủ số liệu/biểu đồ mới nhất)

Yêu cầu thư viện: pip install python-docx
"""

import json
import sys
from pathlib import Path

# Đảm bảo in được tiếng Việt có dấu trên console Windows (mặc định cp1252/cp1258)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = ROOT_DIR / "models"
METRICS_CSV = REPORTS_DIR / "metrics_comparison.csv"
THRESHOLDS_JSON = MODELS_DIR / "thresholds.json"
OUTPUT_PATH = REPORTS_DIR / "final_report.docx"

HEADING_COLOR = RGBColor(0x1F, 0x3A, 0x5F)


def load_metrics() -> pd.DataFrame:
    if not METRICS_CSV.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {METRICS_CSV}. Hãy chạy `python run_pipeline.py` "
            "(hoặc ít nhất `python src/evaluate.py`) trước khi sinh báo cáo."
        )
    return pd.read_csv(METRICS_CSV)


def load_thresholds() -> dict:
    if not THRESHOLDS_JSON.exists():
        return {}
    with open(THRESHOLDS_JSON, encoding="utf-8") as f:
        return json.load(f)


def add_heading(doc, text, level=1):
    h = doc.add_heading(level=level)
    run = h.add_run(text)
    run.font.color.rgb = HEADING_COLOR
    return h


def add_table_from_df(doc, df: pd.DataFrame, float_cols=None, pct_cols=None):
    float_cols = float_cols or []
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Light Grid Accent 1"

    hdr_cells = table.rows[0].cells
    for i, col in enumerate(df.columns):
        hdr_cells[i].text = str(col)
        for p in hdr_cells[i].paragraphs:
            for r in p.runs:
                r.font.bold = True

    for _, row in df.iterrows():
        cells = table.add_row().cells
        for i, col in enumerate(df.columns):
            val = row[col]
            if col in float_cols:
                cells[i].text = f"{val:.4f}"
            elif isinstance(val, (int,)):
                cells[i].text = f"{val:,}"
            else:
                cells[i].text = str(val)
    return table


def add_figure(doc, filename, caption, width_cm=15):
    path = FIGURES_DIR / filename
    if not path.exists():
        p = doc.add_paragraph(f"[Thiếu hình: {filename} - hãy chạy python src/visualize.py]")
        p.runs[0].font.italic = True
        return
    doc.add_picture(str(path), width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cap.add_run(caption)
    run.font.italic = True
    run.font.size = Pt(10)


def build_report():
    metrics_df = load_metrics()
    thresholds = load_thresholds()
    metrics_df = metrics_df.round(4)

    doc = Document()

    # Font mặc định + cỡ chữ toàn tài liệu
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(13)

    # ===== TRANG BÌA =====
    title = doc.add_heading(level=0)
    title_run = title.add_run("PHÁT HIỆN GIAO DỊCH TÀI CHÍNH BẤT THƯỜNG")
    title_run.font.color.rgb = HEADING_COLOR
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub.add_run(
        "Ứng dụng Big Data (Hadoop HDFS + Apache Spark) và Machine Learning\n"
        "trong phát hiện gian lận thẻ tín dụng"
    )
    sub_run.font.size = Pt(14)
    sub_run.font.italic = True

    doc.add_paragraph()
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info.add_run(
        "Bộ dữ liệu: Credit Card Fraud Detection (Kaggle - ULB)\n"
        "284.807 giao dịch, tỉ lệ gian lận ~0,17%"
    )
    doc.add_page_break()

    # ===== MỤC LỤC (danh sách tĩnh, đơn giản) =====
    add_heading(doc, "MỤC LỤC", level=1)
    toc_items = [
        "1. Giới thiệu và đặt vấn đề",
        "2. Cơ sở lý thuyết",
        "3. Kiến trúc hệ thống và phương pháp thực hiện",
        "4. Kết quả thực nghiệm",
        "5. Kết luận và hướng phát triển",
        "Tài liệu tham khảo",
    ]
    for item in toc_items:
        doc.add_paragraph(item, style="List Number")
    doc.add_page_break()

    # ===== 1. GIỚI THIỆU =====
    add_heading(doc, "1. Giới thiệu và đặt vấn đề", level=1)
    doc.add_paragraph(
        "Gian lận trong giao dịch tài chính, đặc biệt là gian lận thẻ tín dụng, gây thiệt hại "
        "hàng tỉ đô la mỗi năm cho các tổ chức tài chính và người tiêu dùng trên toàn thế giới. "
        "Với sự bùng nổ của giao dịch trực tuyến, khối lượng dữ liệu giao dịch tăng lên nhanh "
        "chóng, đòi hỏi các hệ thống phát hiện gian lận phải có khả năng xử lý dữ liệu lớn "
        "(Big Data) theo thời gian gần thực, đồng thời đủ chính xác để phân biệt giao dịch "
        "gian lận với giao dịch hợp lệ - vốn chiếm tỉ lệ áp đảo."
    )
    doc.add_paragraph(
        "Đề tài này xây dựng một pipeline xử lý dữ liệu lớn end-to-end, kết hợp hệ sinh thái "
        "Hadoop HDFS/Apache Spark với các thuật toán Machine Learning, nhằm phát hiện các giao "
        "dịch thẻ tín dụng bất thường. Mục tiêu cụ thể:"
    )
    for item in [
        "Xây dựng pipeline xử lý dữ liệu lớn end-to-end: thu thập → lưu trữ (HDFS) → làm sạch "
        "→ mô hình hóa → đánh giá → trực quan hóa.",
        "So sánh hiệu năng giữa 3 thuật toán đại diện cho 2 nhóm phương pháp: có giám sát "
        "(Logistic Regression, Random Forest) và không giám sát (Isolation Forest).",
        "Xử lý bài toán dữ liệu mất cân bằng nghiêm trọng (gian lận chỉ chiếm ~0,17%).",
        "Trực quan hóa kết quả để hỗ trợ phân tích giao dịch nghi vấn.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_page_break()

    # ===== 2. CƠ SỞ LÝ THUYẾT =====
    add_heading(doc, "2. Cơ sở lý thuyết", level=1)

    add_heading(doc, "2.1. Hệ sinh thái Big Data: HDFS và Apache Spark", level=2)
    doc.add_paragraph(
        "HDFS (Hadoop Distributed File System) là hệ thống lưu trữ phân tán cho phép lưu trữ "
        "dữ liệu khối lượng lớn trên nhiều máy, đảm bảo khả năng chịu lỗi thông qua cơ chế nhân "
        "bản (replication). Apache Spark là công cụ xử lý dữ liệu phân tán trong bộ nhớ (in-memory), "
        "cung cấp Spark SQL để truy vấn dữ liệu có cấu trúc và Spark MLlib để huấn luyện mô hình "
        "Machine Learning trên tập dữ liệu lớn một cách phân tán. Trong phạm vi đề tài học thuật, "
        "HDFS được mô phỏng bằng một thư mục cục bộ (`data/raw/`), còn Spark chạy ở chế độ "
        "local[*] trên một máy - kiến trúc này minh họa đúng luồng xử lý Big Data thực tế và có "
        "thể mở rộng trực tiếp sang cluster nhiều máy bằng cách thay đổi đường dẫn HDFS và địa chỉ "
        "master của Spark."
    )

    add_heading(doc, "2.2. Bài toán dữ liệu mất cân bằng (Imbalanced Data)", level=2)
    doc.add_paragraph(
        "Trong bộ dữ liệu gian lận thẻ tín dụng, số giao dịch gian lận thường chiếm tỉ lệ rất "
        "nhỏ so với giao dịch hợp lệ (trong đề tài này là ~0,17%). Nếu huấn luyện mô hình trực "
        "tiếp trên dữ liệu gốc, mô hình có xu hướng thiên vị lớp đa số, dẫn đến bỏ sót phần lớn "
        "giao dịch gian lận dù độ chính xác (Accuracy) tổng thể vẫn rất cao (do lớp đa số áp đảo). "
        "Hai kỹ thuật phổ biến để xử lý vấn đề này:"
    )
    for item in [
        "Class Weighting: gán trọng số lớn hơn cho lớp thiểu số khi tính hàm mất mát, giúp mô "
        "hình \"chú ý\" hơn đến các giao dịch gian lận mà không làm thay đổi số lượng dòng dữ liệu.",
        "SMOTE (Synthetic Minority Over-sampling Technique): sinh thêm các mẫu tổng hợp cho lớp "
        "thiểu số bằng cách nội suy giữa các điểm dữ liệu gian lận gần nhau trong không gian đặc "
        "trưng, giúp cân bằng lại tỉ lệ lớp.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "2.3. Các thuật toán sử dụng", level=2)
    doc.add_paragraph(
        "Logistic Regression: mô hình hồi quy tuyến tính cho phân loại nhị phân, ước lượng xác "
        "suất một giao dịch là gian lận thông qua hàm sigmoid áp dụng lên tổ hợp tuyến tính của "
        "các đặc trưng đầu vào. Ưu điểm: đơn giản, huấn luyện nhanh, dễ diễn giải hệ số hồi quy."
    )
    doc.add_paragraph(
        "Random Forest: phương pháp học tổ hợp (ensemble) gồm nhiều cây quyết định được huấn "
        "luyện trên các tập con dữ liệu/đặc trưng khác nhau (bagging), kết quả dự đoán là kết "
        "quả bỏ phiếu của toàn bộ các cây. Ưu điểm: xử lý tốt quan hệ phi tuyến giữa các đặc "
        "trưng, ít bị overfitting hơn một cây quyết định đơn lẻ, cho biết mức độ quan trọng của "
        "từng đặc trưng (feature importance)."
    )
    doc.add_paragraph(
        "Isolation Forest: thuật toán phát hiện bất thường (anomaly detection) không giám sát "
        "(unsupervised) - không sử dụng nhãn khi huấn luyện. Ý tưởng cốt lõi: các điểm dữ liệu "
        "bất thường thường dễ bị \"cô lập\" (isolate) hơn - tức cần ít phép chia ngẫu nhiên hơn "
        "để tách một điểm bất thường ra khỏi phần còn lại của dữ liệu so với một điểm bình "
        "thường. Điểm số bất thường được tính dựa trên độ dài đường đi trung bình trong các cây "
        "cô lập (isolation trees). Thuật toán này phù hợp khi không có đủ nhãn gian lận đáng tin "
        "cậy, tuy nhiên - như kết quả thực nghiệm ở mục 4 cho thấy - nó có thể kém chính xác hơn "
        "các mô hình có giám sát vì \"bất thường\" theo nghĩa thống kê không phải lúc nào cũng "
        "trùng với \"gian lận\" theo nghĩa nghiệp vụ."
    )

    add_heading(doc, "2.4. Các chỉ số đánh giá mô hình", level=2)
    doc.add_paragraph(
        "Với bài toán mất cân bằng dữ liệu nghiêm trọng, chỉ số Accuracy không phản ánh đúng "
        "chất lượng mô hình (một mô hình luôn dự đoán \"không gian lận\" vẫn đạt Accuracy ~99,8% "
        "nhưng vô dụng trong thực tế). Đề tài sử dụng các chỉ số sau, tính trên ma trận nhầm lẫn "
        "(Confusion Matrix) gồm True Positive - TP, False Positive - FP, True Negative - TN, "
        "False Negative - FN:"
    )
    for item in [
        "Precision = TP / (TP + FP): trong số giao dịch mô hình dự đoán là gian lận, bao nhiêu "
        "phần trăm thực sự là gian lận (đo mức độ \"báo động giả\").",
        "Recall = TP / (TP + FN): trong số giao dịch gian lận thực tế, mô hình phát hiện được "
        "bao nhiêu phần trăm (đo mức độ \"bỏ sót\").",
        "F1-score = 2·Precision·Recall / (Precision + Recall): trung bình điều hòa, cân bằng "
        "giữa Precision và Recall.",
        "ROC-AUC: diện tích dưới đường cong ROC (True Positive Rate vs False Positive Rate).",
        "PR-AUC (Precision-Recall AUC): diện tích dưới đường cong Precision-Recall - chỉ số "
        "được ưu tiên hơn ROC-AUC khi dữ liệu mất cân bằng nặng, vì ROC-AUC có thể cho giá trị "
        "cao \"ảo\" do số lượng lớp âm (giao dịch hợp lệ) áp đảo.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_page_break()

    # ===== 3. KIẾN TRÚC & PHƯƠNG PHÁP =====
    add_heading(doc, "3. Kiến trúc hệ thống và phương pháp thực hiện", level=1)

    add_heading(doc, "3.1. Kiến trúc tổng thể", level=2)
    doc.add_paragraph(
        "[Dataset gốc] → [HDFS lưu trữ] → [Spark: ETL & xử lý mất cân bằng] "
        "→ [Spark MLlib / scikit-learn: huấn luyện mô hình] "
        "→ [Đánh giá: Precision/Recall/F1/ROC-AUC/PR-AUC] → [Trực quan hóa]"
    ).runs[0].font.name = "Consolas"
    doc.add_paragraph(
        "Công nghệ sử dụng: Hadoop HDFS (mô phỏng bằng thư mục cục bộ) cho lưu trữ; Apache "
        "Spark (PySpark, Spark SQL, Spark MLlib) cho xử lý dữ liệu và huấn luyện Logistic "
        "Regression/Random Forest; scikit-learn cho Isolation Forest và imbalanced-learn (SMOTE) "
        "cho xử lý mất cân bằng; Matplotlib/Seaborn cho trực quan hóa."
    )

    add_heading(doc, "3.2. Dữ liệu", level=2)
    doc.add_paragraph(
        "Bộ dữ liệu Credit Card Fraud Detection (Kaggle - ULB): 284.807 giao dịch thẻ tín dụng "
        "thực hiện bởi chủ thẻ châu Âu trong 2 ngày, gồm 30 đặc trưng đầu vào (Time, Amount và "
        "28 thành phần V1-V28 thu được từ phép biến đổi PCA để bảo mật thông tin gốc) và nhãn "
        "Class (0 = giao dịch hợp lệ, 1 = gian lận). Sau khi loại bỏ dòng trùng lặp/thiếu dữ "
        "liệu, tập dữ liệu còn 283.726 giao dịch, trong đó số giao dịch gian lận chiếm khoảng "
        "0,17%."
    )

    add_heading(doc, "3.3. Quy trình xử lý", level=2)
    steps = [
        ("Bước 1 - ETL", "Đọc dữ liệu bằng Spark DataFrame, khảo sát phân phối lớp/giá trị "
         "thiếu, loại bỏ trùng lặp, chuẩn hóa Amount và Time bằng StandardScaler (giữ nguyên "
         "cột gốc phục vụ trực quan hóa, tạo thêm cột đã chuẩn hóa phục vụ huấn luyện mô hình - "
         "để cùng thang đo với các thành phần PCA)."),
        ("Bước 2 - Chia train/test", "Chia tập huấn luyện/kiểm tra theo THỜI GIAN "
         "(time-based split, tỉ lệ 70/30) thay vì random split, mô phỏng đúng bối cảnh thực tế: "
         "mô hình phải dự đoán giao dịch trong TƯƠNG LAI dựa trên dữ liệu lịch sử."),
        ("Bước 3 - Xử lý mất cân bằng", "Tính trọng số lớp (class weight) tỉ lệ nghịch với tần "
         "suất từng lớp để dùng trực tiếp trong Spark MLlib; đồng thời sinh thêm phiên bản dữ "
         "liệu train qua SMOTE oversampling (tỉ lệ gian lận sau oversample ~10% lớp đa số) để "
         "so sánh."),
        ("Bước 4 - Huấn luyện mô hình", "Huấn luyện Logistic Regression và Random Forest bằng "
         "Spark MLlib (dùng weightCol=class_weight); huấn luyện Isolation Forest bằng "
         "scikit-learn trên mẫu dữ liệu train KHÔNG dùng nhãn."),
        ("Bước 5 - Tinh chỉnh siêu tham số", "Grid Search kết hợp 3-fold Cross-Validation (metric "
         "tối ưu: PR-AUC) cho Logistic Regression (regParam, elasticNetParam) và Random Forest "
         "(numTrees, maxDepth); so sánh chiến lược class-weight và SMOTE với cùng bộ tham số tốt "
         "nhất; tối ưu ngưỡng phân loại (classification threshold) bằng cách tối đa hóa F1-score "
         "trên một tập validation TÁCH RIÊNG từ tập train (không chạm vào tập test, tránh rò rỉ "
         "dữ liệu)."),
        ("Bước 6 - Đánh giá & trực quan hóa", "Đánh giá cả 3 mô hình trên CÙNG một tập test giữ "
         "lại từ đầu (chưa từng được dùng để huấn luyện hay tinh chỉnh), theo các chỉ số ở mục "
         "2.4; xuất biểu đồ minh họa kết quả."),
    ]
    for title_, desc in steps:
        p = doc.add_paragraph()
        p.add_run(f"{title_}: ").bold = True
        p.add_run(desc)

    doc.add_page_break()

    # ===== 4. KẾT QUẢ THỰC NGHIỆM =====
    add_heading(doc, "4. Kết quả thực nghiệm", level=1)

    add_heading(doc, "4.1. Khám phá dữ liệu (EDA)", level=2)
    doc.add_paragraph(
        "Hình 1 minh họa mức độ mất cân bằng cực đoan giữa hai lớp (thang log) và cho thấy các "
        "giao dịch gian lận có xu hướng phân bố số tiền (Amount) khác biệt so với giao dịch hợp "
        "lệ."
    )
    add_figure(doc, "class_distribution.png",
               "Hình 1. Phân phối giao dịch bình thường vs gian lận, và phân phối Amount theo lớp.")

    add_heading(doc, "4.2. Kết quả tinh chỉnh siêu tham số", level=2)
    if thresholds:
        lr_t = thresholds.get("logistic_regression", {})
        rf_t = thresholds.get("random_forest", {})
        rows = [
            ["Logistic Regression", f"regParam={lr_t.get('regParam')}, "
             f"elasticNetParam={lr_t.get('elasticNetParam')}",
             lr_t.get("strategy", "-"), f"{lr_t.get('threshold', 0.5):.4f}"],
            ["Random Forest", f"numTrees={rf_t.get('numTrees')}, maxDepth={rf_t.get('maxDepth')}",
             rf_t.get("strategy", "-"), f"{rf_t.get('threshold', 0.5):.4f}"],
        ]
        tune_df = pd.DataFrame(
            rows, columns=["Mô hình", "Siêu tham số tốt nhất (Grid Search)",
                           "Chiến lược mất cân bằng", "Ngưỡng phân loại tối ưu"])
        add_table_from_df(doc, tune_df)
        doc.add_paragraph(
            "Cả hai mô hình đều được xác định là dùng chiến lược class-weight cho kết quả PR-AUC "
            "nhỉnh hơn (đo trên tập huấn luyện) so với SMOTE. Ngưỡng phân loại tối ưu (tối đa "
            "hóa F1 trên tập validation tách riêng) khác biệt đáng kể so với mặc định 0,5 - cho "
            "thấy tầm quan trọng của việc hiệu chỉnh ngưỡng khi dữ liệu mất cân bằng."
        )
    else:
        doc.add_paragraph(
            "Chưa chạy `tune_models.py` - báo cáo này dùng tham số/ngưỡng mặc định. Chạy "
            "`python src/tune_models.py` rồi sinh lại báo cáo để có kết quả tinh chỉnh."
        )

    add_heading(doc, "4.3. So sánh hiệu năng 3 mô hình", level=2)
    doc.add_paragraph(
        "Bảng 1 trình bày kết quả của cả 3 mô hình trên tập test (85.324 giao dịch, giữ lại từ "
        "đầu, không được dùng để huấn luyện hay tinh chỉnh):"
    )
    display_df = metrics_df.rename(columns={
        "model": "Mô hình", "precision": "Precision", "recall": "Recall",
        "f1_score": "F1-score", "roc_auc": "ROC-AUC", "pr_auc": "PR-AUC",
        "tn": "TN", "fp": "FP", "fn": "FN", "tp": "TP",
    })
    add_table_from_df(
        doc, display_df,
        float_cols=["Precision", "Recall", "F1-score", "ROC-AUC", "PR-AUC"],
    )
    doc.add_paragraph()
    add_figure(doc, "metrics_comparison.png",
               "Hình 2. So sánh Precision/Recall/F1/ROC-AUC/PR-AUC giữa 3 mô hình.")
    add_figure(doc, "confusion_matrices.png",
               "Hình 3. Confusion Matrix của từng mô hình trên tập test.")

    add_heading(doc, "4.4. Phân tích và thảo luận", level=2)
    best_row = metrics_df.loc[metrics_df["f1_score"].idxmax()]
    doc.add_paragraph(
        f"{best_row['model']} đạt F1-score cao nhất ({best_row['f1_score']:.4f}), với Precision "
        f"{best_row['precision']:.4f} và Recall {best_row['recall']:.4f} - cho thấy đây là lựa "
        "chọn cân bằng nhất giữa việc phát hiện đúng giao dịch gian lận và hạn chế báo động giả "
        "trong số 3 mô hình được thử nghiệm."
    )
    doc.add_paragraph(
        "Logistic Regression, sau khi được tinh chỉnh ngưỡng phân loại, đạt Precision khá cao "
        "nhưng Recall thấp hơn Random Forest - phản ánh đặc điểm mô hình tuyến tính khó nắm bắt "
        "các quan hệ phi tuyến phức tạp giữa các đặc trưng PCA so với mô hình cây."
    )
    doc.add_paragraph(
        "Isolation Forest có Precision và PR-AUC thấp hơn rõ rệt so với hai mô hình có giám sát "
        "(có Recall tương đương nhưng đi kèm rất nhiều báo động giả - False Positive cao). Đây "
        "không phải là hạn chế do lỗi triển khai, mà là đặc điểm cố hữu của phương pháp không "
        "giám sát: Isolation Forest xác định bất thường dựa trên việc bị \"cô lập\" trong toàn "
        "bộ không gian đặc trưng (ví dụ giao dịch có Amount rất lớn hoặc rất nhỏ một cách bất "
        "thường), không nhất thiết trùng khớp với các giao dịch gian lận thực tế - vốn có thể có "
        "giá trị Amount hoàn toàn bình thường nhưng bất thường ở các đặc trưng ẩn khác. Kết quả "
        "này minh chứng cho việc: khi có đủ dữ liệu gán nhãn, các mô hình học có giám sát vẫn "
        "vượt trội hơn hẳn so với phương pháp phát hiện bất thường thuần túy cho bài toán phát "
        "hiện gian lận cụ thể này."
    )
    add_figure(doc, "pca_anomaly.png",
               "Hình 4. Chiếu 2D (PCA) minh họa vùng bất thường mà Isolation Forest phát hiện - "
               "không hoàn toàn trùng khớp với ranh giới gian lận thực tế.")
    add_figure(doc, "suspicious_transactions.png",
               "Hình 5. Các giao dịch bị Isolation Forest gắn cờ nghi vấn, theo thời gian và số tiền.")

    doc.add_page_break()

    # ===== 5. KẾT LUẬN =====
    add_heading(doc, "5. Kết luận và hướng phát triển", level=1)
    doc.add_paragraph(
        "Đề tài đã xây dựng thành công một pipeline xử lý dữ liệu lớn end-to-end để phát hiện "
        "giao dịch tài chính bất thường, từ thu thập/lưu trữ dữ liệu (mô phỏng HDFS), xử lý và "
        "làm sạch bằng Apache Spark, xử lý dữ liệu mất cân bằng, huấn luyện và tinh chỉnh 3 mô "
        f"hình Machine Learning, đến đánh giá và trực quan hóa kết quả. Trên bộ dữ liệu thật "
        f"({len(metrics_df)} mô hình được so sánh), {best_row['model']} cho kết quả tốt nhất "
        "với F1-score đạt "
        f"{best_row['f1_score']:.4f}, khẳng định tính phù hợp của phương pháp học có giám sát "
        "kết hợp xử lý mất cân bằng và tinh chỉnh ngưỡng phân loại cho bài toán này."
    )
    doc.add_paragraph("Hướng phát triển tiếp theo:")
    for item in [
        "Triển khai trên cluster Hadoop/Spark thật (nhiều node) để đánh giá khả năng mở rộng "
        "(scalability) khi khối lượng dữ liệu tăng lên hàng chục/hàng trăm triệu giao dịch.",
        "Thử nghiệm thêm các mô hình khác: Gradient Boosting (XGBoost/LightGBM), mạng nơ-ron "
        "(Autoencoder cho phát hiện bất thường), hoặc mô hình kết hợp (ensemble/stacking) giữa "
        "các mô hình có giám sát và không giám sát.",
        "Xây dựng pipeline xử lý theo thời gian thực (streaming) bằng Spark Structured Streaming "
        "hoặc Kafka, thay vì xử lý theo lô (batch) như hiện tại.",
        "Áp dụng thêm các kỹ thuật giải thích mô hình (SHAP, LIME) để tăng khả năng diễn giải "
        "quyết định của mô hình cho đội ngũ nghiệp vụ.",
        "Thu thập thêm dữ liệu gán nhãn thật để giảm phụ thuộc vào phương pháp không giám sát, "
        "hoặc kết hợp học bán giám sát (semi-supervised learning).",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_page_break()

    # ===== TÀI LIỆU THAM KHẢO =====
    add_heading(doc, "Tài liệu tham khảo", level=1)
    refs = [
        "Machine Learning Group - ULB, \"Credit Card Fraud Detection\" dataset, Kaggle, "
        "https://www.kaggle.com/mlg-ulb/creditcardfraud",
        "Apache Spark Documentation, \"MLlib: Machine Learning Library\", "
        "https://spark.apache.org/docs/latest/ml-guide.html",
        "Apache Hadoop Documentation, \"HDFS Architecture Guide\", "
        "https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html",
        "Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). \"Isolation Forest\". "
        "In 2008 Eighth IEEE International Conference on Data Mining (pp. 413-422).",
        "Chawla, N. V., Bowyer, K. W., Hall, L. O., & Kegelmeyer, W. P. (2002). "
        "\"SMOTE: Synthetic Minority Over-sampling Technique\". "
        "Journal of Artificial Intelligence Research, 16, 321-357.",
        "scikit-learn Documentation, \"IsolationForest\", "
        "https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html",
        "imbalanced-learn Documentation, \"SMOTE\", "
        "https://imbalanced-learn.org/stable/references/generated/imblearn.over_sampling.SMOTE.html",
    ]
    for ref in refs:
        doc.add_paragraph(ref, style="List Number")

    doc.save(OUTPUT_PATH)
    print(f"[Report] Đã sinh báo cáo -> {OUTPUT_PATH}")


if __name__ == "__main__":
    build_report()
