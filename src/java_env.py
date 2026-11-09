"""Dò JDK 17 và dựng biến môi trường cho các tiến trình chạy Spark trên Windows.

PySpark 4.x yêu cầu JDK 17. Máy có thể cài nhiều JDK song song và biến JAVA_HOME hệ thống
có thể trỏ nhầm sang JDK khác (vd. JDK 11) -> lỗi UnsupportedClassVersionError. Module này
luôn ưu tiên JDK 17 tự dò được, dùng chung cho backend web, pytest và các script tiện ích.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
JDK_SEARCH_DIRS = (Path(r"C:\Program Files\Eclipse Adoptium"), Path(r"C:\Program Files\Java"))


def _version_key(path: Path) -> tuple:
    # So sánh theo số phiên bản thực (17.0.10 > 17.0.2), không phải chuỗi ký tự.
    return tuple(int(n) for n in re.findall(r"\d+", path.name))


def find_jdk17() -> Path | None:
    """Trả về thư mục JDK 17 mới nhất tìm thấy, hoặc None nếu không có."""
    for base in JDK_SEARCH_DIRS:
        if base.is_dir():
            candidates = sorted(base.glob("jdk-17*"), key=_version_key, reverse=True)
            if candidates:
                return candidates[0]
    return None


def spark_env(base: dict | None = None) -> dict:
    """Bản sao biến môi trường với JAVA_HOME (JDK 17), HADOOP_HOME (<repo>/hadoop) và PATH
    đã đặt đúng cho Spark. Không sửa `base`/os.environ gốc."""
    env = dict(os.environ if base is None else base)
    java_home = find_jdk17() or (Path(env["JAVA_HOME"]) if env.get("JAVA_HOME") else None)
    hadoop_home = Path(env["HADOOP_HOME"]) if env.get("HADOOP_HOME") else ROOT_DIR / "hadoop"
    if java_home and java_home.is_dir():
        env["JAVA_HOME"] = str(java_home)
        env["PATH"] = f"{java_home / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    if hadoop_home.is_dir():
        env["HADOOP_HOME"] = str(hadoop_home)
        env["PATH"] = f"{hadoop_home / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    return env
