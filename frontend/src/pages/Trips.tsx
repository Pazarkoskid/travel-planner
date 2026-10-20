import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, download, unwrap } from "../services/api";
import { eur, fmtDate, fmtDay, hhmm, isoDate, useAsync } from "../hooks";
import { Empty, ErrorBox, Field, Loading, Meta } from "../components/ui";
import MapView, { MapPoint } from "../components/MapView";
import Photo from "../components/Photo";
import WeatherCard, { WeatherChip } from "../components/Weather";
import type { City, Place, Trip } from "../types";

const INTERESTS: [string, string][] = [
  ["history", "Историја"],
  ["religion", "Цркви и манастири"],
  ["nature", "Природа"],
  ["beach", "Плажи"],
  ["culture", "Култура"],
  ["museums", "Музеи"],
  ["local_food", "Локална храна"],
  ["activities", "Активности"],
];
const PACE: Record<string, string> = { relaxed: "бавно темпо", balanced: "умерено темпо", intense: "интензивно темпо" };

export function TripNew() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const { data: cities } = useAsync(() => api<City[]>("/cities/"), []);
  const [form, setForm] = useState({
    city: params.get("city") || "",
    start_date: params.get("start_date") || isoDate(7),
    days: Number(params.get("days") || 3),
    guests: Number(params.get("guests") || 2),
    budget: "250",
    pace: "balanced",
    transport: "car",
  });
  const [interests, setInterests] = useState<string[]>(params.get("interest") ? [params.get("interest")!] : ["history", "nature"]);
  const [mustVisit, setMustVisit] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const cityId = form.city || (cities?.[0]?.id ? String(cities[0].id) : "");
  const { data: places } = useAsync(
    () => (cityId ? api<Place[]>(`/cities/${cityId}/places/`) : Promise.resolve([])),
    [cityId],
  );

  const set = (k: string) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const trip = await api<Trip>("/trips/", {
        method: "POST",
        json: { ...form, city: Number(cityId), days: Number(form.days), guests: Number(form.guests),
                budget: form.budget || null, interests, must_visit: mustVisit },
      });
      await api(`/trips/${trip.id}/generate/`, { method: "POST" });
      nav(`/trips/${trip.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Планот не можеше да се креира.");
      setBusy(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Ново патување</h1>
          <p>Пополнете ги основите. Планот го менувате и подоцна, со обичен текст.</p>
        </div>
      </div>
      <form className="panel stack-lg" onSubmit={submit}>
        {error && <ErrorBox message={error} />}
        <div className="grid grid-3">
          <Field label="Дестинација">
            <select value={cityId} onChange={(e) => { setForm({ ...form, city: e.target.value }); setMustVisit([]); }}>
              {cities?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Почеток"><input type="date" min={isoDate(0)} value={form.start_date} onChange={set("start_date")} required /></Field>
          <Field label="Денови"><input type="number" min={1} max={10} value={form.days} onChange={set("days")} /></Field>
          <Field label="Гости"><input type="number" min={1} max={20} value={form.guests} onChange={set("guests")} /></Field>
          <Field label="Буџет за влезници (EUR, вкупно)" hint="Сместувањето се избира посебно.">
            <input type="number" min={0} value={form.budget} onChange={set("budget")} />
          </Field>
          <Field label="Превоз">
            <select value={form.transport} onChange={set("transport")}>
              <option value="car">Автомобил</option>
              <option value="walking">Пешки</option>
              <option value="public">Јавен превоз или такси</option>
              <option value="bicycle">Велосипед</option>
            </select>
          </Field>
        </div>
        <fieldset>
          <legend>Темпо</legend>
          <div className="chips">
            {Object.entries({ relaxed: "Бавно, до 4 места дневно", balanced: "Умерено, до 6", intense: "Интензивно, до 8" }).map(([k, label]) => (
              <button type="button" key={k} className={form.pace === k ? "chip on" : "chip"} aria-pressed={form.pace === k}
                      onClick={() => setForm({ ...form, pace: k })}>{label}</button>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend>Интереси</legend>
          <div className="chips">
            {INTERESTS.map(([k, label]) => (
              <button type="button" key={k} className={interests.includes(k) ? "chip on" : "chip"} aria-pressed={interests.includes(k)}
                      onClick={() => setInterests(toggle(interests, k))}>{label}</button>
            ))}
          </div>
        </fieldset>
        {places && places.length > 0 && (
          <fieldset>
            <legend>Места што мора да ги видите (опционално)</legend>
            <div className="chips">
              {places.map((p) => (
                <button type="button" key={p.id} className={mustVisit.includes(p.id) ? "chip on" : "chip"} aria-pressed={mustVisit.includes(p.id)}
                        onClick={() => setMustVisit(mustVisit.includes(p.id) ? mustVisit.filter((x) => x !== p.id) : [...mustVisit, p.id])}>
                  {p.name}
                </button>
              ))}
            </div>
          </fieldset>
        )}
        <div>
          <button className="btn btn-primary btn-lg" disabled={busy || !cityId}>{busy ? "Се прави планот" : "Направи план"}</button>
        </div>
      </form>
    </>
  );
}

export function TripList() {
  const { data, error, loading, reload } = useAsync(async () => unwrap(await api<Trip[] | { results: Trip[] }>("/trips/")), []);
  return (
    <>
      <div className="page-head">
        <h1>Мои патувања</h1>
        <Link to="/trips/new" className="btn btn-primary">Ново патување</Link>
      </div>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <Empty title="Сè уште немате патувања.">
          <Link to="/trips/new" className="btn btn-primary btn-sm">Направи прв план</Link>
        </Empty>
      )}
      <div className="grid grid-3">
        {data?.map((t) => (
          <Link key={t.id} to={`/trips/${t.id}`} className="card card-link stack">
            <h3>{t.title || t.city_name}</h3>
            <Meta items={[fmtDate(t.start_date), `${t.guests} гости`, PACE[t.pace]]} />
            <span className={`pill ${t.status === "GENERATED" ? "pill-ok" : "pill-muted"}`} style={{ justifySelf: "start", width: "fit-content" }}>
              {t.status === "GENERATED" ? "Планот е готов" : "Нацрт"}
            </span>
          </Link>
        ))}
      </div>
    </>
  );
}

export function TripDetail() {
  const { id } = useParams();
  const { data: trip, error, loading, reload, setData } = useAsync(() => api<Trip>(`/trips/${id}/`), [id]);
  const [day, setDay] = useState(0);
  const [revision, setRevision] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const days = trip?.itinerary_days || [];
  const current = days[day];
  const placeItems = (current?.items || []).filter((i) => i.source_type !== "MEAL");
  const points: MapPoint[] = useMemo(
    () =>
      (current?.items || [])
        .filter((i) => i.lat !== null && i.lng !== null)
        .map((i) => ({
          lat: i.lat!, lng: i.lng!, label: i.title,
          order: i.source_type === "MEAL" ? undefined : placeItems.indexOf(i) + 1,
          sub: `${hhmm(i.start_time)} до ${hhmm(i.end_time)}`,
          color: i.source_type === "MEAL" ? "#2bb3b1" : "#08415c",
        })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [current],
  );

  const act = async (path: string, json?: unknown) => {
    setBusy(true);
    setActionError(null);
    try {
      setData(await api<Trip>(path, { method: "POST", json }));
      setDay(0);
      setRevision("");
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Промената не успеа.");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Loading />;
  if (error || !trip) return <ErrorBox message={error || "Патувањето не постои."} onRetry={reload} />;
  const m = trip.latest_run?.metrics || {};
  const pct = (v: number | null | undefined) => (v === null || v === undefined ? "нема" : `${Math.round(v * 100)}%`);

  return (
    <div className="stack-lg">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <p className="kicker">{trip.city_name}</p>
          <h1>{trip.title}</h1>
          <Meta items={[`од ${fmtDate(trip.start_date)}`, `${trip.guests} гости`, `буџет ${eur(trip.budget)}`, PACE[trip.pace]]} />
        </div>
        <div className="row gap wrap">
          <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => act(`/trips/${trip.id}/generate/`)}>Направи нов план</button>
          <button className="btn btn-ghost btn-sm" onClick={() => download(`/trips/${trip.id}/export/?format=csv`, `trip-${trip.id}.csv`)}>Преземи CSV</button>
        </div>
      </div>

      {actionError && <ErrorBox message={actionError} />}
      {trip.warnings.length > 0 && (
        <div className="alert alert-warn">
          <ul>{trip.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      {days.length === 0 ? (
        <Empty title="Планот уште не е направен.">
          <button className="btn btn-primary" disabled={busy} onClick={() => act(`/trips/${trip.id}/generate/`)}>Направи план</button>
        </Empty>
      ) : (
        <>
          <div className="day-tabs" role="tablist" aria-label="Денови">
            {days.map((d, i) => (
              <button key={d.day_number} role="tab" aria-selected={i === day} className={i === day ? "day-tab on" : "day-tab"} onClick={() => setDay(i)}>
                <strong>Ден {d.day_number}</strong>
                <span>{fmtDay(d.date)}</span>
                <WeatherChip query={`city=${trip.city}`} date={d.date} />
              </button>
            ))}
          </div>

          <div className="split trip-split">
            <div>
              <p className="small muted" style={{ marginBottom: 14 }}>{current?.notes}</p>
              <ol className="route" aria-label="Редослед на посети">
                {current?.items.map((it) => (
                  <li key={it.id} className={`stop ${it.source_type === "MEAL" ? "stop-meal" : ""}`}>
                    <span className="stop-marker" aria-hidden />
                    <div className="stop-body">
                      {it.travel_minutes_from_prev > 0 && (
                        <span className="stop-travel">{Math.round(it.travel_minutes_from_prev)} мин до тука, {it.distance_km_from_prev} km</span>
                      )}
                      {it.image_url && <Photo className="stop-photo" src={it.image_url} alt="" seed={it.id} />}
                      <div className="stop-time">{hhmm(it.start_time)} до {hhmm(it.end_time)}</div>
                      <div className="stop-title">{it.place ? <Link to={`/places/${it.place}`}>{it.title}</Link> : it.title}</div>
                      <p className="stop-reason">{it.reason}</p>
                      {it.source_type === "PLACE" && <p className="stop-reason">Трошок: {eur(it.est_cost)}</p>}
                      {it.warning && <div className="stop-warn">{it.warning}</div>}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
            <MapView points={points} route height={500} />
          </div>

          <WeatherCard query={`city=${trip.city}`} title={trip.city_name} />

          <form className="revise" onSubmit={(e) => { e.preventDefault(); act(`/trips/${trip.id}/revise/`, { instructions: revision }); }}>
            <input placeholder="Што да сменам? На пример: поевтино, побавно, повеќе природа, помалку пешачење" value={revision}
                   onChange={(e) => setRevision(e.target.value)} aria-label="Барање за измена на планот" />
            <button className="btn" disabled={busy || !revision.trim()}>{busy ? "Се менува" : "Смени го планот"}</button>
          </form>

          {trip.latest_run && (
            <details className="panel panel-tight">
              <summary>
                <strong>Колку е добар планот</strong>
                <span className="small muted">метод {trip.latest_run.provider}, рутирање {trip.latest_run.routing_provider}</span>
              </summary>
              <dl className="metrics">
                <div><dt>Време за движење без оптимизација</dt><dd>{m.baseline_travel_min} мин</dd></div>
                <div><dt>Време за движење со оптимизација</dt><dd>{m.optimized_travel_min} мин</dd></div>
                <div><dt>Заштеда</dt><dd>{m.travel_improvement_pct}%</dd></div>
                <div><dt>Прекршени ограничувања</dt><dd>{m.optimized_violations}</dd></div>
                <div><dt>Покриени интереси</dt><dd>{pct(m.interest_coverage)}</dd></div>
                <div><dt>Места од каталогот</dt><dd>{pct(m.place_validity)}</dd></div>
                <div><dt>Време на генерирање</dt><dd>{m.generation_ms} ms</dd></div>
                <div><dt>Отфрлени непознати места</dt><dd>{trip.latest_run.rejected_ids.length}</dd></div>
              </dl>
            </details>
          )}

          <div className="panel panel-lake row between wrap gap">
            <div>
              <h3 style={{ margin: 0 }}>Каде ќе спиете?</h3>
              <span className="small muted">Сместување за истите датуми и број гости.</span>
            </div>
            <div className="row gap">
              <Link className="btn btn-primary btn-sm" to={`/stay?city=${trip.city}&check_in=${trip.start_date}&days=${trip.days}&guests=${trip.guests}`}>Најди сместување</Link>
              <Link className="btn btn-ghost btn-sm" to="/boat-tours">Бродски тури</Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
