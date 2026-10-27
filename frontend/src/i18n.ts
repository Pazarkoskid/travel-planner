import EN from "./i18n.en";

export type Lang = "mk" | "en";
const KEY = "tpm_lang";

function detect(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "mk" || saved === "en") return saved;
  } catch {  }
  const first = (typeof navigator !== "undefined" && (navigator.languages?.[0] || navigator.language)) || "mk";
  return first.toLowerCase().startsWith("en") ? "en" : "mk";
}

export const lang: Lang = detect();
if (typeof document !== "undefined") {
  document.documentElement.lang = lang;
  if (lang === "en") document.title = "Travel Planner Macedonia";
}

export function setLang(next: Lang) {
  if (next === lang) return;
  try { localStorage.setItem(KEY, next); } catch {  }
  window.location.reload();
}

export function t(text: string, vars?: Record<string, string | number | null | undefined>): string {
  let out = lang === "en" ? EN[text] ?? text : text;
  if (vars) for (const [k, v] of Object.entries(vars)) out = out.split(`{${k}}`).join(String(v ?? ""));
  return out;
}

export function plural(n: number, one: string, many: string) {
  return t(n === 1 ? one : many, { n });
}
