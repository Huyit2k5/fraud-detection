import type { Reason, TransactionExplanation } from "@/lib/api";
import { fmtNumber } from "@/lib/format";

const ICONS: Record<Reason["key"], string> = { behavior: "🧬", amount: "💶" };

export function ReasonList({ e }: { e: TransactionExplanation }) {
  const max = Math.max(...e.reasons.map((r) => Math.abs(r.contribution)), 1e-9);
  return (
    <section className="rounded-xl border border-line bg-panel p-4">
      <h2 className="mb-3 text-sm font-semibold text-muted">
        {e.alert ? "Vì sao hệ thống nghi ngờ?" : "Vì sao hệ thống cho là an toàn?"}
      </h2>
      <ul className="flex flex-col gap-2">
        {e.reasons.map((r) => (
          <li key={r.key} className="grid grid-cols-[32px_1fr_150px] items-center gap-3 rounded-lg bg-panel-2 px-3 py-2.5">
            <span className="text-center text-xl" aria-hidden>
              {ICONS[r.key]}
            </span>
            <div>
              <p className="text-[14px] leading-snug">{r.title}</p>
              <p className="text-xs text-muted">{r.detail}</p>
            </div>
            <div className="relative h-2.5 rounded-full bg-ink" title={r.direction === "fraud" ? "đẩy về phía gian lận" : "đẩy về phía an toàn"}>
              <i
                className={`absolute inset-y-0 left-0 rounded-full ${r.direction === "fraud" ? "bg-risk" : "bg-safe"}`}
                style={{ width: `${(Math.abs(r.contribution) / max) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-muted">
        Thanh càng dài thì yếu tố đó góp càng nhiều vào kết luận. Đỏ: đẩy về phía gian lận, xanh: đẩy về phía an toàn.
      </p>
      <details className="mt-2 text-xs text-muted">
        <summary className="cursor-pointer">🔧 Chi tiết kỹ thuật</summary>
        <p className="mt-2">
          Đóng góp tính bằng SHAP từ chính mô hình (đơn vị: {e.explain_space === "probability" ? "xác suất" : "log-odds"}),
          giá trị cơ sở {fmtNumber(e.base_value, 4)}.
        </p>
        <table className="mt-1 w-full max-w-md">
          <tbody>
            {e.technical.slice(0, 12).map((t) => (
              <tr key={t.feature} className="border-b border-line/60">
                <td className="py-0.5">{t.feature}</td>
                <td className="py-0.5 text-right">{fmtNumber(t.value, 3)}</td>
                <td className={`py-0.5 text-right ${t.contribution > 0 ? "text-risk-ink" : "text-safe-ink"}`}>
                  {t.contribution > 0 ? "+" : ""}
                  {fmtNumber(t.contribution, 4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}
