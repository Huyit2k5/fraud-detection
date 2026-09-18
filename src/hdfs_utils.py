"""Wrapper mỏng quanh WebHDFS REST API (namenode, mặc định port 9870).

Dùng để:
- Bootstrap dữ liệu lên HDFS (scripts/hdfs_bootstrap.py).
- Đọc trạng thái HDFS cho dashboard (dashboard/app.py), tab "HDFS".

Không cần thư viện `hdfs` ngoài — WebHDFS LISTSTATUS/GETFILESTATUS/MKDIRS/CREATE là các
lệnh GET/PUT HTTP đơn giản, đủ dùng với `requests`.
"""

from __future__ import annotations

from pathlib import Path

import requests

from config import HDFS_WEBHDFS_URL

WEBHDFS_BASE = f"{HDFS_WEBHDFS_URL}/webhdfs/v1"
# Pseudo-cluster này không bật security -> WebHDFS coi request ẩn danh là user "dr.who"
# (không có quyền ghi). Set "user.name=root" cho các thao tác ghi (namenode container
# chạy HDFS với user root).
WRITE_USER = {"user.name": "root"}


def liststatus(path: str) -> list[dict]:
    """Liệt kê file/thư mục con của `path` trên HDFS. Trả về [] nếu path không tồn tại."""
    resp = requests.get(f"{WEBHDFS_BASE}{path}", params={"op": "LISTSTATUS"}, timeout=10)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()["FileStatuses"]["FileStatus"]


def mkdirs(path: str) -> None:
    # Pseudo-cluster dev/demo, không bật Kerberos: mở quyền ghi cho mọi user ngay khi tạo
    # (Spark trên host Windows chạy dưới user Windows hiện tại, không phải "root" tạo thư mục
    # này) — truyền permission thẳng trong MKDIRS thay vì gọi thêm SETPERMISSION riêng.
    resp = requests.put(
        f"{WEBHDFS_BASE}{path}", params={"op": "MKDIRS", "permission": "777", **WRITE_USER}, timeout=10,
    )
    resp.raise_for_status()
    if not resp.json().get("boolean"):
        raise RuntimeError(
            f"MKDIRS {path} trả về boolean=false (thường do 1 thành phần trên đường dẫn đã "
            "tồn tại dưới dạng FILE thay vì DIRECTORY)."
        )


def chmod(path: str, permission: str) -> None:
    resp = requests.put(
        f"{WEBHDFS_BASE}{path}", params={"op": "SETPERMISSION", "permission": permission, **WRITE_USER},
        timeout=10,
    )
    resp.raise_for_status()


def upload_file(local_path: Path, hdfs_path: str, overwrite: bool = True) -> None:
    """Upload 1 file local lên HDFS qua WebHDFS (2 bước: CREATE để lấy redirect tới
    DataNode, rồi PUT dữ liệu thật tới URL đó)."""
    local_path = Path(local_path)
    step1 = requests.put(
        f"{WEBHDFS_BASE}{hdfs_path}",
        params={"op": "CREATE", "overwrite": str(overwrite).lower(), **WRITE_USER},
        allow_redirects=False,
        timeout=10,
    )
    if step1.status_code != 307:
        step1.raise_for_status()
        raise RuntimeError(f"Kỳ vọng redirect 307 từ NameNode, nhận được {step1.status_code}")

    datanode_url = step1.headers["Location"]
    with open(local_path, "rb") as f:
        step2 = requests.put(datanode_url, data=f, timeout=300)
    step2.raise_for_status()


def block_locations(path: str) -> list[dict]:
    """Trả về danh sách block HDFS thực tế của 1 file (op=GET_BLOCK_LOCATIONS): mỗi block có
    offset, kích thước và (các) DataNode chứa nó — dùng để trực quan việc HDFS "băm" file lớn
    thành nhiều block (mặc định 128MB/block) và nhân bản (replication) qua nhiều DataNode."""
    resp = requests.get(f"{WEBHDFS_BASE}{path}", params={"op": "GET_BLOCK_LOCATIONS"}, timeout=10)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    blocks = resp.json()["LocatedBlocks"]["locatedBlocks"]
    return sorted(
        [
            {
                "blockId": b["block"]["blockId"],
                "offset": b["startOffset"],
                "length": b["block"]["numBytes"],
                "replicas": [loc["name"] for loc in b["locations"]],
            }
            for b in blocks
        ],
        key=lambda b: b["offset"],
    )


def file_status(path: str) -> dict | None:
    resp = requests.get(f"{WEBHDFS_BASE}{path}", params={"op": "GETFILESTATUS"}, timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()["FileStatus"]
