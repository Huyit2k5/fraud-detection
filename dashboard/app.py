"""Web dashboard trực quan hóa pipeline fraud detection: dữ liệu trên HDFS,
các bước ETL/tiền xử lý, và kết quả huấn luyện/so sánh mô hình.

Chạy: streamlit run dashboard/app.py
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))


def _find_jdk17() -> Path | None:
    """Tìm JDK 17 cài qua Eclipse Adoptium (yêu cầu của PySpark trên Windows — xem README).
    Cần vì máy có thể có nhiều JDK trên PATH (vd. JDK 11 đứng trước) và subprocess của
    dashboard không kế thừa JAVA_HOME đã set thủ công ở 1 terminal khác."""
    def version_key(p: Path) -> tuple:
        # So sánh theo số phiên bản thực (17.0.10 > 17.0.2), không phải chuỗi ký tự
        # ("jdk-17.0.10" < "jdk-17.0.2" nếu so lexicographic vì '1' < '2').
        return tuple(int(n) for n in re.findall(r"\d+", p.name))

    for base in (Path(r"C:\Program Files\Eclipse Adoptium"), Path(r"C:\Program Files\Java")):
        if base.is_dir():
            candidates = sorted(base.glob("jdk-17*"), key=version_key, reverse=True)
            if candidates:
                return candidates[0]
    return None


def spark_subprocess_env() -> dict:
    """Env dùng cho subprocess chạy ETL/pipeline (Spark cần đúng JAVA_HOME/HADOOP_HOME,
    không phụ thuộc vào terminal đã mở dashboard có set sẵn hay chưa).

    Luôn ưu tiên JDK 17 tự dò được (PySpark ở đây yêu cầu đúng JDK 17 - xem README), kể cả khi
    máy đã có sẵn biến môi trường JAVA_HOME trỏ tới JDK khác (vd. JDK 11) - biến hệ thống đó
    KHÔNG được ghi đè lại, nên nếu chỉ dùng khi "chưa set" thì không bao giờ sửa được trường hợp
    JAVA_HOME trỏ sai phiên bản."""
    env = os.environ.copy()
    java_home = _find_jdk17() or (Path(env["JAVA_HOME"]) if env.get("JAVA_HOME") else None)
    hadoop_home = Path(env["HADOOP_HOME"]) if env.get("HADOOP_HOME") else ROOT_DIR / "hadoop"
    if java_home and java_home.is_dir():
        env["JAVA_HOME"] = str(java_home)
        env["PATH"] = f"{java_home}\\bin;{env.get('PATH', '')}"
    if hadoop_home.is_dir():
        env["HADOOP_HOME"] = str(hadoop_home)
        env["PATH"] = f"{hadoop_home}\\bin;{env.get('PATH', '')}"
    return env

from config import (  # noqa: E402
    DATA_BACKEND,
    FIGURES_DIR,
    HDFS_WEBHDFS_URL,
    MODELS_DIR,
    REPORTS_DIR,
)

st.set_page_config(page_title="Fraud Detection Pipeline", layout="wide")
st.title("Fraud Detection — Trực quan hóa pipeline")
st.caption(f"DATA_BACKEND hiện tại: **{DATA_BACKEND}**"
           + ("" if DATA_BACKEND == "hdfs" else " (đặt biến môi trường DATA_BACKEND=hdfs để dùng HDFS thật)"))


def run_streaming(cmd: list[str], placeholder, max_lines: int = 200) -> int:
    """Chạy 1 lệnh và stream stdout theo thời gian thực vào 1 st.empty() placeholder.
    Chỉ giữ tối đa `max_lines` dòng gần nhất trong bộ nhớ (log Spark/pipeline có thể rất dài)."""
    process = subprocess.Popen(
        cmd, cwd=str(ROOT_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, encoding="utf-8", errors="replace", env=spark_subprocess_env(),
    )
    lines: list[str] = []
    for line in process.stdout:
        lines.append(line.rstrip("\n"))
        del lines[:-max_lines]
        placeholder.code("\n".join(lines))
    process.wait()
    return process.returncode


def run_button(label: str, cmd: list[str], ok_msg: str, err_prefix: str) -> None:
    """Nút bấm chạy 1 lệnh với log trực tiếp + thông báo kết quả (dùng chung cho tab ETL/pipeline)."""
    if st.button(label):
        placeholder = st.empty()
        code = run_streaming(cmd, placeholder)
        if code == 0:
            st.success(ok_msg)
        else:
            st.error(f"{err_prefix} {code}.")


tab_hdfs, tab_etl, tab_train = st.tabs(["HDFS", "ETL & tiền xử lý", "Huấn luyện & Đánh giá"])

with tab_hdfs:
    st.subheader("Dữ liệu trên HDFS")
    st.markdown(f"NameNode Web UI: [{HDFS_WEBHDFS_URL}]({HDFS_WEBHDFS_URL})")

    try:
        from hdfs_utils import block_locations as _block_locations
        from hdfs_utils import liststatus as _liststatus

        # Cache ngắn hạn: tránh gọi lại hàng chục request WebHDFS mỗi lần Streamlit
        # rerun toàn bộ script (kể cả khi rerun do bấm nút ở tab khác).
        liststatus = st.cache_data(ttl=5)(_liststatus)
        block_locations = st.cache_data(ttl=5)(_block_locations)

        def render_blocks(full_path: str, size_bytes: int):
            """Hiển thị các block HDFS thực tế của 1 file: HDFS 'băm' file thành nhiều block
            (mặc định 128MB/block) và nhân bản (replication) qua các DataNode."""
            blocks = block_locations(full_path)
            if not blocks:
                st.info("File rỗng hoặc chưa có block.")
                return
            bdf = pd.DataFrame(blocks)
            bdf["length_MB"] = (bdf["length"] / 1_000_000).round(2)
            bdf["DataNode chứa replica"] = bdf["replicas"].apply(", ".join)
            st.dataframe(
                bdf[["blockId", "offset", "length_MB", "DataNode chứa replica"]],
                use_container_width=True,
            )
            st.caption(
                f"File {size_bytes / 1_000_000:.1f}MB bị **băm thành {len(blocks)} block** HDFS "
                f"(block size mặc định 128MB)."
            )

        def render_dir(hdfs_dir: str):
            entries = liststatus(hdfs_dir)
            if not entries:
                st.info(f"`{hdfs_dir}` trống hoặc chưa tồn tại trên HDFS.")
                return
            df = pd.DataFrame(entries)[
                ["pathSuffix", "type", "length", "replication", "blockSize", "modificationTime"]
            ]
            df["length_MB"] = (df["length"] / 1_000_000).round(3)
            df["modificationTime"] = pd.to_datetime(df["modificationTime"], unit="ms")
            st.dataframe(df.drop(columns=["length"]), use_container_width=True)

            for entry in entries:
                full_path = f"{hdfs_dir}/{entry['pathSuffix']}"
                if entry["type"] == "FILE":
                    with st.expander(f"🔍 Chi tiết block: {entry['pathSuffix']}"):
                        render_blocks(full_path, entry["length"])
                else:  # DIRECTORY: thư mục parquet, gồm nhiều part-file do Spark ghi ra
                    with st.expander(f"📁 Các part-file (Spark) trong: {entry['pathSuffix']}"):
                        children = [
                            c for c in liststatus(full_path)
                            if not c["pathSuffix"].startswith(("_", "."))
                        ]
                        if not children:
                            st.info("Chưa có part-file.")
                            continue
                        rows = [
                            {
                                "part-file": c["pathSuffix"],
                                "size_MB": round(c["length"] / 1_000_000, 3),
                                "số block HDFS": len(block_locations(f"{full_path}/{c['pathSuffix']}")),
                            }
                            for c in children
                        ]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True)
                        st.caption(
                            f"{len(children)} part-file (Spark chia dữ liệu thành các partition khi ghi "
                            "ra Parquet) — mỗi part-file lại có thể bị HDFS băm tiếp thành nhiều block "
                            "nếu vượt quá 128MB."
                        )

        st.markdown("**/data/raw**")
        render_dir("/data/raw")
        st.markdown("**/data/processed**")
        render_dir("/data/processed")
    except requests.exceptions.RequestException as e:
        st.warning(
            "Không kết nối được tới HDFS WebHDFS API. Đảm bảo đã chạy "
            "`docker compose -f docker-compose.hdfs.yml up -d`.\n\n"
            f"Chi tiết lỗi: {e}"
        )

with tab_etl:
    st.subheader("Giai đoạn 1-2: ETL (đọc dữ liệu, EDA, làm sạch, chuẩn hóa, split)")
    st.caption("Chạy `src/spark_etl.py` và xem log trực tiếp (EDA, số dòng loại bỏ, ngưỡng split...).")
    run_button("Chạy ETL", [sys.executable, "src/spark_etl.py"], "ETL hoàn tất.", "ETL kết thúc với mã lỗi")

with tab_train:
    st.subheader("Chạy toàn bộ pipeline")
    st.caption("Chạy ETL -> xử lý mất cân bằng -> huấn luyện 3 mô hình -> đánh giá -> vẽ biểu đồ.")
    run_button(
        "Chạy pipeline đầy đủ", [sys.executable, "run_pipeline.py"],
        "Pipeline hoàn tất.", "Pipeline kết thúc với mã lỗi",
    )

    st.divider()
    st.subheader("So sánh mô hình")
    metrics_path = REPORTS_DIR / "metrics_comparison.csv"
    if metrics_path.exists():
        st.dataframe(pd.read_csv(metrics_path), use_container_width=True)
    else:
        st.info("Chưa có `reports/metrics_comparison.csv` — chạy pipeline trước.")

    thresholds_path = MODELS_DIR / "thresholds.json"
    if thresholds_path.exists():
        st.markdown("**Ngưỡng phân loại đã tinh chỉnh** (`models/thresholds.json`)")
        st.json(json.loads(thresholds_path.read_text(encoding="utf-8")))

    st.subheader("Biểu đồ")
    if FIGURES_DIR.exists():
        images = sorted(FIGURES_DIR.glob("*.png"))
        if images:
            cols = st.columns(2)
            for i, img_path in enumerate(images):
                with cols[i % 2]:
                    st.image(str(img_path), caption=img_path.stem, use_container_width=True)
        else:
            st.info("Chưa có biểu đồ trong `reports/figures/` — chạy pipeline trước.")
