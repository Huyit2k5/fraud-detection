"""Dịch vụ suy luận cho tab "Suy luận": kết luận + giải thích bằng lời cho người không chuyên,
giao dịch tương tự trong quá khứ, thử "nếu… thì…" và phát lại luồng giao dịch của tập test."""

import math

import numpy as np
from sklearn.neighbors import NearestNeighbors

from backend.bundle import Bundle
from config import AMOUNT_COL, LABEL_COL, PCA_COLS, SECONDS_PER_DAY, TIME_COL

GROUPS = {
    "behavior": PCA_COLS,
    "hour": ["Hour_sin", "Hour_cos"],
    "amount": ["Amount_scaled"],
}
BEHAVIOR_DETAIL = "Tổng hợp từ 28 dấu hiệu đã được ngân hàng mã hóa để bảo mật"
HIGHLIGHT_RATIO = 1.5  # chỉ nói "gấp k lần mức chung" khi tỉ lệ cao hơn rõ rệt


def time_parts(time_s: float) -> tuple[int, int, int]:
    """(ngày thứ mấy, giờ, phút) từ số giây kể từ giao dịch đầu tiên (giả định bắt đầu lúc 0h)."""
    return (int(time_s // SECONDS_PER_DAY) + 1, int(time_s % SECONDS_PER_DAY // 3600), int(time_s % 3600 // 60))


def part_of_day(hour: int) -> str:
    return "sáng" if hour <= 10 else ("chiều" if hour <= 17 else "tối")


def vn_number(x: float, digits: int = 0) -> str:
    s = f"{x:,.{digits}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def vn_pct(rate: float) -> str:
    return f"{vn_number(rate * 100, 2)}%"


class InferenceService:
    def __init__(self, bundle: Bundle):
        self.bundle = bundle
        self.features = bundle.meta["features"]
        self.threshold = float(bundle.meta["threshold"])
        self.test = bundle.test.set_index("tx_id", drop=False)
        X_test = self.test[self.features].to_numpy()
        self.test_scores = bundle.runtime.predict_proba(X_test)
        self._score_by_id = dict(zip(self.test["tx_id"].to_numpy(), self.test_scores))
        self.train = bundle.train.reset_index(drop=True)
        self._nn = NearestNeighbors(n_neighbors=5).fit(self.train[self.features].to_numpy())
        self._overall = bundle.rates["overall_rate"]
        self._hour_rate = {h["hour"]: h["rate"] for h in bundle.rates["hours"]}
        self._times = self.test[TIME_COL].to_numpy()  # test đã sắp theo Time khi xuất gói

    # ------------------------------------------------------------------ chọn giao dịch
    def sample(self, kind: str, rng: np.random.Generator | None = None) -> int:
        rng = rng or np.random.default_rng()
        pool = self.test
        if kind == "fraud":
            pool = pool[pool[LABEL_COL] == 1]
        elif kind == "normal":
            pool = pool[pool[LABEL_COL] == 0]
        return int(pool["tx_id"].iloc[rng.integers(len(pool))])

    def test_time_range(self) -> tuple[float, float]:
        return float(self._times[0]), float(self._times[-1])

    # ------------------------------------------------------------------ giải thích
    def explain_tx(self, tx_id: int) -> dict:
        row = self.test.loc[tx_id]  # KeyError nếu không có
        return self._explain(row[self.features].to_numpy(dtype=float), row, float(row[AMOUNT_COL]),
                             float(row[TIME_COL]), what_if=False)

    def what_if(self, tx_id: int, amount: float, hour: int) -> dict:
        row = self.test.loc[tx_id]
        x = row[self.features].to_numpy(dtype=float).copy()
        time_s = float(row[TIME_COL])
        frac = (time_s % 3600) / 3600  # giữ nguyên phút của giao dịch gốc
        h = hour + frac
        x[self.features.index("Hour_sin")] = math.sin(2 * math.pi * h / 24)
        x[self.features.index("Hour_cos")] = math.cos(2 * math.pi * h / 24)
        x[self.features.index("Amount_scaled")] = (amount - self.bundle.meta["amount_mean"]) / self.bundle.meta["amount_std"]
        day = int(time_s // SECONDS_PER_DAY)
        new_time = day * SECONDS_PER_DAY + h * 3600
        return self._explain(x, row, float(amount), new_time, what_if=True)

    def _explain(self, x: np.ndarray, row, amount: float, time_s: float, what_if: bool) -> dict:
        prob = float(self.bundle.runtime.predict_proba(x[None])[0])
        exp = self.bundle.runtime.explain(x)
        day, hour, minute = time_parts(time_s)
        contrib = dict(zip(self.features, exp.contributions))
        reasons = [self._reason(key, sum(contrib[f] for f in cols), amount, hour)
                   for key, cols in GROUPS.items()]
        reasons.sort(key=lambda r: abs(r["contribution"]), reverse=True)
        technical = sorted(
            ({"feature": f, "value": float(v), "contribution": float(contrib[f])} for f, v in zip(self.features, x)),
            key=lambda t: abs(t["contribution"]), reverse=True)
        neighbors = self._neighbors(x)
        return {
            "tx_id": int(row["tx_id"]), "time_s": float(time_s), "day": day, "hour": hour, "minute": minute,
            "amount": amount, "probability": prob, "risk": round(prob * 100), "threshold": self.threshold,
            "alert": prob >= self.threshold, "true_label": int(row[LABEL_COL]), "what_if": what_if,
            "explain_space": exp.space, "base_value": float(exp.base_value),
            "reasons": reasons, "technical": technical,
            "neighbors": neighbors, "neighbors_fraud": sum(n["label"] for n in neighbors),
        }

    def _reason(self, key: str, contribution: float, amount: float, hour: int) -> dict:
        direction = "fraud" if contribution > 0 else "safe"
        if key == "behavior":
            title = ("Hành vi thẻ rất khác thường so với giao dịch bình thường" if direction == "fraud"
                     else "Hành vi thẻ giống các giao dịch bình thường")
            detail = BEHAVIOR_DETAIL
        elif key == "hour":
            rate = self._hour_rate.get(hour, 0.0)
            title = f"Giao dịch lúc {hour} giờ {part_of_day(hour)}"
            detail = f"Khung giờ này có tỉ lệ gian lận {vn_pct(rate)}"
            if direction == "fraud" and rate >= HIGHLIGHT_RATIO * self._overall:
                detail += f" — gấp {vn_number(rate / self._overall, 1)} lần mức chung"
            elif direction == "safe":
                detail += ", thấp hơn hoặc gần mức chung" if rate < HIGHLIGHT_RATIO * self._overall else ""
        else:
            bucket = self._amount_bucket(amount)
            title = f"Số tiền {vn_number(amount, 2)} €"
            detail = f"Khoảng {bucket['label']} có tỉ lệ gian lận {vn_pct(bucket['rate'])}"
            if bucket["rate"] >= HIGHLIGHT_RATIO * self._overall:
                detail += f" — gấp {vn_number(bucket['rate'] / self._overall, 1)} lần mức chung"
        return {"key": key, "contribution": float(contribution), "direction": direction,
                "title": title, "detail": detail}

    def _amount_bucket(self, amount: float) -> dict:
        for b in self.bundle.rates["amount_buckets"]:
            if amount >= b["lo"] and (b["hi"] is None or amount < b["hi"]):
                return b
        return self.bundle.rates["amount_buckets"][-1]

    def _neighbors(self, x: np.ndarray) -> list[dict]:
        _, idx = self._nn.kneighbors(x[None])
        out = []
        for i in idx[0]:
            r = self.train.iloc[int(i)]
            _, hour, minute = time_parts(float(r[TIME_COL]))
            out.append({"tx_id": int(r["tx_id"]), "amount": float(r[AMOUNT_COL]), "hour": hour,
                        "minute": minute, "label": int(r[LABEL_COL])})
        return out

    # ------------------------------------------------------------------ phát lại luồng
    def stream_batch(self, start_time: float, end_time: float) -> list[dict]:
        lo, hi = np.searchsorted(self._times, [start_time, end_time], side="left")
        return self.stream_slice(int(lo), int(hi))

    def index_at(self, time_s: float) -> int:
        """Vị trí (theo thứ tự thời gian) của giao dịch đầu tiên có Time >= time_s."""
        return int(np.searchsorted(self._times, time_s, side="left"))

    def time_at(self, index: int) -> float:
        return float(self._times[index])

    def __len__(self) -> int:
        return len(self._times)

    def stream_slice(self, lo: int, hi: int) -> list[dict]:
        """Các giao dịch test từ vị trí lo đến trước hi (theo thứ tự thời gian)."""
        rows = self.test.iloc[lo:hi]
        out = []
        for tx_id, t, amount, label in zip(rows["tx_id"], rows[TIME_COL], rows[AMOUNT_COL], rows[LABEL_COL]):
            prob = self._score_by_id[tx_id]
            day, hour, minute = time_parts(float(t))
            out.append({"tx_id": int(tx_id), "time_s": float(t), "day": day, "hour": hour, "minute": minute,
                        "amount": float(amount), "risk": round(float(prob) * 100),
                        "alert": bool(prob >= self.threshold), "true_label": int(label)})
        return out
