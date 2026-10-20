import { describe, expect, it } from "vitest";
import { eur, fmtDate, hhmm } from "./hooks";

describe("formatters", () => {
  it("never invents a price", () => {
    expect(eur(null)).toBe("непознато");
    expect(eur("")).toBe("непознато");
    expect(eur("15")).toBe("15.00 €");
  });

  it("formats time blocks", () => {
    expect(hhmm("09:05:48")).toBe("09:05");
  });

  it("formats dates in Macedonian without browser locale", () => {
    expect(fmtDate("2026-10-27")).toBe("27 окт 2026");
    expect(fmtDate(null)).toBe("нема");
  });
});
