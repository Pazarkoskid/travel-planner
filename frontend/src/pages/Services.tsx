gimport { t } from "../i18n";
import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../services/api";
import { eur, fmtDateTime, isoDate, useAsync } from "../hooks";
import { useAuth } from "../auth";
import { BizLogo, Empty, ErrorBox, Field, Loading, Meta, Stars } from "../components/ui";
import Icon from "../components/Icon";
import Photo from "../components/Photo";
import type { AccommodationResult, BoatTour, Business, City, Review, TransportService } from "../types";

const AMENITIES: [string, string][] = [
  ["wifi", "Wi-Fi"], ["ac", t("Клима")], ["parking", t("Паркинг")], ["kitchen", t("Кујна")], ["terrace", t("Тераса")], ["lake_view", t("Поглед на езеро")],
];

const addDays = (iso: string, n: number) => {
  const d = new Date(iso);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
};

export function Accommodations() {
  const [params] = useSearchParams();
  const { user } = useAuth();
  const { data: cities } = useAsync(() => api<City[]>("/cities/"), []);
  const checkInDefault = params.get("check_in") || isoDate(7);
  const [q, setQ] = useState({
    city: params.get("city") || "ohrid",
    check_in: checkInDefault,
    check_out: addDays(checkInDefault, Number(params.get("days") || 3)),
    guests: params.get("guests") || "2",
    max_total: "",
  });
  const [amen, setAmen] = useState<string[]>([]);
  const [search, setSearch] = useState(0);
  const { data, error, loading } = useAsync(() => {
    const p = new URLSearchParams({ ...q, amenities: amen.join(",") });
    if (!q.max_total) p.delete("max_total");
    return api<AccommodationResult[]>(`/accommodations/?${p}`);
  }, [search]);
  const [booked, setBooked] = useState<string | null>(null);
  const [bookError, setBookError] = useState<string | null>(null);

  const set = (k: string) => (e: { target: { value: string } }) => setQ({ ...q, [k]: e.target.value });

  const book = async (r: AccommodationResult) => {
    if (!r.quote) return;
    setBookError(null);
    try {
      const res = await api<{ id: number }>("/accommodation-bookings/", {
        method: "POST",
        json: { unit_id: r.quote.unit_id, check_in: q.check_in, check_out: q.check_out, guests: Number(q.guests),
                idempotency_key: crypto.randomUUID() },
      });
      setBooked(t("Барањето #{0} е испратено до „{1}“. Статус: чека одговор.", { 0: res.id, 1: r.business.name }));
      setSearch((s) => s + 1);
    } catch (e) {
      setBookError(e instanceof Error ? e.message : t("Грешка"));
    }
  };

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>{t("Сместување")}</h1>
          <p>{t("Цената е пресметана за секоја ноќ од престојот, со сите познати трошоци.")}</p>
        </div>
      </div>
      <form className="panel stack" onSubmit={(e: FormEvent) => { e.preventDefault(); setSearch((s) => s + 1); }}>
        <div className="grid grid-5">
          <Field label={t("Град")}>
            <select value={q.city} onChange={set("city")}>
              {cities?.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
              {cities && !cities.some((c) => c.slug === q.city) && <option value={q.city}>{t("избран град")}</option>}
            </select>
          </Field>
          <Field label="Check-in"><input type="date" min={isoDate(0)} value={q.check_in} onChange={set("check_in")} /></Field>
          <Field label="Check-out"><input type="date" min={q.check_in} value={q.check_out} onChange={set("check_out")} /></Field>
          <Field label={t("Гости")}><input type="number" min={1} value={q.guests} onChange={set("guests")} /></Field>
          <Field label={t("Макс. вкупно (EUR)")}><input type="number" min={0} value={q.max_total} onChange={set("max_total")} /></Field>
        </div>
        <div className="chips">
          {AMENITIES.map(([k, l]) => (
            <button type="button" key={k} className={amen.includes(k) ? "chip on" : "chip"} aria-pressed={amen.includes(k)}
                    onClick={() => setAmen(amen.includes(k) ? amen.filter((a) => a !== k) : [...amen, k])}>{l}</button>
          ))}
        </div>
        <div><button className="btn btn-primary">{t("Пребарај")}</button></div>
      </form>
      {booked && <div className="alert alert-ok">{booked} <Link to="/reservations">{t("Отвори ги резервациите")}</Link></div>}
      {bookError && <ErrorBox message={bookError} />}
      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {data && data.length === 0 && <Empty title={t("Нема достапно сместување за овие критериуми.")}>{t("Пробајте други датуми или помалку филтри.")}</Empty>}
      {data?.map((r) => (
        <article key={r.id} className="panel offer offer-with-photo">
          <Photo className="offer-photo" src={r.business.image_url || r.business.city_image_url} alt={r.title} seed={r.id} />
          <div className="stack" style={{ gap: 10 }}>
            <div>
              {r.business.is_sponsored && <span className="sponsored">{t("Спонзорирано")}</span>}
              <h2 style={{ marginBottom: 4 }}><Link className="title-link" to={`/stay/${r.id}?check_in=${q.check_in}&check_out=${q.check_out}&guests=${q.guests}`}>{r.title}</Link></h2>
              <div className="row gap" style={{ alignItems: "center" }}><BizLogo b={r.business} size={32} /><Meta items={[r.business.name, t(r.type_label), t("до {0} гости", { 0: r.max_guests }), t("{0} спални", { 0: r.bedrooms })]} /></div>
            </div>
            <div className="chips">{r.amenities.map((a) => <span className="chip static" key={a}>{AMENITIES.find(([k]) => k === a)?.[1] || a}</span>)}</div>
            <p className="small" style={{ margin: 0 }}>{t("Зошто е предложено:")} {r.recommendation_reason.split(", ").map((x) => (x.startsWith("оценка ") ? t("оценка {0}", { 0: x.slice(7) }) : t(x))).join(", ")}.</p>
            <p className="small muted" style={{ margin: 0 }}>{r.rules} {t("Бесплатно откажување до")} {r.free_cancellation_days} {t("дена пред доаѓање.")}</p>
            <Link className="small" to={`/stay/${r.id}?check_in=${q.check_in}&check_out=${q.check_out}&guests=${q.guests}`}>{t("Види го огласот")}</Link>
          </div>
          <div className="offer-price">
            <Stars value={r.avg_rating} count={r.review_count} />
            {r.quote ? (
              <>
                <span className="offer-total">{eur(r.quote.total)}</span>
                <span className="small muted">{r.quote.nights} {t("ноќи")} {eur(r.quote.subtotal)}{t(", трошоци")} {eur(r.quote.fees)}</span>
                {user ? <button className="btn btn-primary btn-block" onClick={() => book(r)}>{t("Испрати барање")}</button>
                  : <Link className="btn btn-ghost btn-block" to="/login">{t("Најави се за да резервираш")}</Link>}
              </>
            ) : <span className="small muted">{t("Изберете датуми за цена.")}</span>}
          </div>
        </article>
      ))}
    </div>
  );
}

export function ReviewsList({ businessId }: { businessId: number }) {
  const [open, setOpen] = useState(false);
  const { data } = useAsync(() => (open ? api<Review[]>(`/businesses/${businessId}/reviews/`) : Promise.resolve(null)), [open, businessId]);
  return (
    <div>
      <button className="link-btn small" onClick={() => setOpen(!open)}>{open ? t("Скриј рецензии") : t("Прикажи рецензии")}</button>
      {open && data && (data.length === 0 ? <p className="small muted">{t("Сè уште нема рецензии.")}</p> : (
        <ul className="reviews">
          {data.map((rv) => (
            <li key={rv.id}>
              <strong>★ {rv.rating}</strong> {rv.username}
               {rv.is_verified_booking && <span className="pill pill-ok">{t("Проверена резервација")}</span>}
              <p>{rv.comment}</p>
              {rv.reply && <p className="reply"><strong>{t("Одговор од бизнисот:")}</strong> {rv.reply.reply_text}</p>}
            </li>
          ))}
        </ul>
      ))}
    </div>
  );
}

export function BoatTours() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useAsync(async () => {
    const r = await api<BoatTour[] | { results: BoatTour[] }>("/boat-tours/");
    return Array.isArray(r) ? r : r.results;
  }, []);
  const [seats, setSeats] = useState<Record<number, number>>({});
  const [showAll, setShowAll] = useState<Record<number, boolean>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const book = async (depId: number) => {
    setErr(null);
    try {
      const r = await api<{ id: number; total_price: string }>("/boat-reservations/", {
        method: "POST", json: { departure_id: depId, seats: seats[depId] || 1, idempotency_key: crypto.randomUUID() },
      });
      setMsg(t("Барањето #{0} е испратено ({1}).", { 0: r.id, 1: eur(r.total_price) }));
      reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : t("Грешка"));
    }
  };

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>{t("Бродски тури")}</h1>
          <p>{t("Слободните места се ажурираат при секое барање. Барањето го потврдува операторот.")}</p>
        </div>
      </div>
      {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">{t("Отвори ги резервациите")}</Link></div>}
      {err && <ErrorBox message={err} />}
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data?.map((tour) => (
        <article key={tour.id} className="panel stack">
          <Photo className="tour-photo" src={tour.business.image_url || tour.business.city_image_url} alt={tour.title} seed={tour.id + 1} />
          <div className="row between wrap gap">
            <div>
              <h2 style={{ marginBottom: 4 }}><Link className="title-link" to={`/boat-tours/${tour.id}`}>{tour.title}</Link></h2>
              <Meta items={[tour.business.name, tour.route, t("{0} часа", { 0: Math.round(tour.duration_min / 60) }), t("поаѓа од {0}", { 0: tour.departure_point })]} />
            </div>
            <div className="price-block">
              <span className="offer-total">{eur(tour.price_per_person)}</span>
              <span className="small muted">{t("по лице")}</span>
            </div>
          </div>
          {tour.description && <p style={{ margin: 0 }}>{tour.description}</p>}
          {tour.stops.length > 0 && (
            <p className="small muted" style={{ margin: 0 }}>{t("Постојки:")} {tour.stops.map((s) => s.name).join(", ")}</p>
          )}
          <Link className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }} to={`/boat-tours/${tour.id}`}>{t("Детали, рута и сите поаѓања")}</Link>
          <table className="table table-cards">
            <thead><tr><th>{t("Поаѓање")}</th><th>{t("Слободни места")}</th><th>{t("Колку места")}</th><th /></tr></thead>
            <tbody>
              {tour.upcoming_departures.slice(0, showAll[tour.id] ? undefined : 4).map((d) => (
                <tr key={d.id}>
                  <td data-label={t("Поаѓање")}>{fmtDateTime(d.starts_at)}</td>
                  <td data-label={t("Слободни")}>{d.remaining_seats} {t("од")} {d.capacity}</td>
                  <td data-label={t("Места")}>
                    <input type="number" min={1} max={d.remaining_seats} value={seats[d.id] || 1} aria-label={t("Број места")}
                           onChange={(e) => setSeats({ ...seats, [d.id]: Number(e.target.value) })} className="input-sm" />
                  </td>
                  <td className="td-actions">
                    {user ? <button className="btn btn-primary btn-sm" disabled={d.remaining_seats < 1} onClick={() => book(d.id)}>{t("Резервирај")}</button>
                      : <Link to="/login" className="small">{t("Најава")}</Link>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {tour.upcoming_departures.length > 4 && !showAll[tour.id] && (
            <button className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => setShowAll({ ...showAll, [tour.id]: true })}>
              {t("Прикажи ги сите поаѓања (")}{tour.upcoming_departures.length})
            </button>
          )}
        </article>
      ))}
    </div>
  );
}

const KINDS: [string, string][] = [
  ["", t("Сите")], ["TAXI", t("Такси")], ["BUS", t("Автобуси")], ["BIKE_RENTAL", t("Велосипеди")], ["RESTAURANT", t("Ресторани")],
];
const KIND_ICON: Record<string, string> = { TAXI: "car", BUS: "bus", BIKE_RENTAL: "bike", RESTAURANT: "fork" };
const detailPath = (b: Business) =>
  b.type === "TAXI" ? `/taxi/${b.id}` : b.type === "RESTAURANT" ? `/restaurants/${b.id}` : `/transport/${b.id}`;

function TransportSummary({ tr }: { tr: TransportService }) {
  if (tr.lines.length) {
    return (
      <ul className="line-list">
        {tr.lines.slice(0, 3).map((l) => (
          <li key={l.code}><span className="line-code">{l.code}</span>{l.name}<span className="small muted"> · {t("на {0} мин", { 0: l.every_min })}</span></li>
        ))}
      </ul>
    );
  }
  const hourly = tr.rentals.map((r) => r.per_hour).filter((x): x is number => x !== null);
  const daily = tr.rentals.map((r) => r.per_day).filter((x): x is number => x !== null);
  return (
    <p className="small" style={{ margin: 0 }}>
      {tr.rentals.map((r) => r.name).join(", ")}.
      {hourly.length > 0 && <> {t("Од {0} на час", { 0: eur(Math.min(...hourly)) })}</>}
      {daily.length > 0 && <> {t("или {0} на ден", { 0: eur(Math.min(...daily)) })}</>}.
    </p>
  );
}

export function OtherServices() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const city = params.get("city") || "";
  const kind = params.get("type") || "";
  const { data: cities } = useAsync(() => api<City[]>("/cities/"), []);
  const { data, loading, error, reload } = useAsync(async () => {
    const [biz, trans] = await Promise.all([
      api<Business[] | { results: Business[] }>(`/businesses/${city ? `?city=${city}` : ""}`),
      api<TransportService[] | { results: TransportService[] }>(`/transport-services/${city ? `?city=${city}` : ""}`),
    ]);
    const list = (Array.isArray(biz) ? biz : biz.results).filter((b) => KIND_ICON[b.type]);
    const byBiz = Object.fromEntries((Array.isArray(trans) ? trans : trans.results).map((x) => [x.business.id, x]));
    return { list, byBiz };
  }, [city]);
  const [form, setForm] = useState<Record<number, { when: string; guests: number; pickup: string; destination: string }>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const shown = (data?.list || []).filter((b) => !kind || b.type === kind);
  const counts = (data?.list || []).reduce<Record<string, number>>((m, b) => ({ ...m, [b.type]: (m[b.type] || 0) + 1 }), {});
  const setParam = (k: string, v: string) => {
    const n = new URLSearchParams(params);
    if (v) n.set(k, v); else n.delete(k);
    setParams(n, { replace: true });
  };

  const send = async (b: Business) => {
    const f = form[b.id] || { when: "", guests: 2, pickup: "", destination: "" };
    setErr(null);
    try {
      const reserved_for = new Date(f.when).toISOString();
      const path = b.type === "TAXI" ? "/taxi-requests/" : "/restaurant-reservations/";
      const json = b.type === "TAXI" ? { business_id: b.id, reserved_for, guests: f.guests, pickup: f.pickup, destination: f.destination }
        : { business_id: b.id, reserved_for, guests: f.guests };
      const r = await api<{ id: number }>(path, { method: "POST", json: { ...json, idempotency_key: crypto.randomUUID() } });
      setMsg(t("Барањето #{0} е испратено до „{1}“.", { 0: r.id, 1: b.name }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : t("Внесете валиден датум и време."));
    }
  };

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>{t("Превоз и ресторани")}</h1>
          <p>{t("Такси, градски автобуси, изнајмување велосипеди и ресторани. Барањето не е гаранција: бизнисот го прифаќа или предлага друг термин.")}</p>
        </div>
        <select value={city} onChange={(e) => setParam("city", e.target.value)} aria-label={t("Град")} style={{ width: "auto" }}>
          <option value="">{t("Сите градови")}</option>
          {cities?.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
        </select>
      </div>
      <div className="chips" role="group" aria-label={t("Тип на услуга")}>
        {KINDS.map(([k, l]) => (
          <button key={k} type="button" className={kind === k ? "chip on" : "chip"} aria-pressed={kind === k} onClick={() => setParam("type", k)}>
            {k && <Icon name={KIND_ICON[k]} size={16} />}{l}{k ? ` ${counts[k] || 0}` : ""}
          </button>
        ))}
      </div>
      {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">{t("Отвори ги резервациите")}</Link></div>}
      {err && <ErrorBox message={err} />}
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && shown.length === 0 && <Empty title={t("Нема услуги за избраниот филтер.")} />}
      <div className="grid grid-2">
        {shown.map((b) => {
          const f = form[b.id] || { when: "", guests: 2, pickup: "", destination: "" };
          const upd = (patch: Partial<typeof f>) => setForm({ ...form, [b.id]: { ...f, ...patch } });
          const tr = data?.byBiz[b.id];
          const bookable = b.type === "TAXI" || b.type === "RESTAURANT";
          return (
            <article key={b.id} className="panel stack service-card">
              <div className="service-head">
                <BizLogo b={b} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <h2 style={{ marginBottom: 4 }}><Link className="title-link" to={detailPath(b)}>{b.name}</Link></h2>
                  <Meta items={[t(b.type_label), b.city_name]} />
                  {b.phone && <a className="phone-link" href={`tel:${b.phone.replace(/\s+/g, "")}`}>{b.phone}</a>}
                </div>
                <Stars value={b.avg_rating} count={b.review_count} />
              </div>
              {b.description && <p className="small" style={{ margin: 0 }}>{b.description}</p>}
              {tr && <TransportSummary tr={tr} />}
              {tr?.opening_hours && <p className="small muted" style={{ margin: 0 }}><Icon name="clock" size={14} /> {tr.opening_hours}</p>}
              {bookable && (user ? (
                <>
                  <div className="grid grid-2">
                    <Field label={t("Датум и време")}><input type="datetime-local" value={f.when} onChange={(e) => upd({ when: e.target.value })} /></Field>
                    <Field label={b.type === "TAXI" ? t("Патници") : t("Гости")}><input type="number" min={1} value={f.guests} onChange={(e) => upd({ guests: Number(e.target.value) })} /></Field>
                  </div>
                  {b.type === "TAXI" && (
                    <div className="grid grid-2">
                      <Field label={t("Преземање")}><input value={f.pickup} onChange={(e) => upd({ pickup: e.target.value })} /></Field>
                      <Field label={t("Дестинација")}><input value={f.destination} onChange={(e) => upd({ destination: e.target.value })} /></Field>
                    </div>
                  )}
                  <button className="btn btn-primary btn-sm" style={{ width: "fit-content" }} disabled={!f.when} onClick={() => send(b)}>{t("Испрати барање")}</button>
                </>
              ) : <Link to="/login" className="btn btn-ghost btn-sm" style={{ width: "fit-content" }}>{t("Најави се за да испратиш барање")}</Link>)}
              <Link className="small" to={detailPath(b)}>
                {b.type === "TAXI" ? t("Тарифи, возила и контакт") : b.type === "RESTAURANT" ? t("Мени, работно време и контакт")
                  : b.type === "BUS" ? t("Сите линии и цени") : t("Цени, опрема и контакт")}
              </Link>
            </article>
          );
        })}
      </div>
    </div>
  );
}
