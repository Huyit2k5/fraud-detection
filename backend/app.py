"""FastAPI backend cho giao diện web: trạng thái hệ thống, suy luận + giải thích, và WebSocket phát lại
luồng giao dịch của tập test (mô phỏng giám sát trực tiếp).

Chạy: .venv\\Scripts\\python -m uvicorn backend.app:app --port 8000
"""

import asyncio
import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.bundle import BundleError, load_bundle
from backend.inference import InferenceService
from config import DATA_BACKEND, INFERENCE_DIR, SPARK_CORES

STREAM_TICK_SECONDS = 0.1
STREAM_SPEEDS = (10, 100, 1000)
DEFAULT_SPEED = 100


class WhatIfRequest(BaseModel):
    tx_id: int
    amount: float = Field(ge=0)


def _hdfs_ok() -> bool:
    if DATA_BACKEND != "hdfs":
        return False
    try:
        from hdfs_utils import liststatus

        liststatus("/")
        return True
    except Exception:
        return False


def create_app(bundle_dir: Path = INFERENCE_DIR) -> FastAPI:
    app = FastAPI(title="Fraud Detection API")
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
                       allow_methods=["*"], allow_headers=["*"])
    state: dict = {"service": None, "error": None}

    def load() -> None:
        try:
            state["service"], state["error"] = InferenceService(load_bundle(bundle_dir)), None
        except BundleError as e:
            state["service"], state["error"] = None, str(e)

    def service() -> InferenceService:
        if state["service"] is None:
            raise HTTPException(status_code=503, detail=state["error"])
        return state["service"]

    def status() -> dict:
        svc = state["service"]
        model = None
        if svc is not None:
            m = svc.bundle.meta
            model = {"name": m["model_name"], "threshold": m["threshold"], "pr_auc": m["pr_auc"],
                     "selection_note": m["selection_note"]}
        return {"backend": "ok", "data_backend": DATA_BACKEND, "spark_cores": SPARK_CORES,
                "hdfs": {"ok": _hdfs_ok()}, "model": model, "model_error": state["error"]}

    load()

    @app.get("/api/status")
    def get_status():
        return status()

    @app.post("/api/reload")
    def reload():
        load()
        return status()

    @app.get("/api/infer/sample")
    def sample(kind: Literal["random", "fraud", "normal"] = "random"):
        svc = service()
        return svc.explain_tx(svc.sample(kind))

    @app.get("/api/infer/tx/{tx_id}")
    def get_tx(tx_id: int):
        try:
            return service().explain_tx(tx_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")

    @app.post("/api/infer/what-if")
    def what_if(req: WhatIfRequest):
        try:
            return service().what_if(req.tx_id, req.amount)
        except KeyError:
            raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")

    @app.websocket("/api/infer/stream")
    async def stream(ws: WebSocket):
        await ws.accept()
        svc = state["service"]
        if svc is None:
            await ws.send_json({"type": "error", "detail": state["error"]})
            await ws.close()
            return

        commands: asyncio.Queue = asyncio.Queue()
        disconnected = asyncio.Event()

        async def reader():
            while True:
                try:
                    text = await ws.receive_text()
                except (WebSocketDisconnect, RuntimeError):
                    disconnected.set()
                    return
                try:
                    await commands.put(json.loads(text))
                except ValueError:
                    pass  # bỏ qua lệnh không phải JSON

        reader_task = asyncio.create_task(reader())
        t0, t1 = svc.test_time_range()
        clock, pos, speed, paused = t0, 0, DEFAULT_SPEED, False
        stats = {"checked": 0, "caught": 0, "false_alarms": 0, "missed": 0, "blocked_amount": 0.0}
        try:
            while not disconnected.is_set():
                await asyncio.sleep(STREAM_TICK_SECONDS)
                step = False
                while not commands.empty():
                    cmd = commands.get_nowait()
                    if not isinstance(cmd, dict):
                        continue
                    if cmd.get("cmd") == "pause":
                        paused = True
                    elif cmd.get("cmd") == "resume":
                        paused = False
                    elif cmd.get("cmd") == "step":
                        # Chế độ từng giao dịch: dừng luồng và đi thêm đúng 1 giao dịch.
                        paused, step = True, True
                    elif cmd.get("cmd") == "speed" and cmd.get("value") in STREAM_SPEEDS:
                        speed = cmd["value"]
                    elif cmd.get("cmd") == "restart":
                        clock, pos = t0, 0
                        stats = dict.fromkeys(stats, 0)
                        stats["blocked_amount"] = 0.0
                txs = []
                if step and pos < len(svc):
                    txs = svc.stream_slice(pos, pos + 1)
                    pos += 1
                    clock = svc.time_at(pos - 1)
                elif not paused:
                    # Vị trí `pos` (không chỉ đồng hồ) để không phát lặp/bỏ sót giao dịch trùng thời điểm
                    # khi xen kẽ chế độ từng giao dịch và chế độ chạy liên tục.
                    end = clock + STREAM_TICK_SECONDS * speed
                    hi = max(pos, svc.index_at(end))
                    txs = svc.stream_slice(pos, hi)
                    pos, clock = hi, end
                for tx in txs:
                    stats["checked"] += 1
                    if tx["alert"] and tx["true_label"] == 1:
                        stats["caught"] += 1
                        stats["blocked_amount"] += tx["amount"]
                    elif tx["alert"]:
                        stats["false_alarms"] += 1
                    elif tx["true_label"] == 1:
                        stats["missed"] += 1
                await ws.send_json({"type": "batch", "txs": txs, "stats": stats, "clock": clock,
                                    "speed": speed, "paused": paused, "step": step})
                if pos >= len(svc) and clock >= t1:
                    await ws.send_json({"type": "end", "stats": stats})
                    await ws.close()
                    break
        except (WebSocketDisconnect, RuntimeError):
            pass  # client đóng kết nối giữa chừng - không phải lỗi
        finally:
            reader_task.cancel()

    return app


app = create_app()
