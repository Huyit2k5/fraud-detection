# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Credit-card fraud detection (Kaggle ULB `creditcard.csv`: `Time`, `V1`–`V28` PCA, `Amount`, `Class`) built as a Big Data course project: PySpark ETL + Spark MLlib / scikit-learn models, optional real HDFS via Docker, a Streamlit dashboard, and an auto-generated Word report. Code comments, docs, and console output are in Vietnamese — keep new text consistent with that. The phase plan the code follows ("Giai đoạn 1–7") is in [ke-hoach-phat-hien-giao-dich-bat-thuong.md](ke-hoach-phat-hien-giao-dich-bat-thuong.md).

Tests: `pytest` for the pipeline/backend (`tests/`, uses a hand-built fake inference bundle, Spark tests need JDK 17) and `vitest` for the frontend.

## Commands

Run everything from the repo root (Windows; venv in `.venv`):

```bash
pip install -r requirements.txt
python src/generate_synthetic_data.py   # writes data/raw/creditcard.csv if the real dataset is absent
python run_pipeline.py                  # ETL → imbalance → train → evaluate → visualize
python src/<step>.py                    # run one stage alone (spark_etl, imbalance, train_models, evaluate, visualize)
python src/tune_models.py               # optional: grid search + CV, weighted vs SMOTE, threshold tuning
python reports/make_figures.py          # matplotlib figures + Spark stats for the report (needs models)
python reports/generate_report.py       # rebuild reports/final_report.docx (Word COM updates TOC on Windows)
python -m pytest -q                     # all Python tests; single test: python -m pytest tests/test_api.py::test_stream -q
powershell -File start_ui.ps1           # web UI: uvicorn backend.app:app --port 8000 + pnpm dev in frontend/
pnpm --dir frontend test | lint | build

# Optional real HDFS pseudo-cluster
docker compose -f docker-compose.hdfs.yml up -d
python scripts/hdfs_bootstrap.py        # upload raw CSV via WebHDFS
DATA_BACKEND=hdfs python run_pipeline.py
```

## Environment gotchas (Windows)

- PySpark needs **JDK 17**. Set `JAVA_HOME` to JDK 17 and `HADOOP_HOME` to `<repo>/hadoop` (contains `winutils.exe`/`hadoop.dll`, needed for local Parquet writes), and prepend both `bin` dirs to `PATH`. A machine-level `JAVA_HOME` pointing at another JDK causes `UnsupportedClassVersionError`. `dashboard/app.py` (`spark_subprocess_env`) auto-detects JDK 17 for its subprocesses; direct CLI runs do not.
- Pin **pandas < 3.0** (2.3.3 tested); pandas 3.x crashes PySpark Python workers. Arrow is deliberately disabled in `get_spark_session` for the same stability reason — don't re-enable it.
- HDFS mode on Windows requires hosts entries `127.0.0.1 namenode` and `127.0.0.1 datanode`.

## Architecture

- **Flat imports from `src/`.** Modules import each other as top-level (`from config import ...`, `from spark_etl import get_spark_session`). Entry points outside `src/` (`run_pipeline.py`, `dashboard/app.py`, `reports/generate_report.py`, notebooks) insert `src/` into `sys.path` first.
- **`src/config.py` is the single source of paths/constants** and creates the data/report/model dirs on import. `data_path(name)` resolves to local `data/<name>` or `hdfs://.../data/<name>` based on `DATA_BACKEND` (`local` default | `hdfs`). Always read raw data via `RAW_CSV_DATA_PATH` (backend-aware); `RAW_CSV_PATH` is local-only and used only for filesystem existence checks.
- **Models are always saved locally in `models/`**, even in HDFS mode. Spark MLlib saves/loads must go through `local_uri(path)` (explicit `file://`), otherwise Spark treats Windows paths as HDFS paths when `fs.defaultFS` points to HDFS.
- **All Spark work uses `spark_etl.get_spark_session()`** (local[*], HDFS config applied when needed). Each stage's `run_*()` creates a session and stops it in `finally`.
- **Data flow** (Parquet between stages): raw CSV → `cleaned` → time-based split (`TRAIN_RATIO=0.7` on `Time`, not random) → `train`/`test` → `imbalance.py` adds `class_weight` column (`train_weighted`, used for MLlib `weightCol`) and a SMOTE-oversampled variant (`train_balanced`, used only by tuning).
- **Two feature lists:** `FEATURE_COLS` (raw `Time`/`Amount`, for EDA/plots) vs `MODEL_FEATURE_COLS` (`Time_scaled`/`Amount_scaled` + V1–V28, for training). Use the latter for any model.
- **Features:** `MODEL_FEATURE_COLS = [Amount_scaled, V1..V28]` (29). `Time`/`Time_scaled` is deliberately NOT a model feature (time-based split puts all test `Time` values outside the train range). An hour-of-day feature was tried and removed (no gain for RF/LR, hurt Isolation Forest) — don't re-add it.
- **Three models:** Logistic Regression and Random Forest (Spark MLlib, saved as Spark model dirs) and Isolation Forest (sklearn, trained on a pandas sample pulled from Spark, saved as `isolation_forest.joblib`; unsupervised, labels used only for evaluation).
- **Tuning:** class-weight vs SMOTE and the decision threshold are chosen on a time-based validation split (last 15% of train) using the model of the chosen strategy — never mix a threshold from one strategy with a model of the other.
- **Tuning → evaluation coupling:** `tune_models.py` overwrites `models/logistic_regression` and `models/random_forest` and writes `models/thresholds.json`. `evaluate.py` uses those thresholds if the file exists (else 0.5). After tuning, rerun `evaluate.py` and `visualize.py`, then `generate_report.py`.
- **Outputs:** `reports/metrics_comparison.csv` and `reports/figures/*.png` feed both the dashboard and `generate_report.py`. Data, models, figures, and the CSV are gitignored.
- **HDFS access outside Spark** goes through `src/hdfs_utils.py` (a thin WebHDFS REST wrapper using `requests`, writes as `user.name=root`). `run_pipeline.py` uses it to check the raw file exists on HDFS before starting Spark.
- **Inference bundle / web backend:** `evaluate.py` calls `export_inference.export_inference_bundle`, writing `models/inference/` (best exportable model by PR-AUC as JSON trees/coefficients, train/test parquet, fraud rates). `backend/` (FastAPI) loads it once and scores/explains with numpy + `shap` — it must never start Spark. Exported RF probabilities match Spark to ~1e-17; keep `tests/test_export_inference.py` parity tests green when touching export. WS `/api/infer/stream` replays the test set (commands pause/resume/speed/step/restart).
- **Frontend:** Next.js 16 (cacheComponents on; read `frontend/node_modules/next/dist/docs/` before using Next APIs, see `frontend/AGENTS.md`). Colors are CSS variables with light/dark sets in `app/globals.css` — use the semantic Tailwind tokens (`bg-panel`, `text-risk-ink`, …), not raw palette colors. UI copy is Vietnamese; V1–V28/SHAP terms only inside "🔧 Chi tiết kỹ thuật".
- **Report:** `reports/build_template.py` turns the faculty's sample .docx into `reports/template/report_template.docx` (format only); `generate_report.py` fills it from `reports/report_stats.json` + CSV/JSON results. All figures must be matplotlib from real data (no generated images); screenshots live in `reports/assets/`.
- Notebooks in `notebooks/` call `src/` functions rather than reimplementing logic; each sets `JAVA_HOME`/`HADOOP_HOME` in its first cell.

## Evaluation conventions

Data is extremely imbalanced (~0.17% fraud): prioritize Precision/Recall/F1/PR-AUC over Accuracy/ROC-AUC. Isolation Forest's much lower precision (~5%) is expected for an unsupervised method, not a bug.
