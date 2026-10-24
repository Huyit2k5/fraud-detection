// Định dạng số kiểu Việt Nam (dấu chấm hàng nghìn, dấu phẩy thập phân). Tự ghép chuỗi thay vì dùng
// Intl để không bị chèn khoảng trắng không ngắt (NBSP) khác nhau giữa trình duyệt và Node.

export function fmtNumber(x: number, digits = 0): string {
  const [int, frac] = Math.abs(x).toFixed(digits).split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return (x < 0 ? "-" : "") + grouped + (frac ? `,${frac}` : "");
}

export const fmtInt = (x: number) => fmtNumber(Math.round(x));

export const fmtMoney = (x: number) => `${fmtNumber(x, 2)} €`;

/** Tỉ lệ 0–1 → "1,71%". */
export const fmtPct = (rate: number, digits = 2) => `${fmtNumber(rate * 100, digits)}%`;

const pad2 = (n: number) => String(n).padStart(2, "0");

export const fmtClock = (day: number, hour: number, minute: number) =>
  `ngày ${day}, ${pad2(hour)}:${pad2(minute)}`;

export const fmtTime = (hour: number, minute: number) => `${pad2(hour)}:${pad2(minute)}`;

/** Cùng mốc với backend (backend/inference.py): 0–10h sáng, 11–17h chiều, 18–23h tối. */
export function partOfDay(hour: number): "sáng" | "chiều" | "tối" {
  if (hour <= 10) return "sáng";
  if (hour <= 17) return "chiều";
  return "tối";
}
