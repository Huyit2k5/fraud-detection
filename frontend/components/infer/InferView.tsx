"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useStream } from "@/hooks/useStream";
import { ApiError, getSample, getStatus, getTx, type SampleKind, type TransactionExplanation } from "@/lib/api";
import { fmtClock } from "@/lib/format";

import { CheckOne } from "./CheckOne";
import { Counters } from "./Counters";
import { ExplanationPanel } from "./ExplanationPanel";
import { LiveFeed } from "./LiveFeed";
import { StreamControls } from "./StreamControls";

type Mode = "live" | "check";

function clockParts(t: number) {
  return { day: Math.floor(t / 86400) + 1, hour: Math.floor((t % 86400) / 3600), minute: Math.floor((t % 3600) / 60) };
}

export function InferView() {
  const [mode, setMode] = useState<Mode>("live");
  const [modelError, setModelError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [explanation, setExplanation] = useState<TransactionExplanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStatus()
      .then((s) => (s.model ? setReady(true) : setModelError(s.model_error ?? "Chưa có mô hình.")))
      .catch((e: Error) => setModelError(e.message));
  }, []);

  // Chế độ từng giao dịch: luồng dừng, mỗi lần bấm "Giao dịch tiếp theo" đi thêm 1 giao dịch và tự mở phần
  // giải thích của giao dịch đó.
  const [stepMode, setStepMode] = useState(false);
  const [filter, setFilter] = useState<"all" | "alerts">("all");
  const stream = useStream(ready && mode === "live", (tx) => setSelectedId(tx.tx_id));

  const onLoadError = useCallback(
    (e: ApiError) => (e.status === 503 ? setModelError(e.detail) : setError(e.message)),
    [],
  );

  // Kiểm tra 1 giao dịch: tải theo thao tác của người dùng.
  const pick = useCallback(
    (kind: SampleKind) => {
      setLoading(true);
      getSample(kind)
        .then((e) => (setExplanation(e), setSelectedId(e.tx_id), setError(null)))
        .catch(onLoadError)
        .finally(() => setLoading(false));
    },
    [onLoadError],
  );

  // Giám sát trực tiếp: hiển thị giao dịch được bấm chọn, hoặc tự chọn giao dịch bị chặn đầu tiên
  // xuất hiện (khóa lại bằng setSelectedId khi tải xong để không nhảy sang giao dịch mới hơn).
  const firstAlert = stream.txs.findLast((t) => t.alert)?.tx_id;
  const liveId = mode === "live" ? (selectedId ?? firstAlert ?? null) : null;
  useEffect(() => {
    if (liveId === null) return;
    let alive = true;
    getTx(liveId)
      .then((e) => alive && (setExplanation(e), setSelectedId(e.tx_id), setError(null)))
      .catch((e: ApiError) => alive && onLoadError(e));
    return () => {
      alive = false;
    };
  }, [liveId, onLoadError]);

  const switchMode = (m: Mode) => {
    setMode(m);
    setSelectedId(null);
    setExplanation(null);
    if (m === "check") pick("random");
  };

  if (modelError) {
    return (
      <section className="mx-auto mt-16 max-w-xl rounded-xl border border-line bg-panel p-6">
        <h1 className="text-lg font-semibold">Chưa có mô hình để suy luận</h1>
        <p className="mt-2 text-sm text-muted">{modelError}</p>
        <Link href="/train" className="mt-4 inline-block rounded-lg bg-action px-3 py-1.5 text-sm font-semibold text-ink">
          Sang tab Huấn luyện
        </Link>
      </section>
    );
  }

  const now = clockParts(stream.clock);
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <div role="tablist" aria-label="Chế độ" className="inline-flex gap-0.5 rounded-lg bg-panel-2 p-0.5">
          {(
            [
              ["live", "📡 Giám sát trực tiếp"],
              ["check", "🔍 Kiểm tra 1 giao dịch"],
            ] as const
          ).map(([m, label]) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              onClick={() => switchMode(m)}
              className={`rounded-md px-3 py-1.5 text-sm ${mode === m ? "bg-action font-semibold text-ink" : "text-muted hover:text-text"}`}
            >
              {label}
            </button>
          ))}
        </div>
        {mode === "live" && stream.clock > 0 && (
          <span className="text-xs text-muted">
            Đang phát lại giao dịch {fmtClock(now.day, now.hour, now.minute)} của tập kiểm tra (mô hình chưa từng thấy)
          </span>
        )}
      </div>

      <div className="mt-3 grid gap-4 lg:grid-cols-[400px_1fr]">
        <aside className="rounded-xl border border-line bg-panel p-4">
          {mode === "live" ? (
            <div className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold text-muted">Giao dịch đang đến</h2>
              <Counters stats={stream.stats} />
              <StreamControls
                paused={stream.paused}
                speed={stream.speed}
                ended={stream.ended}
                stepMode={stepMode}
                onPause={stream.pause}
                onResume={stream.resume}
                onSpeed={(v) => (setStepMode(false), stream.setSpeed(v), stream.resume())}
                onRestart={stream.restart}
                onStepMode={() => (setStepMode(true), stream.pause())}
                onStep={stream.step}
              />
              {stream.error && <p className="text-sm text-warn">{stream.error}</p>}
              {!stream.connected && !stream.ended && !stream.error && (
                <p className="text-xs text-warn">Đang kết nối tới backend…</p>
              )}
              <div role="group" aria-label="Lọc giao dịch" className="inline-flex gap-0.5 self-start rounded-lg bg-panel-2 p-0.5">
                {(
                  [
                    ["all", "Tất cả"],
                    ["alerts", `Chỉ nghi gian lận (${stream.alerts.length})`],
                  ] as const
                ).map(([f, label]) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    aria-pressed={filter === f}
                    className={`rounded-md px-2.5 py-1 text-xs ${filter === f ? (f === "alerts" ? "bg-risk font-semibold text-white" : "bg-action font-semibold text-ink") : "text-muted hover:text-text"}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-muted">Bấm vào một giao dịch để xem vì sao hệ thống duyệt hoặc chặn.</p>
              <LiveFeed
                txs={filter === "alerts" ? stream.alerts : stream.txs}
                selectedId={selectedId}
                onSelect={setSelectedId}
                animate={stepMode || filter === "alerts"}
              />
            </div>
          ) : (
            <CheckOne onPick={pick} loading={loading} />
          )}
        </aside>

        <div>
          {error && <p className="mb-3 rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn-ink">{error}</p>}
          {explanation ? (
            <ExplanationPanel key={explanation.tx_id} e={explanation} />
          ) : (
            <p className="mt-10 text-center text-sm text-muted">
              {mode === "live" ? "Đang chờ giao dịch đáng ngờ đầu tiên…" : "Đang tải giao dịch…"}
            </p>
          )}
        </div>
      </div>

      <p className="mt-6 text-xs text-muted">
        Giờ được tính từ cột Time, giả định giao dịch đầu tiên của bộ dữ liệu diễn ra lúc 0h.
      </p>
    </div>
  );
}
