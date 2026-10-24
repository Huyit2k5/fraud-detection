"""Backend FastAPI cho giao diện web: suy luận + giải thích mô hình, không khởi động Spark."""

import sys
from pathlib import Path

# Các module trong src/ import lẫn nhau dạng phẳng (from config import ...).
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
