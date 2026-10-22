import { DependencyList, useCallback, useEffect, useState } from "react";
import { lang, t } from "./i18n";

export function useAsync<T>(fn: () => Promise<T>, deps: DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await run());
    } catch (e) {
      setError(e instanceof Error ? e.message : t("Грешка"));
    } finally {
      setLoading(false);
    }
  }, [run]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, error, loading, reload, setData };
}

const MONTHS = lang === "en"
  ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
  : [t("јан"), t("фев"), t("мар"), t("апр"), t("мај"), t("јун"), t("јул"), t("авг"), t("сеп"), t("окт"), t("ное"), t("дек")];
const WEEKDAYS = lang === "en"
  ? ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
  : [t("недела"), t("понеделник"), t("вторник"), t("среда"), t("четврток"), t("петок"), t("сабота")];

/** Датуми на избраниот јазик, без зависност од локалните поставки на прелистувачот. */
export const fmtDate = (d: string | null | undefined) => {
  if (!d) return t("нема");
  const x = new Date(d.length === 10 ? `${d}T12:00:00` : d);
  return `${x.getDate()} ${MONTHS[x.getMonth()]} ${x.getFullYear()}`;
};

export const fmtDay = (d: string) => {
  const x = new Date(`${d}T12:00:00`);
  return `${WEEKDAYS[x.getDay()]}, ${x.getDate()} ${MONTHS[x.getMonth()]}`;
};

export const fmtDateTime = (d: string | null | undefined) => {
  if (!d) return t("нема");
  const x = new Date(d);
  const hm = `${String(x.getHours()).padStart(2, "0")}:${String(x.getMinutes()).padStart(2, "0")}`;
  return `${x.getDate()} ${MONTHS[x.getMonth()]}, ${hm}`;
};

export const hhmm = (t: string) => t.slice(0, 5);

export const eur = (v: string | number | null | undefined) =>
  v === null || v === undefined || v === "" ? t("непознато") : `${Number(v).toFixed(2)} €`;

export const isoDate = (offsetDays = 0) => {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
};
