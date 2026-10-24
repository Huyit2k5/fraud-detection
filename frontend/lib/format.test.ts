import { describe, expect, it } from "vitest";

import { fmtClock, fmtInt, fmtMoney, fmtPct, partOfDay } from "./format";

describe("định dạng kiểu Việt Nam", () => {
  it("số tiền có 2 chữ số thập phân và dấu €", () => {
    expect(fmtMoney(529)).toBe("529,00 €");
    expect(fmtMoney(12480.5)).toBe("12.480,50 €");
  });

  it("số nguyên có dấu chấm phân cách hàng nghìn", () => {
    expect(fmtInt(12480)).toBe("12.480");
    expect(fmtInt(7)).toBe("7");
  });

  it("tỉ lệ 0–1 thành phần trăm 2 chữ số thập phân", () => {
    expect(fmtPct(0.0171)).toBe("1,71%");
    expect(fmtPct(0)).toBe("0,00%");
  });

  it("thời điểm theo ngày và giờ:phút", () => {
    expect(fmtClock(2, 3, 2)).toBe("ngày 2, 03:02");
  });

  it("buổi trong ngày cùng mốc với backend", () => {
    expect(partOfDay(3)).toBe("sáng");
    expect(partOfDay(10)).toBe("sáng");
    expect(partOfDay(11)).toBe("chiều");
    expect(partOfDay(17)).toBe("chiều");
    expect(partOfDay(18)).toBe("tối");
    expect(partOfDay(23)).toBe("tối");
  });
});
