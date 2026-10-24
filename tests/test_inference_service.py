import numpy as np
import pytest

from config import MODEL_FEATURE_COLS


@pytest.fixture
def service(fake_bundle_dir):
    from backend.bundle import load_bundle
    from backend.inference import InferenceService

    return InferenceService(load_bundle(fake_bundle_dir))


def _model_score(e: dict) -> float:
    p = e["probability"]
    return p if e["explain_space"] == "probability" else float(np.log(p / (1 - p)))


def test_explain_reasons_sum(service):
    for tx_id in range(0, 50, 7):
        e = service.explain_tx(tx_id)
        assert e["base_value"] + sum(r["contribution"] for r in e["reasons"]) == pytest.approx(_model_score(e))
        assert len(e["reasons"]) == 3
        assert {r["key"] for r in e["reasons"]} == {"behavior", "hour", "amount"}
        assert len(e["technical"]) == 31
        assert e["risk"] == round(e["probability"] * 100)
        assert e["alert"] == (e["probability"] >= e["threshold"])
        assert e["what_if"] is False


def test_reasons_sorted_by_magnitude(service):
    e = service.explain_tx(3)
    mags = [abs(r["contribution"]) for r in e["reasons"]]
    assert mags == sorted(mags, reverse=True)


def test_reason_direction_and_copy(service):
    seen_safe = False
    for tx_id in range(50):
        for r in service.explain_tx(tx_id)["reasons"]:
            assert r["direction"] == ("fraud" if r["contribution"] > 0 else "safe")
            if r["direction"] == "safe":
                seen_safe = True
                assert "khác thường" not in r["title"]
    assert seen_safe


def test_hour_and_amount_copy(service):
    e = service.explain_tx(0)
    by_key = {r["key"]: r for r in e["reasons"]}
    assert by_key["hour"]["title"].startswith(f"Giao dịch lúc {e['hour']} giờ ")
    assert by_key["amount"]["title"].startswith("Số tiền ") and by_key["amount"]["title"].endswith(" €")
    assert "%" in by_key["amount"]["detail"]
    assert "28 dấu hiệu" in by_key["behavior"]["detail"]


def test_sample_kinds(service, fake_bundle_dir):
    test = service.bundle.test.set_index("tx_id")
    rng = np.random.default_rng(1)
    assert test.loc[service.sample("fraud", rng), "Class"] == 1
    assert test.loc[service.sample("normal", rng), "Class"] == 0
    assert service.sample("random", rng) in test.index


def test_neighbors(service):
    e = service.explain_tx(5)
    train_ids = set(service.bundle.train["tx_id"])
    assert len(e["neighbors"]) == 5
    assert e["neighbors_fraud"] == sum(n["label"] for n in e["neighbors"])
    assert all(n["tx_id"] in train_ids for n in e["neighbors"])
    assert set(e["neighbors"][0]) == {"tx_id", "amount", "hour", "minute", "label"}


def test_what_if_edges(service):
    for amount, hour in [(0, 0), (25691.16, 23)]:
        e = service.what_if(4, amount, hour)
        assert 0 <= e["risk"] <= 100
        assert e["what_if"] is True
        assert e["amount"] == amount and e["hour"] == hour

    tech = lambda e: {t["feature"]: t["value"] for t in e["technical"]}  # noqa: E731
    assert tech(service.what_if(4, 50, 14))["Hour_sin"] != pytest.approx(tech(service.what_if(4, 50, 2))["Hour_sin"])
    assert tech(service.what_if(4, 50, 2))["Amount_scaled"] == pytest.approx((50 - 88.0) / 250.0)


def test_explain_unknown_tx(service):
    with pytest.raises(KeyError):
        service.explain_tx(999_999)


def test_stream_batch(service):
    t0, t1 = service.test_time_range()
    rows = service.stream_batch(t0, t1 + 1)
    assert len(rows) == len(service.bundle.test)
    assert [r["time_s"] for r in rows] == sorted(r["time_s"] for r in rows)
    assert service.stream_batch(t0, t0) == []
    assert set(rows[0]) == {"tx_id", "time_s", "day", "hour", "minute", "amount", "risk", "alert", "true_label"}


def test_time_parts():
    from backend.inference import time_parts

    assert time_parts(97200 + 125) == (2, 3, 2)
    assert time_parts(0) == (1, 0, 0)
