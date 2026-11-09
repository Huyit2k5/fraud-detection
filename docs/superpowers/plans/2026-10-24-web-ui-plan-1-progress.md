# SDD ledger — plan: docs/superpowers/plans/2026-10-24-web-ui-plan-1-inference.md
Spec: docs/superpowers/specs/2026-10-24-web-ui-design.md
Branch: feature/web-ui (created from main @ 8867d41; user approved "làm giao diện web đi")

Pre-flight:
- T1→T2: MODEL_FEATURE_COLS / INFERENCE_DIR / SCALER_PARAMS_PATH produced by T1, consumed by T2 — consistent.
- T2→T3: model.json / train.parquet / test.parquet / rates.json format; compute_rates (T2) used by T3 fixture — consistent.
- T3→T4: Bundle.meta must carry amount_mean/amount_std (T2 writes them into model.json) — consistent.
- T4→T5, T5→T6/T7: TransactionExplanation / StreamTx / stats keys — consistent.

Task 1: Ruling: implementation of hour features was written BEFORE its tests (done during the report work, earlier in session); tests then passed on first run — no RED observed — cost if wrong: tests might not catch a regression; mitigated: test asserts exact numeric values (would fail on any formula change).
Task 1: Ruling: baseline (Step 0) run with old features via git stash; RF PR-AUC 0.7912 → 0.7895 after hour features (Δ −0.0017, within 0.05 bound).
Task 1: Ruling: added PYSPARK_PYTHON=sys.executable in get_spark_session (not in plan) — Spark workers hit the MS Store "python" alias on this machine — cost if wrong: none (setdefault respects user env).
Task 1: Ruling: tune_models.py strategy/threshold selection moved to time-based validation (not in plan) — old code picked SMOTE in-sample and applied a class_weight threshold to the SMOTE model (RF F1 0.77→0.38) — cost if wrong: different tuned params than README.
Task 1: complete (commits 8867d41..819b6c2, tests: .venv/Scripts/python.exe -m pytest tests/test_hour_features.py -q → 3 passed in 19.77s)
Task 2: complete (commits 819b6c2..82a6023, tests: .venv/Scripts/python.exe -m pytest tests/test_export_inference.py -q → 4 passed in 49.36s)
Task 2: Ruling: commits 236fb71/5f6c865 (report: Kaggle screenshots, heading outline levels) landed inside Task 2's range at user request mid-task — not part of the plan — cost if wrong: none (report-only files).
Task 3: complete (commits 82a6023..c18e0e1, tests: .venv/Scripts/python.exe -m pytest tests/test_runtime.py -q → 5 passed, 3 warnings in 5.21s)
Task 3: Ruling: no threshold shift needed — verified shap goes left on x <= threshold like Spark (test_rf_known_tree); parity on real bundle: max |numpy-spark| = 1.4e-17 over 200 test rows — cost if wrong: none.

## Bàn giao sang cloud session (2026-10-24)
- Xong Task 1–3 (xem các dòng "Task N: complete" ở trên). Làm tiếp từ **Task 4** của
  docs/superpowers/plans/2026-10-24-web-ui-plan-1-inference.md.
- Test Task 4–5 dùng gói giả (tests/fake_bundle.py), KHÔNG cần dữ liệu thật hay Spark:
  `pip install -r requirements.txt && python -m pytest tests/test_runtime.py -q`.
- Dữ liệu thật (data/raw/creditcard.csv, 151 MB) và models/ bị gitignore. Muốn chạy với dữ liệu
  thật trên cloud: tải creditcard.csv từ https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud vào
  data/raw/, cần Java 17, rồi `python run_pipeline.py && python src/tune_models.py && python src/evaluate.py`
  (evaluate.py xuất gói suy luận models/inference/).
- Cập nhật mục lục báo cáo Word (reports/update_fields.ps1) chỉ chạy trên Windows có Word.
