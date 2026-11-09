import type { StreamTx } from "@/lib/api";
import { fmtMoney, fmtTime } from "@/lib/format";

type Props = { txs: StreamTx[]; selectedId: number | null; onSelect: (id: number) => void; animate: boolean };

// Mọi dòng đều bấm được để xem giải thích. Hiệu ứng trượt vào chỉ bật khi luồng chạy chậm (chế độ từng giao
// dịch): ở tốc độ ×100 trở lên mỗi 0,1 giây có hàng chục dòng mới, dòng nào cũng luôn ở đầu hiệu ứng.
export function LiveFeed({ txs, selectedId, onSelect, animate }: Props) {
  if (txs.length === 0) {
    return <p className="py-10 text-center text-sm text-muted">Đang chờ giao dịch đầu tiên…</p>;
  }
  return (
    <ul className="flex flex-col gap-1">
      {txs.map((tx) => {
        const selected = tx.tx_id === selectedId;
        const tone = tx.alert
          ? "bg-risk-soft hover:bg-risk-soft-hover outline-risk/40"
          : "bg-row hover:bg-panel-2 outline-transparent";
        return (
          <li key={tx.tx_id} className={animate ? "row-in" : undefined}>
            <button
              onClick={() => onSelect(tx.tx_id)}
              aria-pressed={selected}
              aria-label={`Giao dịch ${fmtMoney(tx.amount)} lúc ${fmtTime(tx.hour, tx.minute)}, ${tx.alert ? "bị chặn" : "được duyệt"}`}
              className={`grid w-full grid-cols-[48px_1fr_92px_56px] items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[13px] ${tone} ${
                selected ? "outline-2 outline-warn" : "outline"
              }`}
            >
              <span className="text-xs text-muted">{fmtTime(tx.hour, tx.minute)}</span>
              <span className="relative h-1.5 rounded-full bg-panel-2">
                <i
                  className={`absolute inset-y-0 left-0 rounded-full ${tx.alert ? "bg-risk" : "bg-safe"}`}
                  style={{ width: `${Math.max(tx.risk, 2)}%` }}
                />
              </span>
              <span className="text-right">{fmtMoney(tx.amount)}</span>
              <span className={`text-right text-xs ${tx.alert ? "font-semibold text-risk-ink" : "text-muted"}`}>
                {tx.alert ? "⚠ chặn" : "✓ duyệt"}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
