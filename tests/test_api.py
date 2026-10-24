import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(fake_bundle_dir):
    from backend.app import create_app

    return TestClient(create_app(fake_bundle_dir))


def test_status_with_model(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "ok"
    assert body["model"]["name"] == "Random Forest"
    assert body["model_error"] is None
    assert set(body) >= {"data_backend", "spark_cores", "hdfs"}


def test_no_bundle_503(tmp_path):
    from backend.app import create_app

    c = TestClient(create_app(tmp_path))
    r = c.get("/api/infer/sample", params={"kind": "random"})
    assert r.status_code == 503
    assert "Chưa có mô hình" in r.json()["detail"]
    s = c.get("/api/status").json()
    assert s["model"] is None and "Chưa có mô hình" in s["model_error"]


def test_sample_and_tx(client):
    e = client.get("/api/infer/sample", params={"kind": "fraud"}).json()
    assert e["true_label"] == 1
    assert client.get(f"/api/infer/tx/{e['tx_id']}").json()["tx_id"] == e["tx_id"]
    r = client.get("/api/infer/tx/999999")
    assert r.status_code == 404 and r.json()["detail"] == "Không tìm thấy giao dịch"
    assert client.get("/api/infer/sample", params={"kind": "abc"}).status_code == 422


def test_what_if_validation(client):
    assert client.post("/api/infer/what-if", json={"tx_id": 0, "amount": -1}).status_code == 422
    r = client.post("/api/infer/what-if", json={"tx_id": 0, "amount": 0})
    assert r.status_code == 200 and r.json()["what_if"] is True
    assert client.post("/api/infer/what-if", json={"tx_id": 999999, "amount": 0}).status_code == 404


def test_stream(client, fake_bundle_dir):
    import pandas as pd

    test = pd.read_parquet(fake_bundle_dir / "test.parquet")
    seen, end = 0, None
    with client.websocket_connect("/api/infer/stream") as ws:
        ws.send_json({"cmd": "speed", "value": 1000})
        for _ in range(400):
            msg = ws.receive_json()
            if msg["type"] == "end":
                end = msg
                break
            assert msg["type"] == "batch"
            seen += len(msg["txs"])
    assert end is not None
    assert seen == len(test)
    assert end["stats"]["checked"] == len(test)
    assert end["stats"]["caught"] + end["stats"]["missed"] == int(test["Class"].sum())


def test_stream_pause_and_bad_command(client):
    with client.websocket_connect("/api/infer/stream") as ws:
        ws.send_json({"cmd": "pause"})
        msgs = [ws.receive_json() for _ in range(5)]
        assert msgs[-1]["paused"] is True
        assert msgs[-1]["clock"] == msgs[-2]["clock"]  # đồng hồ đứng yên khi tạm dừng
        ws.send_json({"cmd": "speed", "value": 7})  # tốc độ không hợp lệ -> bỏ qua
        assert ws.receive_json()["speed"] == 100


def test_stream_step_one_transaction(client, fake_bundle_dir):
    import pandas as pd

    test = pd.read_parquet(fake_bundle_dir / "test.parquet")
    with client.websocket_connect("/api/infer/stream") as ws:
        ws.send_json({"cmd": "pause"})
        ws.send_json({"cmd": "step"})
        stepped = []
        for _ in range(10):
            msg = ws.receive_json()
            if msg["txs"]:
                stepped.append(msg)
                if len(stepped) == 1:
                    ws.send_json({"cmd": "step"})
                else:
                    break
    first, second = stepped
    assert len(first["txs"]) == 1 and len(second["txs"]) == 1
    assert first["paused"] is True and first["step"] is True
    assert [first["txs"][0]["tx_id"], second["txs"][0]["tx_id"]] == test["tx_id"].tolist()[:2]
    assert second["stats"]["checked"] == 2


def test_stream_reconnect(client):
    with client.websocket_connect("/api/infer/stream") as ws:
        ws.send_json({"cmd": "speed", "value": 1000})
        for _ in range(3):
            ws.receive_json()
    with client.websocket_connect("/api/infer/stream") as ws:
        first = ws.receive_json()
    assert first["stats"]["checked"] == len(first["txs"])  # kết nối mới bắt đầu lại từ đầu
