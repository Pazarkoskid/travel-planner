import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../services/api";
import { eur, fmtDateTime, isoDate, useAsync } from "../hooks";
import { useAuth } from "../auth";
import { Empty, ErrorBox, Field, Loading, Meta, Stars } from "../components/ui";
import Photo from "../components/Photo";
import type { AccommodationResult, BoatTour, Business, City, Review } from "../types";

const AMENITIES: [string, string][] = [
  ["wifi", "Wi-Fi"], ["ac", "Клима"], ["parking", "Паркинг"], ["kitchen", "Кујна"], ["terrace", "Тераса"], ["lake_view", "Поглед на езеро"],
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      setBooked(`Барањето #${res.id} е испратено до „${r.business.name}“. Статус: чека одговор.`);
      setSearch((s) => s + 1);
    } catch (e) {
      setBookError(e instanceof Error ? e.message : "Грешка");
    }
  };

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Сместување</h1>
          <p>Цената е пресметана за секоја ноќ од престојот, со сите познати трошоци.</p>
        </div>
      </div>
      <form className="panel stack" onSubmit={(e: FormEvent) => { e.preventDefault(); setSearch((s) => s + 1); }}>
        <div className="grid grid-5">
          <Field label="Град">
            <select value={q.city} onChange={set("city")}>
              {cities?.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
              {cities && !cities.some((c) => c.slug === q.city) && <option value={q.city}>избран град</option>}
            </select>
          </Field>
          <Field label="Check-in"><input type="date" min={isoDate(0)} value={q.check_in} onChange={set("check_in")} /></Field>
          <Field label="Check-out"><input type="date" min={q.check_in} value={q.check_out} onChange={set("check_out")} /></Field>
          <Field label="Гости"><input type="number" min={1} value={q.guests} onChange={set("guests")} /></Field>
          <Field label="Макс. вкупно (EUR)"><input type="number" min={0} value={q.max_total} onChange={set("max_total")} /></Field>
        </div>
        <div className="chips">
          {AMENITIES.map(([k, l]) => (
            <button type="button" key={k} className={amen.includes(k) ? "chip on" : "chip"} aria-pressed={amen.includes(k)}
                    onClick={() => setAmen(amen.includes(k) ? amen.filter((a) => a !== k) : [...amen, k])}>{l}</button>
          ))}
        </div>
        <div><button className="btn btn-primary">Пребарај</button></div>
      </form>
      {booked && <div className="alert alert-ok">{booked} <Link to="/reservations">Отвори ги резервациите</Link></div>}
      {bookError && <ErrorBox message={bookError} />}
      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {data && data.length === 0 && <Empty title="Нема достапно сместување за овие критериуми.">Пробајте други датуми или помалку филтри.</Empty>}
      {data?.map((r) => (
        <article key={r.id} className="panel offer offer-with-photo">
          <Photo className="offer-photo" src={r.business.image_url || r.business.city_image_url} alt={r.title} seed={r.id} />
          <div className="stack" style={{ gap: 10 }}>
            <div>
              {r.business.is_sponsored && <span className="sponsored">Спонзорирано</span>}
              <h2 style={{ marginBottom: 4 }}><Link className="title-link" to={`/stay/${r.id}?check_in=${q.check_in}&check_out=${q.check_out}&guests=${q.guests}`}>{r.title}</Link></h2>
              <Meta items={[r.business.name, r.type_label, `до ${r.max_guests} гости`, `${r.bedrooms} спални`]} />
            </div>
            <div className="chips">{r.amenities.map((a) => <span className="chip static" key={a}>{AMENITIES.find(([k]) => k === a)?.[1] || a}</span>)}</div>
            <p className="small" style={{ margin: 0 }}>Зошто е предложено: {r.recommendation_reason}.</p>
            <p className="small muted" style={{ margin: 0 }}>{r.rules} Бесплатно откажување до {r.free_cancellation_days} дена пред доаѓање.</p>
            <Link className="small" to={`/stay/${r.id}?check_in=${q.check_in}&check_out=${q.check_out}&guests=${q.guests}`}>Види го огласот</Link>
          </div>
          <div className="offer-price">
            <Stars value={r.avg_rating} count={r.review_count} />
            {r.quote ? (
              <>
                <span className="offer-total">{eur(r.quote.total)}</span>
                <span className="small muted">{r.quote.nights} ноќи {eur(r.quote.subtotal)}, трошоци {eur(r.quote.fees)}</span>
                {user ? <button className="btn btn-primary btn-block" onClick={() => book(r)}>Испрати барање</button>
                  : <Link className="btn btn-ghost btn-block" to="/login">Најави се за да резервираш</Link>}
              </>
            ) : <span className="small muted">Изберете датуми за цена.</span>}
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
      <button className="link-btn small" onClick={() => setOpen(!open)}>{open ? "Скриј рецензии" : "Прикажи рецензии"}</button>
      {open && data && (data.length === 0 ? <p className="small muted">Сè уште нема рецензии.</p> : (
        <ul className="reviews">
          {data.map((rv) => (
            <li key={rv.id}>
              <strong>★ {rv.rating}</strong> {rv.username}
               {rv.is_verified_booking && <span className="pill pill-ok">Проверена резервација</span>}
              <p>{rv.comment}</p>
              {rv.reply && <p className="reply"><strong>Одговор од бизнисот:</strong> {rv.reply.reply_text}</p>}
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
      setMsg(`Барањето #${r.id} е испратено (${eur(r.total_price)}).`);
      reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Грешка");
    }
  };

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Бродски тури</h1>
          <p>Слободните места се ажурираат при секое барање. Барањето го потврдува операторот.</p>
        </div>
      </div>
      {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">Отвори ги резервациите</Link></div>}
      {err && <ErrorBox message={err} />}
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data?.map((t) => (
        <article key={t.id} className="panel stack">
          <Photo className="tour-photo" src={t.business.image_url || t.business.city_image_url} alt={t.title} seed={t.id + 1} />
          <div className="row between wrap gap">
            <div>
              <h2 style={{ marginBottom: 4 }}><Link className="title-link" to={`/boat-tours/${t.id}`}>{t.title}</Link></h2>
              <Meta items={[t.business.name, t.route, `${Math.round(t.duration_min / 60)} часа`, `поаѓа од ${t.departure_point}`]} />
            </div>
            <div className="price-block">
              <span className="offer-total">{eur(t.price_per_person)}</span>
              <span className="small muted">по лице</span>
            </div>
          </div>
          {t.description && <p style={{ margin: 0 }}>{t.description}</p>}
          {t.stops.length > 0 && (
            <p className="small muted" style={{ margin: 0 }}>Постојки: {t.stops.map((s) => s.name).join(", ")}</p>
          )}
          <Link className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }} to={`/boat-tours/${t.id}`}>Детали, рута и сите поаѓања</Link>
          <table className="table table-cards">
            <thead><tr><th>Поаѓање</th><th>Слободни места</th><th>Колку места</th><th /></tr></thead>
            <tbody>
              {t.upcoming_departures.slice(0, showAll[t.id] ? undefined : 4).map((d) => (
                <tr key={d.id}>
                  <td data-label="Поаѓање">{fmtDateTime(d.starts_at)}</td>
                  <td data-label="Слободни">{d.remaining_seats} од {d.capacity}</td>
                  <td data-label="Места">
                    <input type="number" min={1} max={d.remaining_seats} value={seats[d.id] || 1} aria-label="Број места"
                           onChange={(e) => setSeats({ ...seats, [d.id]: Number(e.target.value) })} className="input-sm" />
                  </td>
                  <td className="td-actions">
                    {user ? <button className="btn btn-primary btn-sm" disabled={d.remaining_seats < 1} onClick={() => book(d.id)}>Резервирај</button>
                      : <Link to="/login" className="small">Најава</Link>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {t.upcoming_departures.length > 4 && !showAll[t.id] && (
            <button className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => setShowAll({ ...showAll, [t.id]: true })}>
              Прикажи ги сите поаѓања ({t.upcoming_departures.length})
            </button>
          )}
        </article>
      ))}
    </div>
  );
}

export function OtherServices() {
  const { user } = useAuth();
  const { data } = useAsync(async () => {
    const r = await api<Business[] | { results: Business[] }>("/businesses/");
    return (Array.isArray(r) ? r : r.results).filter((b) => b.type === "RESTAURANT" || b.type === "TAXI");
  }, []);
  const [form, setForm] = useState<Record<number, { when: string; guests: number; pickup: string; destination: string }>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const send = async (b: Business) => {
    const f = form[b.id] || { when: "", guests: 2, pickup: "", destination: "" };
    setErr(null);
    try {
      const reserved_for = new Date(f.when).toISOString();
      const path = b.type === "TAXI" ? "/taxi-requests/" : "/restaurant-reservations/";
      const json = b.type === "TAXI" ? { business_id: b.id, reserved_for, guests: f.guests, pickup: f.pickup, destination: f.destination }
        : { business_id: b.id, reserved_for, guests: f.guests };
      const r = await api<{ id: number }>(path, { method: "POST", json: { ...json, idempotency_key: crypto.randomUUID() } });
      setMsg(`Барањето #${r.id} е испратено до „${b.name}“.`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Внесете валиден датум и време.");
    }
  };

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Ресторани и такси</h1>
          <p>Барањето не е гаранција. Бизнисот го прифаќа, одбива или предлага друг термин; таксито испраќа понуда со цена.</p>
        </div>
      </div>
      {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">Отвори ги резервациите</Link></div>}
      {err && <ErrorBox message={err} />}
      <div className="grid grid-2">
        {data?.map((b) => {
          const f = form[b.id] || { when: "", guests: 2, pickup: "", destination: "" };
          const upd = (patch: Partial<typeof f>) => setForm({ ...form, [b.id]: { ...f, ...patch } });
          return (
            <article key={b.id} className="panel stack">
              <div className="row between wrap gap">
                <div>
                  <h2 style={{ marginBottom: 4 }}><Link className="title-link" to={b.type === "TAXI" ? `/taxi/${b.id}` : `/restaurants/${b.id}`}>{b.name}</Link></h2>
                  <Meta items={[b.type_label, b.city_name]} />
                  {b.phone && <a className="phone-link" href={`tel:${b.phone.replace(/\s+/g, "")}`}>{b.phone}</a>}
                </div>
                <Stars value={b.avg_rating} count={b.review_count} />
              </div>
              {user ? (
                <>
                  <div className="grid grid-2">
                    <Field label="Датум и време"><input type="datetime-local" value={f.when} onChange={(e) => upd({ when: e.target.value })} /></Field>
                    <Field label={b.type === "TAXI" ? "Патници" : "Гости"}><input type="number" min={1} value={f.guests} onChange={(e) => upd({ guests: Number(e.target.value) })} /></Field>
                  </div>
                  {b.type === "TAXI" && (
                    <div className="grid grid-2">
                      <Field label="Преземање"><input value={f.pickup} onChange={(e) => upd({ pickup: e.target.value })} /></Field>
                      <Field label="Дестинација"><input value={f.destination} onChange={(e) => upd({ destination: e.target.value })} /></Field>
                    </div>
                  )}
                  <button className="btn btn-primary btn-sm" disabled={!f.when} onClick={() => send(b)}>Испрати барање</button>
                </>
              ) : <Link to="/login" className="btn btn-ghost btn-sm" style={{ width: "fit-content" }}>Најави се за да испратиш барање</Link>}
              <Link className="small" to={b.type === "TAXI" ? `/taxi/${b.id}` : `/restaurants/${b.id}`}>{b.type === "TAXI" ? "Тарифи, возила и контакт" : "Мени, работно време и контакт"}</Link>
            </article>
          );
        })}
      </div>
    </div>
  );
}
