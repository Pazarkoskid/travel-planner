import { lang, t } from "../i18n";

const API_ORIGIN = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");
const BASE = `${API_ORIGIN}/api/v1`;
const ACCESS = "tpm_access";
const REFRESH = "tpm_refresh";

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;
  constructor(status: number, code: string, message: string, details: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export const tokens = {
  get: () => localStorage.getItem(ACCESS),
  set: (access: string, refresh?: string) => {
    localStorage.setItem(ACCESS, access);
    if (refresh) localStorage.setItem(REFRESH, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
};

let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const r = localStorage.getItem(REFRESH);
  if (!r) return false;
  try {
    const res = await fetch(`${BASE}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: r }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    tokens.set(data.access, data.refresh);
    return true;
  } catch {
    return false;
  }
}

async function refresh(): Promise<boolean> {
  refreshing ??= doRefresh().finally(() => { refreshing = null; });
  const ok = await refreshing;
  if (!ok) tokens.clear();
  return ok;
}

function flattenDetails(details: unknown): string {
  if (!details || typeof details !== "object") return "";
  return Object.entries(details as Record<string, unknown>)
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(" ") : String(v)}`)
    .join(" · ");
}

export async function api<T = unknown>(path: string, opts: RequestInit & { json?: unknown } = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = { "Accept-Language": lang, ...(opts.headers as Record<string, string>) };
  const token = tokens.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body = opts.body;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  }
  const res = await fetch(`${BASE}${path}`, { ...opts, headers, body });
  if (res.status === 401 && retry && token) {

    if (await refresh()) return api<T>(path, opts, false);
    if (!tokens.get()) return api<T>(path, opts, false);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    const err = (data as { error?: { code: string; message: string; details: unknown } })?.error;
    const detail = flattenDetails(err?.details);
    const message = err?.message ? t(err.message) : "";
    throw new ApiError(res.status, err?.code || "error", [message, detail].filter(Boolean).join(" ") || t("Грешка {n}", { n: res.status }), err?.details);
  }
  return data as T;
}

export const unwrap = <T,>(data: T[] | { results: T[] }): T[] => (Array.isArray(data) ? data : data.results);

export async function download(path: string, filename: string) {
  const res = await fetch(`${BASE}${path}`, { headers: { Authorization: `Bearer ${tokens.get()}`, "Accept-Language": lang } });
  if (!res.ok) throw new ApiError(res.status, "download", t("Извозот не успеа."), null);
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
