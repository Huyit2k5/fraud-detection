import json

import numpy as np
import pytest

from config import MODEL_FEATURE_COLS


def test_rf_shap_additivity(fake_bundle_dir):
    from backend.bundle import load_bundle

    b = load_bundle(fake_bundle_dir)
    X = b.test[MODEL_FEATURE_COLS].to_numpy()
    probs = b.runtime.predict_proba(X)
    for x, p in zip(X, probs):
        e = b.runtime.explain(x)
        assert e.space == "probability"
        assert e.base_value + e.contributions.sum() == pytest.approx(p, abs=1e-6)


def test_rf_known_tree():
    from backend.runtime import RFRuntime

    i14 = MODEL_FEATURE_COLS.index("V14")
    tree = {"children_left": [1, -1, -1], "children_right": [2, -1, -1], "features": [i14, -1, -1],
            "thresholds": [-1.0, 0.0, 0.0], "values": [0.5, 0.9, 0.1], "node_sample_weight": [10.0, 5.0, 5.0]}
    rt = RFRuntime([tree], MODEL_FEATURE_COLS)
    x_eq, x_right = np.zeros(31), np.zeros(31)
    x_eq[i14] = -1.0  # đúng bằng ngưỡng -> đi trái (quy ước Spark: x <= threshold)

    assert rt.predict_proba(np.stack([x_eq, x_right])).tolist() == pytest.approx([0.9, 0.1])
    e = rt.explain(x_eq)
    others = np.delete(e.contributions, i14)
    assert np.allclose(others, 0.0)
    assert e.contributions[i14] == pytest.approx(0.4)  # 0,9 - giá trị cơ sở 0,5


def test_lr_additivity():
    from backend.runtime import LRRuntime

    rng = np.random.default_rng(0)
    coef, means = rng.normal(size=31), rng.normal(size=31)
    rt = LRRuntime(coef.tolist(), -2.0, means.tolist(), MODEL_FEATURE_COLS)
    x = rng.normal(size=31)
    p = rt.predict_proba(x[None])[0]
    e = rt.explain(x)

    assert e.space == "log-odds"
    assert e.base_value + e.contributions.sum() == pytest.approx(np.log(p / (1 - p)), abs=1e-9)


def test_load_bundle_missing(tmp_path):
    from backend.bundle import BundleError, load_bundle

    with pytest.raises(BundleError, match="Chưa có mô hình"):
        load_bundle(tmp_path)


def test_load_bundle_old_features(fake_bundle_dir):
    from backend.bundle import BundleError, load_bundle

    meta = json.loads((fake_bundle_dir / "model.json").read_text(encoding="utf-8"))
    meta["features"][0] = "Time_scaled"
    (fake_bundle_dir / "model.json").write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(BundleError, match="bộ đặc trưng cũ"):
        load_bundle(fake_bundle_dir)
