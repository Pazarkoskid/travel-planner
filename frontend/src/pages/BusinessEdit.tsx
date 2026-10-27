import { t } from "../i18n";
import { FormEvent, ReactNode, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../services/api";
import { fmtDateTime, isoDate, useAsync } from "../hooks";
import { ErrorBox, Field, Loading, StatusPill } from "../components/ui";
import MapView from "../components/MapView";
import Icon from "../components/Icon";
import type { City, Departure, MenuItem, TourStop } from "../types";

interface AccEdit {
  id: number; title: string; property_type: string; description: string; max_guests: number; bedrooms: number; beds: number;
  amenities: string[]; rules: string; cleaning_fee: string; free_cancellation_days: number; image_url: string;
  units: { id: number; unit_name: string }[];
}
interface TourEdit {
  id: number; title: string; route: string; description: string; stops: TourStop[]; includes: string; duration_min: number;
  price_per_person: string; departure_point: string; rules: string; departures: Departure[];
}
interface MyBusiness {
  id: number; name: string; type: "ACCOMMODATION" | "RESTAURANT" | "BOAT_TOUR" | "TAXI"; city: number; description: string;
  address: string; lat: number; lng: number; phone: string; email: string; website: string; image_url: string;
  verification_status: string;
  accommodations?: AccEdit[];
  restaurant?: { opening_hours: Record<string, string[] | string | null>; menu: MenuItem[]; price_range: string; cuisine: string; max_party_size: number };
  boat_tours?: TourEdit[];
  taxi?: { service_area: string; passenger_capacity: number; base_fare: string | null; per_km: string | null; available_24h: boolean; vehicles: string; languages: string; fare_info: string };
}

const TYPE_LABEL = { ACCOMMODATION: t("Сместување"), RESTAURANT: t("Ресторан"), BOAT_TOUR: t("Бродска тура"), TAXI: t("Такси") };
const STATUS_LABEL: Record<string, string> = { APPROVED: t("Одобрен"), PENDING: t("Чека одобрување"), REJECTED: t("Одбиен"), SUSPENDED: t("Суспендиран") };
const AMENITIES: [string, string][] = [["wifi", "Wi-Fi"], ["ac", t("Клима")], ["parking", t("Паркинг")], ["kitchen", t("Кујна")],
  ["terrace", t("Тераса")], ["lake_view", t("Поглед на езеро")], ["accessible", t("Пристапно")], ["pets", t("Миленичиња")]];
const DAYS: [string, string][] = [["mon", t("Понеделник")], ["tue", t("Вторник")], ["wed", t("Среда")], ["thu", t("Четврток")],
  ["fri", t("Петок")], ["sat", t("Сабота")], ["sun", t("Недела")]];

function SaveForm({ title, onSave, children, saveLabel = t("Зачувај промени") }: {
  title: string; onSave: () => Promise<unknown>; children: ReactNode; saveLabel?: string;
}) {
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");
  const [err, setErr] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    setState("saving");
    try {
      await onSave();
      setState("saved");
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : t("Не е зачувано."));
      setState("idle");
    }
  };
  return (
    <form className="panel stack" onSubmit={submit} onChange={() => state === "saved" && setState("idle")}>
      <h2>{title}</h2>
      {err && <ErrorBox message={err} />}
      {children}
      <div className="row gap">
        <button className="btn btn-primary" disabled={state === "saving"}>{state === "saving" ? t("Се зачувува") : saveLabel}</button>
        {state === "saved" && <span className="small saved-note">{t("Зачувано")}</span>}
      </div>
    </form>
  );
}

const num = (v: string) => (v === "" ? null : v);

function ProfileForm({ b, onSaved }: { b: MyBusiness; onSaved: (x: MyBusiness) => void }) {
  const [f, setF] = useState({ name: b.name, description: b.description, address: b.address, phone: b.phone, email: b.email,
    website: b.website, image_url: b.image_url, lat: String(b.lat), lng: String(b.lng) });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <SaveForm title={t("Профил на бизнисот")} onSave={async () => onSaved(await api<MyBusiness>(`/business/my/${b.id}/`, {
      method: "PATCH", json: { ...f, lat: Number(f.lat), lng: Number(f.lng) } }))}>
      <div className="grid grid-2">
        <Field label={t("Име")}><input value={f.name} onChange={set("name")} required /></Field>
        <Field label={t("Телефон")} hint={t("Се прикажува на огласот и може да се повика од мобилен.")}><input type="tel" value={f.phone} onChange={set("phone")} placeholder="+389 …" /></Field>
        <Field label={t("Е-пошта")}><input type="email" value={f.email} onChange={set("email")} /></Field>
        <Field label={t("Веб-страница")}><input type="url" value={f.website} onChange={set("website")} placeholder="https://" /></Field>
        <Field label={t("Адреса")}><input value={f.address} onChange={set("address")} /></Field>
        <Field label={t("Фотографија (URL)")} hint={t("Линк до ваша фотографија.")}><input type="url" value={f.image_url} onChange={set("image_url")} /></Field>
      </div>
      <Field label={t("Опис")}><textarea rows={4} value={f.description} onChange={set("description")} /></Field>
      <div className="grid grid-2">
        <Field label={t("Географска ширина")}><input inputMode="decimal" value={f.lat} onChange={set("lat")} /></Field>
        <Field label={t("Географска должина")}><input inputMode="decimal" value={f.lng} onChange={set("lng")} /></Field>
      </div>
      {Number(f.lat) && Number(f.lng) ? <MapView points={[{ lat: Number(f.lat), lng: Number(f.lng), label: f.name }]} height={200} /> : null}
    </SaveForm>
  );
}

function AccommodationForm({ a, onSaved }: { a: AccEdit; onSaved: () => void }) {
  const [f, setF] = useState({ ...a, cleaning_fee: String(a.cleaning_fee) });
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const toggle = (k: string) => setF({ ...f, amenities: f.amenities.includes(k) ? f.amenities.filter((x) => x !== k) : [...f.amenities, k] });
  return (
    <SaveForm title={a.title} onSave={async () => {
      await api(`/business/accommodations/${a.id}/`, { method: "PATCH", json: {
        title: f.title, property_type: f.property_type, description: f.description, max_guests: Number(f.max_guests),
        bedrooms: Number(f.bedrooms), beds: Number(f.beds), amenities: f.amenities, rules: f.rules,
        cleaning_fee: f.cleaning_fee || "0", free_cancellation_days: Number(f.free_cancellation_days), image_url: f.image_url } });
      onSaved();
    }}>
      <div className="grid grid-3">
        <Field label={t("Наслов")}><input value={f.title} onChange={set("title")} required /></Field>
        <Field label={t("Тип")}>
          <select value={f.property_type} onChange={set("property_type")}>
            <option value="ROOM">{t("Соба")}</option><option value="STUDIO">{t("Студио")}</option><option value="APARTMENT">{t("Апартман")}</option><option value="HOUSE">{t("Цел објект")}</option>
          </select>
        </Field>
        <Field label={t("Фотографија (URL)")}><input type="url" value={f.image_url} onChange={set("image_url")} /></Field>
        <Field label={t("Макс. гости")}><input type="number" min={1} max={30} value={f.max_guests} onChange={set("max_guests")} /></Field>
        <Field label={t("Спални")}><input type="number" min={0} value={f.bedrooms} onChange={set("bedrooms")} /></Field>
        <Field label={t("Кревети")}><input type="number" min={0} value={f.beds} onChange={set("beds")} /></Field>
        <Field label={t("Чистење (EUR)")}><input type="number" min={0} step="0.01" value={f.cleaning_fee} onChange={set("cleaning_fee")} /></Field>
        <Field label={t("Бесплатно откажување (дена пред)")}><input type="number" min={0} value={f.free_cancellation_days} onChange={set("free_cancellation_days")} /></Field>
      </div>
      <Field label={t("Опис")}><textarea rows={3} value={f.description} onChange={set("description")} /></Field>
      <fieldset>
        <legend>{t("Удобности")}</legend>
        <div className="chips">{AMENITIES.map(([k, l]) => (
          <button type="button" key={k} className={f.amenities.includes(k) ? "chip on" : "chip"} aria-pressed={f.amenities.includes(k)} onClick={() => toggle(k)}>{l}</button>
        ))}</div>
      </fieldset>
      <Field label={t("Правила")}><textarea rows={2} value={f.rules} onChange={set("rules")} /></Field>
      {a.units.map((u) => <AvailabilityTool key={u.id} unit={u} />)}
    </SaveForm>
  );
}

function AvailabilityTool({ unit }: { unit: { id: number; unit_name: string } }) {
  const [f, setF] = useState({ start: isoDate(1), end: isoDate(31), available_units: "1", price_per_night: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const apply = async () => {
    setMsg(null); setErr(null);
    try {
      await api(`/business/units/${unit.id}/availability/`, { method: "POST", json: f });
      setMsg(t("Цената и достапноста се поставени од {0} до {1}.", { 0: f.start, 1: f.end }));
    } catch (e) { setErr(e instanceof Error ? e.message : t("Не е зачувано.")); }
  };
  return (
    <div className="subcard stack">
      <strong>{t("Цени и достапност:")} {unit.unit_name}</strong>
      <div className="grid grid-5">
        <Field label={t("Од")}><input type="date" min={isoDate(0)} value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} /></Field>
        <Field label={t("До (не вклучено)")}><input type="date" min={f.start} value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} /></Field>
        <Field label={t("Слободни единици")}><input type="number" min={0} value={f.available_units} onChange={(e) => setF({ ...f, available_units: e.target.value })} /></Field>
        <Field label={t("Цена по ноќ (EUR)")}><input type="number" min={1} step="0.01" value={f.price_per_night} onChange={(e) => setF({ ...f, price_per_night: e.target.value })} /></Field>
        <div className="field"><span className="field-label">&nbsp;</span><button type="button" className="btn btn-ghost" disabled={!f.price_per_night} onClick={apply}>{t("Примени за периодот")}</button></div>
      </div>
      {msg && <span className="small saved-note">{msg}</span>}
      {err && <ErrorBox message={err} />}
    </div>
  );
}

function NewAccommodation({ businessId, onCreated }: { businessId: number; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [type, setType] = useState("APARTMENT");
  const [guests, setGuests] = useState("2");
  if (!open) return <button className="btn btn-ghost" onClick={() => setOpen(true)}><Icon name="plus" size={18} />{t("Додај нов оглас за сместување")}</button>;
  return (
    <SaveForm title={t("Нов оглас")} saveLabel={t("Креирај")} onSave={async () => {
      await api(`/business/my/${businessId}/accommodations/`, { method: "POST", json: { title, property_type: type, max_guests: Number(guests), amenities: [] } });
      setOpen(false); onCreated();
    }}>
      <div className="grid grid-3">
        <Field label={t("Наслов")}><input value={title} onChange={(e) => setTitle(e.target.value)} required /></Field>
        <Field label={t("Тип")}><select value={type} onChange={(e) => setType(e.target.value)}><option value="ROOM">{t("Соба")}</option><option value="STUDIO">{t("Студио")}</option><option value="APARTMENT">{t("Апартман")}</option><option value="HOUSE">{t("Цел објект")}</option></select></Field>
        <Field label={t("Макс. гости")}><input type="number" min={1} value={guests} onChange={(e) => setGuests(e.target.value)} /></Field>
      </div>
      <p className="small muted" style={{ margin: 0 }}>{t("По креирањето внесете цени и достапност за датумите.")}</p>
    </SaveForm>
  );
}

function RestaurantForm({ b, onSaved }: { b: MyBusiness; onSaved: () => void }) {
  const r = b.restaurant!;
  const [hours, setHours] = useState<Record<string, { open: string; close: string; closed: boolean }>>(
    Object.fromEntries(DAYS.map(([k]) => {
      const v = r.opening_hours[k];
      return [k, Array.isArray(v) ? { open: v[0], close: v[1], closed: false } : { open: "10:00", close: "22:00", closed: v === "closed" || v === null }];
    })),
  );
  const [menu, setMenu] = useState<MenuItem[]>(r.menu.length ? r.menu : [{ name: "", price: null }]);
  const [meta, setMeta] = useState({ cuisine: r.cuisine, price_range: r.price_range, max_party_size: String(r.max_party_size) });
  const upd = (i: number, patch: Partial<MenuItem>) => setMenu(menu.map((m, j) => (j === i ? { ...m, ...patch } : m)));
  return (
    <SaveForm title={t("Ресторан: работно време и мени")} onSave={async () => {
      await api(`/business/my/${b.id}/restaurant/`, { method: "PATCH", json: {
        ...meta, max_party_size: Number(meta.max_party_size),
        opening_hours: Object.fromEntries(Object.entries(hours).map(([k, v]) => [k, v.closed ? "closed" : [v.open, v.close]])),
        menu: menu.filter((m) => m.name.trim()),
      } });
      onSaved();
    }}>
      <div className="grid grid-3">
        <Field label={t("Кујна")}><input value={meta.cuisine} onChange={(e) => setMeta({ ...meta, cuisine: e.target.value })} /></Field>
        <Field label={t("Ценовен ранг")}><select value={meta.price_range} onChange={(e) => setMeta({ ...meta, price_range: e.target.value })}><option value="">{t("нема")}</option><option>€</option><option>€€</option><option>€€€</option></select></Field>
        <Field label={t("Макс. гости по маса")}><input type="number" min={1} value={meta.max_party_size} onChange={(e) => setMeta({ ...meta, max_party_size: e.target.value })} /></Field>
      </div>
      <fieldset>
        <legend>{t("Работно време")}</legend>
        <div className="hours-editor">
          {DAYS.map(([k, l]) => (
            <div key={k} className="hours-row">
              <span>{l}</span>
              <input type="time" value={hours[k].open} disabled={hours[k].closed} onChange={(e) => setHours({ ...hours, [k]: { ...hours[k], open: e.target.value } })} aria-label={t("{0} од", { 0: l })} />
              <input type="time" value={hours[k].close} disabled={hours[k].closed} onChange={(e) => setHours({ ...hours, [k]: { ...hours[k], close: e.target.value } })} aria-label={t("{0} до", { 0: l })} />
              <label className="check"><input type="checkbox" checked={hours[k].closed} onChange={(e) => setHours({ ...hours, [k]: { ...hours[k], closed: e.target.checked } })} />{t("Затворено")}</label>
            </div>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend>{t("Мени")}</legend>
        <div className="stack" style={{ gap: 8 }}>
          {menu.map((m, i) => (
            <div key={i} className="menu-row">
              <input placeholder={t("Јадење")} value={m.name} onChange={(e) => upd(i, { name: e.target.value })} aria-label={t("Јадење")} />
              <input type="number" min={0} step="0.01" placeholder={t("Цена €")} value={m.price ?? ""} onChange={(e) => upd(i, { price: e.target.value === "" ? null : Number(e.target.value) })} aria-label={t("Цена")} />
              <input placeholder={t("Белешка")} value={m.note || ""} onChange={(e) => upd(i, { note: e.target.value })} aria-label={t("Белешка")} />
              <button type="button" className="icon-btn" aria-label={t("Отстрани")} onClick={() => setMenu(menu.filter((_, j) => j !== i))}><Icon name="close" size={18} /></button>
            </div>
          ))}
          <button type="button" className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => setMenu([...menu, { name: "", price: null }])}><Icon name="plus" size={16} />{t("Додај ставка")}</button>
        </div>
      </fieldset>
    </SaveForm>
  );
}

function TourForm({ tour, onSaved }: { tour: TourEdit; onSaved: () => void }) {
  const [f, setF] = useState({ title: tour.title, route: tour.route, description: tour.description, includes: tour.includes, rules: tour.rules,
    duration_min: String(tour.duration_min), price_per_person: String(tour.price_per_person), departure_point: tour.departure_point });
  const [stops, setStops] = useState<TourStop[]>(tour.stops);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const upd = (i: number, patch: Partial<TourStop>) => setStops(stops.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const move = (i: number, d: number) => {
    const n = [...stops];
    [n[i], n[i + d]] = [n[i + d], n[i]];
    setStops(n);
  };
  return (
    <SaveForm title={tour.title} onSave={async () => {
      await api(`/business/boat-tours/${tour.id}/`, { method: "PATCH", json: {
        ...f, duration_min: Number(f.duration_min),
        stops: stops.filter((s) => s.name.trim()).map((s) => ({ ...s, minutes: Number(s.minutes) || 0, stop_min: Number(s.stop_min) || 0,
          lat: s.lat === undefined || s.lat === null || (s.lat as unknown) === "" ? null : Number(s.lat),
          lng: s.lng === undefined || s.lng === null || (s.lng as unknown) === "" ? null : Number(s.lng) })),
      } });
      onSaved();
    }}>
      <div className="grid grid-3">
        <Field label={t("Наслов")}><input value={f.title} onChange={set("title")} required /></Field>
        <Field label={t("Цена по лице (EUR)")}><input type="number" min={0.01} step="0.01" value={f.price_per_person} onChange={set("price_per_person")} /></Field>
        <Field label={t("Траење (минути)")}><input type="number" min={10} value={f.duration_min} onChange={set("duration_min")} /></Field>
        <Field label={t("Место на поаѓање")}><input value={f.departure_point} onChange={set("departure_point")} /></Field>
        <Field label={t("Рута (кратко)")}><input value={f.route} onChange={set("route")} /></Field>
      </div>
      <Field label={t("Опис")}><textarea rows={3} value={f.description} onChange={set("description")} /></Field>
      <div className="grid grid-2">
        <Field label={t("Вклучено во цената")}><textarea rows={2} value={f.includes} onChange={set("includes")} /></Field>
        <Field label={t("Правила")}><textarea rows={2} value={f.rules} onChange={set("rules")} /></Field>
      </div>
      <fieldset>
        <legend>{t("Постојки (по редослед, минути од поаѓањето)")}</legend>
        <div className="stack" style={{ gap: 8 }}>
          {stops.length > 0 && (
            <div className="stop-row stop-head" aria-hidden>
              <span>{t("Постојка")}</span><span>{t("Мин. од поаѓање")}</span><span>{t("Пауза (мин)")}</span><span>{t("Белешка")}</span><span>{t("Ширина")}</span><span>{t("Должина")}</span><span />
            </div>
          )}
          {stops.map((s, i) => (
            <div key={i} className="stop-row">
              <input placeholder={t("Име на постојка")} value={s.name} onChange={(e) => upd(i, { name: e.target.value })} aria-label={t("Постојка")} />
              <input type="number" min={0} placeholder={t("мин")} value={s.minutes} onChange={(e) => upd(i, { minutes: Number(e.target.value) })} aria-label={t("Минути од поаѓање")} title={t("Минути од поаѓање")} />
              <input type="number" min={0} placeholder={t("пауза")} value={s.stop_min ?? 0} onChange={(e) => upd(i, { stop_min: Number(e.target.value) })} aria-label={t("Пауза (мин)")} title={t("Колку трае постојката")} />
              <input placeholder={t("Белешка")} value={s.note || ""} onChange={(e) => upd(i, { note: e.target.value })} aria-label={t("Белешка")} />
              <input inputMode="decimal" placeholder="lat" value={s.lat ?? ""} onChange={(e) => upd(i, { lat: e.target.value as unknown as number })} aria-label={t("Ширина")} />
              <input inputMode="decimal" placeholder="lng" value={s.lng ?? ""} onChange={(e) => upd(i, { lng: e.target.value as unknown as number })} aria-label={t("Должина")} />
              <span className="row">
                <button type="button" className="icon-btn" aria-label={t("Нагоре")} disabled={i === 0} onClick={() => move(i, -1)}><Icon name="left" size={16} /></button>
                <button type="button" className="icon-btn" aria-label={t("Надолу")} disabled={i === stops.length - 1} onClick={() => move(i, 1)}><Icon name="right" size={16} /></button>
                <button type="button" className="icon-btn" aria-label={t("Отстрани")} onClick={() => setStops(stops.filter((_, j) => j !== i))}><Icon name="close" size={16} /></button>
              </span>
            </div>
          ))}
          <button type="button" className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }}
                  onClick={() => setStops([...stops, { name: "", minutes: (stops[stops.length - 1]?.minutes || 0) + 30, stop_min: 0, note: "" }])}>
            <Icon name="plus" size={16} />{t("Додај постојка")}
          </button>
        </div>
      </fieldset>
      <Departures tour={tour} onChanged={onSaved} />
    </SaveForm>
  );
}

function Departures({ tour, onChanged }: { tour: TourEdit; onChanged: () => void }) {
  const [when, setWhen] = useState("");
  const [cap, setCap] = useState("20");
  const [err, setErr] = useState<string | null>(null);
  const add = async () => {
    setErr(null);
    try {
      await api(`/business/boat-tours/${tour.id}/departures/`, { method: "POST", json: { starts_at: new Date(when).toISOString(), capacity: Number(cap) } });
      setWhen(""); onChanged();
    } catch (e) { setErr(e instanceof Error ? e.message : t("Не е додадено.")); }
  };
  const cancel = async (d: Departure) => {
    if (!window.confirm(t("Да се откаже поаѓањето {0}? Сите барања за него ќе се откажат и туристите ќе бидат известени.", { 0: fmtDateTime(d.starts_at) }))) return;
    await api(`/business/departures/${d.id}/cancel/`, { method: "POST" });
    onChanged();
  };
  return (
    <div className="subcard stack">
      <strong>{t("Поаѓања")}</strong>
      <div className="grid grid-3">
        <Field label={t("Датум и време")}><input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} /></Field>
        <Field label={t("Капацитет")}><input type="number" min={1} value={cap} onChange={(e) => setCap(e.target.value)} /></Field>
        <div className="field"><span className="field-label">&nbsp;</span><button type="button" className="btn btn-ghost" disabled={!when} onClick={add}>{t("Додај поаѓање")}</button></div>
      </div>
      {err && <ErrorBox message={err} />}
      <ul className="plain dep-list">
        {tour.departures.slice(0, 20).map((d) => (
          <li key={d.id}>
            <span>{fmtDateTime(d.starts_at)}</span>
            <span className="small muted">{d.reserved_seats} {t("од")} {d.capacity} {t("резервирани")}</span>
            {d.status === "CANCELLED" ? <StatusPill status="CANCELLED" label={t("Откажано")} /> :
              <button type="button" className="link-btn small" onClick={() => cancel(d)}>{t("Откажи")}</button>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function NewTour({ businessId, onCreated }: { businessId: number; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ title: "", route: "", duration_min: "120", price_per_person: "", departure_point: "" });
  if (!open) return <button className="btn btn-ghost" onClick={() => setOpen(true)}><Icon name="plus" size={18} />{t("Додај нова тура")}</button>;
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <SaveForm title={t("Нова тура")} saveLabel={t("Креирај")} onSave={async () => {
      await api(`/business/my/${businessId}/boat-tours/`, { method: "POST", json: { ...f, duration_min: Number(f.duration_min) } });
      setOpen(false); onCreated();
    }}>
      <div className="grid grid-3">
        <Field label={t("Наслов")}><input value={f.title} onChange={set("title")} required /></Field>
        <Field label={t("Рута")}><input value={f.route} onChange={set("route")} required /></Field>
        <Field label={t("Место на поаѓање")}><input value={f.departure_point} onChange={set("departure_point")} required /></Field>
        <Field label={t("Траење (мин)")}><input type="number" min={10} value={f.duration_min} onChange={set("duration_min")} /></Field>
        <Field label={t("Цена по лице (EUR)")}><input type="number" min={0.01} step="0.01" value={f.price_per_person} onChange={set("price_per_person")} required /></Field>
      </div>
    </SaveForm>
  );
}

function TaxiForm({ b, onSaved }: { b: MyBusiness; onSaved: () => void }) {
  const taxi = b.taxi!;
  const [f, setF] = useState({ ...taxi, base_fare: taxi.base_fare ?? "", per_km: taxi.per_km ?? "", passenger_capacity: String(taxi.passenger_capacity) });
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <SaveForm title={t("Такси: тарифи и услуга")} onSave={async () => {
      await api(`/business/my/${b.id}/taxi/`, { method: "PATCH", json: { ...f, passenger_capacity: Number(f.passenger_capacity),
        base_fare: num(String(f.base_fare)), per_km: num(String(f.per_km)) } });
      onSaved();
    }}>
      <div className="grid grid-3">
        <Field label={t("Подрачје на услуга")}><input value={f.service_area} onChange={set("service_area")} /></Field>
        <Field label={t("Патници по возило")}><input type="number" min={1} max={20} value={f.passenger_capacity} onChange={set("passenger_capacity")} /></Field>
        <Field label={t("Возила")}><input value={f.vehicles} onChange={set("vehicles")} placeholder={t("пр. седан, комбе")} /></Field>
        <Field label={t("Старт (EUR)")} hint={t("Празно ако цената е по понуда.")}><input type="number" min={0} step="0.01" value={f.base_fare} onChange={set("base_fare")} /></Field>
        <Field label={t("По километар (EUR)")}><input type="number" min={0} step="0.01" value={f.per_km} onChange={set("per_km")} /></Field>
        <Field label={t("Јазици")}><input value={f.languages} onChange={set("languages")} /></Field>
      </div>
      <label className="check"><input type="checkbox" checked={f.available_24h} onChange={(e) => setF({ ...f, available_24h: e.target.checked })} />{t("Достапно 0–24")}</label>
      <Field label={t("Дополнителни информации за тарифи")} hint={t("Фиксни релации, доплати, начин на плаќање.")}><textarea rows={3} value={f.fare_info} onChange={set("fare_info")} /></Field>
    </SaveForm>
  );
}

export function BusinessEditPage() {
  const { id } = useParams();
  const { data, error, loading, reload, setData } = useAsync(() => api<MyBusiness>(`/business/my/${id}/`), [id]);
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error || t("Бизнисот не постои.")} />;
  const b = data;
  const publicLink = b.type === "TAXI" ? `/taxi/${b.id}` : b.type === "RESTAURANT" ? `/restaurants/${b.id}`
    : b.type === "BOAT_TOUR" && b.boat_tours?.[0] ? `/boat-tours/${b.boat_tours[0].id}`
    : b.type === "ACCOMMODATION" && b.accommodations?.[0] ? `/stay/${b.accommodations[0].id}` : null;
  return (
    <div className="stack-lg">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <p className="kicker"><Link to="/business">{t("Бизнис-табла")}</Link>, {TYPE_LABEL[b.type]}</p>
          <h1>{b.name}</h1>
          <StatusPill status={b.verification_status === "APPROVED" ? "APPROVED" : b.verification_status === "PENDING" ? "PENDING" : "REJECTED"}
                      label={STATUS_LABEL[b.verification_status] || b.verification_status} />
        </div>
        {publicLink && b.verification_status === "APPROVED" && <Link className="btn btn-ghost" to={publicLink}>{t("Види го јавниот оглас")}</Link>}
      </div>
      {b.verification_status !== "APPROVED" && (
        <div className="alert alert-warn">{t("Огласот не е јавен додека администраторот не го одобри бизнисот. Можете да ги внесете сите податоци однапред.")}</div>
      )}
      <ProfileForm b={b} onSaved={setData} />
      {b.type === "ACCOMMODATION" && (
        <>
          {b.accommodations?.map((a) => <AccommodationForm key={a.id} a={a} onSaved={reload} />)}
          <NewAccommodation businessId={b.id} onCreated={reload} />
        </>
      )}
      {b.type === "RESTAURANT" && b.restaurant && <RestaurantForm b={b} onSaved={reload} />}
      {b.type === "BOAT_TOUR" && (
        <>
          {b.boat_tours?.map((tour) => <TourForm key={tour.id} tour={tour} onSaved={reload} />)}
          <NewTour businessId={b.id} onCreated={reload} />
        </>
      )}
      {b.type === "TAXI" && b.taxi && <TaxiForm b={b} onSaved={reload} />}
    </div>
  );
}

export function NewBusinessPage() {
  const nav = useNavigate();
  const { data: cities } = useAsync(() => api<City[]>("/cities/"), []);
  const [f, setF] = useState({ name: "", type: "ACCOMMODATION", city: "", phone: "", address: "" });
  const city = cities?.find((c) => String(c.id) === (f.city || String(cities?.[0]?.id)));
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="stack-lg">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div><h1>{t("Нов бизнис")}</h1><p>{t("По креирањето го пополнувате огласот. Јавно се прикажува по одобрување од администратор.")}</p></div>
      </div>
      <SaveForm title={t("Основни податоци")} saveLabel={t("Креирај бизнис")} onSave={async () => {
        if (!city) return;
        const b = await api<MyBusiness>("/business/my/", { method: "POST", json: { ...f, city: city.id, lat: city.center_lat, lng: city.center_lng } });
        nav(`/business/${b.id}/edit`);
      }}>
        <div className="grid grid-2">
          <Field label={t("Име")}><input value={f.name} onChange={set("name")} required /></Field>
          <Field label={t("Тип")}>
            <select value={f.type} onChange={set("type")}>
              {Object.entries(TYPE_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </Field>
          <Field label={t("Град")}><select value={f.city || String(cities?.[0]?.id || "")} onChange={set("city")}>{cities?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
          <Field label={t("Телефон")}><input type="tel" value={f.phone} onChange={set("phone")} /></Field>
        </div>
        <Field label={t("Адреса")}><input value={f.address} onChange={set("address")} /></Field>
        <p className="small muted" style={{ margin: 0 }}>{t("Локацијата е центарот на градот; точната ја поставувате во профилот.")}</p>
      </SaveForm>
    </div>
  );
}
