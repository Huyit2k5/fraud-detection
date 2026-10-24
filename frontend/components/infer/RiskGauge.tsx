export function RiskGauge({ risk, threshold, alert }: { risk: number; threshold: number; alert: boolean }) {
  const cut = Math.round(threshold * 100);
  return (
    <div className="flex flex-wrap items-center gap-5">
      <div
        className={`rounded-xl border px-4 py-2 text-2xl font-black ${
          alert ? "border-risk bg-risk-soft text-risk-ink" : "border-safe bg-safe-soft text-safe-ink"
        }`}
      >
        {alert ? "⚠ NGHI GIAN LẬN" : "✓ AN TOÀN"}
      </div>
      <div className="min-w-60 flex-1">
        <p className="text-sm">
          Mức rủi ro: <b className={alert ? "text-risk" : "text-safe"}>{risk} / 100</b>{" "}
          <span className="text-muted">(cảnh báo từ mức {cut})</span>
        </p>
        <div className="relative my-2 h-3.5 rounded-full bg-gradient-to-r from-safe via-warn to-risk">
          <span className="absolute -top-1 h-5.5 w-0.5 bg-ink" style={{ left: `${cut}%` }} aria-hidden />
          <span
            className="absolute -top-1.5 h-6.5 w-1 -translate-x-1/2 rounded bg-white shadow ring-1 ring-black/40"
            style={{ left: `${risk}%` }}
            aria-hidden
          />
        </div>
        <div className="flex justify-between text-[11px] text-muted">
          <span>an toàn</span>
          <span>cần xem xét</span>
          <span>rủi ro cao</span>
        </div>
      </div>
    </div>
  );
}
