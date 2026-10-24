// Kiểu dữ liệu và lời gọi tới backend FastAPI (backend/app.py). Khóa JSON khớp đúng backend.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Status = {
  backend: "ok";
  data_backend: string;
  spark_cores: number;
  hdfs: { ok: boolean };
  model: { name: string; threshold: number; pr_auc: number; selection_note: string } | null;
  model_error: string | null;
};

export type Reason = {
  key: "behavior" | "hour" | "amount";
  contribution: number;
  direction: "fraud" | "safe";
  title: string;
  detail: string;
};

export type Neighbor = { tx_id: number; amount: number; hour: number; minute: number; label: number };

export type TransactionExplanation = {
  tx_id: number;
  time_s: number;
  day: number;
  hour: number;
  minute: number;
  amount: number;
  probability: number;
  risk: number;
  threshold: number;
  alert: boolean;
  true_label: number;
  what_if: boolean;
  explain_space: "probability" | "log-odds";
  base_value: number;
  reasons: Reason[];
  technical: { feature: string; value: number; contribution: number }[];
  neighbors: Neighbor[];
  neighbors_fraud: number;
};

export type StreamTx = {
  tx_id: number;
  time_s: number;
  day: number;
  hour: number;
  minute: number;
  amount: number;
  risk: number;
  alert: boolean;
  true_label: number;
};

export type StreamStats = {
  checked: number;
  caught: number;
  false_alarms: number;
  missed: number;
  blocked_amount: number;
};

export type StreamMessage =
  | { type: "batch"; txs: StreamTx[]; stats: StreamStats; clock: number; speed: number; paused: boolean; step: boolean }
  | { type: "end"; stats: StreamStats }
  | { type: "error"; detail: string };

export type SampleKind = "random" | "fraud" | "normal";

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new ApiError(0, "Không kết nối được tới backend. Hãy chạy: python -m uvicorn backend.app:app --port 8000");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `Lỗi ${res.status}`;
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const getStatus = () => request<Status>("/api/status");
export const reloadModel = () => request<Status>("/api/reload", { method: "POST" });
export const getSample = (kind: SampleKind) => request<TransactionExplanation>(`/api/infer/sample?kind=${kind}`);
export const getTx = (id: number) => request<TransactionExplanation>(`/api/infer/tx/${id}`);
export const postWhatIf = (body: { tx_id: number; amount: number; hour: number }) =>
  request<TransactionExplanation>("/api/infer/what-if", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const openStream = () => new WebSocket(`${API_URL.replace(/^http/, "ws")}/api/infer/stream`);
