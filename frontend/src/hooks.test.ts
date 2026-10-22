import { describe, expect, it, vi } from "vitest";

// Јазикот се одредува при вчитување на модулот → за секој јазик свежо вчитување.
async function load(lang: "mk" | "en") {
  vi.resetModules();
  vi.stubGlobal("localStorage", { getItem: (k: string) => (k === "tpm_lang" ? lang : null), setItem: () => {}, removeItem: () => {} });
  const hooks = await import("./hooks");
  const i18n = await import("./i18n");
  return { ...hooks, ...i18n };
}

describe("formatters (mk)", () => {
  it("never invents a price", async () => {
    const { eur } = await load("mk");
    expect(eur(null)).toBe("непознато");
    expect(eur("")).toBe("непознато");
    expect(eur("15")).toBe("15.00 €");
  });

  it("formats time blocks", async () => {
    const { hhmm } = await load("mk");
    expect(hhmm("09:05:48")).toBe("09:05");
  });

  it("formats dates in Macedonian without browser locale", async () => {
    const { fmtDate } = await load("mk");
    expect(fmtDate("2026-10-27")).toBe("27 окт 2026");
    expect(fmtDate(null)).toBe("нема");
  });
});

describe("i18n (en)", () => {
  it("translates UI text, dates and interpolates values", async () => {
    const { t, fmtDate, eur } = await load("en");
    expect(t("Места")).toBe("Places");
    expect(t("{0} гости", { 0: 3 })).toBe("3 guests");
    expect(t("Текст што го нема во речникот")).toBe("Текст што го нема во речникот");
    expect(fmtDate("2026-10-27")).toBe("27 Oct 2026");
    expect(eur(null)).toBe("unknown");
  });
});
