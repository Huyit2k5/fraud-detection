import numpy as np
import pandas as pd
import pytest

from config import MODEL_FEATURE_COLS


def _random_training_df(spark, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    pdf = pd.DataFrame(rng.normal(size=(n, len(MODEL_FEATURE_COLS))), columns=MODEL_FEATURE_COLS)
    pdf["Class"] = ((pdf["V14"] < -1) | (pdf["Amount_scaled"] > 2)).astype(int)
    pdf["class_weight"] = np.where(pdf["Class"] == 1, 5.0, 1.0)
    from train_models import assemble_features

    return pdf, assemble_features(spark.createDataFrame(pdf))


def _spark_prob(model, df):
    from pyspark.ml.functions import vector_to_array

    rows = model.transform(df).select(vector_to_array("probability")[1].alias("p")).collect()
    return np.array([r["p"] for r in rows])


def _numpy_tree_prob(trees, X):
    out = np.zeros(len(X))
    for t in trees:
        for i, x in enumerate(X):
            node = 0
            while t["children_left"][node] != -1:
                f, thr = t["features"][node], t["thresholds"][node]
                node = t["children_left"][node] if x[f] <= thr else t["children_right"][node]
            out[i] += t["values"][node]
    return out / len(trees)


def test_rf_export_matches_spark(spark):
    from pyspark.ml.classification import RandomForestClassifier

    from export_inference import export_rf

    pdf, df = _random_training_df(spark)
    model = RandomForestClassifier(featuresCol="features", labelCol="Class", weightCol="class_weight",
                                   numTrees=7, maxDepth=4, seed=1).fit(df)
    trees = export_rf(model)

    assert len(trees) == 7
    np.testing.assert_allclose(_numpy_tree_prob(trees, pdf[MODEL_FEATURE_COLS].to_numpy()),
                               _spark_prob(model, df), atol=1e-9)
    root = trees[0]
    assert root["node_sample_weight"][0] == pytest.approx(pdf["class_weight"].sum(), rel=0.5)


def test_lr_export_matches_spark(spark):
    from pyspark.ml.classification import LogisticRegression

    from export_inference import export_lr

    pdf, df = _random_training_df(spark)
    model = LogisticRegression(featuresCol="features", labelCol="Class", weightCol="class_weight",
                               maxIter=50).fit(df)
    exp = export_lr(model, pdf)
    X = pdf[MODEL_FEATURE_COLS].to_numpy()
    prob = 1 / (1 + np.exp(-(X @ np.array(exp["coefficients"]) + exp["intercept"])))

    np.testing.assert_allclose(prob, _spark_prob(model, df), atol=1e-9)
    np.testing.assert_allclose(exp["feature_means"], X.mean(axis=0))


def test_choose_model():
    from export_inference import choose_model

    df = pd.DataFrame({"model": ["Logistic Regression", "Random Forest", "Isolation Forest"],
                       "pr_auc": [0.71, 0.80, 0.12]})
    assert choose_model(df)[0] == "Random Forest"

    df.loc[2, "pr_auc"] = 0.95
    name, note = choose_model(df)
    assert name == "Random Forest" and "Isolation Forest" in note


def test_rates():
    from export_inference import compute_rates

    train = pd.DataFrame({"Amount": [0.5, 0.5, 5, 600], "Class": [1, 0, 0, 1], "Hour": [2, 2, 14, 2]})
    r = compute_rates(train)

    assert r["amount_buckets"][0] == {"label": "<1 €", "lo": 0, "hi": 1, "n": 2, "fraud": 1, "rate": 0.5}
    assert r["amount_buckets"][-1]["hi"] is None
    assert r["hours"][2]["rate"] == pytest.approx(2 / 3)
    assert r["hours"][14] == {"hour": 14, "n": 1, "fraud": 0, "rate": 0.0}
    assert r["hours"][5] == {"hour": 5, "n": 0, "fraud": 0, "rate": 0.0}
    assert len(r["hours"]) == 24
    assert r["overall_rate"] == pytest.approx(0.5)
