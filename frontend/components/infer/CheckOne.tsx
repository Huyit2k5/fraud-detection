import type { SampleKind } from "@/lib/api";

const CHOICES: { kind: SampleKind; label: string }[] = [
  { kind: "random", label: "🎲 Ngẫu nhiên" },
  { kind: "fraud", label: "Lấy 1 ca gian lận" },
  { kind: "normal", label: "Lấy 1 ca bình thường" },
];

export function CheckOne({ onPick, loading }: { onPick: (k: SampleKind) => void; loading: boolean }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[13px] text-muted">
        Chọn một giao dịch thật trong tập kiểm tra. Kết quả thật được ẩn cho
        đến khi bạn bấm “Xem kết quả thật”.
      </p>
      {CHOICES.map((c) => (
        <button
          key={c.kind}
          disabled={loading}
          onClick={() => onPick(c.kind)}
          className="rounded-lg border border-line bg-panel-2 px-3 py-2 text-left text-sm hover:border-action disabled:opacity-50"
        >
          {c.label}
        </button>
      ))}
    </div>
  );
}
