import { useEffect, useState } from "react";
import { api, ApiError } from "../services/api";
import { useAuth } from "../auth";
import type { Weather as WeatherData, WeatherDay } from "../types";

const DAYS = ["нед", "пон", "вто", "сре", "чет", "пет", "саб"];
const icon = (code: string) => `https://openweathermap.org/img/wn/${code}@2x.png`;

// Кеш во меморијата за сесијата — една страница може да има неколку виџети за ист град.
const memo = new Map<string, Promise<WeatherData>>();

export function useWeather(query: string | null) {
  const [data, setData] = useState<WeatherData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!query) return;
    let alive = true;
    if (!memo.has(query)) memo.set(query, api<WeatherData>(`/weather/?${query}`));
    memo.get(query)!
      .then((d) => alive && setData(d))
      .catch((e) => {
        memo.delete(query);
        if (alive) setError(e instanceof ApiError ? e.code : "error");
      });
    return () => { alive = false; };
  }, [query]);
  return { data, error };
}

/** Целосен виџет: моментално време + неколку дена. */
export default function WeatherCard({ query, title }: { query: string; title?: string }) {
  const { data, error } = useWeather(query);
  const { user } = useAuth();
  if (error === "weather_not_configured") {
    // Туристите не гледаат празна кутија; администраторот гледа како да ја вклучи.
    return user?.role === "ADMIN" ? (
      <div className="weather weather-muted small">
        <strong>Временската прогноза не е вклучена.</strong> Додајте <code>OPENWEATHER_API_KEY=…</code> во датотеката
        <code> .env</code> во главната папка на проектот и рестартирајте го backend-от.
      </div>
    ) : null;
  }
  if (error) return <div className="weather weather-muted small">Прогнозата моментално не е достапна.</div>;
  if (!data) return <div className="weather weather-loading" aria-busy="true" />;
  const c = data.current;
  return (
    <section className="weather" aria-label={`Временска прогноза за ${data.location || title || "локацијата"}`}>
      <div className="weather-now">
        <img src={icon(c.icon)} alt="" width={64} height={64} />
        <div>
          <div className="weather-temp">{c.temp}°</div>
          <div className="weather-desc">{c.description}</div>
        </div>
        <dl className="weather-meta">
          <div><dt>Чувство</dt><dd>{c.feels_like}°</dd></div>
          <div><dt>Ветер</dt><dd>{c.wind} km/h</dd></div>
          <div><dt>Влажност</dt><dd>{c.humidity}%</dd></div>
        </dl>
      </div>
      <ol className="weather-days">
        {data.daily.slice(0, 5).map((d) => <DayCell key={d.date} d={d} />)}
      </ol>
      <p className="weather-note">{title || data.location}, прогноза од {data.source}. Прогнозата е до 5 дена однапред и може да се промени.</p>
    </section>
  );
}

function DayCell({ d }: { d: WeatherDay }) {
  const date = new Date(`${d.date}T12:00:00`);
  return (
    <li>
      <span className="wd-name">{DAYS[date.getDay()]}</span>
      <img src={icon(d.icon)} alt="" title={d.description} width={40} height={40} />
      <span className="wd-temp"><b>{d.max}°</b> {d.min}°</span>
      {d.pop >= 30 && <span className="wd-pop">{d.pop}% дожд</span>}
    </li>
  );
}

/** Мал знак за ден од план или поаѓање — само ако денот е во прозорецот на прогнозата. */
export function WeatherChip({ query, date }: { query: string; date: string }) {
  const { data } = useWeather(query);
  const day = data?.daily.find((d) => d.date === date);
  if (!day) return null;
  return (
    <span className="weather-chip" title={day.description}>
      <img src={icon(day.icon)} alt="" width={26} height={26} />
      {day.max}° / {day.min}°{day.pop >= 30 ? `, ${day.pop}% дожд` : ""}
    </span>
  );
}
