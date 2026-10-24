"""Chấm điểm và giải thích (SHAP chính xác) mô hình đã xuất từ Spark, chỉ dùng numpy + shap."""

from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np
import shap


@dataclass
class Explanation:
    base_value: float
    contributions: np.ndarray  # theo thứ tự `features`
    space: Literal["probability", "log-odds"]


class ModelRuntime(Protocol):
    features: list[str]

    def predict_proba(self, X: np.ndarray) -> np.ndarray: ...

    def explain(self, x: np.ndarray) -> Explanation: ...


class RFRuntime:
    """Random Forest của Spark: xác suất = trung bình P(gian lận) tại lá của các cây."""

    def __init__(self, trees: list[dict], features: list[str]):
        self.features = features
        self._trees = [{k: np.asarray(v) for k, v in t.items()} for t in trees]
        n = len(trees)
        # Mô hình dạng "custom tree" của shap: tổng đầu ra các cây = trung bình nên chia values cho n.
        # shap và Spark cùng đi trái khi x <= threshold (đã kiểm chứng: test_rf_known_tree).
        shap_trees = []
        for t in self._trees:
            shap_trees.append({
                "children_left": t["children_left"], "children_right": t["children_right"],
                "children_default": t["children_left"], "features": t["features"],
                "thresholds": t["thresholds"], "values": (t["values"] / n).reshape(-1, 1),
                "node_sample_weight": t["node_sample_weight"],
            })
        self._explainer = shap.TreeExplainer({"trees": shap_trees}, feature_perturbation="tree_path_dependent")

    @staticmethod
    def _tree_predict(t: dict, X: np.ndarray) -> np.ndarray:
        node = np.zeros(len(X), dtype=int)
        while True:
            active = np.flatnonzero(t["children_left"][node] != -1)
            if active.size == 0:
                return t["values"][node]
            n = node[active]
            go_left = X[active, t["features"][n]] <= t["thresholds"][n]
            node[active] = np.where(go_left, t["children_left"][n], t["children_right"][n])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return np.mean([self._tree_predict(t, X) for t in self._trees], axis=0)

    def explain(self, x: np.ndarray) -> Explanation:
        values = self._explainer.shap_values(np.asarray(x, dtype=float).reshape(1, -1))
        base = float(np.ravel(self._explainer.expected_value)[0])
        return Explanation(base, np.asarray(values).reshape(-1), "probability")


class LRRuntime:
    """Logistic Regression: SHAP tuyến tính chính xác trong không gian log-odds."""

    def __init__(self, coefficients, intercept, feature_means, features: list[str]):
        self.features = features
        self.coef = np.asarray(coefficients, dtype=float)
        self.intercept = float(intercept)
        self.means = np.asarray(feature_means, dtype=float)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-(np.asarray(X, dtype=float) @ self.coef + self.intercept)))

    def explain(self, x: np.ndarray) -> Explanation:
        x = np.asarray(x, dtype=float)
        return Explanation(self.intercept + float(self.coef @ self.means), self.coef * (x - self.means), "log-odds")
