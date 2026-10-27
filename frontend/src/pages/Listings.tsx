import { t } from "../i18n";
import { FormEvent, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../services/api";
import { eur, fmtDateTime, isoDate, useAsync } from "../hooks";
import { useAuth } from "../auth";
import { BizLogo, Empty, ErrorBox, Field, Loading, Meta, Stars } from "../components/ui";
import Photo from "../components/Photo";
import MapView from "../components/MapView";
import Icon from "../components/Icon";
import WeatherCard, { WeatherChip } from "../components/Weather";
import { ReviewsList } from "./Services";
import type { AccommodationResult, BoatTour, Business, Restaurant, TaxiService, TransportService } from "../types";

const AMENITY_LABEL: Record<string, string> = {
  wifi: "Wi-Fi", ac: t("Клима"), parking: t("Паркинг"), kitchen: t("Кујна"), terrace: t("Тераса"), lake_view: t("Поглед на езеро"),
  accessible: t("Пристапно"), pets: t("Миленичиња"),
};
const DAY_LABEL: [string, string][] = [
  ["mon", t("Понеделник")], ["tue", t("Вторник")], ["wed", t("Среда")], ["thu", t("Четврток")], ["fri", t("Петок")], ["sat", t("Сабота")], ["sun", t("Недела")],
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

function ContactCard({ b, extra }: { b: Business; extra?: React.ReactNode }) {
  return (
    <aside className="panel contact-card">
      <h2>{t("Контакт")}</h2>
      <div className="row gap" style={{ alignItems: "center" }}>
        <BizLogo b={b} size={48} />
        <strong className="contact-name">{b.name}</strong>
      </div>
      {b.phone ? (
        <a className="btn btn-primary btn-block contact-phone" href={`tel:${b.phone.replace(/\s+/g, "")}`}>
          <Icon name="phone" size={18} />{b.phone}
        </a>
      ) : <p className="small muted">{t("Бизнисот не објавил телефон.")}</p>}
      {b.email && <a className="contact-line" href={`mailto:${b.email}`}><Icon name="mail" size={18} />{b.email}</a>}
      {b.website && <a className="contact-line" href={b.website} target="_blank" rel="noreferrer"><Icon name="globe" size={18} />{t("Веб-страница")}</a>}
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

  if (!user) return <Link to="/login" className="btn btn-ghost">{t("Најави се за да испратиш барање")}</Link>;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const base = { business_id: b.id, reserved_for: new Date(when).toISOString(), guests, notes, idempotency_key: crypto.randomUUID() };
      const r = await api<{ id: number }>(kind === "TAXI" ? "/taxi-requests/" : "/restaurant-reservations/", {
        method: "POST", json: kind === "TAXI" ? { ...base, pickup, destination } : base,
      });
      setMsg(t("Барањето #{0} е испратено. {1}", { 0: r.id, 1: kind === "TAXI" ? t("Операторот ќе испрати понуда со цена.") : t("Ресторанот ќе го потврди терминот.") }));
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : t("Барањето не е испратено."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="stack" onSubmit={submit}>
      {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">{t("Мои резервации")}</Link></div>}
      {err && <ErrorBox message={err} />}
      <div className="grid grid-2">
        <Field label={t("Датум и време")}><input type="datetime-local" value={when} min={`${isoDate(0)}T00:00`} onChange={(e) => setWhen(e.target.value)} required /></Field>
        <Field label={kind === "TAXI" ? t("Патници (до {0})", { 0: capacity }) : t("Гости (до {0})", { 0: capacity })}>
          <input type="number" min={1} max={capacity} value={guests} onChange={(e) => setGuests(Number(e.target.value))} />
        </Field>
      </div>
      {kind === "TAXI" && (
        <div className="grid grid-2">
          <Field label={t("Преземање")}><input value={pickup} onChange={(e) => setPickup(e.target.value)} placeholder={t("пр. Хотел, улица")} required /></Field>
          <Field label={t("Дестинација")}><input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder={t("пр. Св. Наум")} required /></Field>
        </div>
      )}
      <Field label={t("Белешка (опционално)")}><input value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} /></Field>
      <div><button className="btn btn-primary" disabled={busy || !when}>{busy ? t("Се испраќа") : t("Испрати барање")}</button></div>
    </form>
  );
}

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
      setMsg(t("Барањето #{0} е испратено. Домаќинот ќе го потврди.", { 0: r.id }));
      setRefresh((x) => x + 1);
    } catch (e) {
      setErr(e instanceof Error ? e.message : t("Барањето не е испратено."));
    }
  };

  if (loading) return <Loading />;
  if (error || !acc) return <ErrorBox message={error || t("Огласот не постои.")} />;
  const b = acc.business;

  return (
    <div className="stack-lg">
      <DetailHero img={acc.image_url || b.image_url || b.city_image_url} alt={acc.title} seed={acc.id}
                  kicker={<><Link to="/stay">{t("Сместување")}</Link>, {b.city_name}</>} title={acc.title} />
      <div className="detail-grid">
        <div className="stack-lg">
          <section className="panel stack">
            <Meta items={[t(acc.type_label), t("до {0} гости", { 0: acc.max_guests }), t("{0} спални", { 0: acc.bedrooms }), t("{0} кревети", { 0: acc.beds })]} />
            {acc.description && <p style={{ margin: 0 }}>{acc.description}</p>}
            <div className="chips">{acc.amenities.map((a) => <span key={a} className="chip static">{AMENITY_LABEL[a] || a}</span>)}</div>
          </section>

          <section className="panel stack">
            <h2>{t("Провери достапност")}</h2>
            <div className="grid grid-3">
              <Field label="Check-in"><input type="date" min={isoDate(0)} value={checkIn} onChange={(e) => { setCheckIn(e.target.value); if (e.target.value >= checkOut) setCheckOut(addDays(e.target.value, 1)); }} /></Field>
              <Field label="Check-out"><input type="date" min={addDays(checkIn, 1)} value={checkOut} onChange={(e) => setCheckOut(e.target.value)} /></Field>
              <Field label={t("Гости (до {0})", { 0: acc.max_guests })}><input type="number" min={1} max={acc.max_guests} value={guests} onChange={(e) => setGuests(Number(e.target.value))} /></Field>
            </div>
            {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">{t("Мои резервации")}</Link></div>}
            {err && <ErrorBox message={err} />}
            {avail.loading && <Loading label={t("Се проверува")} />}
            {avail.error && <ErrorBox message={avail.error} />}
            <ul className="plain">
              {avail.data?.units.map((u) => (
                <li key={u.unit_id} className="unit-row">
                  <div>
                    <strong>{u.unit_name}</strong>
                    <div className="small muted">{u.available ? t("{0} ноќи, со сите познати трошоци", { 0: u.nights }) : t("Не е слободно за сите ноќи")}</div>
                  </div>
                  {u.available && <span className="offer-total">{eur(u.total)}</span>}
                  {u.available && (user
                    ? <button className="btn btn-primary btn-sm" onClick={() => book(u.unit_id)}>{t("Испрати барање")}</button>
                    : <Link className="btn btn-ghost btn-sm" to="/login">{t("Најави се")}</Link>)}
                </li>
              ))}
            </ul>
          </section>

          <section className="panel stack">
            <h2>{t("Правила")}</h2>
            <p style={{ margin: 0 }}>{acc.rules || t("Домаќинот нема внесено посебни правила.")}</p>
            <p className="small muted" style={{ margin: 0 }}>
              {t("Бесплатно откажување до")} {acc.free_cancellation_days} {t("дена пред доаѓање. Трошок за чистење:")} {eur(acc.cleaning_fee)}.
            </p>
          </section>

          <section className="panel"><h2>{t("Рецензии")}</h2><ReviewsList businessId={b.id} /></section>
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

function clock(start: string | null, plusMin: number) {
  if (!start) return null;
  const d = new Date(new Date(start).getTime() + plusMin * 60000);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function BoatTourDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data: tour, error, loading, reload } = useAsync(() => api<BoatTour>(`/boat-tours/${id}/`), [id]);
  const [selected, setSelected] = useState<number | null>(null);
  const [seats, setSeats] = useState(2);
  const [showAll, setShowAll] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const dep = tour?.upcoming_departures.find((d) => d.id === selected) || tour?.upcoming_departures[0] || null;
  const stopPoints = useMemo(
    () => (tour?.stops || []).filter((s) => s.lat && s.lng).map((s, i) => ({ lat: s.lat!, lng: s.lng!, label: s.name, order: i + 1, sub: s.note })),
    [tour],
  );

  const book = async () => {
    if (!dep) return;
    setErr(null);
    try {
      const r = await api<{ id: number; total_price: string }>("/boat-reservations/", {
        method: "POST", json: { departure_id: dep.id, seats, idempotency_key: crypto.randomUUID() },
      });
      setMsg(t("Барањето #{0} е испратено ({1}). Операторот ќе го потврди.", { 0: r.id, 1: eur(r.total_price) }));
      reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : t("Барањето не е испратено."));
    }
  };

  if (loading) return <Loading />;
  if (error || !tour) return <ErrorBox message={error || t("Турата не постои.")} />;
  const b = tour.business;
  const hours = Math.floor(tour.duration_min / 60);
  const mins = tour.duration_min % 60;

  return (
    <div className="stack-lg">
      <DetailHero img={b.image_url || b.city_image_url} alt={tour.title} seed={tour.id + 1}
                  kicker={<><Link to="/boat-tours">{t("Бродски тури")}</Link>, {b.city_name}</>} title={tour.title}>
        <div className="banner-facts">
          <span><Icon name="clock" size={16} />{hours} {t("ч")}{mins ? t(" {0} мин", { 0: mins }) : ""}</span>
          <span><Icon name="pin" size={16} />{t("Поаѓа од")} {tour.departure_point}</span>
          <span><Icon name="ticket" size={16} />{eur(tour.price_per_person)} {t("по лице")}</span>
        </div>
      </DetailHero>

      <div className="detail-grid">
        <div className="stack-lg">
          {tour.description && <section className="panel"><h2>{t("За турата")}</h2><p style={{ margin: 0 }}>{tour.description}</p></section>}

          <section className="panel stack">
            <div className="row between wrap gap">
              <h2 style={{ margin: 0 }}>{t("Рута и постојки")}</h2>
              {dep && <span className="small muted">{t("Времиња за поаѓање")} {fmtDateTime(dep.starts_at)}</span>}
            </div>
            {tour.stops.length === 0 ? <p className="muted" style={{ margin: 0 }}>{tour.route}</p> : (
              <ol className="route">
                {tour.stops.map((s, i) => (
                  <li key={i} className={`stop ${i === 0 || i === tour.stops.length - 1 ? "stop-end" : ""}`}>
                    <span className="stop-marker" aria-hidden />
                    <div className="stop-body">
                      <div className="stop-time">{clock(dep?.starts_at || null, s.minutes) || t("+{0} мин", { 0: s.minutes })}</div>
                      <div className="stop-title">{s.name}</div>
                      {s.note && <p className="stop-reason">{s.note}</p>}
                      {!!s.stop_min && <span className="stop-travel">{t("Постојка")} {s.stop_min} {t("мин")}</span>}
                    </div>
                  </li>
                ))}
              </ol>
            )}
            {stopPoints.length > 1 && <MapView points={stopPoints} route height={300} />}
          </section>

          <section className="panel stack">
            <h2>{t("Поаѓања")}</h2>
            {tour.upcoming_departures.length === 0 ? <Empty title={t("Нема закажани поаѓања.")} /> : (
              <>
                <div className="departure-grid" role="radiogroup" aria-label={t("Избери поаѓање")}>
                  {tour.upcoming_departures.slice(0, showAll ? undefined : 12).map((d) => (
                    <button key={d.id} role="radio" aria-checked={dep?.id === d.id} disabled={d.remaining_seats < 1}
                            className={dep?.id === d.id ? "dep on" : "dep"} onClick={() => setSelected(d.id)}>
                      <strong>{fmtDateTime(d.starts_at)}</strong>
                      <span>{d.remaining_seats > 0 ? t("{0} слободни", { 0: d.remaining_seats }) : t("Полно")}</span>
                      <WeatherChip query={`city=${b.city}`} date={d.starts_at.slice(0, 10)} />
                    </button>
                  ))}
                </div>
                {!showAll && tour.upcoming_departures.length > 12 && (
                  <button className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => setShowAll(true)}>
                    {t("Прикажи ги сите {0} поаѓања", { 0: tour.upcoming_departures.length })}
                  </button>
                )}
                {msg && <div className="alert alert-ok">{msg} <Link to="/reservations">{t("Мои резервации")}</Link></div>}
                {err && <ErrorBox message={err} />}
                {dep && (
                  <div className="book-bar">
                    <div>
                      <strong>{fmtDateTime(dep.starts_at)}</strong>
                      <div className="small muted">{seats} × {eur(tour.price_per_person)} = <b>{eur(Number(tour.price_per_person) * seats)}</b></div>
                    </div>
                    <Field label={t("Места")}>
                      <input type="number" min={1} max={dep.remaining_seats} value={seats} onChange={(e) => setSeats(Number(e.target.value))} className="input-sm" />
                    </Field>
                    {user ? <button className="btn btn-primary" onClick={book}>{t("Резервирај")}</button>
                      : <Link className="btn btn-ghost" to="/login">{t("Најави се")}</Link>}
                  </div>
                )}
              </>
            )}
          </section>

          {(tour.includes || tour.rules) && (
            <section className="panel stack">
              {tour.includes && <div><h2>{t("Вклучено во цената")}</h2><p style={{ margin: 0 }}>{tour.includes}</p></div>}
              {tour.rules && <div><h2>{t("Правила")}</h2><p style={{ margin: 0 }}>{tour.rules}</p></div>}
            </section>
          )}
          <section className="panel"><h2>{t("Рецензии")}</h2><ReviewsList businessId={b.id} /></section>
        </div>
        <div className="stack-lg detail-side">
          <ContactCard b={b} />
          <WeatherCard query={`city=${b.city}`} title={b.city_name} />
        </div>
      </div>
    </div>
  );
}

export function TaxiDetail() {
  const { id } = useParams();
  const { data: taxi, error, loading } = useAsync(() => api<TaxiService>(`/taxi-services/${id}/`), [id]);
  if (loading) return <Loading />;
  if (error || !taxi) return <ErrorBox message={error || t("Таксито не постои.")} />;
  const b = taxi.business;
  const fares = taxi.base_fare || taxi.per_km;
  return (
    <div className="stack-lg">
      <DetailHero img={b.image_url || b.city_image_url} alt={b.name} seed={b.id} title={b.name}
                  kicker={<><Link to="/services">{t("Такси")}</Link>, {b.city_name}</>}>
        <div className="banner-facts">
          {taxi.available_24h && <span><Icon name="clock" size={16} />{t("Достапно 0–24")}</span>}
          <span><Icon name="user" size={16} />{t("До")} {taxi.passenger_capacity} {t("патници")}</span>
        </div>
      </DetailHero>
      <div className="detail-grid">
        <div className="stack-lg">
          <section className="panel stack">
            <h2>{t("За службата")}</h2>
            {b.description && <p style={{ margin: 0 }}>{b.description}</p>}
            <dl className="facts">
              <dt>{t("Подрачје")}</dt><dd>{taxi.service_area}</dd>
              {taxi.vehicles && <><dt>{t("Возила")}</dt><dd>{taxi.vehicles}</dd></>}
              {taxi.languages && <><dt>{t("Јазици")}</dt><dd>{taxi.languages}</dd></>}
              <dt>{t("Работно време")}</dt><dd>{taxi.available_24h ? t("0–24, секој ден") : t("Според договор")}</dd>
              <dt>{t("Тарифа")}</dt>
              <dd>{fares ? <>{t("Старт")} {eur(taxi.base_fare)}{t(", по километар")} {eur(taxi.per_km)}</> : t("По понуда за секое возење")}</dd>
            </dl>
            {taxi.fare_info && <p className="small muted" style={{ margin: 0 }}>{taxi.fare_info}</p>}
          </section>
          <section className="panel stack">
            <h2>{t("Барај превоз")}</h2>
            <p className="small muted" style={{ margin: 0 }}>{t("Операторот испраќа понуда со цена, која ја прифаќате во „Мои резервации“.")}</p>
            <RequestForm b={b} kind="TAXI" capacity={taxi.passenger_capacity} />
          </section>
          <section className="panel"><h2>{t("Рецензии")}</h2><ReviewsList businessId={b.id} /></section>
        </div>
        <div className="stack-lg detail-side">
          <ContactCard b={b} />
          <MapView points={[{ lat: b.lat, lng: b.lng, label: b.name }]} height={240} />
        </div>
      </div>
    </div>
  );
}

export function RestaurantDetail() {
  const { id } = useParams();
  const { data: r, error, loading } = useAsync(() => api<Restaurant>(`/restaurants/${id}/`), [id]);
  if (loading) return <Loading />;
  if (error || !r) return <ErrorBox message={error || t("Ресторанот не постои.")} />;
  const b = r.business;
  const today = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"][new Date().getDay()];
  const fmtSpan = (span: string[] | string | null | undefined) =>
    Array.isArray(span) && span.length === 2 ? t("{0} до {1}", { 0: span[0], 1: span[1] }) : span === undefined ? t("нема податок") : t("затворено");
  return (
    <div className="stack-lg">
      <DetailHero img={b.image_url || b.city_image_url} alt={b.name} seed={b.id + 2} title={b.name}
                  kicker={<><Link to="/services">{t("Ресторани")}</Link>, {b.city_name}</>}>
        <div className="banner-facts">
          {r.cuisine && <span><Icon name="fork" size={16} />{r.cuisine}</span>}
          {r.price_range && <span>{r.price_range}</span>}
          <span><Icon name="clock" size={16} />{t("Денес:")} {fmtSpan(r.opening_hours[today])}</span>
        </div>
      </DetailHero>
      <div className="detail-grid">
        <div className="stack-lg">
          {b.description && <section className="panel"><h2>{t("За ресторанот")}</h2><p style={{ margin: 0 }}>{b.description}</p></section>}
          <section className="panel stack">
            <h2>{t("Мени")}</h2>
            {r.menu.length === 0 ? <p className="muted" style={{ margin: 0 }}>{t("Менито не е објавено.")}</p> : (
              <ul className="menu-list">
                {r.menu.map((m, i) => (
                  <li key={i}>
                    <span><strong>{m.name}</strong>{m.note && <span className="small muted"> {m.note}</span>}</span>
                    <span className="menu-dots" aria-hidden />
                    <b>{m.price !== null && m.price !== undefined ? eur(m.price) : t("по ден")}</b>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="panel stack">
            <h2>{t("Резервирај маса")}</h2>
            <RequestForm b={b} kind="RESTAURANT" capacity={r.max_party_size} />
          </section>
          <section className="panel"><h2>{t("Рецензии")}</h2><ReviewsList businessId={b.id} /></section>
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
          <p className="small muted">{t("Мени, цени и работно време ги внесува ресторанот.")}</p>
        </div>
      </div>
    </div>
  );
}

export function TransportDetail() {
  const { id } = useParams();
  const { data: tr, error, loading } = useAsync(() => api<TransportService>(`/transport-services/${id}/`), [id]);
  if (loading) return <Loading />;
  if (error || !tr) return <ErrorBox message={error || t("Услугата не постои.")} />;
  const b = tr.business;
  const isBus = b.type === "BUS";
  const price = (v: number | null) => (v === null || v === undefined ? "—" : eur(v));
  return (
    <div className="stack-lg">
      <DetailHero img={b.image_url || b.city_image_url} alt={b.name} seed={b.id + 3} title={b.name}
                  kicker={<><Link to={`/services?type=${b.type}`}>{isBus ? t("Автобуси") : t("Велосипеди")}</Link>, {b.city_name}</>}>
        <div className="banner-facts">
          {tr.service_area && <span><Icon name="pin" size={16} />{tr.service_area}</span>}
          {tr.opening_hours && <span><Icon name="clock" size={16} />{tr.opening_hours}</span>}
        </div>
      </DetailHero>
      <div className="detail-grid">
        <div className="stack-lg">
          {b.description && <section className="panel"><h2>{isBus ? t("За превозникот") : t("За изнајмувањето")}</h2><p style={{ margin: 0 }}>{b.description}</p></section>}
          {tr.lines.length > 0 && (
            <section className="panel stack">
              <h2>{t("Линии и возен ред")}</h2>
              <table className="table table-cards">
                <thead><tr><th>{t("Линија")}</th><th>{t("Релација")}</th><th>{t("Прв / последен")}</th><th>{t("Честота")}</th><th>{t("Цена")}</th></tr></thead>
                <tbody>
                  {tr.lines.map((l) => (
                    <tr key={l.code}>
                      <td data-label={t("Линија")}><span className="line-code">{l.code}</span></td>
                      <td data-label={t("Релација")}><strong>{l.name}</strong><br /><span className="small muted">{l.route} · {t("{0} мин", { 0: l.duration_min })}</span></td>
                      <td data-label={t("Прв / последен")}>{l.first} – {l.last}</td>
                      <td data-label={t("Честота")}>{t("на {0} мин", { 0: l.every_min })}</td>
                      <td data-label={t("Цена")}>{eur(l.price)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
          {tr.rentals.length > 0 && (
            <section className="panel stack">
              <h2>{t("Ценовник")}</h2>
              <table className="table table-cards">
                <thead><tr><th>{t("Возило / услуга")}</th><th>{t("На час")}</th><th>{t("На ден")}</th></tr></thead>
                <tbody>
                  {tr.rentals.map((r) => (
                    <tr key={r.name}>
                      <td data-label={t("Возило / услуга")}><strong>{r.name}</strong></td>
                      <td data-label={t("На час")}>{price(r.per_hour)}</td>
                      <td data-label={t("На ден")}>{price(r.per_day)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
          {(tr.price_info || tr.features.length > 0) && (
            <section className="panel stack">
              <h2>{t("Добро е да знаете")}</h2>
              {tr.price_info && <p style={{ margin: 0 }}>{tr.price_info}</p>}
              {tr.features.length > 0 && <div className="chips">{tr.features.map((f) => <span key={f} className="chip static"><Icon name="check" size={14} />{f}</span>)}</div>}
            </section>
          )}
          <section className="panel"><h2>{t("Рецензии")}</h2><ReviewsList businessId={b.id} /></section>
        </div>
        <div className="stack-lg detail-side">
          <ContactCard b={b} extra={<>
            {tr.payment && <span className="contact-line"><Icon name="ticket" size={18} />{tr.payment}</span>}
            {tr.languages && <span className="contact-line"><Icon name="globe" size={18} />{tr.languages}</span>}
          </>} />
          <MapView points={[{ lat: b.lat, lng: b.lng, label: b.name }]} height={240} />
          <p className="small muted">{t("Демо податоци: возниот ред и цените ги внесува превозникот и треба да се проверат.")}</p>
        </div>
      </div>
    </div>
  );
}
