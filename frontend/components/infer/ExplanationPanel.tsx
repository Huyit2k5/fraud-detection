"use client";

import { useCallback, useState } from "react";

import type { TransactionExplanation } from "@/lib/api";
import { fmtClock, fmtInt, fmtMoney } from "@/lib/format";

import { NeighborsTable } from "./NeighborsTable";
import { ReasonList } from "./ReasonList";
import { RiskGauge } from "./RiskGauge";
import { WhatIf } from "./WhatIf";

/** Giải thích 1 giao dịch. Component được gắn key = tx_id ở trang cha nên trạng thái (lật nhãn, kết quả
 *  thử thay đổi) tự đặt lại khi chọn giao dịch khác. */
export function ExplanationPanel({ e }: { e: TransactionExplanation }) {
  const [revealed, setRevealed] = useState(false);
  const [whatIf, setWhatIf] = useState<TransactionExplanation | null>(null);
  const onWhatIf = useCallback((r: TransactionExplanation | null) => setWhatIf(r), []);
  const shown = whatIf ?? e;
  const correct = e.alert === (e.true_label === 1);

  return (
    <div className="flex flex-col gap-3">
      <section className="rounded-xl border border-line bg-panel p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">Giao dịch #{fmtInt(e.tx_id)}</h2>
            <p className="text-[13px] text-muted">
              {fmtMoney(e.amount)}, {fmtClock(e.day, e.hour, e.minute)}
            </p>
          </div>
          {revealed ? (
            <p className={`rounded-lg px-3 py-1.5 text-sm ${correct ? "bg-safe-soft text-safe-ink" : "bg-warn-soft text-warn-ink"}`}>
              Thực tế: <b>{e.true_label ? "Gian lận" : "Bình thường"}</b>, mô hình đoán <b>{correct ? "đúng" : "sai"}</b>
            </p>
          ) : (
            <button
              onClick={() => setRevealed(true)}
              className="rounded-lg border border-line bg-panel-2 px-3 py-1.5 text-sm hover:border-action"
            >
              👁 Xem kết quả thật
            </button>
          )}
        </div>
        <div className="mt-4">
          <RiskGauge risk={e.risk} threshold={e.threshold} alert={e.alert} />
        </div>
        <p className="mt-3 rounded-lg border border-warn/40 bg-warn-soft px-3 py-2 text-[13px] text-warn-ink">
          💡 Đề xuất:{" "}
          {e.alert
            ? "tạm giữ giao dịch, gửi mã xác minh hoặc gọi chủ thẻ trước khi duyệt."
            : "duyệt giao dịch."}
        </p>
      </section>

      {whatIf && (
        <p className="text-xs text-action">Đang hiển thị lý do cho giao dịch sau khi thay đổi số tiền/giờ.</p>
      )}
      <ReasonList e={shown} />

      <div className="grid gap-3 lg:grid-cols-2">
        <NeighborsTable neighbors={e.neighbors} fraudCount={e.neighbors_fraud} />
        <WhatIf base={e} onResult={onWhatIf} />
      </div>
    </div>
  );
}
