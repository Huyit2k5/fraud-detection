import type { StreamStats } from "@/lib/api";
import { fmtInt, fmtMoney } from "@/lib/format";

export function Counters({ stats }: { stats: StreamStats }) {
  const items = [
    { label: "đã kiểm tra", value: stats.checked, tone: "text-text" },
    { label: "bắt đúng", value: stats.caught, tone: "text-safe" },
    { label: "báo nhầm", value: stats.false_alarms, tone: "text-warn" },
    { label: "bỏ sót", value: stats.missed, tone: "text-risk" },
  ];
  return (
    <div>
      <dl className="grid grid-cols-4 gap-1.5">
        {items.map((it) => (
          <div key={it.label} className="rounded-lg bg-panel-2 px-2.5 py-2">
            <dd className={`text-lg leading-tight font-extrabold ${it.tone}`}>{fmtInt(it.value)}</dd>
            <dt className="text-[11px] text-muted">{it.label}</dt>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-xs text-muted">
        Đã chặn kịp <b className="text-safe">{fmtMoney(stats.blocked_amount)}</b> tiền gian lận
      </p>
    </div>
  );
}
