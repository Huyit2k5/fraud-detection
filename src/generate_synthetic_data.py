"""
Sinh dữ liệu giả lập (synthetic) có cấu trúc giống bộ dữ liệu
Credit Card Fraud Detection (Kaggle - ULB), dùng để test toàn bộ pipeline
khi chưa có dữ liệu thật.

Cấu trúc: Time, V1..V28 (giả lập thành phần PCA), Amount, Class
Tỉ lệ gian lận ~0.17%, giống dataset gốc (492/284807).

Chạy: python src/generate_synthetic_data.py
"""

import numpy as np
import pandas as pd

from config import RAW_CSV_PATH, PCA_COLS, RANDOM_SEED

N_SAMPLES = 50_000
FRAUD_RATIO = 0.0017  # ~0.17%, giống dataset gốc


def generate(n_samples: int = N_SAMPLES, fraud_ratio: float = FRAUD_RATIO,
             seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    n_fraud = max(1, int(n_samples * fraud_ratio))
    n_normal = n_samples - n_fraud

    # Time: giây kể từ giao dịch đầu tiên, tăng dần trong ~2 ngày (giống dataset gốc)
    time = np.sort(rng.uniform(0, 172_800, n_samples))

    # Amount: normal ~ lognormal nhỏ, fraud thường có amount bất thường (nhỏ lẻ hoặc lớn đột biến)
    amount_normal = rng.lognormal(mean=3.0, sigma=1.2, size=n_normal)
    amount_fraud = rng.lognormal(mean=4.0, sigma=1.8, size=n_fraud)

    # V1..V28: giả lập thành phần PCA. Với normal ~ N(0,1) độc lập.
    # Với fraud, dịch chuyển mean/variance ở một số chiều để tạo tín hiệu phân biệt được (giả lập anomaly).
    v_normal = rng.normal(loc=0.0, scale=1.0, size=(n_normal, len(PCA_COLS)))

    v_fraud = rng.normal(loc=0.0, scale=1.0, size=(n_fraud, len(PCA_COLS)))
    shift_dims = [0, 3, 7, 10, 14]  # một vài chiều "nhạy cảm" với gian lận
    for d in shift_dims:
        v_fraud[:, d] += rng.normal(loc=-4.0, scale=1.5, size=n_fraud)

    df_normal = pd.DataFrame(v_normal, columns=PCA_COLS)
    df_normal["Amount"] = amount_normal
    df_normal["Class"] = 0

    df_fraud = pd.DataFrame(v_fraud, columns=PCA_COLS)
    df_fraud["Amount"] = amount_fraud
    df_fraud["Class"] = 1

    df = pd.concat([df_normal, df_fraud], ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)  # xáo trộn hàng
    df["Time"] = time
    df = df.sort_values("Time").reset_index(drop=True)

    # sắp xếp lại cột đúng thứ tự giống dataset gốc: Time, V1..V28, Amount, Class
    df = df[["Time"] + PCA_COLS + ["Amount", "Class"]]
    return df


if __name__ == "__main__":
    df = generate()
    RAW_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_CSV_PATH, index=False)
    print(f"Đã sinh {len(df):,} giao dịch synthetic -> {RAW_CSV_PATH}")
    print(f"Số giao dịch gian lận: {int(df['Class'].sum())} "
          f"({df['Class'].mean() * 100:.3f}%)")
