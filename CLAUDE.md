# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Credit-card fraud detection (Kaggle ULB `creditcard.csv`: `Time`, `V1`–`V28` PCA, `Amount`, `Class`) built as a Big Data course project: PySpark ETL + Spark MLlib / scikit-learn models, optional real HDFS via Docker, a Streamlit dashboard, and an auto-generated Word report. Code comments, docs, and console output are in Vietnamese — keep new text consistent with that. The phase plan the code follows ("Giai đoạn 1–7") is in [ke-hoach-phat-hien-giao-dich-bat-thuong.md](ke-hoach-phat-hien-giao-dich-bat-thuong.md).

There is no test suite or linter configured.

## Commands

Run everything from the repo root (Windows; venv in `.venv`):

```bash
pip install -r requirements.txt
python src/generate_synthetic_data.py   # writes data/raw/creditcard.csv if the real dataset is absent
python run_pipeline.py                  # ETL → imbalance → train → evaluate → visualize
python src/<step>.py                    # run one stage alone (spark_etl, imbalance, train_models, evaluate, visualize)
python src/tune_models.py               # optional: grid search + CV, weighted vs SMOTE, threshold tuning
python reports/generate_report.py       # rebuild reports/final_report.docx from latest metrics/figures
streamlit run dashboard/app.py

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
- **Three models:** Logistic Regression and Random Forest (Spark MLlib, saved as Spark model dirs) and Isolation Forest (sklearn, trained on a pandas sample pulled from Spark, saved as `isolation_forest.joblib`; unsupervised, labels used only for evaluation).
- **Tuning → evaluation coupling:** `tune_models.py` overwrites `models/logistic_regression` and `models/random_forest` and writes `models/thresholds.json`. `evaluate.py` uses those thresholds if the file exists (else 0.5). After tuning, rerun `evaluate.py` and `visualize.py`, then `generate_report.py`.
- **Outputs:** `reports/metrics_comparison.csv` and `reports/figures/*.png` feed both the dashboard and `generate_report.py`. Data, models, figures, and the CSV are gitignored.
- **HDFS access outside Spark** goes through `src/hdfs_utils.py` (a thin WebHDFS REST wrapper using `requests`, writes as `user.name=root`). `run_pipeline.py` uses it to check the raw file exists on HDFS before starting Spark.
- Notebooks in `notebooks/` call `src/` functions rather than reimplementing logic; each sets `JAVA_HOME`/`HADOOP_HOME` in its first cell.

## Evaluation conventions

Data is extremely imbalanced (~0.17% fraud): prioritize Precision/Recall/F1/PR-AUC over Accuracy/ROC-AUC. Isolation Forest's much lower precision (~5%) is expected for an unsupervised method, not a bug.
