"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { getStatus, type Status } from "@/lib/api";
import { fmtNumber } from "@/lib/format";

import { ThemeToggle } from "./ThemeToggle";

const TABS = [
  { href: "/etl", label: "① ETL" },
  { href: "/train", label: "② Huấn luyện & Đánh giá" },
  { href: "/infer", label: "③ Suy luận" },
];

function Dot({ ok }: { ok: boolean }) {
  return <span aria-hidden className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-safe" : "bg-risk"}`} />;
}

export function Header() {
  const pathname = usePathname();
  const [status, setStatus] = useState<Status | null>(null);
  const [online, setOnline] = useState(true);

  useEffect(() => {
    let alive = true;
    const poll = () =>
      getStatus()
        .then((s) => alive && (setStatus(s), setOnline(true)))
        .catch(() => alive && setOnline(false));
    poll();
    const id = setInterval(poll, 10_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-line bg-panel px-5 py-3">
      <span className="text-[15px] font-bold tracking-tight">🛡️ Fraud Detection</span>
      <nav className="flex gap-1" aria-label="Các tab">
        {TABS.map((t) => {
          const active = pathname.startsWith(t.href);
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={active ? "page" : undefined}
              className={`rounded-lg px-3.5 py-1.5 text-sm transition-colors ${
                active ? "bg-panel-2 text-text" : "text-muted hover:text-text"
              }`}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>
      <div className="ml-auto flex flex-wrap items-center gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <Dot ok={online} /> {online ? "Backend đang chạy" : "Mất kết nối backend"}
        </span>
        {status && (
          <>
            <span>Dữ liệu: <b className="font-semibold text-text">{status.data_backend}</b></span>
            <span>Spark: <b className="font-semibold text-text">{status.spark_cores} luồng</b></span>
            {status.model ? (
              <span>
                Mô hình: <b className="font-semibold text-text">{status.model.name}</b>, ngưỡng cảnh báo{" "}
                <b className="font-semibold text-text">{fmtNumber(status.model.threshold * 100)}</b>/100
              </span>
            ) : (
              <span className="text-warn">Chưa có mô hình</span>
            )}
          </>
        )}
        <ThemeToggle />
      </div>
    </header>
  );
}
