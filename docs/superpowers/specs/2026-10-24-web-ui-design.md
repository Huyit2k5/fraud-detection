# Thiết kế: Giao diện web cho pipeline phát hiện gian lận (FastAPI + Next.js)

Ngày: 2026-10-24 · Trạng thái: chờ duyệt (bản 2)

Các phác thảo đã thống nhất nằm trong `.superpowers/brainstorm/987-1792812546/content/`:
- `etl-v2.html`: DAG + dòng sự kiện.
- `etl-eda-v5.html`: EDA cho người không chuyên.
- `ui-mockup-v1.html`: tab Huấn luyện. Riêng phần B và C của tab này đã được điều chỉnh, xem mục 8.2.
- `inference-v2.html`: tab Suy luận.

Các con số trong phác thảo chỉ để minh họa.

## 1. Mục đích và lý do

Dashboard Streamlit hiện tại (`dashboard/app.py`) chỉ in log thô của Spark, khó đọc và khó hiểu. Giao diện mới dùng để **demo khi bảo vệ đồ án**. Người xem cần được coi như **khách hàng không chuyên**: họ không biết Spark là gì, cũng không biết V14 là gì.

- **Khi demo, trọng tâm là tab Suy luận:** hệ thống giám sát giao dịch, phát hiện gian lận và **giải thích bằng lời** vì sao nó nghi ngờ.
- **ETL và EDA vẫn có trong app**, nhưng chủ yếu để chụp đưa lên slide và để chứng minh dữ liệu được Spark xử lý song song.
- **Yêu cầu cốt lõi:** mọi hình ảnh trực quan phải chạy theo **số liệu thật của lần chạy đó**, không phải animation dựng sẵn.

## 2. Mục tiêu

- Làm lại giao diện thành **backend FastAPI + frontend Next.js**, một trang web với 3 tab: **① ETL → ② Huấn luyện & Đánh giá → ③ Suy luận**.
- Thay log thô bằng **dòng sự kiện viết bằng câu dễ hiểu**. Log thô vẫn giữ, nhưng ẩn trong ô "Xem log chi tiết".
- Thêm **đặc trưng giờ trong ngày** vào dữ liệu và mô hình (mục 7), để phần giải thích có lý do "giờ giao dịch" thật.
- Spark chạy **4 luồng** (`local[4]`) để máy người dùng chịu được.

## 3. Ngoài phạm vi (non-goals)

- **Không có 3D.** Người dùng đã bỏ các cảnh 3D để giữ đơn giản và chạy ổn khi máy dùng pin. Mọi trực quan là 2D (SVG/canvas), có chuyển động nhẹ.
- Không đăng nhập, không triển khai lên server, không đóng gói Docker cho app. HDFS vẫn chạy bằng `docker-compose.hdfs.yml` như cũ.
- Không dùng Spark Structured Streaming cho chế độ giám sát trực tiếp (lý do ở mục 8.3).
- Không cho nhập tay V1–V28.
- Không trực quan hóa từng dòng dữ liệu trong Spark. Đơn vị nhỏ nhất là **task**.

## 4. Điều tuyệt đối tránh (anti-goals)

- **Số liệu bịa hoặc animation dựng sẵn.** Mọi con số, khối hay câu nhận xét phải sinh từ sự kiện hoặc kết quả thật. Chưa có dữ liệu thì hiện trạng thái trống hoặc chờ, không được hiện số mẫu.
- **Câu chữ khách hàng không hiểu** ở các vị trí chính, ví dụ "V14 = −8,2", "SHAP", "stage 6". Thuật ngữ kỹ thuật chỉ nằm trong các ô "🔧 Chi tiết kỹ thuật" mặc định đóng.
- **Giải thích sai sự thật.** Mỗi lý do trong phần "Vì sao" phải đúng là đóng góp của mô hình, không được thêm lý do mà mô hình không dùng.
- **Phá CLI hiện có.** `python run_pipeline.py`, `python src/<step>.py`, `tune_models.py` và `reports/generate_report.py` vẫn chạy được như cũ. Phần phát sự kiện cho UI chỉ bật khi được yêu cầu (mục 6.1).
- **Làm máy đứng** khi chạy cùng Spark trên laptop dùng pin.

## 5. Ràng buộc

- Chạy trên Windows. Laptop có i5-12450HX, 28 GB RAM, RTX 3050 cùng card Intel, và **có thể demo khi không cắm sạc**.
- PySpark 4.2 cần **JDK 17** và `HADOOP_HOME=<repo>/hadoop`. Backend phải tự dò JDK 17 cho tiến trình con, chuyển logic `_find_jdk17` / `spark_subprocess_env` từ `dashboard/app.py` sang.
- Giữ `pandas < 3.0` và để Arrow tắt trong `get_spark_session` (xem CLAUDE.md).
- `DATA_BACKEND` = `local` hoặc `hdfs`, và UI phải chạy được ở cả hai chế độ.
- Toàn bộ chữ trên giao diện, chú thích code và output console bằng **tiếng Việt**.
- Máy có Node 22 và pnpm 10.

## 6. Kiến trúc

```
frontend/ (Next.js)  ──HTTP + WebSocket──▶  backend/ (FastAPI)
                                              │ chạy từng bước pipeline như tiến trình con
                                              ▼
                                       python src/<step>.py  (FRAUD_UI_EVENTS=1)
                                              │ in sự kiện JSON ra stdout
                                              │ + luồng phụ đọc tiến độ Spark của chính nó
                                              ▼
                                       Spark local[4] ── đọc/ghi ── data/ local hoặc HDFS
```

### 6.1 Sự kiện từ pipeline (nguồn số liệu thật duy nhất)

- Thêm một module nhỏ trong `src/` (ví dụ `src/ui_events.py`). Khi `FRAUD_UI_EVENTS=1`, module này in mỗi sự kiện thành **một dòng JSON có tiền tố nhận diện** ra stdout, ví dụ `@@EVENT {...}`. Khi không bật thì không làm gì.
- Các hàm `run_*` phát `step_start` / `step_end` cho từng bước con, kèm số liệu thật của bước đó. Các lệnh `print` hiện có giữ nguyên.
- Mỗi bước con gắn `sparkContext.setJobGroup(<step_id>, <mô tả tiếng Việt>)` để biết job Spark nào thuộc bước nào.
- **Tiến độ Spark:** trong tiến trình con, một luồng nền đọc định kỳ (khoảng 250–500 ms) `StatusTracker` và REST API Spark UI của chính tiến trình đó (jobs, stages, taskList). Luồng này phát sự kiện job, stage và task: trạng thái, thời điểm bắt đầu, thời lượng, số bản ghi, chỉ số partition. **Trước `spark.stop()` phải phát một bản chụp cuối.**
- `get_spark_session` đọc số luồng từ biến môi trường (ví dụ `SPARK_CORES`, mặc định **4**) và dùng `local[N]`. Cổng Spark UI cố định.
- *(Quyết định của Claude)* Đặt `spark.sql.files.maxPartitionBytes` nhỏ hơn mặc định (cấu hình được, ví dụ 16 MB). Nhờ vậy file 151 MB thành khoảng 10 partition thay vì 2, và cả 4 luồng đều có việc. Đây là hành vi thật của Spark, và cũng là một điểm để giải thích: "2 block HDFS → ~10 phần → 4 luồng".
- Backend đọc stdout của tiến trình con. Dòng có tiền tố được đẩy qua WebSocket dưới dạng sự kiện. Dòng thường được đẩy làm log thô.
- *(Quyết định của Claude)* **Mỗi lần chạy được lưu lại** thành file JSONL (ví dụ `reports/ui/runs/<bước>-<thời điểm>.jsonl`). Nhờ vậy tải lại trang không mất trạng thái, và có nút **"Phát lại lần chạy lúc HH:MM"** chiếu lại đúng chuỗi sự kiện thật đã ghi, phòng khi chạy trực tiếp bị lỗi. Màn hình phải ghi rõ đang phát lại.

### 6.2 Backend (FastAPI, `backend/`)

- Dùng chung `.venv`, import `src/config.py`.
- **Mỗi lúc chỉ chạy một bước pipeline.** Yêu cầu thứ hai bị từ chối kèm thông báo. Có nút dừng.
- Endpoint chạy từng bước (ETL, cân bằng, huấn luyện, tinh chỉnh, đánh giá, chạy tất cả), WebSocket sự kiện, lịch sử lần chạy, HDFS (dùng `src/hdfs_utils.py`), và suy luận (mục 8.3).
- Thanh trạng thái: backend, HDFS, `DATA_BACKEND`, số luồng Spark, mô hình đang dùng.

### 6.3 Frontend (Next.js, `frontend/`)

- *(Quyết định của Claude)* Next.js (App Router) + TypeScript + Tailwind, **motion** (Framer Motion) cho chuyển động, và một thư viện biểu đồ 2D (ví dụ Recharts hoặc visx) cho DAG và biểu đồ.
- Giao diện tối, hợp với máy chiếu, chữ tiếng Việt, kiểu dáng theo các phác thảo.
- *(Quyết định của Claude)* Mỗi tab có địa chỉ riêng (`/etl`, `/train`, `/infer`) để mở thẳng tab cần nói. Thanh tiêu đề dùng chung.
- Chuyển động phải nhẹ: tránh hiệu ứng liên tục khi không có sự kiện mới.

## 7. Đặc trưng mới: giờ trong ngày (người dùng đã đồng ý)

**Lý do:**
- `Time` là số giây kể từ giao dịch đầu tiên (0 → 172.792, tức 48 giờ). Nó không cho mô hình biết sáng hay đêm.
- Vì train/test chia theo thời gian, **mọi giá trị `Time` trong tập test đều lớn hơn mọi giá trị trong tập train**, nên `Time_scaled` gần như vô dụng hoặc gây nhiễu.
- Dữ liệu thật cho thấy lúc 2h sáng, tỉ lệ gian lận là **1,71%**, so với khoảng 0,05–0,2% ban ngày.

**Thay đổi:**
- Trong `spark_etl.py`, sau bước làm sạch, tính bằng Spark:
  - `hour = (Time % 86400) / 3600`, là giờ có phần lẻ.
  - `Hour` = phần nguyên của `hour` (0–23), **chỉ dùng để hiển thị và vẽ biểu đồ**.
  - `Hour_sin = sin(2π·hour/24)` và `Hour_cos = cos(2π·hour/24)`, **dùng cho mô hình**.
- `config.py`: `MODEL_FEATURE_COLS = [Hour_sin, Hour_cos, Amount_scaled, V1…V28]`. **Bỏ `Time_scaled` khỏi mô hình.** Cột `Time` gốc vẫn giữ để chia train/test.
- **Giả định "giao dịch đầu tiên lúc 0h"** được ghi thành chú thích nhỏ trên giao diện, trong slide và trong báo cáo. Bằng chứng ủng hộ: số giao dịch thấp nhất rơi vào khoảng 1h–6h.
- **So sánh trước/sau:** trước khi đổi đặc trưng, lưu lại bảng chỉ số hiện tại (`metrics_comparison.csv`, `thresholds.json`). Sau khi chạy lại pipeline và tinh chỉnh với đặc trưng mới, xuất bảng so sánh trước/sau để đưa vào slide và báo cáo.
- Cập nhật `reports/generate_report.py`: thêm mục "Tạo đặc trưng" và bảng so sánh, sửa các đoạn mô tả đặc trưng cũ, và sửa các con số cố định trong README/CLAUDE.md nếu thay đổi.
- Các notebook dùng `MODEL_FEATURE_COLS` sẽ tự theo. Notebook nào in số liệu cố định thì không bắt buộc sửa.

## 8. Các tab

### 8.1 Tab ① ETL

Hai chế độ xem, chuyển bằng một nút: **DAG Spark** và **📊 Biểu đồ EDA**.

**Chung cho cả hai chế độ:**
- Nút **Chạy ETL / Dừng / Phát lại**.
- **Thanh 6 bước:** Đọc → EDA → Làm sạch → Chuẩn hóa & tạo đặc trưng giờ → Chia train/test → Ghi Parquet. Mỗi bước có trạng thái, thời gian chạy và một con số chính khi xong.

**Chế độ DAG Spark** (phác thảo `etl-v2.html`), cùng **dòng sự kiện**:
- Bắt đầu bằng **nút nguồn HDFS** với các **block thật** của `creditcard.csv` (lấy từ `GET_BLOCK_LOCATIONS`). Ở chế độ `local`, nút này là file cục bộ kèm chú thích. Kết thúc bằng nút đích, nơi ghi Parquet (HDFS `/data/processed` hoặc local), hiện số part-file thật.
- Mỗi bước ETL là một khối. Khối đang chạy bung ra thành **các task thật** của stage hiện tại, với các trạng thái chờ / đang chạy (nhấp nháy nhẹ) / xong. Dòng chú thích: "4 task đang chạy cùng lúc = 4 luồng Spark đều bận". Di chuột vào task để xem số dòng xử lý và thời gian chạy.
- Nếu REST API cho biết stage cha thì vẽ quan hệ thật. Nếu không, vẽ theo thứ tự thực thi và ghi chú như vậy.
- **Dòng sự kiện** (cột bên phải): các sự kiện theo thời gian, nhóm theo bước, mỗi sự kiện gồm giờ, một câu dễ hiểu và một dòng "vì sao" nếu cần. Ví dụ: "Spark chia dữ liệu thành 10 phần để xử lý song song" và "10 phần / 4 luồng → chạy thành khoảng 3 lượt". Bên dưới là ô "Xem log chi tiết".

**Chế độ Biểu đồ EDA** (phác thảo `etl-eda-v5.html`), viết cho người không chuyên. Màn hình **tự chuyển sang đây khi bước EDA xong**. Bấm ô EDA trên thanh bước cũng mở trang này.
- **4 con số chính:** số giao dịch, số vụ gian lận (và "cứ ~N giao dịch có 1"), tổng tiền bị gian lận, trung bình mỗi vụ.
- **Tổng quan:** gian lận hiếm đến mức nào (hình ô vuông), dữ liệu có sạch không (viết bằng câu: không thiếu giá trị, số dòng trùng đã loại, số dòng còn lại).
- **Số tiền & gian lận:** tỉ lệ gian lận theo từng khoảng tiền, và tổng tiền bị mất theo từng khoảng tiền.
- **Thời điểm & gian lận:** số giao dịch và tỉ lệ gian lận theo giờ (dùng `Hour`), và ô số tiền × giờ (tỉ lệ gian lận theo từng tổ hợp).
- Mỗi biểu đồ có một **câu hỏi tiêu đề** và **một dòng nhận xét sinh từ số liệu thật** (không viết cố định). Không hiện câu đếm số lượng biểu đồ.
- **🔧 Phần kỹ thuật** (mặc định đóng): bản đồ tương quan giữa các đặc trưng (Toàn bộ / Chỉ gian lận / Chỉ bình thường), ghi rõ V1…V28 là thông tin ngân hàng đã mã hóa.
- Tất cả số liệu do Spark tính trên toàn bộ dữ liệu, rồi phát qua sự kiện hoặc lưu thành JSON nhỏ.
- *(Quyết định của Claude)* Mỗi biểu đồ có nút **tải ảnh PNG** để đưa vào slide.

### 8.2 Tab ② Huấn luyện & Đánh giá

- Nút từng bước **Cân bằng → Huấn luyện → Tinh chỉnh → Đánh giá** và nút **Chạy tất cả**. *(Quyết định của Claude)* "Chạy tất cả" mặc định bỏ qua Tinh chỉnh vì chạy lâu, có ô đánh dấu để bao gồm. Có thanh bước, dòng sự kiện và ô log như tab ETL.
- **A. Cân bằng dữ liệu:** số ca trước khi xử lý, trọng số lớp thật, số ca trước/sau SMOTE, và biểu đồ tán xạ 2D gồm mẫu điểm thật cùng **các điểm SMOTE sinh ra thật**. `imbalance.py` lưu mẫu này thành JSON.
- **B. Spark huấn luyện song song:** dùng lại **DAG + task** của tab ETL cho các job huấn luyện. Phác thảo cũ dùng kiểu timeline, nay đổi theo quyết định bỏ timeline.
- **C. Bên trong mô hình** (chọn LR / RF / IF):
  - LR: loss qua từng vòng lặp (`objectiveHistory`) và trọng số từng đặc trưng.
  - RF: **lưới 2D các cây thật đã học**, mỗi ô một cây. Bấm vào ô để xem cây với các điều kiện tách thật. Không dùng 3D.
  - IF: số nhát cắt trung bình để cô lập một vài giao dịch thật, so sánh ca gian lận với ca bình thường.
- **D. Tinh chỉnh:** lưới tham số tô màu theo PR-AUC trung bình qua CV (`avgMetrics` thật), so sánh class weight với SMOTE, và đường Precision–Recall có đánh dấu ngưỡng tối ưu.
- **E. Đánh giá:** bảng chỉ số, ma trận nhầm lẫn, đường PR. Ghi rõ **mô hình nào được dùng cho tab Suy luận và vì sao**. Thêm bảng **so sánh trước/sau khi thêm đặc trưng giờ** (mục 7).
- Phần chưa có dữ liệu hiện trạng thái trống kèm nút chạy bước tương ứng.

### 8.3 Tab ③ Suy luận (trọng tâm khi demo, phác thảo `inference-v2.html`)

**Mô hình:** *(người dùng quyết định)* chỉ dùng **một mô hình tốt nhất**, không cho các mô hình bỏ phiếu. *(Quyết định của Claude)* Hệ thống tự chọn mô hình có **PR-AUC cao nhất** trong `metrics_comparison.csv` và hiện tên mô hình trên thanh tiêu đề. Ngưỡng lấy từ `thresholds.json`, mặc định 0,5.

**Hai chế độ:**
- **📡 Giám sát trực tiếp** (mặc định):
  - Phát lại giao dịch của **tập test theo đúng thứ tự `Time`**, có tăng tốc (×10 / ×100 / ×1000) và nút tạm dừng/tiếp tục. Mô hình chấm điểm từng giao dịch khi nó đến.
  - Mỗi dòng hiện giờ, thanh rủi ro, số tiền, và "✓ duyệt" hoặc "⚠ chặn". Dòng bị chặn tô đỏ, bấm vào để xem giải thích.
  - **Bộ đếm** (so với nhãn thật): đã kiểm tra, bắt đúng, báo nhầm, bỏ sót, và **tổng số tiền gian lận đã chặn kịp**.
- **🔍 Kiểm tra 1 giao dịch:** Ngẫu nhiên / Lấy 1 ca gian lận / Lấy 1 ca bình thường. Dùng cùng khung giải thích.

**Khung giải thích một giao dịch** (viết cho khách hàng):
1. **Kết luận:** "⚠ NGHI GIAN LẬN" hoặc "✓ AN TOÀN", **mức rủi ro 0–100** (bằng xác suất × 100), vạch ngưỡng cảnh báo, và một **đề xuất hành động** ví dụ "tạm giữ giao dịch, gửi mã xác minh hoặc gọi chủ thẻ". Nút **"Xem kết quả thật"** lật nhãn thật (đúng/sai).
2. **Vì sao hệ thống nghi ngờ:** đúng 3 nhóm lý do, viết bằng lời, kèm thanh độ lớn và chiều (đẩy về phía gian lận hay an toàn):
   - **🧬 Hành vi thẻ:** tổng SHAP của V1…V28, mô tả là "28 dấu hiệu ngân hàng đã mã hóa để bảo mật".
   - **🌙 Giờ giao dịch:** tổng SHAP của `Hour_sin` + `Hour_cos`, hiện giờ đọc được (ví dụ "lúc 3 giờ sáng") kèm tỉ lệ gian lận thật của khung giờ đó.
   - **💶 Số tiền:** SHAP của `Amount_scaled`, hiện số tiền thật kèm tỉ lệ gian lận thật của khoảng tiền đó.

   Gộp như vậy là hợp lệ vì giá trị SHAP cộng dồn được. Câu chữ phải phản ánh đúng chiều của đóng góp: một yếu tố đẩy về phía an toàn thì không được viết như lý do nghi ngờ. Ô **"🔧 Chi tiết kỹ thuật"** (mặc định đóng) liệt kê SHAP từng đặc trưng. Phải là **SHAP chính xác của đúng mô hình đang dùng**.
3. **Những vụ giống nhất trong quá khứ:** 5 láng giềng gần nhất trong tập train, theo các đặc trưng mô hình. Hiện **số tiền, giờ và kết quả thật**, không hiện V. Có một dòng tóm tắt "x / 5 vụ giống nhất từng là gian lận".
4. **Thử thay đổi giao dịch:** thanh trượt **số tiền** và **giờ**. Mức rủi ro và kết luận được chấm lại ngay, các dấu hiệu mã hóa giữ nguyên. Ghi chú rõ điều này.

Khối "So với phân bố dữ liệu" ở phác thảo đầu tiên được thay bằng tỉ lệ gian lận của khoảng tiền và khung giờ, đặt ngay trong lý do 🌙 và 💶 (phác thảo v2 đã bỏ biểu đồ V14).

**Yêu cầu kỹ thuật:**
- Mỗi yêu cầu suy luận **không được khởi động Spark**.
- Ở bước đánh giá, mô hình được chọn được xuất sang dạng chạy bằng Python/numpy, và **phải cho cùng xác suất với Spark trên tập test** (kiểm tra tự động, chấp nhận sai số làm tròn). Với Random Forest của Spark: xuất cấu trúc cây kèm số mẫu ở mỗi nút (cần cho TreeSHAP), rồi tính SHAP bằng thư viện `shap` (thêm vào `requirements.txt`). Cách xuất do người code quyết định.
- *(Quyết định của Claude)* Bước đánh giá cũng xuất các cột cần dùng của train/test ra file **local** trong `reports/ui/`, để backend đọc được cả khi `DATA_BACKEND=hdfs`. Bước này cũng lưu sẵn các tỉ lệ gian lận theo khoảng tiền và theo giờ để dùng trong phần lý do.
- Khi thanh trượt giờ thay đổi, backend tính lại `Hour_sin`/`Hour_cos` từ giờ mới. Khi số tiền thay đổi, chuẩn hóa lại bằng đúng mean/std của StandardScaler đã học ở ETL (cần lưu lại các tham số này).
- *(Quyết định của Claude)* Chế độ giám sát **không dùng Spark Structured Streaming**: backend tự phát lại và chấm điểm bằng mô hình đã xuất, để máy nhẹ và demo ổn định.
- Chưa có mô hình thì hiện trạng thái trống kèm nút dẫn sang tab Huấn luyện.

## 9. Thay đổi khác với code hiện có

- `src/`: thêm module sự kiện, job group, luồng đọc tiến độ và đặc trưng giờ. `get_spark_session` đọc số luồng và `maxPartitionBytes` từ cấu hình. Các bước lưu thêm JSON nhỏ cho UI vào `reports/ui/` (thêm vào `.gitignore`).
- `dashboard/app.py` (Streamlit): *(quyết định của Claude)* xóa khi UI mới đã thay thế đầy đủ, rồi bỏ `streamlit` khỏi `requirements.txt`.
- Cập nhật README và CLAUDE.md: cách chạy backend và frontend, biến môi trường mới, đặc trưng mới.
- Thêm `.superpowers/` vào `.gitignore`.

## 10. Thứ tự làm

*(Quyết định của Claude)* Ưu tiên phần dùng khi demo, để luôn có một bản chạy được:

1. **Đặc trưng giờ:** lưu chỉ số cũ, thêm đặc trưng, chạy lại pipeline, kiểm tra kết quả.
2. **Nền móng:** sự kiện pipeline, backend, khung frontend 3 tab.
3. **Tab Suy luận** (xuất mô hình, SHAP, láng giềng, giám sát trực tiếp).
4. **Tab ETL** (DAG + dòng sự kiện, biểu đồ EDA).
5. **Tab Huấn luyện & Đánh giá.**
6. Cập nhật báo cáo Word, gỡ Streamlit, cập nhật tài liệu.

## 11. Để người code tự quyết

- Định dạng sự kiện, tên endpoint, cấu trúc thư mục `backend/` và `frontend/`.
- Cách khởi động cả hai cùng lúc (ví dụ `start_ui.ps1`).
- Màu sắc và chi tiết hình khối, miễn là theo tinh thần các phác thảo và đọc được trên máy chiếu.
- Cách xuất cây Random Forest và cách tìm láng giềng gần nhất.
- Mức độ kiểm thử, nhưng **bắt buộc** có:
  - kiểm tra khớp xác suất giữa mô hình xuất ra và Spark;
  - kiểm tra tổng SHAP cộng điểm cơ sở bằng đúng điểm của mô hình;
  - kiểm tra CLI vẫn chạy như cũ khi tắt `FRAUD_UI_EVENTS`.
