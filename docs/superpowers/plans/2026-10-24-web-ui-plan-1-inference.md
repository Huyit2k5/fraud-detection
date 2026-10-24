# Web UI – Kế hoạch 1: Đặc trưng giờ + nền móng + tab Suy luận

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Có một web app (FastAPI + Next.js) chạy được, với tab **Suy luận** hoàn chỉnh (giám sát trực tiếp + giải thích bằng lời). Mô hình được huấn luyện lại có thêm đặc trưng giờ.

**Architecture:**
- Bước đánh giá của pipeline xuất một **gói suy luận** (`models/inference/`): mô hình tốt nhất dạng JSON, tập train/test dạng Parquet local, tham số chuẩn hóa, tỉ lệ gian lận theo khoảng tiền và theo giờ.
- Backend FastAPI nạp gói này một lần. Backend chấm điểm và tính SHAP bằng numpy + `shap`, **không khởi động Spark**. Backend cũng phát lại tập test qua WebSocket.
- Frontend Next.js hiển thị theo các phác thảo.

**Tech Stack:** PySpark 4.2, scikit-learn, shap 0.51, FastAPI, uvicorn, pytest; Next.js (App Router) + TypeScript + Tailwind + motion, pnpm.

**Spec:** `docs/superpowers/specs/2026-10-24-web-ui-design.md`. Phác thảo giao diện: `.superpowers/brainstorm/987-1792812546/content/inference-v2.html`.

**Phạm vi:** Kế hoạch này làm mục 10, bước 1–3 của spec (đặc trưng giờ, nền móng tối thiểu, tab Suy luận). Tab ETL và tab Huấn luyện ở đây chỉ là trang giữ chỗ. Phần còn lại của spec để cho:
- **Kế hoạch 2:** sự kiện pipeline, DAG, EDA.
- **Kế hoạch 3:** tab Huấn luyện, báo cáo Word, gỡ Streamlit.

## Global Constraints

- Chữ trên giao diện, chú thích code và output console bằng **tiếng Việt**. Định dạng số theo `vi-VN` (dấu chấm phân cách hàng nghìn, dấu phẩy thập phân).
- Không có 3D.
- Python dùng `.venv` (3.11.9). Giữ `pandas>=2.2.2,<3.0`. **Không bật Arrow** trong `get_spark_session`.
- Spark chạy `local[N]`, `N` = biến môi trường `SPARK_CORES`, mặc định **4**.
- Tiến trình Spark trên Windows cần JDK 17 (`C:\Program Files\Eclipse Adoptium\jdk-17*` hoặc `C:\Program Files\Java\jdk-17*`) và `HADOOP_HOME=<repo>/hadoop`.
- Suy luận **không được khởi động Spark**.
- Mức rủi ro = `round(xác suất × 100)`, trong khoảng 0–100.
- Cảnh báo khi `xác suất >= ngưỡng`. Ngưỡng lấy từ `models/thresholds.json`, mặc định 0,5.
- Mô hình dùng cho suy luận là mô hình có `pr_auc` cao nhất trong `reports/metrics_comparison.csv` **trong số các mô hình xuất được** (Random Forest, Logistic Regression).
- Đặc trưng mô hình: `MODEL_FEATURE_COLS = ["Hour_sin", "Hour_cos", "Amount_scaled", "V1", …, "V28"]`. Không còn `Time_scaled`.
- Giả định "giao dịch đầu tiên lúc 0h" phải hiện thành chú thích ở mọi chỗ hiển thị giờ.
- Ở vị trí chính của giao diện không được xuất hiện chữ "V1…V28", "SHAP", "stage". Các chữ này chỉ được nằm trong ô "🔧 Chi tiết kỹ thuật".
- Không phá CLI: `python run_pipeline.py`, `python src/<step>.py`, `python src/tune_models.py` vẫn chạy như cũ.

## Review Focus

1. **Chưa có gói suy luận** (chưa chạy pipeline, hoặc thư mục `models/` trống): API trả 503 kèm thông báo tiếng Việt, và trang `/infer` hiện trạng thái trống có nút dẫn sang `/train`, không được crash. Kiểm thử ở Task 5 và Task 7.
2. **Gói suy luận cũ**, tức mô hình huấn luyện trước khi có đặc trưng giờ (danh sách đặc trưng không khớp `MODEL_FEATURE_COLS`): loader báo lỗi rõ "Mô hình được huấn luyện với bộ đặc trưng cũ, hãy chạy lại pipeline". Kiểm thử ở Task 3.
3. **Mô hình PR-AUC cao nhất không xuất được** (Isolation Forest), hoặc thiếu `metrics_comparison.csv`: chọn mô hình tốt nhất trong số RF/LR và ghi lý do vào `model.json`; không có CSV thì báo lỗi rõ. Kiểm thử ở Task 2.
4. **What-if với giá trị biên:** `amount = 0`, `amount = 25691,16` (lớn nhất trong dữ liệu), `hour = 0` và `hour = 23` phải chạy được. `amount < 0` hoặc `hour` ngoài 0–23 trả 422. Kiểm thử ở Task 5.
5. **Client WebSocket ngắt giữa chừng rồi kết nối lại:** tác vụ phát lại cũ phải dừng, không sinh lỗi trong log. Kết nối mới bắt đầu lại từ đầu tập test. Kiểm thử ở Task 5.

---

## File Structure

```
src/java_env.py            (mới)  dò JDK 17, dựng env cho tiến trình Spark — dùng chung cho conftest, backend
src/config.py              (sửa)  HOUR_* cột, MODEL_FEATURE_COLS mới, SPARK_CORES, INFERENCE_DIR
src/spark_etl.py           (sửa)  add_hour_features, tách fit scaler + lưu tham số scaler
src/export_inference.py    (mới)  xuất gói suy luận: model.json, train/test parquet, rates.json
src/evaluate.py            (sửa)  gọi export_inference_bundle ở cuối run_evaluation
backend/__init__.py        (mới)
backend/runtime.py         (mới)  RFRuntime / LRRuntime: predict_proba, explain (numpy + shap)
backend/bundle.py          (mới)  load_bundle(): đọc + kiểm tra gói suy luận
backend/inference.py       (mới)  InferenceService: chọn mẫu, giải thích có nhóm lý do, láng giềng, what-if, lô phát lại
backend/app.py             (mới)  FastAPI: /api/status, /api/infer/*, WS /api/infer/stream
tests/conftest.py          (mới)  spark fixture, fake bundle fixture
tests/test_hour_features.py, tests/test_export_inference.py, tests/test_runtime.py,
tests/test_inference_service.py, tests/test_api.py   (mới)
frontend/                  (mới)  Next.js app
start_ui.ps1               (mới)  khởi động backend + frontend
requirements.txt, .gitignore, README.md, CLAUDE.md   (sửa)
```

---

### Task 1: Đặc trưng giờ trong ETL + hạ tầng test

**Files:**
- Create: `src/java_env.py`, `tests/conftest.py`, `tests/test_hour_features.py`
- Modify: `src/config.py`, `src/spark_etl.py:34-54` (get_spark_session), `src/spark_etl.py:104-159` (scale_features, run_etl), `requirements.txt`, `.gitignore`

**Interfaces:**
- Produces:
  - `java_env.find_jdk17() -> Path | None`
  - `java_env.spark_env(base: dict | None = None) -> dict`: bản sao env có `JAVA_HOME`, `HADOOP_HOME` và `PATH` đúng. Logic chuyển từ `dashboard/app.py:23-58`, ưu tiên JDK 17 tự dò được.
  - `config.HOUR_COL = "Hour"`, `config.HOUR_SIN_COL = "Hour_sin"`, `config.HOUR_COS_COL = "Hour_cos"`, `config.SECONDS_PER_DAY = 86_400`
  - `config.MODEL_FEATURE_COLS = [HOUR_SIN_COL, HOUR_COS_COL, AMOUNT_SCALED_COL] + PCA_COLS` (31 cột)
  - `config.SPARK_CORES: int` (env `SPARK_CORES`, mặc định 4), `config.INFERENCE_DIR = MODELS_DIR / "inference"`, `config.SCALER_PARAMS_PATH = MODELS_DIR / "feature_scaler.json"`
  - `spark_etl.add_hour_features(df: DataFrame) -> DataFrame`: thêm `Hour` (int 0–23), `Hour_sin`, `Hour_cos`. Công thức: `h = (Time % 86400) / 3600`, `Hour = floor(h)`, `Hour_sin = sin(2πh/24)`, `Hour_cos = cos(2πh/24)`. Dùng `h` có phần lẻ, không dùng `Hour` đã làm tròn.
  - `spark_etl.fit_amount_time_scaler(df) -> StandardScalerModel` và `spark_etl.scale_features(df, scaler_model=None) -> DataFrame` (tự fit nếu `None`, giữ tương thích lời gọi cũ)
  - `spark_etl.save_scaler_params(model, path) -> None`: ghi JSON `{"amount_mean", "amount_std", "time_mean", "time_std"}`. Vector đầu vào của scaler có thứ tự `[Amount, Time]`.

- [ ] **Step 0: Ghi lại chỉ số trước khi đổi đặc trưng (baseline)**

Chạy pipeline với code **hiện tại** rồi lưu bảng chỉ số:
```powershell
python run_pipeline.py
Copy-Item reports/metrics_comparison.csv reports/metrics_before_hour.csv
```
Expected: file `reports/metrics_before_hour.csv` tồn tại, có 3 dòng. Không commit file này (`reports/*.csv` đã bị gitignore). Kế hoạch 3 sẽ dùng nó.

- [ ] **Step 1: Cài thư viện, thêm `.gitignore`**

Thêm vào `requirements.txt`: `shap>=0.51.0`, `fastapi>=0.115.0`, `uvicorn[standard]>=0.30.0`, `pytest>=8.0.0`, `httpx>=0.27.0` (httpx dùng cho TestClient). Thêm `.superpowers/` và `frontend/node_modules/`, `frontend/.next/` vào `.gitignore`. Rồi chạy `.venv\Scripts\pip install -r requirements.txt`.

- [ ] **Step 2: Viết test thất bại**

`tests/conftest.py`:
- Thêm `src/` và gốc repo vào `sys.path`.
- Fixture `spark` (phạm vi session): áp `java_env.spark_env()` vào `os.environ` rồi gọi `get_spark_session("tests")`, và `stop()` khi xong.

`tests/test_hour_features.py::test_add_hour_features`: DataFrame với `Time` = `[0, 10800, 82800, 97200, 5400]`.
```python
rows = {r["Time"]: r for r in add_hour_features(df).collect()}
assert [rows[t]["Hour"] for t in (0, 10800, 82800, 97200, 5400)] == [0, 3, 23, 3, 1]
assert rows[0]["Hour_sin"] == pytest.approx(0.0, abs=1e-9) and rows[0]["Hour_cos"] == pytest.approx(1.0)
assert rows[10800]["Hour_sin"] == pytest.approx(0.70710678) and rows[10800]["Hour_cos"] == pytest.approx(0.70710678)
assert rows[97200]["Hour_sin"] == pytest.approx(rows[10800]["Hour_sin"])     # 3h ngày 2 == 3h ngày 1
assert rows[82800]["Hour_cos"] == pytest.approx(0.96592583)                  # 23h sát 0h
assert rows[5400]["Hour_sin"] == pytest.approx(math.sin(2 * math.pi * 1.5 / 24))  # dùng giờ có phần lẻ
```
`tests/test_hour_features.py::test_model_feature_cols`:
```python
assert MODEL_FEATURE_COLS[:3] == ["Hour_sin", "Hour_cos", "Amount_scaled"] and len(MODEL_FEATURE_COLS) == 31
assert "Time_scaled" not in MODEL_FEATURE_COLS
```
`tests/test_hour_features.py::test_save_scaler_params`: fit scaler trên DataFrame có `Amount` = `[0, 10, 20]` và `Time` = `[0, 100, 200]`, lưu ra `tmp_path`.
```python
assert p["amount_mean"] == pytest.approx(10.0) and p["amount_std"] == pytest.approx(10.0)
```
(Spark dùng độ lệch chuẩn mẫu: std của [0,10,20] = 10.)

- [ ] **Step 3: Chạy để thấy thất bại**

Run: `.venv\Scripts\python -m pytest tests/test_hour_features.py -v`
Expected: FAIL (ImportError `add_hour_features` / `java_env`)

- [ ] **Step 4: Cài đặt**

- Viết `java_env.py`.
- Sửa `config.py` theo Interfaces, và cập nhật chú thích tiếng Việt của `MODEL_FEATURE_COLS`: giải thích vì sao bỏ `Time_scaled` và vì sao dùng sin/cos.
- `get_spark_session` dùng `.master(f"local[{SPARK_CORES}]")`.
- Trong `run_etl`, thứ tự là: `clean_data` → `add_hour_features` → `fit_amount_time_scaler` + `save_scaler_params(..., SCALER_PARAMS_PATH)` → `scale_features(df, scaler)` → ghi.
- In một dòng `[ETL] Thêm đặc trưng giờ: Hour, Hour_sin, Hour_cos (giả định giao dịch đầu tiên lúc 0h)`.

- [ ] **Step 5: Chạy test**

Run: `.venv\Scripts\python -m pytest tests/test_hour_features.py -v`
Expected: 3 passed

- [ ] **Step 6: Chạy lại pipeline thật với đặc trưng mới**

Run: `python run_pipeline.py`
Expected:
- Chạy hết 5 giai đoạn, có file `models/feature_scaler.json`.
- `reports/metrics_comparison.csv` có 3 dòng.
- So với `reports/metrics_before_hour.csv`, Random Forest không được tệ đi quá 0,05 PR-AUC. Nếu tệ hơn mức đó, dừng lại và báo người dùng trước khi làm tiếp.

- [ ] **Step 7: Commit**

```bash
git add src/java_env.py src/config.py src/spark_etl.py tests/ requirements.txt .gitignore
git commit -m "feat: thêm đặc trưng giờ (Hour, Hour_sin, Hour_cos), bỏ Time_scaled khỏi mô hình"
```

---

### Task 2: Xuất gói suy luận ở bước đánh giá

**Files:**
- Create: `src/export_inference.py`, `tests/test_export_inference.py`
- Modify: `src/evaluate.py:114-147` (cuối `run_evaluation`, trước `spark.stop()`)

**Interfaces:**
- Consumes: `config.MODEL_FEATURE_COLS`, `config.INFERENCE_DIR`, `config.SCALER_PARAMS_PATH`, `evaluate.load_thresholds()`
- Produces (định dạng file. Backend ở Task 3–4 đọc đúng các khóa này):
  - `INFERENCE_DIR/model.json`:
    ```
    {"model_name": "Random Forest" | "Logistic Regression", "model_type": "random_forest" | "logistic_regression",
     "features": [...MODEL_FEATURE_COLS], "threshold": float, "pr_auc": float, "selection_note": str,
     "amount_mean": float, "amount_std": float,
     # random_forest:
     "trees": [{"children_left": [int], "children_right": [int], "features": [int], "thresholds": [float],
                "values": [float],            # P(gian lận) tại nút = stats[1]/sum(stats)
                "node_sample_weight": [float]}],   # sum(impurityStats.stats) (có trọng số lớp)
     # logistic_regression:
     "coefficients": [float], "intercept": float, "feature_means": [float]}   # means trên tập train
    ```
    Lá có `children_left = children_right = -1`, `features = -1`, `thresholds = 0`. Nút nội bộ: đi trái khi `x[feature] <= threshold` (quy ước `ContinuousSplit` của Spark).
  - `INFERENCE_DIR/train.parquet` và `INFERENCE_DIR/test.parquet`, cột: `tx_id` (int, chỉ số dòng sau khi sắp theo `Time`, bắt đầu từ 0), `Time`, `Hour`, `Amount`, `Class`, cùng toàn bộ `MODEL_FEATURE_COLS`. Ghi bằng pandas/pyarrow ra đĩa local, kể cả khi `DATA_BACKEND=hdfs`.
  - `INFERENCE_DIR/rates.json`: `{"overall_rate": float, "amount_buckets": [{"label": str, "lo": float, "hi": float | null, "n": int, "fraud": int, "rate": float}], "hours": [{"hour": int, "n": int, "fraud": int, "rate": float}]}`. Tính trên **train**. `rate` là tỉ lệ (0–1), không phải phần trăm. Mốc khoảng tiền: `[0, 1, 10, 50, 100, 500, 1000, ∞)`, nhãn `["<1 €", "1–10 €", "10–50 €", "50–100 €", "100–500 €", "500–1.000 €", ">1.000 €"]`, mỗi khoảng là `lo <= Amount < hi`.
  - `export_inference.export_rf(model: RandomForestClassificationModel) -> list[dict]`. Duyệt cây qua py4j: `model._java_obj.trees()[i].rootNode()`. Nút nội bộ có `.split().featureIndex()`, `.split().threshold()`, `.leftChild()`, `.rightChild()`. Mọi nút có `.impurityStats().stats()`.
  - `export_inference.export_lr(model: LogisticRegressionModel, train_pdf) -> dict`
  - `export_inference.choose_model(comparison_df: pd.DataFrame) -> tuple[str, str]`: trả `(model_name, selection_note)`. Chỉ xét "Random Forest" và "Logistic Regression", lấy `pr_auc` cao nhất. Nếu mô hình có PR-AUC cao nhất toàn bảng không phải hai mô hình này, `selection_note` phải nói rõ.
  - `export_inference.export_inference_bundle(spark, test_df, comparison_df, thresholds) -> Path`

- [ ] **Step 1: Viết test thất bại**

`tests/test_export_inference.py`:
- `test_rf_export_matches_spark(spark)`: tạo 2.000 dòng ngẫu nhiên với 31 cột `MODEL_FEATURE_COLS` (seed 0), `Class = (V14 < -1) | (Amount_scaled > 2)`, cột `class_weight` (1 cho lớp 0, 5 cho lớp 1). Fit `RandomForestClassifier(numTrees=7, maxDepth=4, weightCol="class_weight", seed=1)`. Dùng `export_rf` rồi tính xác suất bằng numpy: duyệt từng cây, lấy trung bình `values` tại lá. So với `vector_to_array(probability)[1]` của Spark:
  ```python
  np.testing.assert_allclose(numpy_prob, spark_prob, atol=1e-9)
  ```
- `test_lr_export_matches_spark(spark)`: cùng dữ liệu, `LogisticRegression(maxIter=50, weightCol="class_weight")`.
  ```python
  np.testing.assert_allclose(1 / (1 + np.exp(-(X @ coef + intercept))), spark_prob, atol=1e-9)
  ```
- `test_choose_model`:
  ```python
  df = pd.DataFrame({"model": ["Logistic Regression", "Random Forest", "Isolation Forest"], "pr_auc": [0.71, 0.80, 0.12]})
  assert choose_model(df)[0] == "Random Forest"
  df.loc[2, "pr_auc"] = 0.95
  name, note = choose_model(df)
  assert name == "Random Forest" and "Isolation Forest" in note
  ```
- `test_rates`: hàm `compute_rates(train_pdf) -> dict` trên DataFrame nhỏ dựng tay.
  ```python
  # Amount [0.5, 0.5, 5, 600], Class [1, 0, 0, 1], Hour [2, 2, 14, 2]
  assert r["amount_buckets"][0] == {"label": "<1 €", "lo": 0, "hi": 1, "n": 2, "fraud": 1, "rate": 0.5}
  assert r["hours"][2]["rate"] == pytest.approx(2 / 3)
  assert len(r["hours"]) == 24
  ```
  Giờ không có giao dịch nào thì `n = 0`, `rate = 0`.

- [ ] **Step 2: Chạy để thấy thất bại**

Run: `.venv\Scripts\python -m pytest tests/test_export_inference.py -v`
Expected: FAIL (ModuleNotFoundError `export_inference`)

- [ ] **Step 3: Cài đặt**

- Viết `src/export_inference.py` theo Interfaces.
- `export_inference_bundle`:
  - Lấy train từ `TRAIN_PARQUET_PATH`, chỉ chọn các cột cần.
  - Load mô hình đã lưu tương ứng `choose_model`.
  - Ghi 4 file vào `INFERENCE_DIR`, bằng cách ghi ra thư mục tạm rồi đổi tên, để không có gói dở dang.
  - In `[Export] Đã xuất gói suy luận (<model_name>) -> <INFERENCE_DIR>`.
- Gọi hàm này ở cuối `run_evaluation`.

- [ ] **Step 4: Chạy test**

Run: `.venv\Scripts\python -m pytest tests/test_export_inference.py -v`
Expected: 4 passed

- [ ] **Step 5: Chạy thật**

Run: `python src/evaluate.py`
Expected: `models/inference/` có `model.json`, `train.parquet`, `test.parquet`, `rates.json`, và `model.json["model_name"]` khớp dòng PR-AUC cao nhất (RF/LR) trong CSV.

- [ ] **Step 6: Commit**

```bash
git add src/export_inference.py src/evaluate.py tests/test_export_inference.py
git commit -m "feat: xuất gói suy luận (mô hình JSON, dữ liệu, tỉ lệ gian lận) ở bước đánh giá"
```

---

### Task 3: Runtime mô hình và loader gói suy luận (không Spark)

**Files:**
- Create: `backend/__init__.py`, `backend/runtime.py`, `backend/bundle.py`, `tests/test_runtime.py`
- Modify: `tests/conftest.py` (thêm fixture `fake_bundle_dir`)

**Interfaces:**
- Consumes: định dạng file của Task 2
- Produces:
  - `runtime.Explanation` (dataclass): `base_value: float`, `contributions: np.ndarray` (theo thứ tự `features`), `space: Literal["probability", "log-odds"]`
  - `runtime.ModelRuntime` (Protocol): `features: list[str]`, `predict_proba(X: np.ndarray) -> np.ndarray` (P(gian lận), shape `(n,)`), `explain(x: np.ndarray) -> Explanation` (x shape `(n_features,)`)
  - `runtime.RFRuntime(trees: list[dict], features: list[str])`:
    - `predict_proba` lấy trung bình `values` lá qua các cây.
    - `explain` dùng `shap.TreeExplainer` với mô hình tùy biến `{"trees": [...]}`, trong đó `values` của mỗi cây chia cho số cây để tổng ra trung bình. `space = "probability"`.
  - `runtime.LRRuntime(coefficients, intercept, feature_means, features)`: `explain` cho `contributions = coef * (x - means)`, `base_value = intercept + coef @ means`, `space = "log-odds"`.
  - `bundle.Bundle` (dataclass): `meta: dict` (nội dung `model.json`, bỏ `trees` / `coefficients`), `runtime: ModelRuntime`, `train: pd.DataFrame`, `test: pd.DataFrame`, `rates: dict`
  - `bundle.BundleError(Exception)` (thông báo tiếng Việt)
  - `bundle.load_bundle(path: Path = INFERENCE_DIR) -> Bundle`: thiếu file thì raise `BundleError("Chưa có mô hình, hãy chạy pipeline (Huấn luyện & Đánh giá) trước.")`. `features` khác `MODEL_FEATURE_COLS` thì raise `BundleError("Mô hình được huấn luyện với bộ đặc trưng cũ, hãy chạy lại pipeline.")`.
- Fixture `fake_bundle_dir(tmp_path)`:
  - Ghi một gói nhỏ hợp lệ: RF 3 cây, độ sâu 2, chia trên `V14` và `Amount_scaled`.
  - Train 200 dòng, test 50 dòng có `Time` tăng dần, cả hai đều có ca `Class = 1`.
  - `rates.json` tính bằng `compute_rates`.
  - Fixture này dùng cho Task 3–5 và không cần Spark.

- [ ] **Step 1: Viết test thất bại**

`tests/test_runtime.py`:
- `test_rf_shap_additivity(fake_bundle_dir)`: với mọi dòng của test, `e.base_value + e.contributions.sum() == pytest.approx(rt.predict_proba(x[None])[0], abs=1e-6)`.
- `test_rf_known_tree`: một cây có gốc tách `V14 <= -1` → lá trái `values = 0.9`, lá phải `values = 0.1`. Với `V14 = -1` (đúng bằng ngưỡng) thì `predict_proba == 0.9` (đi trái khi bằng ngưỡng). Với `V14 = 0` thì `== 0.1`. Đóng góp SHAP của các đặc trưng khác `V14` đều bằng 0.
- `test_lr_additivity`: `base + sum == logit(p)` với `abs=1e-9`.
- `test_load_bundle_missing(tmp_path)`: `pytest.raises(BundleError, match="Chưa có mô hình")`.
- `test_load_bundle_old_features(fake_bundle_dir)`: sửa `model.json` cho `features[0] = "Time_scaled"` → `pytest.raises(BundleError, match="bộ đặc trưng cũ")`.

- [ ] **Step 2: Chạy để thấy thất bại**

Run: `.venv\Scripts\python -m pytest tests/test_runtime.py -v`
Expected: FAIL (ModuleNotFoundError `backend.runtime`)

- [ ] **Step 3: Cài đặt `runtime.py`, `bundle.py` và fixture**

Nếu `test_rf_known_tree` cho thấy `shap` xử lý trường hợp bằng ngưỡng khác Spark (Spark đi trái khi `<=`), dịch ngưỡng xuất sang `np.nextafter(threshold, +inf)` trong `RFRuntime` để hai bên khớp. Ghi chú lý do trong code.

- [ ] **Step 4: Chạy test**

Run: `.venv\Scripts\python -m pytest tests/test_runtime.py -v`
Expected: 5 passed

- [ ] **Step 5: Kiểm tra trên gói thật**

Run:
```powershell
.venv\Scripts\python -c "from backend.bundle import load_bundle; import numpy as np; b=load_bundle(); X=b.test[b.meta['features']].to_numpy()[:200]; p=b.runtime.predict_proba(X); print(b.meta['model_name'], p.min(), p.max())"
```
Expected: in tên mô hình, xác suất nằm trong [0, 1]. Đối chiếu thêm một lần: chạy lại Spark trên 200 dòng đầu của test (đoạn script nhỏ dùng `get_spark_session` + `RandomForestClassificationModel.load`) và kiểm tra `max |chênh lệch| < 1e-9`.

- [ ] **Step 6: Commit**

```bash
git add backend/ tests/
git commit -m "feat: runtime suy luận không cần Spark (RF + LR) với SHAP chính xác"
```

---

### Task 4: InferenceService – giải thích bằng lời, láng giềng, what-if, lô phát lại

**Files:**
- Create: `backend/inference.py`, `tests/test_inference_service.py`

**Interfaces:**
- Consumes: `bundle.Bundle`, `runtime.Explanation`
- Produces:
  - `InferenceService(bundle: Bundle)`. Dựng `sklearn.neighbors.NearestNeighbors(n_neighbors=5)` trên `train[features]` một lần. Chấm điểm toàn bộ test một lần, lưu vào `self.test_scores`.
  - `.sample(kind: Literal["random", "fraud", "normal"], rng: np.random.Generator | None = None) -> int` (tx_id của test)
  - `.explain_tx(tx_id: int) -> dict` (định dạng `TransactionExplanation` bên dưới). `tx_id` không có trong test thì raise `KeyError`.
  - `.what_if(tx_id: int, amount: float, hour: int) -> dict`:
    - Thay `Amount_scaled = (amount - amount_mean) / amount_std`.
    - Thay `Hour_sin` / `Hour_cos` từ `hour + phần lẻ giờ gốc`.
    - Trả về `TransactionExplanation` với `amount`/`hour` mới và `"what_if": true`.
  - `.stream_batch(start_time: float, end_time: float) -> list[dict]`: các giao dịch test có `start_time <= Time < end_time`, theo định dạng `StreamTx`.
  - `.test_time_range() -> tuple[float, float]`
- `TransactionExplanation`:
  ```
  {"tx_id": int, "time_s": float, "day": int, "hour": int, "minute": int, "amount": float,
   "probability": float, "risk": int, "threshold": float, "alert": bool, "true_label": int, "what_if": bool,
   "explain_space": "probability" | "log-odds", "base_value": float,
   "reasons": [{"key": "behavior" | "hour" | "amount", "contribution": float, "direction": "fraud" | "safe",
                "title": str, "detail": str}],        # sắp xếp theo |contribution| giảm dần, luôn đủ 3 nhóm
   "technical": [{"feature": str, "value": float, "contribution": float}],   # đủ 31, sắp xếp |contribution| giảm dần
   "neighbors": [{"tx_id": int, "amount": float, "hour": int, "minute": int, "label": int}],   # 5, gần nhất trước
   "neighbors_fraud": int}
  ```
- `StreamTx`: `{"tx_id", "time_s", "day", "hour", "minute", "amount", "risk", "alert", "true_label"}`
- Quy ước tính toán:
  - `day = int(Time // 86400) + 1`, `hour = int(Time % 86400 // 3600)`, `minute = int(Time % 3600 // 60)`.
  - Nhóm lý do: `behavior` là tổng đóng góp V1…V28, `hour` là `Hour_sin + Hour_cos`, `amount` là `Amount_scaled`. `direction = "fraud"` nếu đóng góp > 0, ngược lại `"safe"`.
  - Câu chữ của lý do (copy cố định, thay số thật):

    | key | direction | title | detail |
    |---|---|---|---|
    | behavior | fraud | `Hành vi thẻ rất khác thường so với giao dịch bình thường` | `Tổng hợp từ 28 dấu hiệu đã được ngân hàng mã hóa để bảo mật` |
    | behavior | safe | `Hành vi thẻ giống các giao dịch bình thường` | (như trên) |
    | hour | fraud | `Giao dịch lúc {H} giờ {sáng/chiều/tối}` | `Khung giờ này có tỉ lệ gian lận {r} — gấp {k} lần mức chung` |
    | hour | safe | `Giao dịch lúc {H} giờ {…}` | `Khung giờ này có tỉ lệ gian lận {r}, thấp hơn hoặc gần mức chung` |
    | amount | fraud / safe | `Số tiền {amount} €` | `Khoảng {label} có tỉ lệ gian lận {r}` (+ `— gấp {k} lần mức chung` khi `k >= 1,5`) |

    - `{r}` là phần trăm hai chữ số thập phân kiểu `vi-VN` ("1,71%").
    - `{k} = rate / overall_rate`, làm tròn đến 1 chữ số thập phân.
    - Buổi: 0–10h là "sáng", 11–17h là "chiều", 18–23h là "tối".

- [ ] **Step 1: Viết test thất bại** (dùng `fake_bundle_dir`)

- `test_explain_reasons_sum`: `e["base_value"] + sum(r["contribution"] for r in e["reasons"]) == pytest.approx(score)`, trong đó `score` là xác suất khi `explain_space == "probability"`, hoặc logit nếu `"log-odds"`. Thêm `len(e["reasons"]) == 3`, `len(e["technical"]) == 31` và `e["risk"] == round(e["probability"] * 100)`.
- `test_reason_direction_and_copy`: lý do có `contribution < 0` phải có `direction == "safe"` và tiêu đề không chứa "khác thường".
- `test_sample_kinds`: `sample("fraud")` trả về tx có `Class == 1`, và `sample("normal")` trả về tx có `Class == 0`.
- `test_neighbors`: 5 phần tử, `neighbors_fraud == sum(n["label"] for n in neighbors)`, và mọi `tx_id` đều thuộc train.
- `test_what_if_edges`: `what_if(tx, 0, 0)`, `what_if(tx, 25691.16, 23)` đều trả `0 <= risk <= 100` và `what_if is True`. Đổi `hour` từ 14 sang 2 thì `Hour_sin` trong `technical` thay đổi.
- `test_stream_batch`: `stream_batch(t0, t0 + 1e9)` trả về đủ số dòng test, sắp theo `time_s` tăng dần. `stream_batch(t, t)` trả `[]`.
- `test_time_parts`: `Time = 97200 + 125` → `day == 2`, `hour == 3`, `minute == 2`.

- [ ] **Step 2: Chạy để thấy thất bại**

Run: `.venv\Scripts\python -m pytest tests/test_inference_service.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Cài đặt `backend/inference.py`**

- [ ] **Step 4: Chạy test**

Run: `.venv\Scripts\python -m pytest tests/test_inference_service.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/inference.py tests/test_inference_service.py
git commit -m "feat: dịch vụ suy luận – lý do bằng lời, giao dịch tương tự, what-if, phát lại"
```

---

### Task 5: FastAPI app – REST + WebSocket phát lại

**Files:**
- Create: `backend/app.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: `InferenceService`, `load_bundle`, `BundleError`, `hdfs_utils.liststatus`, `config.DATA_BACKEND`, `config.SPARK_CORES`
- Produces (frontend ở Task 6–7 dựa vào đây):
  - `create_app(bundle_dir: Path = INFERENCE_DIR) -> FastAPI`, và `app = create_app()` ở cấp module.
    - CORS cho `http://localhost:3000`.
    - Nạp gói lúc khởi động. Nếu lỗi thì giữ `BundleError` để trả 503.
  - `GET /api/status` → `{"backend": "ok", "data_backend": str, "spark_cores": int, "hdfs": {"ok": bool}, "model": {"name": str, "threshold": float, "pr_auc": float, "selection_note": str} | null, "model_error": str | null}`. Kiểm tra HDFS bằng `liststatus("/")` với timeout ngắn, và chỉ kiểm tra khi `DATA_BACKEND == "hdfs"`, ngược lại `ok: false`.
  - `POST /api/reload` → nạp lại gói (dùng sau khi chạy lại pipeline), trả về như `/api/status`.
  - `GET /api/infer/sample?kind=random|fraud|normal` → `TransactionExplanation`
  - `GET /api/infer/tx/{tx_id}` → `TransactionExplanation`, hoặc 404 `{"detail": "Không tìm thấy giao dịch"}`
  - `POST /api/infer/what-if` body `{"tx_id": int, "amount": float (>= 0), "hour": int (0..23)}` → `TransactionExplanation`. Sai kiểu hoặc ngoài khoảng thì trả 422 (pydantic `Field(ge=..., le=...)`).
  - Mọi `/api/infer/*` khi chưa có gói thì trả 503 `{"detail": "<thông báo BundleError>"}`.
  - `WS /api/infer/stream`:
    - Server tiến đồng hồ mô phỏng mỗi **100 ms** một đoạn `0,1 × speed` giây. Mỗi tick gửi `{"type": "batch", "txs": [StreamTx], "stats": {"checked", "caught", "false_alarms", "missed", "blocked_amount"}, "clock": float, "speed": int, "paused": bool}`. Batch rỗng vẫn gửi để cập nhật đồng hồ.
    - Client gửi `{"cmd": "pause"}`, `{"cmd": "resume"}`, `{"cmd": "speed", "value": 10 | 100 | 1000}` hoặc `{"cmd": "restart"}`.
    - Mặc định `speed = 100`, không tạm dừng. Hết tập test thì gửi `{"type": "end", "stats": ...}`.
    - Ý nghĩa bộ đếm: `caught` = alert ∧ label 1; `false_alarms` = alert ∧ label 0; `missed` = ¬alert ∧ label 1; `blocked_amount` = tổng `amount` của `caught`.
    - Mỗi kết nối có trạng thái riêng. Khi ngắt kết nối thì hủy vòng lặp, bắt `WebSocketDisconnect` và không log lỗi.
- Lệnh chạy: `.venv\Scripts\python -m uvicorn backend.app:app --port 8000`

- [ ] **Step 1: Viết test thất bại** (`fastapi.testclient.TestClient`, dùng `create_app(fake_bundle_dir)`)

- `test_status_with_model`: `r.json()["model"]["name"]` có giá trị, và `model_error is None`.
- `test_no_bundle_503(tmp_path)`: `create_app(tmp_path)` → `GET /api/infer/sample` trả 503 và `"Chưa có mô hình" in detail`. Đồng thời `GET /api/status` trả 200 với `model is None`.
- `test_sample_and_tx`: `sample?kind=fraud` → `true_label == 1`. `GET /api/infer/tx/{id}` trả cùng `tx_id`. `GET /api/infer/tx/999999` trả 404.
- `test_what_if_validation`: `amount=-1` → 422, `hour=24` → 422, `amount=0, hour=0` → 200.
- `test_stream`:
  - Mở WS, gửi `{"cmd": "speed", "value": 1000}`, nhận tối đa 200 tin cho đến khi gặp `type == "end"`.
  - Tổng `len(txs)` == số dòng test.
  - `stats["caught"] + stats["missed"] == số ca Class 1 trong test`.
- `test_stream_reconnect`: mở WS, nhận 1 tin, đóng, mở lại. Tin đầu của kết nối mới có `stats["checked"] <= số tx trong tin đó` (bắt đầu lại từ đầu).

- [ ] **Step 2: Chạy để thấy thất bại**

Run: `.venv\Scripts\python -m pytest tests/test_api.py -v`
Expected: FAIL

- [ ] **Step 3: Cài đặt `backend/app.py`**

- [ ] **Step 4: Chạy toàn bộ test**

Run: `.venv\Scripts\python -m pytest -v`
Expected: tất cả pass (khoảng 25 test)

- [ ] **Step 5: Thử với gói thật**

Run: `.venv\Scripts\python -m uvicorn backend.app:app --port 8000`, rồi `curl http://localhost:8000/api/infer/sample?kind=fraud`
Expected: JSON có `reasons` đủ 3 nhóm, câu chữ tiếng Việt và `risk` trong 0–100.

- [ ] **Step 6: Commit**

```bash
git add backend/app.py tests/test_api.py
git commit -m "feat: FastAPI – API suy luận và WebSocket giám sát trực tiếp"
```

---

### Task 6: Khung frontend Next.js (thanh tiêu đề, 3 tab, trạng thái)

**Files:**
- Create: `frontend/` (scaffold), `frontend/lib/api.ts`, `frontend/lib/format.ts`, `frontend/components/Header.tsx`, `frontend/app/layout.tsx`, `frontend/app/page.tsx`, `frontend/app/etl/page.tsx`, `frontend/app/train/page.tsx`, `frontend/app/infer/page.tsx` (tạm thời), `frontend/lib/format.test.ts`

**Interfaces:**
- Consumes: các endpoint của Task 5
- Produces:
  - `lib/api.ts`:
    - Các type TypeScript `Status`, `TransactionExplanation`, `Reason`, `Neighbor`, `StreamTx`, `StreamStats`, `StreamMessage`, khớp đúng khóa của Task 4–5.
    - `API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`.
    - Các hàm `getStatus()`, `getSample(kind)`, `getTx(id)`, `postWhatIf(body)`, `reloadModel()`, và `openStream(): WebSocket` (đổi `http` thành `ws`).
    - Lỗi 503 được ném thành `ApiError` có `status` và `detail`.
  - `lib/format.ts`:
    - `fmtMoney(x) -> "529,00 €"`
    - `fmtInt(x) -> "12.480"`
    - `fmtPct(rate) -> "1,71%"` (đầu vào là tỉ lệ 0–1)
    - `fmtClock(day, hour, minute) -> "ngày 2, 03:12"`
    - `partOfDay(hour) -> "sáng" | "chiều" | "tối"` (cùng mốc với backend)
  - `Header`: tên "🛡️ Fraud Detection", các tab `① ETL` `/etl`, `② Huấn luyện & Đánh giá` `/train`, `③ Suy luận` `/infer`, tab đang mở được tô sáng. Bên phải là chấm trạng thái backend, chế độ dữ liệu, số luồng Spark, mô hình đang dùng và ngưỡng (gọi `getStatus` mỗi 10 giây).
  - `/` chuyển hướng sang `/infer`. `/etl` và `/train` là trang giữ chỗ có dòng "Đang xây dựng".
  - Giao diện tối: màu nền, panel và các màu nhấn lấy đúng biến CSS của phác thảo (`--bg:#0b1020; --panel:#121a2e; --panel2:#18223a; --line:#25314d; --text:#e6ebf5; --muted:#8b98b5; --blue:#38bdf8; --green:#22c55e; --red:#ef4444; --amber:#f59e0b`).

- [ ] **Step 1: Scaffold**

Run (tại gốc repo):
```powershell
pnpm create next-app@latest frontend --ts --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-pnpm
cd frontend; pnpm add motion; pnpm add -D vitest
```
Thêm script `"test": "vitest run"` vào `frontend/package.json`.

- [ ] **Step 2: Viết test thất bại** `frontend/lib/format.test.ts`

```ts
expect(fmtMoney(529)).toBe("529,00 €"); expect(fmtInt(12480)).toBe("12.480"); expect(fmtPct(0.0171)).toBe("1,71%");
expect(fmtClock(2, 3, 2)).toBe("ngày 2, 03:02"); expect(partOfDay(3)).toBe("sáng"); expect(partOfDay(23)).toBe("tối");
```
Lưu ý: `Intl` có thể chèn khoảng trắng không ngắt (NBSP) trước "€". Test phải so khớp đúng chuỗi mà `fmtMoney` trả về, vì vậy `fmtMoney` cần chuẩn hóa thành một khoảng trắng thường.

- [ ] **Step 3: Chạy để thấy thất bại**

Run: `cd frontend; pnpm test`
Expected: FAIL (module chưa có)

- [ ] **Step 4: Cài đặt `lib/format.ts`, `lib/api.ts`, `Header`, layout và các trang**

Font: Be Vietnam Pro qua `next/font/google`, để hiển thị đúng dấu tiếng Việt.

- [ ] **Step 5: Kiểm tra**

Run: `cd frontend; pnpm test; pnpm lint; pnpm build`
Expected: test pass, lint không lỗi, build thành công.

Chạy `pnpm dev` cùng backend, mở `http://localhost:3000`. Kết quả mong đợi:
- Trang chuyển sang `/infer`.
- Header hiện tên mô hình, và chấm backend màu xanh.
- Tắt backend thì chấm chuyển đỏ.

- [ ] **Step 6: Commit**

```bash
git add frontend/ .gitignore
git commit -m "feat: khung frontend Next.js với thanh tiêu đề và 3 tab"
```

---

### Task 7: Trang Suy luận (giám sát trực tiếp + giải thích)

**Files:**
- Create: `frontend/components/infer/LiveFeed.tsx`, `StreamControls.tsx`, `Counters.tsx`, `ExplanationPanel.tsx`, `RiskGauge.tsx`, `ReasonList.tsx`, `NeighborsTable.tsx`, `WhatIf.tsx`, `CheckOne.tsx`, `frontend/hooks/useStream.ts`
- Modify: `frontend/app/infer/page.tsx`

**Interfaces:**
- Consumes: `lib/api.ts`, `lib/format.ts` (Task 6)
- Produces:
  - `useStream() -> { txs: StreamTx[] (tối đa 40, mới nhất trước), stats: StreamStats, clock: number, speed: number, paused: boolean, ended: boolean, pause(), resume(), setSpeed(v), restart() }`. Hook tự kết nối lại sau 2 giây nếu WS bị đóng ngoài ý muốn.
  - Trang `/infer` theo `inference-v2.html`:
    - Hai chế độ **📡 Giám sát trực tiếp** (mặc định) và **🔍 Kiểm tra 1 giao dịch**.
    - Cột trái (rộng khoảng 400px): `Counters` (đã kiểm tra / bắt đúng / báo nhầm / bỏ sót, cộng "Đã chặn kịp {fmtMoney}"), `StreamControls` (tạm dừng/tiếp tục, ×10 / ×100 / ×1000, chơi lại từ đầu) và `LiveFeed`. Mỗi dòng hiện giờ, thanh rủi ro, số tiền và "✓ duyệt" hoặc "⚠ chặn". Dòng chặn tô đỏ, bấm được, và dòng mới trượt vào bằng `motion`.
    - Ở chế độ Kiểm tra 1 giao dịch, cột trái là `CheckOne` gồm 3 nút "🎲 Ngẫu nhiên", "Lấy 1 ca gian lận", "Lấy 1 ca bình thường".
    - Cột phải là `ExplanationPanel` cho giao dịch đang chọn:
      - Tiêu đề "Giao dịch #{fmtInt(tx_id)}" kèm "{fmtMoney} · {fmtClock}".
      - `RiskGauge`: nhãn "⚠ NGHI GIAN LẬN" hoặc "✓ AN TOÀN", "Mức rủi ro: {risk} / 100 · cảnh báo từ mức {round(threshold*100)}", và vạch ngưỡng.
      - Đề xuất hành động, copy cố định. Khi alert: "💡 Đề xuất: tạm giữ giao dịch, gửi mã xác minh hoặc gọi chủ thẻ trước khi duyệt." Khi không: "💡 Đề xuất: duyệt giao dịch."
      - Nút "👁 Xem kết quả thật": hiện "Thực tế: Gian lận/Bình thường · mô hình đoán Đúng/Sai". Trạng thái này đặt lại khi đổi giao dịch.
      - `ReasonList` với tiêu đề "Vì sao hệ thống nghi ngờ?" khi alert, hoặc "Vì sao hệ thống cho là an toàn?" khi không. Mỗi lý do có biểu tượng 🧬/🌙/💶, `title`, `detail` và thanh dài tỉ lệ `|contribution| / max|contribution|`, màu đỏ nếu `fraud`, xanh nếu `safe`. Chú thích: "Thanh càng dài = yếu tố đó góp càng nhiều vào kết luận".
      - Ô `<details>` "🔧 Chi tiết kỹ thuật" liệt kê `technical`, kèm dòng "Đóng góp tính bằng SHAP từ chính mô hình ({explain_space})".
      - `NeighborsTable`: "Những vụ giống nhất trong quá khứ", với các cột Số tiền / Lúc / Kết quả thật, và dòng "{neighbors_fraud} / 5 vụ giống nhất từng là gian lận".
      - `WhatIf`: thanh trượt số tiền (0–2.000 €, bước 1, có ô nhập cho số lớn hơn) và giờ (0–23). Debounce 150 ms rồi gọi `postWhatIf`, hiện "Mức rủi ro mới: {risk} / 100 → {vẫn nghi gian lận | chuyển thành an toàn | vẫn an toàn | chuyển thành nghi gian lận}" và cập nhật `ReasonList`. Ghi chú: "Mô hình chấm lại ngay khi kéo, các dấu hiệu mã hóa giữ nguyên".
    - Chú thích nhỏ ở chân trang: "Giờ được tính từ cột Time, giả định giao dịch đầu tiên lúc 0h."
    - Khi chưa chọn giao dịch: chế độ giám sát tự chọn dòng chặn đầu tiên xuất hiện; chế độ kiểm tra tự gọi `getSample("random")`.
    - Khi API trả 503: hiện trạng thái trống "Chưa có mô hình" kèm `detail` và nút "Sang tab Huấn luyện" (`/train`), không render các khối khác.

- [ ] **Step 1: Cài đặt các component và hook**

- [ ] **Step 2: Kiểm tra build**

Run: `cd frontend; pnpm lint; pnpm build`
Expected: không lỗi

- [ ] **Step 3: Kiểm tra trên trình duyệt** (backend + `pnpm dev` đang chạy)

Mở `http://localhost:3000/infer`. Kết quả mong đợi:
- Luồng giao dịch chạy, bộ đếm tăng.
- Bấm một dòng đỏ thì panel phải đổi đúng `tx_id`.
- Bấm "Xem kết quả thật" thì nhãn hiện ra.
- Kéo giờ từ 3 sang 14 thì mức rủi ro thay đổi.
- Đổi tốc độ ×1000 thì luồng nhanh hẳn. Tạm dừng thì luồng đứng.
- Đổi tên thư mục `models/inference` thành tên khác, gọi `POST /api/reload` và tải lại trang: thấy trạng thái trống "Chưa có mô hình". Đổi tên lại như cũ khi xong.

Chụp màn hình bằng công cụ trình duyệt và tự kiểm tra:
- Không có chữ "V14", "SHAP" hay "stage" ngoài ô "🔧".
- Chữ tiếng Việt hiển thị đúng dấu.

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: trang Suy luận – giám sát trực tiếp, giải thích bằng lời, thử thay đổi"
```

---

### Task 8: Script khởi động và tài liệu

**Files:**
- Create: `start_ui.ps1`
- Modify: `README.md` (thêm mục "Giao diện web mới"), `CLAUDE.md` (lệnh chạy và kiến trúc backend/frontend, đặc trưng giờ, test)

**Interfaces:**
- `start_ui.ps1`:
  - Mở 2 cửa sổ PowerShell: một chạy `.venv\Scripts\python -m uvicorn backend.app:app --port 8000`, một chạy `pnpm --dir frontend dev`.
  - Rồi mở `http://localhost:3000`.
  - Nếu chưa có `frontend/node_modules` thì chạy `pnpm --dir frontend install` trước.

- [ ] **Step 1: Viết `start_ui.ps1` và cập nhật tài liệu**

- README: cách chạy (`.\start_ui.ps1`), thứ tự cần làm (chạy pipeline trước, rồi `POST /api/reload` hoặc khởi động lại backend), giải thích đặc trưng giờ và giả định 0h. Cũng sửa đoạn "Kết quả sau khi tinh chỉnh" nếu số liệu đã đổi.
- CLAUDE.md: thêm lệnh `pytest`, lệnh chạy backend/frontend, và mô tả gói suy luận `models/inference/`.

- [ ] **Step 2: Kiểm tra từ đầu**

Run: `.\start_ui.ps1`
Expected: trong khoảng 20 giây trình duyệt mở `/infer`, luồng giao dịch chạy.

Run: `.venv\Scripts\python -m pytest -v`
Expected: tất cả pass.

Run: `python run_pipeline.py`
Expected: vẫn chạy như cũ (CLI không đổi hành vi).

- [ ] **Step 3: Commit**

```bash
git add start_ui.ps1 README.md CLAUDE.md
git commit -m "docs: hướng dẫn chạy giao diện web mới"
```
