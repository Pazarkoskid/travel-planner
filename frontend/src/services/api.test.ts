import { beforeEach, describe, expect, it, vi } from "vitest";

const store = new Map<string, string>();
vi.stubGlobal("localStorage", {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
});

const { api, tokens } = await import("./api");

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("api со стар токен", () => {
  beforeEach(() => store.clear());

  it("по неуспешно освежување го брише токенот и го повторува барањето без најава", async () => {
    tokens.set("stale-access", "stale-refresh");
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh/")) return json(401, { error: { code: "token_not_valid" } });
      const auth = (init?.headers as Record<string, string> | undefined)?.Authorization;
      return auth ? json(401, { error: { code: "token_not_valid" } }) : json(200, [{ id: 1, name: "Охрид" }]);
    });
    vi.stubGlobal("fetch", fetchMock);
    const cities = await api<{ name: string }[]>("/cities/");
    expect(cities[0].name).toBe("Охрид");
    expect(tokens.get()).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("паралелни барања делат едно освежување", async () => {
    tokens.set("old", "good-refresh");
    let refreshCalls = 0;
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh/")) { refreshCalls++; return json(200, { access: "new", refresh: "r2" }); }
      const auth = (init?.headers as Record<string, string>).Authorization;
      return auth === "Bearer new" ? json(200, { ok: true }) : json(401, {});
    }));
    await Promise.all([api("/a/"), api("/b/"), api("/c/")]);
    expect(refreshCalls).toBe(1);
  });
});
