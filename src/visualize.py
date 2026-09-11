"""
Giai đoạn 6 của kế hoạch: Trực quan hóa.

Xuất các biểu đồ:
1. Phân phối giao dịch bình thường vs gian lận (Amount, theo thời gian)
2. PCA 2D scatter minh họa vùng anomaly mà Isolation Forest phát hiện
3. Confusion matrix heatmap cho từng mô hình
4. Bar chart so sánh Precision/Recall/F1 giữa 3 mô hình
5. Biểu đồ tổng hợp giao dịch nghi vấn theo thời gian/số tiền

Chạy độc lập: python src/visualize.py
(yêu cầu đã chạy evaluate.py trước đó để có reports/metrics_comparison.csv)
"""

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA

from config import (
    FEATURE_COLS,
    FIGURES_DIR,
    LABEL_COL,
    MODEL_FEATURE_COLS,
    MODELS_DIR,
    REPORTS_DIR,
    TEST_PARQUET_PATH,
)
from spark_etl import get_spark_session

sns.set_theme(style="whitegrid")


def plot_class_distribution(test_pdf: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    sns.countplot(x=LABEL_COL, data=test_pdf, ax=axes[0])
    axes[0].set_title("Phân phối giao dịch: Bình thường (0) vs Gian lận (1)")
    axes[0].set_yscale("log")

    sns.histplot(
        data=test_pdf, x="Amount", hue=LABEL_COL, bins=50, log_scale=(True, False),
        stat="density", common_norm=False, ax=axes[1],
    )
    axes[1].set_title("Phân phối Amount: Bình thường vs Gian lận")

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "class_distribution.png", dpi=150)
    plt.close(fig)
    print(f"[Viz] Đã lưu class_distribution.png")


def plot_pca_anomaly(test_pdf: pd.DataFrame, iso_model):
    # PCA 2D minh họa dùng thang đo gốc (dễ diễn giải); dự đoán anomaly dùng đúng đặc trưng
    # đã chuẩn hóa mà Isolation Forest được huấn luyện (MODEL_FEATURE_COLS).
    X_display = test_pdf[FEATURE_COLS]
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_display)

    raw_pred = iso_model.predict(test_pdf[MODEL_FEATURE_COLS])  # -1 = anomaly, 1 = normal
    is_anomaly = raw_pred == -1

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(coords[~is_anomaly, 0], coords[~is_anomaly, 1],
               s=8, alpha=0.4, label="Bình thường (dự đoán)", color="tab:blue")
    ax.scatter(coords[is_anomaly, 0], coords[is_anomaly, 1],
               s=12, alpha=0.8, label="Gian lận/Anomaly (Isolation Forest)", color="tab:red")
    ax.set_title("PCA 2D: Vùng anomaly do Isolation Forest phát hiện")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.legend()

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "pca_anomaly.png", dpi=150)
    plt.close(fig)
    print(f"[Viz] Đã lưu pca_anomaly.png")


def plot_confusion_matrices(comparison_df: pd.DataFrame):
    fig, axes = plt.subplots(1, len(comparison_df), figsize=(5 * len(comparison_df), 4))
    if len(comparison_df) == 1:
        axes = [axes]

    for ax, (_, row) in zip(axes, comparison_df.iterrows()):
        cm = np.array([[row["tn"], row["fp"]], [row["fn"], row["tp"]]])
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                    xticklabels=["Pred 0", "Pred 1"], yticklabels=["True 0", "True 1"])
        ax.set_title(row["model"])

    fig.suptitle("Confusion Matrix theo từng mô hình")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "confusion_matrices.png", dpi=150)
    plt.close(fig)
    print(f"[Viz] Đã lưu confusion_matrices.png")


def plot_metrics_comparison(comparison_df: pd.DataFrame):
    metrics = ["precision", "recall", "f1_score", "roc_auc", "pr_auc"]
    plot_df = comparison_df.melt(id_vars="model", value_vars=metrics,
                                  var_name="metric", value_name="value")

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=plot_df, x="metric", y="value", hue="model", ax=ax)
    ax.set_title("So sánh Precision / Recall / F1 / ROC-AUC / PR-AUC giữa 3 mô hình")
    ax.set_ylim(0, 1.05)
    ax.legend(title="Mô hình", bbox_to_anchor=(1.02, 1), loc="upper left")

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "metrics_comparison.png", dpi=150)
    plt.close(fig)
    print(f"[Viz] Đã lưu metrics_comparison.png")


def plot_suspicious_transactions(test_pdf: pd.DataFrame, iso_model):
    """Dashboard tổng hợp: giao dịch nghi vấn (theo Isolation Forest) theo thời gian/số tiền."""
    raw_pred = iso_model.predict(test_pdf[MODEL_FEATURE_COLS])
    df = test_pdf.copy()
    df["is_suspicious"] = raw_pred == -1

    fig, ax = plt.subplots(figsize=(10, 5))
    normal = df[~df["is_suspicious"]]
    suspicious = df[df["is_suspicious"]]

    ax.scatter(normal["Time"], normal["Amount"], s=6, alpha=0.3,
               color="tab:blue", label="Bình thường")
    ax.scatter(suspicious["Time"], suspicious["Amount"], s=20, alpha=0.9,
               color="tab:red", label="Nghi vấn (Isolation Forest)")
    ax.set_xlabel("Thời gian (giây)")
    ax.set_ylabel("Số tiền giao dịch (Amount)")
    ax.set_yscale("log")
    ax.set_title("Giao dịch nghi vấn theo thời gian và số tiền")
    ax.legend()

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "suspicious_transactions.png", dpi=150)
    plt.close(fig)
    print(f"[Viz] Đã lưu suspicious_transactions.png")


def run_visualization():
    spark = get_spark_session()
    try:
        test_df = spark.read.parquet(str(TEST_PARQUET_PATH))
        select_cols = list(dict.fromkeys(FEATURE_COLS + MODEL_FEATURE_COLS + [LABEL_COL]))
        test_pdf = test_df.select(select_cols).toPandas()
    finally:
        spark.stop()

    iso_model = joblib.load(MODELS_DIR / "isolation_forest.joblib")
    comparison_df = pd.read_csv(REPORTS_DIR / "metrics_comparison.csv")

    plot_class_distribution(test_pdf)
    plot_pca_anomaly(test_pdf, iso_model)
    plot_confusion_matrices(comparison_df)
    plot_metrics_comparison(comparison_df)
    plot_suspicious_transactions(test_pdf, iso_model)


if __name__ == "__main__":
    run_visualization()
