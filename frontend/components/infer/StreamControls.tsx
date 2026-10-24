const SPEEDS = [10, 100, 1000];

type Props = {
  paused: boolean;
  speed: number;
  ended: boolean;
  stepMode: boolean;
  onPause: () => void;
  onResume: () => void;
  onSpeed: (v: number) => void;
  onRestart: () => void;
  onStepMode: () => void;
  onStep: () => void;
};

const primary = "rounded-lg bg-action px-3 py-1.5 text-sm font-semibold text-ink";

export function StreamControls(p: Props) {
  const speedBtn = (active: boolean) =>
    `rounded-md px-2.5 py-1 text-xs ${active ? "bg-action font-semibold text-ink" : "text-muted hover:text-text"}`;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        {p.ended ? (
          <button onClick={p.onRestart} className={primary}>▶ Phát lại từ đầu</button>
        ) : p.stepMode ? (
          <button onClick={p.onStep} className={primary}>⏭ Giao dịch tiếp theo</button>
        ) : p.paused ? (
          <button onClick={p.onResume} className={primary}>▶ Tiếp tục</button>
        ) : (
          <button onClick={p.onPause} className={primary}>⏸ Tạm dừng</button>
        )}
        <div role="group" aria-label="Tốc độ phát lại" className="inline-flex gap-0.5 rounded-lg bg-panel-2 p-0.5">
          <button onClick={p.onStepMode} aria-pressed={p.stepMode} className={speedBtn(p.stepMode)}>
            Từng giao dịch
          </button>
          {SPEEDS.map((s) => (
            <button
              key={s}
              onClick={() => p.onSpeed(s)}
              aria-pressed={!p.stepMode && p.speed === s}
              className={speedBtn(!p.stepMode && p.speed === s)}
            >
              ×{s}
            </button>
          ))}
        </div>
      </div>
      {!p.ended && (
        <button
          onClick={p.onRestart}
          className="self-start text-xs text-muted underline-offset-2 hover:text-text hover:underline"
        >
          Chơi lại từ đầu
        </button>
      )}
    </div>
  );
}
