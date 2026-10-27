import { t } from "../i18n";
import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, download, unwrap } from "../services/api";
import { eur, fmtDate, fmtDay, hhmm, isoDate, useAsync } from "../hooks";
import { AccessBadge, Empty, ErrorBox, Field, Loading, Meta } from "../components/ui";
import Icon from "../components/Icon";
import MapView, { MapPoint } from "../components/MapView";
import Photo from "../components/Photo";
import WeatherCard, { WeatherChip } from "../components/Weather";
import type { City, Place, Trip } from "../types";

const INTERESTS: [string, string][] = [
  ["history", t("Историја")],
  ["religion", t("Цркви и манастири")],
  ["nature", t("Природа")],
  ["beach", t("Плажи")],
  ["culture", t("Култура")],
  ["museums", t("Музеи")],
  ["local_food", t("Локална храна")],
  ["activities", t("Активности")],
];
const MOBILITY: [string, string][] = [
  ["standard", t("Без посебни потреби")],
  ["reduced", t("Намалена подвижност")],
  ["wheelchair", t("Инвалидска количка")],
];
const PACE: Record<string, string> = { relaxed: t("бавно темпо"), balanced: t("умерено темпо"), intense: t("интензивно темпо") };

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
    mobility: params.get("mobility") || "standard",
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
      setError(err instanceof Error ? err.message : t("Планот не можеше да се креира."));
      setBusy(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{t("Ново патување")}</h1>
          <p>{t("Пополнете ги основите. Планот го менувате и подоцна, со обичен текст.")}</p>
        </div>
      </div>
      <form className="panel stack-lg" onSubmit={submit}>
        {error && <ErrorBox message={error} />}
        <div className="grid grid-3">
          <Field label={t("Дестинација")}>
            <select value={cityId} onChange={(e) => { setForm({ ...form, city: e.target.value }); setMustVisit([]); }}>
              {cities?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label={t("Почеток")}><input type="date" min={isoDate(0)} value={form.start_date} onChange={set("start_date")} required /></Field>
          <Field label={t("Денови")}><input type="number" min={1} max={10} value={form.days} onChange={set("days")} /></Field>
          <Field label={t("Гости")}><input type="number" min={1} max={20} value={form.guests} onChange={set("guests")} /></Field>
          <Field label={t("Буџет за влезници (EUR, вкупно)")} hint={t("Сместувањето се избира посебно.")}>
            <input type="number" min={0} value={form.budget} onChange={set("budget")} />
          </Field>
          <Field label={t("Превоз")}>
            <select value={form.transport} onChange={set("transport")}>
              <option value="car">{t("Автомобил")}</option>
              <option value="walking">{t("Пешки")}</option>
              <option value="public">{t("Јавен превоз или такси")}</option>
              <option value="bicycle">{t("Велосипед")}</option>
            </select>
          </Field>
        </div>
        <fieldset>
          <legend><Icon name="accessible" size={16} /> {t("Пристапност")}</legend>
          <div className="chips">
            {MOBILITY.map(([k, label]) => (
              <button type="button" key={k} className={form.mobility === k ? "chip on" : "chip"} aria-pressed={form.mobility === k}
                      onClick={() => setForm({ ...form, mobility: k })}>{label}</button>
            ))}
          </div>
          {form.mobility !== "standard" && (
            <p className="field-hint" style={{ marginTop: 8 }}>
              {t("Планот ги изостава непристапните места, им дава предност на пристапните, предвидува повеќе време и предупредува кај делумно пристапните. Податоците за пристапност се проценки, проверете пред тргнување.")}
            </p>
          )}
        </fieldset>
        <fieldset>
          <legend>{t("Темпо")}</legend>
          <div className="chips">
            {Object.entries({ relaxed: t("Бавно, до 4 места дневно"), balanced: t("Умерено, до 6"), intense: t("Интензивно, до 8") }).map(([k, label]) => (
              <button type="button" key={k} className={form.pace === k ? "chip on" : "chip"} aria-pressed={form.pace === k}
                      onClick={() => setForm({ ...form, pace: k })}>{label}</button>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend>{t("Интереси")}</legend>
          <div className="chips">
            {INTERESTS.map(([k, label]) => (
              <button type="button" key={k} className={interests.includes(k) ? "chip on" : "chip"} aria-pressed={interests.includes(k)}
                      onClick={() => setInterests(toggle(interests, k))}>{label}</button>
            ))}
          </div>
        </fieldset>
        {places && places.length > 0 && (
          <fieldset>
            <legend>{t("Места што мора да ги видите (опционално)")}</legend>
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
          <button className="btn btn-primary btn-lg" disabled={busy || !cityId}>{busy ? t("Се прави планот") : t("Направи план")}</button>
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
        <h1>{t("Мои патувања")}</h1>
        <Link to="/trips/new" className="btn btn-primary">{t("Ново патување")}</Link>
      </div>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <Empty title={t("Сè уште немате патувања.")}>
          <Link to="/trips/new" className="btn btn-primary btn-sm">{t("Направи прв план")}</Link>
        </Empty>
      )}
      <div className="grid grid-3">
        {data?.map((trip) => (
          <Link key={trip.id} to={`/trips/${trip.id}`} className="card card-link stack">
            <h3>{trip.title || trip.city_name}</h3>
            <Meta items={[fmtDate(trip.start_date), t("{0} гости", { 0: trip.guests }), PACE[trip.pace]]} />
            <span className={`pill ${trip.status === "GENERATED" ? "pill-ok" : "pill-muted"}`} style={{ justifySelf: "start", width: "fit-content" }}>
              {trip.status === "GENERATED" ? t("Планот е готов") : t("Нацрт")}
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
          sub: t("{0} до {1}", { 0: hhmm(i.start_time), 1: hhmm(i.end_time) }),
          color: i.source_type === "MEAL" ? "#2bb3b1" : "#08415c",
        })),
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
      setActionError(e instanceof Error ? e.message : t("Промената не успеа."));
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Loading />;
  if (error || !trip) return <ErrorBox message={error || t("Патувањето не постои.")} onRetry={reload} />;
  const m = trip.latest_run?.metrics || {};
  const pct = (v: number | null | undefined) => (v === null || v === undefined ? t("нема") : `${Math.round(v * 100)}%`);

  return (
    <div className="stack-lg">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <p className="kicker">{trip.city_name}</p>
          <h1>{trip.title}</h1>
          <Meta items={[t("од {0}", { 0: fmtDate(trip.start_date) }), t("{0} гости", { 0: trip.guests }), t("буџет {0}", { 0: eur(trip.budget) }), PACE[trip.pace]]} />
          {trip.mobility !== "standard" && (
            <span className="access access-yes" style={{ marginTop: 6 }}>
              <Icon name="accessible" size={16} />{t("Пристапна маршрута:")} {MOBILITY.find(([k]) => k === trip.mobility)?.[1]}
            </span>
          )}
        </div>
        <div className="row gap wrap">
          <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => act(`/trips/${trip.id}/generate/`)}>{t("Направи нов план")}</button>
          <button className="btn btn-primary btn-sm" onClick={() => download(`/trips/${trip.id}/export/?format=pdf`, `trip-${trip.id}.pdf`)}>
            <Icon name="download" size={16} />{t("Преземи PDF")}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => download(`/trips/${trip.id}/export/?format=csv`, `trip-${trip.id}.csv`)}>CSV</button>
        </div>
      </div>

      {actionError && <ErrorBox message={actionError} />}
      {trip.warnings.length > 0 && (
        <div className="alert alert-warn">
          <ul>{trip.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      {days.length === 0 ? (
        <Empty title={t("Планот уште не е направен.")}>
          <button className="btn btn-primary" disabled={busy} onClick={() => act(`/trips/${trip.id}/generate/`)}>{t("Направи план")}</button>
        </Empty>
      ) : (
        <>
          <div className="day-tabs" role="tablist" aria-label={t("Денови")}>
            {days.map((d, i) => (
              <button key={d.day_number} role="tab" aria-selected={i === day} className={i === day ? "day-tab on" : "day-tab"} onClick={() => setDay(i)}>
                <strong>{t("Ден")} {d.day_number}</strong>
                <span>{fmtDay(d.date)}</span>
                <WeatherChip query={`city=${trip.city}`} date={d.date} />
              </button>
            ))}
          </div>

          <div className="split trip-split">
            <div>
              <p className="small muted" style={{ marginBottom: 14 }}>{current?.notes}</p>
              <ol className="route" aria-label={t("Редослед на посети")}>
                {current?.items.map((it) => (
                  <li key={it.id} className={`stop ${it.source_type === "MEAL" ? "stop-meal" : ""}`}>
                    <span className="stop-marker" aria-hidden />
                    <div className="stop-body">
                      {it.travel_minutes_from_prev > 0 && (
                        <span className="stop-travel">{Math.round(it.travel_minutes_from_prev)} {t("мин до тука,")} {it.distance_km_from_prev} km</span>
                      )}
                      {it.image_url && <Photo className="stop-photo" src={it.image_url} alt="" seed={it.id} />}
                      <div className="stop-time">{hhmm(it.start_time)} {t("до")} {hhmm(it.end_time)}</div>
                      <div className="stop-title">{it.place ? <Link to={`/places/${it.place}`}>{it.title}</Link> : it.title}</div>
                      {trip.mobility !== "standard" && it.source_type === "PLACE" && <AccessBadge level={it.wheelchair} notes={it.accessibility_notes} compact />}
                      <p className="stop-reason">{it.reason}</p>
                      {it.source_type === "PLACE" && <p className="stop-reason">{t("Трошок:")} {eur(it.est_cost)}</p>}
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
            <input placeholder={t("Што да сменам? На пример: поевтино, побавно, повеќе природа, помалку пешачење")} value={revision}
                   onChange={(e) => setRevision(e.target.value)} aria-label={t("Барање за измена на планот")} />
            <button className="btn" disabled={busy || !revision.trim()}>{busy ? t("Се менува") : t("Смени го планот")}</button>
          </form>

          {trip.latest_run && (
            <details className="panel panel-tight">
              <summary>
                <strong>{t("Колку е добар планот")}</strong>
                <span className="small muted">{t("метод")} {trip.latest_run.provider}{t(", рутирање")} {trip.latest_run.routing_provider}</span>
              </summary>
              <dl className="metrics">
                <div><dt>{t("Време за движење без оптимизација")}</dt><dd>{m.baseline_travel_min} {t("мин")}</dd></div>
                <div><dt>{t("Време за движење со оптимизација")}</dt><dd>{m.optimized_travel_min} {t("мин")}</dd></div>
                <div><dt>{t("Заштеда")}</dt><dd>{m.travel_improvement_pct}%</dd></div>
                <div><dt>{t("Прекршени ограничувања")}</dt><dd>{m.optimized_violations}</dd></div>
                <div><dt>{t("Покриени интереси")}</dt><dd>{pct(m.interest_coverage)}</dd></div>
                <div><dt>{t("Места од каталогот")}</dt><dd>{pct(m.place_validity)}</dd></div>
                <div><dt>{t("Време на генерирање")}</dt><dd>{m.generation_ms} ms</dd></div>
                <div><dt>{t("Отфрлени непознати места")}</dt><dd>{trip.latest_run.rejected_ids.length}</dd></div>
                {m.accessible_share != null && <div><dt>{t("Целосно пристапни места")}</dt><dd>{pct(m.accessible_share)}</dd></div>}
              </dl>
            </details>
          )}

          <div className="panel panel-lake row between wrap gap">
            <div>
              <h3 style={{ margin: 0 }}>{t("Каде ќе спиете?")}</h3>
              <span className="small muted">{t("Сместување за истите датуми и број гости.")}</span>
            </div>
            <div className="row gap">
              <Link className="btn btn-primary btn-sm" to={`/stay?city=${trip.city}&check_in=${trip.start_date}&days=${trip.days}&guests=${trip.guests}`}>{t("Најди сместување")}</Link>
              <Link className="btn btn-ghost btn-sm" to="/boat-tours">{t("Бродски тури")}</Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
