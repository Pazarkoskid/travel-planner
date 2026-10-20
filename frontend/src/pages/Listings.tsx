import { FormEvent, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../services/api";
import { eur, fmtDateTime, isoDate, useAsync } from "../hooks";
import { useAuth } from "../auth";
import { Empty, ErrorBox, Field, Loading, Meta, Stars } from "../components/ui";
import Photo from "../components/Photo";
import MapView from "../components/MapView";
import Icon from "../components/Icon";
import WeatherCard, { WeatherChip } from "../components/Weather";
import { ReviewsList } from "./Services";
import type { AccommodationResult, BoatTour, Business, Restaurant, TaxiService } from "../types";

const AMENITY_LABEL: Record<string, string> = {
  wifi: "Wi-Fi", ac: "Клима", parking: "Паркинг", kitchen: "Кујна", terrace: "Тераса", lake_view: "Поглед на езеро",
  accessible: "Пристапно", pets: "Миленичиња",
};
const DAY_LABEL: [string, string][] = [
  ["mon", "Понеделник"], ["tue", "Вторник"], ["wed", "Среда"], ["thu", "Четврток"], ["fri", "Петок"], ["sat", "Сабота"], ["sun", "Недела"],
];

function addDays(iso: string, n: number) {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function DetailHero({ img, alt, seed, kicker, title, children }: {
  img?: string; alt: string; seed: number; kicker: React.ReactNode; title: string; children?: React.ReactNode;
}) {
  return (
    <div className="place-banner listing-banner">
      <Photo src={img} alt={alt} seed={seed} eager />
      <div className="place-banner-text">
        <p className="kicker">{kicker}</p>
        <h1>{title}</h1>
        {children}
      </div>
    </div>
  );
}

/** Контакт на бизнисот. Телефонот е линк за повик на мобилен. */
function ContactCard({ b, extra }: { b: Business; extra?: React.ReactNode }) {
  return (
    <aside className="panel contact-card">
      <h2>Контакт</h2>
      <strong className="contact-name">{b.name}</strong>
      {b.phone ? (
        <a className="btn btn-primary btn-block contact-phone" href={`tel:${b.phone.replace(/\s+/g, "")}`}>
          <Icon name="phone" size={18} />{b.phone}
        </a>
      ) : <p className="small muted">Бизнисот не објавил телефон.</p>}
      {b.email && <a className="contact-line" href={`mailto:${b.email}`}><Icon name="mail" size={18} />{b.email}</a>}
      {b.website && <a className="contact-line" href={b.website} target="_blank" rel="noreferrer"><Icon name="globe" size={18} />Веб-страница</a>}
      {b.address && <span className="contact-line"><Icon name="pin" size={18} />{b.address}, {b.city_name}</span>}
      {extra}
      <Stars value={b.avg_rating} count={b.review_count} />
    </aside>
  );
}

function RequestForm({ b, kind, capacity }: { b: Business; kind: "TAXI" | "RESTAURANT"; capacity: number }) {
  const { user } = useAuth();
  const [when, setWhen] = useState("");
  const [guests, setGuests] = useState(2);
  const [pickup, setPickup] = useState("");
  const [destination, setDestination] = useState("");
  const [notes, setNotes] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!user) return <Link to="/login" className="btn btn-ghost">Најави се за да испратиш барање</Link>;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const base = { business_id: b.id, reserved_for: new Date(when).toISOString(), guests, notes, idempotency_key: crypto.randomUUID() };
      const r = await api<{ id: number }>(kind === "TAXI" ? "/taxi-requests/" : "/restaurant-reservations/", {
        method: "POST", json: kind === "TAXI" ? { ...base, pickup, destination } : base,
      });
      setMsg(`Барањето #${r.id} е испратено. ${kind === "TAXI" ? "Операторот ќе испрати понуда со цена." : "Ресторанот ќе го потврди терминот."}`);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "Барањето не е испратено.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="stack" onSubmit={submit}>
      {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">Мои резервации</Link></div>}
      {err && <ErrorBox message={err} />}
      <div className="grid grid-2">
        <Field label="Датум и време"><input type="datetime-local" value={when} min={`${isoDate(0)}T00:00`} onChange={(e) => setWhen(e.target.value)} required /></Field>
        <Field label={kind === "TAXI" ? `Патници (до ${capacity})` : `Гости (до ${capacity})`}>
          <input type="number" min={1} max={capacity} value={guests} onChange={(e) => setGuests(Number(e.target.value))} />
        </Field>
      </div>
      {kind === "TAXI" && (
        <div className="grid grid-2">
          <Field label="Преземање"><input value={pickup} onChange={(e) => setPickup(e.target.value)} placeholder="пр. Хотел, улица" required /></Field>
          <Field label="Дестинација"><input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="пр. Св. Наум" required /></Field>
        </div>
      )}
      <Field label="Белешка (опционално)"><input value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} /></Field>
      <div><button className="btn btn-primary" disabled={busy || !when}>{busy ? "Се испраќа" : "Испрати барање"}</button></div>
    </form>
  );
}

/* ============================ Сместување ============================ */

export function AccommodationDetail() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const { user } = useAuth();
  const { data: acc, error, loading } = useAsync(() => api<AccommodationResult>(`/accommodations/${id}/`), [id]);
  const [checkIn, setCheckIn] = useState(params.get("check_in") || isoDate(7));
  const [checkOut, setCheckOut] = useState(params.get("check_out") || addDays(params.get("check_in") || isoDate(7), 3));
  const [guests, setGuests] = useState(Number(params.get("guests") || 2));
  const [refresh, setRefresh] = useState(0);
  const avail = useAsync(
    () => api<{ units: { unit_id: number; unit_name: string; available: boolean; nights: number | null; total: string | null }[] }>(
      `/accommodations/${id}/availability/?check_in=${checkIn}&check_out=${checkOut}`),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [id, checkIn, checkOut, refresh],
  );
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const book = async (unitId: number) => {
    setErr(null);
    try {
      const r = await api<{ id: number }>("/accommodation-bookings/", {
        method: "POST", json: { unit_id: unitId, check_in: checkIn, check_out: checkOut, guests, idempotency_key: crypto.randomUUID() },
      });
      setMsg(`Барањето #${r.id} е испратено. Домаќинот ќе го потврди.`);
      setRefresh((x) => x + 1);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Барањето не е испратено.");
    }
  };

  if (loading) return <Loading />;
  if (error || !acc) return <ErrorBox message={error || "Огласот не постои."} />;
  const b = acc.business;

  return (
    <div className="stack-lg">
      <DetailHero img={acc.image_url || b.image_url || b.city_image_url} alt={acc.title} seed={acc.id}
                  kicker={<><Link to="/stay">Сместување</Link>, {b.city_name}</>} title={acc.title} />
      <div className="detail-grid">
        <div className="stack-lg">
          <section className="panel stack">
            <Meta items={[acc.type_label, `до ${acc.max_guests} гости`, `${acc.bedrooms} спални`, `${acc.beds} кревети`]} />
            {acc.description && <p style={{ margin: 0 }}>{acc.description}</p>}
            <div className="chips">{acc.amenities.map((a) => <span key={a} className="chip static">{AMENITY_LABEL[a] || a}</span>)}</div>
          </section>

          <section className="panel stack">
            <h2>Провери достапност</h2>
            <div className="grid grid-3">
              <Field label="Check-in"><input type="date" min={isoDate(0)} value={checkIn} onChange={(e) => { setCheckIn(e.target.value); if (e.target.value >= checkOut) setCheckOut(addDays(e.target.value, 1)); }} /></Field>
              <Field label="Check-out"><input type="date" min={addDays(checkIn, 1)} value={checkOut} onChange={(e) => setCheckOut(e.target.value)} /></Field>
              <Field label={`Гости (до ${acc.max_guests})`}><input type="number" min={1} max={acc.max_guests} value={guests} onChange={(e) => setGuests(Number(e.target.value))} /></Field>
            </div>
            {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">Мои резервации</Link></div>}
            {err && <ErrorBox message={err} />}
            {avail.loading && <Loading label="Се проверува" />}
            {avail.error && <ErrorBox message={avail.error} />}
            <ul className="plain">
              {avail.data?.units.map((u) => (
                <li key={u.unit_id} className="unit-row">
                  <div>
                    <strong>{u.unit_name}</strong>
                    <div className="small muted">{u.available ? `${u.nights} ноќи, со сите познати трошоци` : "Не е слободно за сите ноќи"}</div>
                  </div>
                  {u.available && <span className="offer-total">{eur(u.total)}</span>}
                  {u.available && (user
                    ? <button className="btn btn-primary btn-sm" onClick={() => book(u.unit_id)}>Испрати барање</button>
                    : <Link className="btn btn-ghost btn-sm" to="/login">Најави се</Link>)}
                </li>
              ))}
            </ul>
          </section>

          <section className="panel stack">
            <h2>Правила</h2>
            <p style={{ margin: 0 }}>{acc.rules || "Домаќинот нема внесено посебни правила."}</p>
            <p className="small muted" style={{ margin: 0 }}>
              Бесплатно откажување до {acc.free_cancellation_days} дена пред доаѓање. Трошок за чистење: {eur(acc.cleaning_fee)}.
            </p>
          </section>

          <section className="panel"><h2>Рецензии</h2><ReviewsList businessId={b.id} /></section>
        </div>
        <div className="stack-lg detail-side">
          <ContactCard b={b} />
          <MapView points={[{ lat: b.lat, lng: b.lng, label: b.name }]} height={240} />
          <WeatherCard query={`city=${b.city}`} title={b.city_name} />
        </div>
      </div>
    </div>
  );
}

/* ============================ Бродска тура ============================ */

function clock(start: string | null, plusMin: number) {
  if (!start) return null;
  const d = new Date(new Date(start).getTime() + plusMin * 60000);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function BoatTourDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data: t, error, loading, reload } = useAsync(() => api<BoatTour>(`/boat-tours/${id}/`), [id]);
  const [selected, setSelected] = useState<number | null>(null);
  const [seats, setSeats] = useState(2);
  const [showAll, setShowAll] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const dep = t?.upcoming_departures.find((d) => d.id === selected) || t?.upcoming_departures[0] || null;
  const stopPoints = useMemo(
    () => (t?.stops || []).filter((s) => s.lat && s.lng).map((s, i) => ({ lat: s.lat!, lng: s.lng!, label: s.name, order: i + 1, sub: s.note })),
    [t],
  );

  const book = async () => {
    if (!dep) return;
    setErr(null);
    try {
      const r = await api<{ id: number; total_price: string }>("/boat-reservations/", {
        method: "POST", json: { departure_id: dep.id, seats, idempotency_key: crypto.randomUUID() },
      });
      setMsg(`Барањето #${r.id} е испратено (${eur(r.total_price)}). Операторот ќе го потврди.`);
      reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Барањето не е испратено.");
    }
  };

  if (loading) return <Loading />;
  if (error || !t) return <ErrorBox message={error || "Турата не постои."} />;
  const b = t.business;
  const hours = Math.floor(t.duration_min / 60);
  const mins = t.duration_min % 60;

  return (
    <div className="stack-lg">
      <DetailHero img={b.image_url || b.city_image_url} alt={t.title} seed={t.id + 1}
                  kicker={<><Link to="/boat-tours">Бродски тури</Link>, {b.city_name}</>} title={t.title}>
        <div className="banner-facts">
          <span><Icon name="clock" size={16} />{hours} ч{mins ? ` ${mins} мин` : ""}</span>
          <span><Icon name="pin" size={16} />Поаѓа од {t.departure_point}</span>
          <span><Icon name="ticket" size={16} />{eur(t.price_per_person)} по лице</span>
        </div>
      </DetailHero>

      <div className="detail-grid">
        <div className="stack-lg">
          {t.description && <section className="panel"><h2>За турата</h2><p style={{ margin: 0 }}>{t.description}</p></section>}

          <section className="panel stack">
            <div className="row between wrap gap">
              <h2 style={{ margin: 0 }}>Рута и постојки</h2>
              {dep && <span className="small muted">Времиња за поаѓање {fmtDateTime(dep.starts_at)}</span>}
            </div>
            {t.stops.length === 0 ? <p className="muted" style={{ margin: 0 }}>{t.route}</p> : (
              <ol className="route">
                {t.stops.map((s, i) => (
                  <li key={i} className={`stop ${i === 0 || i === t.stops.length - 1 ? "stop-end" : ""}`}>
                    <span className="stop-marker" aria-hidden />
                    <div className="stop-body">
                      <div className="stop-time">{clock(dep?.starts_at || null, s.minutes) || `+${s.minutes} мин`}</div>
                      <div className="stop-title">{s.name}</div>
                      {s.note && <p className="stop-reason">{s.note}</p>}
                      {!!s.stop_min && <span className="stop-travel">Постојка {s.stop_min} мин</span>}
                    </div>
                  </li>
                ))}
              </ol>
            )}
            {stopPoints.length > 1 && <MapView points={stopPoints} route height={300} />}
          </section>

          <section className="panel stack">
            <h2>Поаѓања</h2>
            {t.upcoming_departures.length === 0 ? <Empty title="Нема закажани поаѓања." /> : (
              <>
                <div className="departure-grid" role="radiogroup" aria-label="Избери поаѓање">
                  {t.upcoming_departures.slice(0, showAll ? undefined : 12).map((d) => (
                    <button key={d.id} role="radio" aria-checked={dep?.id === d.id} disabled={d.remaining_seats < 1}
                            className={dep?.id === d.id ? "dep on" : "dep"} onClick={() => setSelected(d.id)}>
                      <strong>{fmtDateTime(d.starts_at)}</strong>
                      <span>{d.remaining_seats > 0 ? `${d.remaining_seats} слободни` : "Полно"}</span>
                      <WeatherChip query={`city=${b.city}`} date={d.starts_at.slice(0, 10)} />
                    </button>
                  ))}
                </div>
                {!showAll && t.upcoming_departures.length > 12 && (
                  <button className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => setShowAll(true)}>
                    Прикажи ги сите {t.upcoming_departures.length} поаѓања
                  </button>
                )}
                {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">Мои резервации</Link></div>}
                {err && <ErrorBox message={err} />}
                {dep && (
                  <div className="book-bar">
                    <div>
                      <strong>{fmtDateTime(dep.starts_at)}</strong>
                      <div className="small muted">{seats} × {eur(t.price_per_person)} = <b>{eur(Number(t.price_per_person) * seats)}</b></div>
                    </div>
                    <Field label="Места">
                      <input type="number" min={1} max={dep.remaining_seats} value={seats} onChange={(e) => setSeats(Number(e.target.value))} className="input-sm" />
                    </Field>
                    {user ? <button className="btn btn-primary" onClick={book}>Резервирај</button>
                      : <Link className="btn btn-ghost" to="/login">Најави се</Link>}
                  </div>
                )}
              </>
            )}
          </section>

          {(t.includes || t.rules) && (
            <section className="panel stack">
              {t.includes && <div><h2>Вклучено во цената</h2><p style={{ margin: 0 }}>{t.includes}</p></div>}
              {t.rules && <div><h2>Правила</h2><p style={{ margin: 0 }}>{t.rules}</p></div>}
            </section>
          )}
          <section className="panel"><h2>Рецензии</h2><ReviewsList businessId={b.id} /></section>
        </div>
        <div className="stack-lg detail-side">
          <ContactCard b={b} />
          <WeatherCard query={`city=${b.city}`} title={b.city_name} />
        </div>
      </div>
    </div>
  );
}

/* ============================ Такси ============================ */

export function TaxiDetail() {
  const { id } = useParams();
  const { data: t, error, loading } = useAsync(() => api<TaxiService>(`/taxi-services/${id}/`), [id]);
  if (loading) return <Loading />;
  if (error || !t) return <ErrorBox message={error || "Таксито не постои."} />;
  const b = t.business;
  const fares = t.base_fare || t.per_km;
  return (
    <div className="stack-lg">
      <DetailHero img={b.image_url || b.city_image_url} alt={b.name} seed={b.id} title={b.name}
                  kicker={<><Link to="/services">Такси</Link>, {b.city_name}</>}>
        <div className="banner-facts">
          {t.available_24h && <span><Icon name="clock" size={16} />Достапно 0–24</span>}
          <span><Icon name="user" size={16} />До {t.passenger_capacity} патници</span>
        </div>
      </DetailHero>
      <div className="detail-grid">
        <div className="stack-lg">
          <section className="panel stack">
            <h2>За службата</h2>
            {b.description && <p style={{ margin: 0 }}>{b.description}</p>}
            <dl className="facts">
              <dt>Подрачје</dt><dd>{t.service_area}</dd>
              {t.vehicles && <><dt>Возила</dt><dd>{t.vehicles}</dd></>}
              {t.languages && <><dt>Јазици</dt><dd>{t.languages}</dd></>}
              <dt>Работно време</dt><dd>{t.available_24h ? "0–24, секој ден" : "Според договор"}</dd>
              <dt>Тарифа</dt>
              <dd>{fares ? <>Старт {eur(t.base_fare)}, по километар {eur(t.per_km)}</> : "По понуда за секое возење"}</dd>
            </dl>
            {t.fare_info && <p className="small muted" style={{ margin: 0 }}>{t.fare_info}</p>}
          </section>
          <section className="panel stack">
            <h2>Барај превоз</h2>
            <p className="small muted" style={{ margin: 0 }}>Операторот испраќа понуда со цена, која ја прифаќате во „Мои резервации“.</p>
            <RequestForm b={b} kind="TAXI" capacity={t.passenger_capacity} />
          </section>
          <section className="panel"><h2>Рецензии</h2><ReviewsList businessId={b.id} /></section>
        </div>
        <div className="stack-lg detail-side">
          <ContactCard b={b} />
          <MapView points={[{ lat: b.lat, lng: b.lng, label: b.name }]} height={240} />
        </div>
      </div>
    </div>
  );
}

/* ============================ Ресторан ============================ */

export function RestaurantDetail() {
  const { id } = useParams();
  const { data: r, error, loading } = useAsync(() => api<Restaurant>(`/restaurants/${id}/`), [id]);
  if (loading) return <Loading />;
  if (error || !r) return <ErrorBox message={error || "Ресторанот не постои."} />;
  const b = r.business;
  const today = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"][new Date().getDay()];
  const fmtSpan = (span: string[] | string | null | undefined) =>
    Array.isArray(span) && span.length === 2 ? `${span[0]} до ${span[1]}` : span === undefined ? "нема податок" : "затворено";
  return (
    <div className="stack-lg">
      <DetailHero img={b.image_url || b.city_image_url} alt={b.name} seed={b.id + 2} title={b.name}
                  kicker={<><Link to="/services">Ресторани</Link>, {b.city_name}</>}>
        <div className="banner-facts">
          {r.cuisine && <span><Icon name="fork" size={16} />{r.cuisine}</span>}
          {r.price_range && <span>{r.price_range}</span>}
          <span><Icon name="clock" size={16} />Денес: {fmtSpan(r.opening_hours[today])}</span>
        </div>
      </DetailHero>
      <div className="detail-grid">
        <div className="stack-lg">
          {b.description && <section className="panel"><h2>За ресторанот</h2><p style={{ margin: 0 }}>{b.description}</p></section>}
          <section className="panel stack">
            <h2>Мени</h2>
            {r.menu.length === 0 ? <p className="muted" style={{ margin: 0 }}>Менито не е објавено.</p> : (
              <ul className="menu-list">
                {r.menu.map((m, i) => (
                  <li key={i}>
                    <span><strong>{m.name}</strong>{m.note && <span className="small muted"> {m.note}</span>}</span>
                    <span className="menu-dots" aria-hidden />
                    <b>{m.price !== null && m.price !== undefined ? eur(m.price) : "по ден"}</b>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="panel stack">
            <h2>Резервирај маса</h2>
            <RequestForm b={b} kind="RESTAURANT" capacity={r.max_party_size} />
          </section>
          <section className="panel"><h2>Рецензии</h2><ReviewsList businessId={b.id} /></section>
        </div>
        <div className="stack-lg detail-side">
          <ContactCard b={b} extra={
            <dl className="hours">
              {DAY_LABEL.map(([k, l]) => (
                <div key={k} className={k === today ? "today" : ""}><dt>{l}</dt><dd>{fmtSpan(r.opening_hours[k])}</dd></div>
              ))}
            </dl>
          } />
          <MapView points={[{ lat: b.lat, lng: b.lng, label: b.name }]} height={240} />
          <p className="small muted">Мени, цени и работно време ги внесува ресторанот.</p>
        </div>
      </div>
    </div>
  );
}
