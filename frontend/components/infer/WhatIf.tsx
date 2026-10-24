"use client";

import { useEffect, useState } from "react";

import { postWhatIf, type TransactionExplanation } from "@/lib/api";
import { fmtMoney, partOfDay } from "@/lib/format";

const DEBOUNCE_MS = 150;
const SLIDER_MAX = 2000;

type Props = { base: TransactionExplanation; onResult: (e: TransactionExplanation | null) => void };

function verdictChange(before: boolean, after: boolean) {
  if (before && after) return { text: "vẫn nghi gian lận", tone: "text-risk" };
  if (before && !after) return { text: "chuyển thành an toàn", tone: "text-safe" };
  if (!before && after) return { text: "chuyển thành nghi gian lận", tone: "text-risk" };
  return { text: "vẫn an toàn", tone: "text-safe" };
}

export function WhatIf({ base, onResult }: Props) {
  const [amount, setAmount] = useState(base.amount);
  const [hour, setHour] = useState(base.hour);
  const [result, setResult] = useState<TransactionExplanation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const changed = amount !== base.amount || hour !== base.hour;

  useEffect(() => {
    if (!changed) {
      onResult(null); // kéo về đúng giá trị gốc -> hiển thị lại giải thích gốc
      return;
    }
    const id = setTimeout(() => {
      postWhatIf({ tx_id: base.tx_id, amount, hour })
        .then((r) => (setResult(r), setError(null), onResult(r)))
        .catch((e: Error) => setError(e.message));
    }, DEBOUNCE_MS);
    return () => clearTimeout(id);
  }, [amount, hour, changed, base.tx_id, onResult]);

  const change = result ? verdictChange(base.alert, result.alert) : null;
  return (
    <section className="rounded-xl border border-line bg-panel p-4">
      <h2 className="mb-1 text-sm font-semibold text-muted">Thử thay đổi giao dịch</h2>
      <p className="text-xs text-muted">Nếu giao dịch này khác đi một chút thì sao?</p>
      <label className="mt-3 block text-[13px]">
        <span className="flex justify-between">
          <span>Số tiền</span>
          <b>{fmtMoney(amount)}</b>
        </span>
        <input
          type="range"
          min={0}
          max={Math.max(SLIDER_MAX, Math.ceil(base.amount))}
          step={1}
          value={amount}
          onChange={(ev) => setAmount(Number(ev.target.value))}
          className="w-full accent-action"
        />
      </label>
      <label className="mt-2 block text-[13px]">
        <span className="flex justify-between">
          <span>Giờ giao dịch</span>
          <b>{hour} giờ {partOfDay(hour)}</b>
        </span>
        <input
          type="range"
          min={0}
          max={23}
          step={1}
          value={hour}
          onChange={(ev) => setHour(Number(ev.target.value))}
          className="w-full accent-action"
        />
      </label>
      {changed && result && change && (
        <p className="mt-3 text-sm">
          Mức rủi ro mới: <b className={change.tone}>{result.risk} / 100</b> →{" "}
          <span className={change.tone}>{change.text}</span>
        </p>
      )}
      {error && <p className="mt-3 text-sm text-warn">{error}</p>}
      <p className="mt-2 text-xs text-muted">Mô hình chấm lại ngay khi kéo, các dấu hiệu mã hóa giữ nguyên.</p>
    </section>
  );
}
