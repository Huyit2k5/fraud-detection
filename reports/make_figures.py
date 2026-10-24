"""
Sinh toàn bộ hình (matplotlib) và số liệu thống kê cho báo cáo Word, từ DỮ LIỆU THẬT và MÔ HÌNH
THẬT của pipeline (không dùng ảnh minh họa có sẵn).

- Số liệu khám phá dữ liệu được Spark tổng hợp trên toàn bộ dữ liệu (groupBy, approxQuantile,
  Correlation), chỉ kết quả tổng hợp nhỏ mới được đưa về pandas để vẽ.
- Các sơ đồ kiến trúc/nguyên lý cũng được vẽ bằng code (matplotlib).

Kết quả: reports/figures/report/*.png và reports/report_stats.json.
Chạy (sau run_pipeline.py + tune_models.py + evaluate.py): python reports/make_figures.py
"""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

import joblib  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from pyspark.ml.classification import (  # noqa: E402
    LogisticRegressionModel,
    RandomForestClassificationModel,
)
from pyspark.ml.feature import VectorAssembler  # noqa: E402
from pyspark.ml.functions import vector_to_array  # noqa: E402
from pyspark.ml.stat import Correlation  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    auc,
    precision_recall_curve,
    roc_curve,
)

from config import (  # noqa: E402
    AMOUNT_COL,
    CLEANED_PARQUET_PATH,
    FEATURE_COLS,
    HOUR_COL,
    LABEL_COL,
    MODEL_FEATURE_COLS,
    MODELS_DIR,
    REPORTS_DIR,
    SPARK_CORES,
    TEST_PARQUET_PATH,
    TIME_COL,
    TRAIN_BALANCED_PARQUET_PATH,
    TRAIN_PARQUET_PATH,
    TRAIN_WEIGHTED_PARQUET_PATH,
    local_uri,
)
from spark_etl import analyze_amount_outliers, get_spark_session, read_raw_data  # noqa: E402
from train_models import assemble_features  # noqa: E402

OUT_DIR = REPORTS_DIR / "figures" / "report"
STATS_PATH = REPORTS_DIR / "report_stats.json"

BLUE, RED, AMBER, GREEN, GRAY, PURPLE = "#2E6F9E", "#C8414B", "#E3A33B", "#3C9D5D", "#8A8F98", "#7B5EA7"
MODEL_COLORS = {"Logistic Regression": BLUE, "Random Forest": GREEN, "Isolation Forest": AMBER}

AMOUNT_EDGES = [0, 1, 10, 50, 100, 500, 1000, float("inf")]
AMOUNT_LABELS = ["<1", "1–10", "10–50", "50–100", "100–500", "500–1.000", ">1.000"]
HOUR_BLOCKS = ["0–4h", "4–8h", "8–12h", "12–16h", "16–20h", "20–24h"]

plt.rcParams.update({
    "font.family": ["Times New Roman", "DejaVu Serif"],
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def vn(x: float, digits: int = 0) -> str:
    """Định dạng số kiểu Việt Nam: 284.807 / 0,17."""
    s = f"{x:,.{digits}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def save(fig, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{name}.png")
    plt.close(fig)
    print(f"[Hình] {name}.png")


# --------------------------------------------------------------------------------------------
# Sơ đồ vẽ bằng code
# --------------------------------------------------------------------------------------------
def _box(ax, x, y, w, h, text, color, fontsize=10.5, text_color="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                facecolor=color, edgecolor="none"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            color=text_color, wrap=True)


def _arrow(ax, p0, p1, color="#555"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=14, color=color, lw=1.6))


def _canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def diagram_architecture():
    fig, ax = _canvas(12, 5.2)
    w, h = 2.45, 1.25
    top = [
        ("Nguồn dữ liệu\ncreditcard.csv\n(Kaggle – ULB)", GRAY),
        ("Lưu trữ phân tán\nHDFS\n(NameNode + DataNode)", "#B5651D"),
        ("Spark ETL (DataFrame)\nEDA · làm sạch · tạo\nđặc trưng · chuẩn hóa", BLUE),
        ("Parquet\ncleaned / train / test", "#4F6D7A"),
    ]
    bottom = [
        ("Ứng dụng web\nFastAPI + Next.js\n(giám sát, giải thích)", PURPLE),
        ("Đánh giá & trực quan\nPrecision · Recall · F1\nPR-AUC · biểu đồ", "#A23B72"),
        ("Tinh chỉnh\nGrid Search + CV\ntối ưu ngưỡng", AMBER),
        ("Mất cân bằng + Huấn luyện\nclass weight · SMOTE\nLR · RF (MLlib) · IF", GREEN),
    ]
    xs = [0.3 + i * 2.95 for i in range(4)]
    for (t, c), x in zip(top, xs):
        _box(ax, x, 3.4, w, h, t, c)
    for (t, c), x in zip(bottom, xs):
        _box(ax, x, 0.6, w, h, t, c)
    for i in range(3):
        _arrow(ax, (xs[i] + w, 4.02), (xs[i + 1], 4.02))
        _arrow(ax, (xs[i + 1], 1.22), (xs[i] + w, 1.22))
    _arrow(ax, (xs[3] + w / 2, 3.4), (xs[3] + w / 2, 1.85))
    ax.text(6, 2.65, "Luồng dữ liệu xử lý theo lô (batch) – Spark chạy song song trên "
            f"{SPARK_CORES} luồng", ha="center", fontsize=10, style="italic", color="#333")
    save(fig, "kien_truc_he_thong")


def diagram_hdfs(file_mb: float, n_blocks: int):
    fig, ax = _canvas(11, 5)
    _box(ax, 0.3, 3.4, 2.4, 1.1, "Client\n(Spark driver)", GRAY)
    _box(ax, 4.2, 3.4, 2.8, 1.1, "NameNode\nquản lý metadata:\ntên file → block → vị trí", "#B5651D")
    _arrow(ax, (2.7, 3.95), (4.2, 3.95))
    ax.text(3.45, 4.12, "1. hỏi vị trí", ha="center", fontsize=9)
    colors = [BLUE, GREEN, AMBER]
    placement = [[0, 1], [1, 0], [0, 1]]  # minh họa nhân bản: mỗi block nằm trên 2 DataNode
    for d in range(3):
        x = 0.6 + d * 3.5
        _box(ax, x, 0.4, 3.0, 1.9, "", "#E9ECEF", text_color="#222")
        ax.text(x + 1.5, 2.05, f"DataNode {d + 1}", ha="center", fontsize=10.5, weight="bold")
        for k, b in enumerate(placement[d]):
            _box(ax, x + 0.3 + k * 1.3, 0.75, 1.1, 0.8, f"Block {b + 1}", colors[b], fontsize=10)
        _arrow(ax, (5.6, 3.4), (x + 1.5, 2.3), color="#999")
    _arrow(ax, (1.5, 3.4), (2.0, 2.3), color=BLUE)
    ax.text(0.3, 2.85, "2. đọc block trực tiếp\ntừ DataNode", fontsize=9, color=BLUE)
    ax.text(7.4, 4.3, f"creditcard.csv ≈ {vn(file_mb)} MB\n→ {n_blocks} block (128 MB/block)",
            fontsize=10, color="#333")
    save(fig, "hdfs_nguyen_ly")


def diagram_spark(n_partitions: int):
    fig, ax = _canvas(11.5, 5.2)
    _box(ax, 0.3, 3.6, 2.6, 1.2, "Driver\nSparkSession\nDAG Scheduler", BLUE)
    _box(ax, 3.6, 3.6, 2.2, 1.2, "Job\n(mỗi action:\ncount, write…)", "#4F6D7A")
    _box(ax, 6.5, 3.6, 2.2, 1.2, "Stage\n(ranh giới\nshuffle)", "#4F6D7A")
    _box(ax, 9.3, 3.6, 1.9, 1.2, f"{n_partitions} task\n= {n_partitions}\npartition", "#4F6D7A")
    _arrow(ax, (2.9, 4.2), (3.6, 4.2))
    _arrow(ax, (5.8, 4.2), (6.5, 4.2))
    _arrow(ax, (8.7, 4.2), (9.3, 4.2))
    _box(ax, 0.3, 0.3, 10.9, 2.6, "", "#E9ECEF")
    ax.text(5.75, 2.6, f"Executor – local[{SPARK_CORES}]: {SPARK_CORES} luồng xử lý song song",
            ha="center", fontsize=10.5, weight="bold")
    for c in range(SPARK_CORES):
        x = 0.7 + c * 2.65
        _box(ax, x, 0.6, 2.3, 1.6, f"Luồng {c + 1}\nchạy 1 task\ntrên 1 partition", GREEN, fontsize=10)
    _arrow(ax, (10.25, 3.6), (10.25, 2.9))
    save(fig, "spark_mo_hinh_thuc_thi")


def diagram_time_split(s: dict):
    fig, ax = plt.subplots(figsize=(11, 2.6))
    total_h = s["time_max_s"] / 3600
    cut_h = s["split_cutoff_s"] / 3600
    ax.barh([0], [cut_h], color=BLUE, height=0.5)
    ax.barh([0], [total_h - cut_h], left=[cut_h], color=AMBER, height=0.5)
    ax.text(cut_h / 2, 0, f"TRAIN – {vn(s['train_rows'])} giao dịch\n({vn(s['train_fraud'])} gian lận)",
            ha="center", va="center", color="white", fontsize=11, weight="bold")
    ax.text(cut_h + (total_h - cut_h) / 2, 0,
            f"TEST – {vn(s['test_rows'])} giao dịch\n({vn(s['test_fraud'])} gian lận)",
            ha="center", va="center", color="white", fontsize=11, weight="bold")
    ax.axvline(cut_h, color=RED, lw=2, ls="--")
    ax.text(cut_h, 0.42, f"mốc chia: giây {vn(s['split_cutoff_s'])} (≈ {vn(cut_h, 1)} giờ)",
            ha="center", color=RED, fontsize=10)
    ax.set_xlim(0, total_h)
    ax.set_yticks([])
    ax.set_xlabel("Thời gian kể từ giao dịch đầu tiên (giờ)")
    ax.grid(False)
    save(fig, "chia_tap_theo_thoi_gian")


# --------------------------------------------------------------------------------------------
# Thống kê bằng Spark
# --------------------------------------------------------------------------------------------
def _bucket_expr(col):
    expr = None
    for i in range(len(AMOUNT_EDGES) - 1):
        cond = (col >= AMOUNT_EDGES[i]) & (col < AMOUNT_EDGES[i + 1])
        expr = F.when(cond, i) if expr is None else expr.when(cond, i)
    return expr


def compute_data_stats(spark) -> tuple[dict, dict]:
    s, tables = {}, {}
    raw = read_raw_data(spark)
    s["raw_rows"] = raw.count()
    s["raw_cols"] = len(raw.columns)
    s["raw_partitions"] = raw.rdd.getNumPartitions()
    s["raw_fraud"] = raw.filter(F.col(LABEL_COL) == 1).count()
    s["missing_total"] = int(raw.select(
        sum(F.sum(F.col(c).isNull().cast("int")) for c in raw.columns)).first()[0])
    s["duplicates"] = s["raw_rows"] - raw.dropDuplicates().count()
    s["time_max_s"] = float(raw.agg(F.max(TIME_COL)).first()[0])
    s["file_mb"] = (ROOT_DIR / "data" / "raw" / "creditcard.csv").stat().st_size / 1e6
    s["hdfs_blocks"] = int(np.ceil(s["file_mb"] * 1e6 / (128 * 1024 * 1024)))

    desc_all = raw.select(FEATURE_COLS + [LABEL_COL]).describe().toPandas().set_index("summary")
    tables["describe_all"] = {c: {k: float(desc_all.loc[k, c]) for k in ["mean", "stddev", "min", "max"]}
                              for c in FEATURE_COLS + [LABEL_COL]}
    desc = raw.select(TIME_COL, AMOUNT_COL).describe().toPandas().set_index("summary")
    tables["describe"] = {c: {k: float(desc.loc[k, c]) for k in ["mean", "stddev", "min", "max"]}
                          for c in [TIME_COL, AMOUNT_COL]}
    for c in [TIME_COL, AMOUNT_COL]:
        q = raw.approxQuantile(c, [0.25, 0.5, 0.75], 0.001)
        tables["describe"][c].update({"q1": q[0], "median": q[1], "q3": q[2]})

    cleaned = spark.read.parquet(str(CLEANED_PARQUET_PATH)).cache()
    s["clean_rows"] = cleaned.count()
    s["clean_fraud"] = cleaned.filter(F.col(LABEL_COL) == 1).count()
    s["fraud_duplicates_removed"] = s["raw_fraud"] - s["clean_fraud"]
    s["fraud_rate"] = s["clean_fraud"] / s["clean_rows"]
    fraud_amt = cleaned.filter(F.col(LABEL_COL) == 1).agg(
        F.sum(AMOUNT_COL), F.avg(AMOUNT_COL)).first()
    s["fraud_amount_total"], s["fraud_amount_mean"] = float(fraud_amt[0]), float(fraud_amt[1])
    s["amount_median_by_class"] = {
        str(k): cleaned.filter(F.col(LABEL_COL) == k).approxQuantile(AMOUNT_COL, [0.5], 0.001)[0]
        for k in (0, 1)}

    amount_rows = (
        cleaned.withColumn("bucket", _bucket_expr(F.col(AMOUNT_COL)))
        .groupBy("bucket")
        .agg(F.count("*").alias("n"), F.sum(LABEL_COL).alias("fraud"),
             F.sum(F.when(F.col(LABEL_COL) == 1, F.col(AMOUNT_COL)).otherwise(0)).alias("fraud_amount"))
        .orderBy("bucket").toPandas()
    )
    amount_rows["label"] = [AMOUNT_LABELS[int(b)] for b in amount_rows["bucket"]]
    amount_rows["rate"] = amount_rows["fraud"] / amount_rows["n"]
    tables["amount_buckets"] = amount_rows.to_dict("records")

    hour_rows = (cleaned.groupBy(HOUR_COL).agg(F.count("*").alias("n"), F.sum(LABEL_COL).alias("fraud"))
                 .orderBy(HOUR_COL).toPandas())
    hour_rows["rate"] = hour_rows["fraud"] / hour_rows["n"]
    tables["hours"] = hour_rows.to_dict("records")

    cross = (cleaned.withColumn("bucket", _bucket_expr(F.col(AMOUNT_COL)))
             .withColumn("block", F.floor(F.col(HOUR_COL) / 4).cast("int"))
             .groupBy("block", "bucket").agg(F.count("*").alias("n"), F.sum(LABEL_COL).alias("fraud"))
             .toPandas())
    tables["hour_amount_cross"] = cross.to_dict("records")

    s["outliers"] = analyze_amount_outliers(cleaned)
    s["outliers"]["by_class"] = {str(k): v for k, v in s["outliers"]["by_class"].items()}

    # Ma trận tương quan Pearson (Spark MLlib Correlation) - toàn bộ / chỉ gian lận / chỉ bình thường
    def corr(df, cols):
        vec = VectorAssembler(inputCols=cols, outputCol="v").transform(df.select(cols)).select("v")
        return Correlation.corr(vec, "v").first()[0].toArray()

    all_cols = FEATURE_COLS + [LABEL_COL]
    corr_all = corr(cleaned, all_cols)
    tables["corr_all"] = {"cols": all_cols, "matrix": corr_all.tolist()}
    tables["corr_fraud"] = {"cols": FEATURE_COLS,
                            "matrix": corr(cleaned.filter(F.col(LABEL_COL) == 1), FEATURE_COLS).tolist()}
    tables["corr_normal"] = {"cols": FEATURE_COLS,
                             "matrix": corr(cleaned.filter(F.col(LABEL_COL) == 0), FEATURE_COLS).tolist()}
    with_class = pd.Series(corr_all[-1, :-1], index=FEATURE_COLS)
    tables["corr_with_class"] = with_class.sort_values(key=np.abs, ascending=False).to_dict()

    top4 = list(with_class.abs().sort_values(ascending=False).index[:4])
    s["top_corr_features"] = top4
    sample = (cleaned.filter(F.col(LABEL_COL) == 1)
              .unionByName(cleaned.filter(F.col(LABEL_COL) == 0).sample(fraction=0.05, seed=42))
              .select(top4 + [AMOUNT_COL, LABEL_COL]).toPandas())

    train = spark.read.parquet(str(TRAIN_PARQUET_PATH))
    test = spark.read.parquet(str(TEST_PARQUET_PATH))
    s["train_rows"], s["test_rows"] = train.count(), test.count()
    s["train_fraud"] = train.filter(F.col(LABEL_COL) == 1).count()
    s["test_fraud"] = test.filter(F.col(LABEL_COL) == 1).count()
    s["split_cutoff_s"] = float(train.agg(F.max(TIME_COL)).first()[0])

    weighted = spark.read.parquet(str(TRAIN_WEIGHTED_PARQUET_PATH))
    w = {int(r[LABEL_COL]): float(r["class_weight"])
         for r in weighted.select(LABEL_COL, "class_weight").distinct().collect()}
    s["class_weight"] = {str(k): v for k, v in w.items()}
    balanced = spark.read.parquet(str(TRAIN_BALANCED_PARQUET_PATH))
    s["smote"] = {str(int(r[LABEL_COL])): r["count"] for r in balanced.groupBy(LABEL_COL).count().collect()}
    s["spark_cores"] = SPARK_CORES
    cleaned.unpersist()
    return s, {**tables, "sample": sample}


def compute_model_scores(spark) -> pd.DataFrame:
    test = assemble_features(spark.read.parquet(str(TEST_PARQUET_PATH)))
    lr = LogisticRegressionModel.load(local_uri(MODELS_DIR / "logistic_regression"))
    rf = RandomForestClassificationModel.load(local_uri(MODELS_DIR / "random_forest"))
    keep = [TIME_COL, HOUR_COL, AMOUNT_COL, LABEL_COL] + MODEL_FEATURE_COLS
    base = lr.transform(test).withColumn("lr_score", vector_to_array("probability")[1]).select(
        keep + ["lr_score", "features"])
    pdf = rf.transform(base.withColumnRenamed("probability", "p0")).withColumn(
        "rf_score", vector_to_array("probability")[1]).select(keep + ["lr_score", "rf_score"]).toPandas()
    iso = joblib.load(MODELS_DIR / "isolation_forest.joblib")
    pdf["if_score"] = -iso.score_samples(pdf[MODEL_FEATURE_COLS])
    pdf["if_pred"] = (iso.predict(pdf[MODEL_FEATURE_COLS]) == -1).astype(int)
    importances = pd.Series(rf.featureImportances.toArray(), index=MODEL_FEATURE_COLS)
    pdf.attrs["rf_importance"] = importances.sort_values(ascending=False)
    pdf.attrs["rf_params"] = {"numTrees": rf.getNumTrees, "maxDepth": rf.getOrDefault("maxDepth")}
    pdf.attrs["lr_params"] = {"regParam": lr.getRegParam(), "elasticNetParam": lr.getElasticNetParam(),
                              "iterations": lr.summary.totalIterations if lr.hasSummary else None}
    return pdf


# --------------------------------------------------------------------------------------------
# Biểu đồ dữ liệu
# --------------------------------------------------------------------------------------------
def fig_class_balance(s):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"width_ratios": [1.2, 1]})
    normal = s["clean_rows"] - s["clean_fraud"]
    bars = a1.bar(["Bình thường (0)", "Gian lận (1)"], [normal, s["clean_fraud"]], color=[BLUE, RED])
    a1.set_yscale("log")
    a1.set_ylim(1, normal * 4)
    a1.set_ylabel("Số giao dịch (thang log)")
    a1.set_title("Số lượng giao dịch theo nhãn")
    for b, v in zip(bars, [normal, s["clean_fraud"]]):
        a1.text(b.get_x() + b.get_width() / 2, v * 1.15, vn(v), ha="center", fontsize=11)
    a2.pie([normal, s["clean_fraud"]], colors=[BLUE, RED], startangle=90, counterclock=False,
           labels=[f"Bình thường\n{vn(100 - s['fraud_rate'] * 100, 2)}%",
                   f"Gian lận\n{vn(s['fraud_rate'] * 100, 2)}%"],
           wedgeprops={"width": 0.38, "edgecolor": "white"})
    a2.set_title("Tỉ lệ nhãn")
    save(fig, "phan_bo_nhan")


def fig_amount(tables, s):
    df = pd.DataFrame(tables["amount_buckets"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.2))
    overall = s["fraud_rate"] * 100
    b = a1.bar(df["label"], df["rate"] * 100, color=RED, alpha=0.85)
    a1.axhline(overall, color=GRAY, ls="--", lw=1.2)
    a1.text(-0.45, overall, f" mức chung {vn(overall, 2)}%", ha="left", va="bottom", color="#555",
            fontsize=9, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1})
    a1.set_title("Tỉ lệ gian lận theo khoảng số tiền")
    a1.set_xlabel("Khoảng số tiền (€)")
    a1.set_ylabel("Tỉ lệ gian lận (%)")
    for rect, v in zip(b, df["rate"] * 100):
        a1.text(rect.get_x() + rect.get_width() / 2, v, f"{vn(v, 2)}%", ha="center", va="bottom", fontsize=9)
    b2 = a2.bar(df["label"], df["fraud_amount"] / 1000, color=AMBER)
    a2.set_title("Tổng số tiền bị gian lận theo khoảng số tiền")
    a2.set_xlabel("Khoảng số tiền (€)")
    a2.set_ylabel("Tổng tiền gian lận (nghìn €)")
    for rect, v, n in zip(b2, df["fraud_amount"] / 1000, df["fraud"]):
        a2.text(rect.get_x() + rect.get_width() / 2, v, f"{vn(v, 1)}k\n({int(n)} vụ)", ha="center",
                va="bottom", fontsize=8.5)
    for a in (a1, a2):
        a.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    save(fig, "gian_lan_theo_so_tien")


def fig_hour(tables, s):
    df = pd.DataFrame(tables["hours"])
    fig, a1 = plt.subplots(figsize=(11, 4.2))
    a1.bar(df[HOUR_COL], df["n"], color=BLUE, alpha=0.45, label="Số giao dịch")
    a1.set_xlabel("Giờ trong ngày (giả định giao dịch đầu tiên lúc 0h)")
    a1.set_ylabel("Số giao dịch")
    a1.set_xticks(range(24))
    a2 = a1.twinx()
    a2.plot(df[HOUR_COL], df["rate"] * 100, color=RED, marker="o", lw=2, label="Tỉ lệ gian lận")
    a2.set_ylabel("Tỉ lệ gian lận (%)", color=RED)
    a2.grid(False)
    a2.spines["right"].set_visible(True)
    peak = df.loc[df["rate"].idxmax()]
    a2.annotate(f"{int(peak[HOUR_COL])}h: {vn(peak['rate'] * 100, 2)}%", (peak[HOUR_COL], peak["rate"] * 100),
                xytext=(peak[HOUR_COL] + 2, peak["rate"] * 100), color=RED,
                arrowprops={"arrowstyle": "->", "color": RED})
    h1, l1 = a1.get_legend_handles_labels()
    h2, l2 = a2.get_legend_handles_labels()
    a1.legend(h1 + h2, l1 + l2, loc="lower center", bbox_to_anchor=(0.5, 1.06), ncol=2, frameon=False)
    a1.set_title("Số giao dịch và tỉ lệ gian lận theo giờ trong ngày", pad=30)
    save(fig, "gian_lan_theo_gio")


def fig_hour_amount(tables):
    df = pd.DataFrame(tables["hour_amount_cross"])
    n = df.pivot(index="block", columns="bucket", values="n").reindex(index=range(6), columns=range(7))
    f = df.pivot(index="block", columns="bucket", values="fraud").reindex(index=range(6), columns=range(7))
    rate = (f / n * 100).fillna(0)
    fig, ax = plt.subplots(figsize=(10, 4.4))
    im = ax.imshow(rate.values, cmap="Reds", aspect="auto")
    ax.set_xticks(range(7), AMOUNT_LABELS)
    ax.set_yticks(range(6), HOUR_BLOCKS)
    ax.set_xlabel("Khoảng số tiền (€)")
    ax.set_ylabel("Khung giờ")
    ax.grid(False)
    for i in range(6):
        for j in range(7):
            v = rate.values[i, j]
            ax.text(j, i, f"{vn(v, 2)}%", ha="center", va="center", fontsize=9,
                    color="white" if v > rate.values.max() * 0.55 else "#222")
    fig.colorbar(im, ax=ax, label="Tỉ lệ gian lận (%)")
    ax.set_title("Tỉ lệ gian lận theo khung giờ × khoảng số tiền")
    save(fig, "gio_x_so_tien")


def fig_outliers(tables, s):
    sample = tables["sample"]
    o = s["outliers"]
    fig, ax = plt.subplots(figsize=(10, 4))
    data = [sample.loc[sample[LABEL_COL] == 0, AMOUNT_COL] + 0.01, sample.loc[sample[LABEL_COL] == 1, AMOUNT_COL] + 0.01]
    bp = ax.boxplot(data, orientation="horizontal", tick_labels=["Bình thường", "Gian lận"],
                    patch_artist=True, widths=0.5,
                    flierprops={"markersize": 2.5, "alpha": 0.35})
    for patch, c in zip(bp["boxes"], [BLUE, RED]):
        patch.set_facecolor(c)
        patch.set_alpha(0.6)
    ax.set_xscale("log")
    ax.axvline(o["upper"], color=AMBER, ls="--", lw=1.5)
    ax.text(o["upper"] * 1.1, 2.35, f"ngưỡng ngoại lệ IQR\nQ3 + 1,5·IQR = {vn(o['upper'], 2)} €",
            color="#8a5a00", fontsize=9.5)
    ax.set_xlabel("Số tiền giao dịch (€, thang log)")
    ax.set_title("Phân bố số tiền và ngoại lệ theo quy tắc IQR")
    save(fig, "ngoai_le_so_tien")


def fig_correlation(tables):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4))
    for ax, key, title in [(axes[0], "corr_normal", "Giao dịch bình thường"),
                           (axes[1], "corr_fraud", "Giao dịch gian lận")]:
        m = np.array(tables[key]["matrix"])
        cols = tables[key]["cols"]
        im = ax.imshow(m, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(cols)), cols, rotation=90, fontsize=7)
        ax.set_yticks(range(len(cols)), cols, fontsize=7)
        ax.set_title(f"Tương quan giữa các đặc trưng – {title}")
        ax.grid(False)
    fig.colorbar(im, ax=axes, shrink=0.75, label="Hệ số tương quan Pearson")
    save(fig, "tuong_quan_dac_trung")


def fig_corr_with_class(tables):
    sr = pd.Series(tables["corr_with_class"]).iloc[:12][::-1]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.barh(sr.index, sr.values, color=[RED if v > 0 else BLUE for v in sr.values])
    ax.axvline(0, color="#333", lw=0.8)
    ax.set_xlabel("Hệ số tương quan với nhãn Class")
    ax.set_title("12 đặc trưng tương quan mạnh nhất với nhãn gian lận")
    save(fig, "tuong_quan_voi_nhan")


def fig_top_features(tables, s):
    sample = tables["sample"]
    top = s["top_corr_features"]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.6))
    for ax, f in zip(axes, top):
        lo, hi = np.percentile(sample[f], [0.5, 99.5])
        bins = np.linspace(lo, hi, 50)
        for lab, c, name in [(0, BLUE, "Bình thường"), (1, RED, "Gian lận")]:
            ax.hist(sample.loc[sample[LABEL_COL] == lab, f].clip(lo, hi), bins=bins, density=True,
                    alpha=0.55, color=c, label=name)
        ax.set_title(f)
    axes[0].legend()
    fig.suptitle("Phân bố của 4 đặc trưng tương quan mạnh nhất với nhãn (mật độ)", weight="bold")
    fig.tight_layout()
    save(fig, "phan_bo_dac_trung_manh")


def fig_smote(s):
    before = [s["train_rows"] - s["train_fraud"], s["train_fraud"]]
    after = [s["smote"]["0"], s["smote"]["1"]]
    fig, ax = plt.subplots(figsize=(8.5, 4))
    x = np.arange(2)
    b1 = ax.bar(x - 0.2, before, 0.4, color=GRAY, label="Trước SMOTE")
    b2 = ax.bar(x + 0.2, after, 0.4, color=[BLUE, RED], label="Sau SMOTE")
    ax.set_xticks(x, ["Bình thường (0)", "Gian lận (1)"])
    ax.set_yscale("log")
    ax.set_ylabel("Số mẫu huấn luyện (thang log)")
    for bars in (b1, b2):
        for r in bars:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() * 1.12, vn(r.get_height()), ha="center", fontsize=9.5)
    ax.legend()
    ax.set_title("Số mẫu tập huấn luyện trước và sau SMOTE (tỉ lệ thiểu số/đa số = 0,1)")
    save(fig, "smote")


# --------------------------------------------------------------------------------------------
# Biểu đồ mô hình
# --------------------------------------------------------------------------------------------
def fig_confusion(metrics: pd.DataFrame):
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9))
    for ax, (_, r) in zip(axes, metrics.iterrows()):
        cm = np.array([[r["tn"], r["fp"]], [r["fn"], r["tp"]]])
        ax.imshow(np.log10(cm + 1), cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, vn(cm[i, j]), ha="center", va="center", fontsize=13,
                        color="white" if cm[i, j] > 1000 else "#222", weight="bold")
        ax.set_xticks([0, 1], ["Dự đoán: BT", "Dự đoán: GL"])
        ax.set_yticks([0, 1], ["Thực tế: BT", "Thực tế: GL"])
        ax.set_title(r["model"])
        ax.grid(False)
    fig.suptitle("Ma trận nhầm lẫn trên tập test (BT = bình thường, GL = gian lận)", weight="bold")
    fig.tight_layout()
    save(fig, "ma_tran_nham_lan")


def fig_metrics(metrics: pd.DataFrame):
    cols = ["precision", "recall", "f1_score", "pr_auc", "roc_auc"]
    names = ["Precision", "Recall", "F1-score", "PR-AUC", "ROC-AUC"]
    fig, ax = plt.subplots(figsize=(11, 4.3))
    x = np.arange(len(cols))
    for k, (_, r) in enumerate(metrics.iterrows()):
        bars = ax.bar(x + (k - 1) * 0.26, [r[c] for c in cols], 0.26, label=r["model"],
                      color=MODEL_COLORS[r["model"]])
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01, vn(b.get_height(), 2),
                    ha="center", fontsize=8)
    ax.set_xticks(x, names)
    ax.set_ylim(0, 1.1)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    ax.set_title("So sánh các độ đo của 3 mô hình trên tập test")
    save(fig, "so_sanh_do_do")


def fig_curves(pdf: pd.DataFrame) -> dict:
    out = {}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
    base = pdf[LABEL_COL].mean()
    for name, col in [("Logistic Regression", "lr_score"), ("Random Forest", "rf_score"),
                      ("Isolation Forest", "if_score")]:
        p, r, _ = precision_recall_curve(pdf[LABEL_COL], pdf[col])
        fpr, tpr, _ = roc_curve(pdf[LABEL_COL], pdf[col])
        a1.plot(r, p, color=MODEL_COLORS[name], lw=2, label=f"{name} (AUC={vn(auc(r, p), 3)})")
        a2.plot(fpr, tpr, color=MODEL_COLORS[name], lw=2, label=f"{name} (AUC={vn(auc(fpr, tpr), 3)})")
        out[name] = {"pr_auc_curve": float(auc(r, p)), "roc_auc_curve": float(auc(fpr, tpr))}
    a1.axhline(base, color=GRAY, ls="--", lw=1)
    a1.text(0.02, base + 0.02, f"đoán ngẫu nhiên ({vn(base * 100, 2)}%)", color=GRAY, fontsize=9)
    a1.set_xlabel("Recall")
    a1.set_ylabel("Precision")
    a1.set_title("Đường Precision – Recall")
    a2.plot([0, 1], [0, 1], color=GRAY, ls="--", lw=1)
    a2.set_xlabel("False Positive Rate")
    a2.set_ylabel("True Positive Rate (Recall)")
    a2.set_title("Đường ROC")
    for a in (a1, a2):
        a.legend(loc="lower left" if a is a1 else "lower right", fontsize=9)
    save(fig, "duong_pr_roc")
    return out


def fig_threshold(pdf: pd.DataFrame, thr: float):
    p, r, t = precision_recall_curve(pdf[LABEL_COL], pdf["rf_score"])
    f1 = 2 * p * r / np.clip(p + r, 1e-12, None)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, p[:-1], color=BLUE, lw=2, label="Precision")
    ax.plot(t, r[:-1], color=RED, lw=2, label="Recall")
    ax.plot(t, f1[:-1], color=GREEN, lw=2, label="F1-score")
    ax.axvline(0.5, color=GRAY, ls=":", lw=1.4)
    ax.text(0.505, 0.05, "ngưỡng mặc định 0,5", color=GRAY, fontsize=9)
    ax.axvline(thr, color=AMBER, ls="--", lw=2)
    ax.text(thr + 0.005, 0.15, f"ngưỡng đã tinh chỉnh {vn(thr, 3)}\n(chọn trên tập validation)",
            color="#8a5a00", fontsize=9)
    ax.set_xlabel("Ngưỡng phân loại (xác suất gian lận)")
    ax.set_ylabel("Giá trị")
    ax.set_xlim(0, 1)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False)
    ax.set_title("Random Forest: Precision, Recall, F1 theo ngưỡng (trên tập test)", pad=28)
    save(fig, "nguong_phan_loai")


def fig_importance(pdf: pd.DataFrame):
    imp = pdf.attrs["rf_importance"].iloc[:15][::-1]
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [AMBER if c.startswith(("Hour", "Amount")) else GREEN for c in imp.index]
    ax.barh(imp.index, imp.values, color=colors)
    ax.set_xlabel("Mức độ quan trọng (giảm impurity trung bình)")
    ax.set_title("15 đặc trưng quan trọng nhất của Random Forest")
    save(fig, "do_quan_trong_dac_trung")


def fig_suspicious(pdf: pd.DataFrame, thr: float) -> dict:
    pred = (pdf["rf_score"] >= thr).astype(int)
    y = pdf[LABEL_COL]
    groups = {
        "Bình thường – duyệt đúng (TN)": (pred == 0) & (y == 0),
        "Gian lận – phát hiện đúng (TP)": (pred == 1) & (y == 1),
        "Báo nhầm (FP)": (pred == 1) & (y == 0),
        "Bỏ sót (FN)": (pred == 0) & (y == 1),
    }
    style = {"Bình thường – duyệt đúng (TN)": (BLUE, 4, 0.12, "o"),
             "Gian lận – phát hiện đúng (TP)": (RED, 30, 0.9, "o"),
             "Báo nhầm (FP)": (AMBER, 45, 0.95, "X"),
             "Bỏ sót (FN)": (PURPLE, 40, 0.95, "s")}
    fig, ax = plt.subplots(figsize=(11.5, 4.8))
    hours = pdf[TIME_COL] / 3600
    for name, mask in groups.items():
        c, sz, al, mk = style[name]
        ax.scatter(hours[mask], pdf.loc[mask, AMOUNT_COL] + 0.01, s=sz, alpha=al, color=c, marker=mk,
                   label=f"{name}: {vn(int(mask.sum()))}", edgecolors="none")
    ax.set_yscale("log")
    ax.set_xlabel("Thời điểm giao dịch (giờ kể từ giao dịch đầu tiên)")
    ax.set_ylabel("Số tiền (€, thang log)")
    ax.legend(loc="upper left", fontsize=9, ncol=2)
    ax.set_title("Các giao dịch nghi vấn do Random Forest phát hiện trên tập test")
    save(fig, "giao_dich_nghi_van")
    caught = groups["Gian lận – phát hiện đúng (TP)"]
    return {"blocked_amount": float(pdf.loc[caught, AMOUNT_COL].sum()),
            "fraud_amount_test": float(pdf.loc[y == 1, AMOUNT_COL].sum())}


def fig_hour_feature_gain(before: pd.DataFrame, after: pd.DataFrame):
    cols = ["precision", "recall", "f1_score", "pr_auc"]
    names = ["Precision", "Recall", "F1-score", "PR-AUC"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, model in zip(axes, ["Logistic Regression", "Random Forest"]):
        b = before.set_index("model").loc[model, cols].values.astype(float)
        a = after.set_index("model").loc[model, cols].values.astype(float)
        x = np.arange(len(cols))
        ax.bar(x - 0.2, b, 0.4, color=GRAY, label="Trước (Time_scaled)")
        ax.bar(x + 0.2, a, 0.4, color=MODEL_COLORS[model], label="Sau (Hour_sin, Hour_cos)")
        for xi, (vb, va) in enumerate(zip(b, a)):
            ax.text(xi - 0.2, vb + 0.01, vn(vb, 2), ha="center", fontsize=8.5)
            ax.text(xi + 0.2, va + 0.01, vn(va, 2), ha="center", fontsize=8.5)
        ax.set_xticks(x, names)
        ax.set_ylim(0, 1.1)
        ax.set_title(model)
        ax.legend(fontsize=9, loc="upper left")
    fig.suptitle("Ảnh hưởng của đặc trưng giờ (cùng tham số mặc định, ngưỡng 0,5)", weight="bold")
    fig.tight_layout()
    save(fig, "anh_huong_dac_trung_gio")


def fig_tuning(tuning: dict):
    grid = pd.DataFrame(tuning.get("grid_random_forest", []))
    if grid.empty:
        return
    piv = grid.pivot(index="numTrees", columns="maxDepth", values="pr_auc")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 3.8))
    im = a1.imshow(piv.values, cmap="Greens", aspect="auto")
    a1.set_xticks(range(len(piv.columns)), [f"maxDepth={c}" for c in piv.columns])
    a1.set_yticks(range(len(piv.index)), [f"numTrees={i}" for i in piv.index])
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            a1.text(j, i, vn(piv.values[i, j], 4), ha="center", va="center", fontsize=11,
                    color="white" if piv.values[i, j] > piv.values.mean() else "#222")
    a1.set_title("Random Forest: PR-AUC trung bình 3-fold")
    a1.grid(False)
    lr = pd.DataFrame(tuning.get("grid_logistic_regression", []))
    if not lr.empty:
        piv2 = lr.pivot(index="regParam", columns="elasticNetParam", values="pr_auc")
        a2.imshow(piv2.values, cmap="Blues", aspect="auto")
        a2.set_xticks(range(len(piv2.columns)), [f"elasticNet={c}" for c in piv2.columns])
        a2.set_yticks(range(len(piv2.index)), [f"regParam={i}" for i in piv2.index])
        for i in range(piv2.shape[0]):
            for j in range(piv2.shape[1]):
                a2.text(j, i, vn(piv2.values[i, j], 4), ha="center", va="center", fontsize=11,
                        color="white" if piv2.values[i, j] >= piv2.values.max() - 1e-9 else "#222")
        a2.set_title("Logistic Regression: PR-AUC trung bình 3-fold")
        a2.grid(False)
    fig.tight_layout()
    save(fig, "tinh_chinh_luoi_tham_so")


def main():
    spark = get_spark_session("ReportFigures")
    try:
        stats, tables = compute_data_stats(spark)
        pdf = compute_model_scores(spark)
    finally:
        spark.stop()

    metrics = pd.read_csv(REPORTS_DIR / "metrics_comparison.csv")
    thresholds = json.loads((MODELS_DIR / "thresholds.json").read_text(encoding="utf-8"))
    tuning_path = MODELS_DIR / "tuning_results.json"
    tuning = json.loads(tuning_path.read_text(encoding="utf-8")) if tuning_path.exists() else {}
    rf_thr = thresholds["random_forest"]["threshold"]

    diagram_architecture()
    diagram_hdfs(stats["file_mb"], stats["hdfs_blocks"])
    diagram_spark(stats["raw_partitions"])
    diagram_time_split(stats)
    fig_class_balance(stats)
    fig_amount(tables, stats)
    fig_hour(tables, stats)
    fig_hour_amount(tables)
    fig_outliers(tables, stats)
    fig_correlation(tables)
    fig_corr_with_class(tables)
    fig_top_features(tables, stats)
    fig_smote(stats)
    fig_confusion(metrics)
    fig_metrics(metrics)
    stats["curves"] = fig_curves(pdf)
    fig_threshold(pdf, rf_thr)
    fig_importance(pdf)
    stats.update(fig_suspicious(pdf, rf_thr))
    before_path = REPORTS_DIR / "metrics_before_hour.csv"
    after_path = REPORTS_DIR / "metrics_after_hour_untuned.csv"
    if before_path.exists() and after_path.exists():
        fig_hour_feature_gain(pd.read_csv(before_path), pd.read_csv(after_path))
    fig_tuning(tuning)

    stats["rf_importance_top"] = pdf.attrs["rf_importance"].iloc[:10].to_dict()
    stats["rf_params"] = pdf.attrs["rf_params"]
    stats["lr_params"] = pdf.attrs["lr_params"]
    tables.pop("sample")
    STATS_PATH.write_text(json.dumps({"stats": stats, "tables": tables}, ensure_ascii=False, indent=2,
                                     default=float), encoding="utf-8")
    print(f"[Hình] Đã lưu số liệu thống kê -> {STATS_PATH}")


if __name__ == "__main__":
    main()
