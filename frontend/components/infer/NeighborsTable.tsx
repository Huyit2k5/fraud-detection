import type { Neighbor } from "@/lib/api";
import { fmtMoney, fmtTime } from "@/lib/format";

export function NeighborsTable({ neighbors, fraudCount }: { neighbors: Neighbor[]; fraudCount: number }) {
  return (
    <section className="rounded-xl border border-line bg-panel p-4">
      <h2 className="mb-2 text-sm font-semibold text-muted">Những vụ giống nhất trong quá khứ</h2>
      <table className="w-full text-[13px]">
        <thead>
          <tr className="text-left text-xs text-muted">
            <th className="pb-1 font-medium">Số tiền</th>
            <th className="pb-1 font-medium">Lúc</th>
            <th className="pb-1 font-medium">Kết quả thật</th>
          </tr>
        </thead>
        <tbody>
          {neighbors.map((n) => (
            <tr key={n.tx_id} className="border-t border-line/60">
              <td className="py-1">{fmtMoney(n.amount)}</td>
              <td className="py-1">{fmtTime(n.hour, n.minute)}</td>
              <td className={`py-1 ${n.label ? "text-risk-ink" : "text-safe-ink"}`}>{n.label ? "Gian lận" : "Bình thường"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-sm">
        <b>{fraudCount} / {neighbors.length}</b> vụ giống nhất từng là gian lận
      </p>
    </section>
  );
}
