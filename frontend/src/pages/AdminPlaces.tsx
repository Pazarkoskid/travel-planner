import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { eur, fmtDate, useAsync } from "../hooks";
import { ErrorBox, Field, Loading, StatusPill } from "../components/ui";
import Icon from "../components/Icon";
import type { City } from "../types";

interface AdminPlace {
  id: number; city: number; city_name: string; name: string; slug: string; category: string; description: string;
  lat: number; lng: number; visit_duration_min: number; price_eur: string | null; opening_time: string | null;
  closing_time: string | null; source: string; verified_at: string | null; status: string; is_required_landmark: boolean;
  checkin_radius_m: number; image_url: string; image_credit: string; wiki_query: string;
}

const CATEGORIES: [string, string][] = [["HISTORY", "Историја"], ["RELIGIOUS", "Цркви и манастири"], ["MUSEUM", "Музеј"],
  ["NATURE", "Природа"], ["VIEWPOINT", "Видиковец"], ["BEACH", "Плажа"], ["CULTURE", "Култура"], ["FOOD", "Локална храна"], ["ACTIVITY", "Активност"]];
const STATUS: Record<string, string> = { VERIFIED: "Проверено", UNVERIFIED: "Непроверено", ARCHIVED: "Архивирано" };
const hm = (t: string | null) => (t ? t.slice(0, 5) : "");

function PlaceEditor({ p, onSaved, onClose }: { p: AdminPlace; onSaved: (x: AdminPlace) => void; onClose: () => void }) {
  const [f, setF] = useState({
    price_eur: p.price_eur ?? "", opening_time: hm(p.opening_time), closing_time: hm(p.closing_time),
    visit_duration_min: String(p.visit_duration_min), description: p.description, status: p.status,
    is_required_landmark: p.is_required_landmark, source: p.source, verified_at: p.verified_at ?? "",
    image_url: p.image_url, image_credit: p.image_credit, checkin_radius_m: String(p.checkin_radius_m),
  });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    const touchedChecked = f.price_eur !== (p.price_eur ?? "") || f.opening_time !== hm(p.opening_time) || f.closing_time !== hm(p.closing_time);
    const payload: Record<string, unknown> = {
      price_eur: f.price_eur === "" ? null : f.price_eur,
      opening_time: f.opening_time || null, closing_time: f.closing_time || null,
      visit_duration_min: Number(f.visit_duration_min), description: f.description, status: f.status,
      is_required_landmark: f.is_required_landmark, source: f.source, image_url: f.image_url, image_credit: f.image_credit,
      checkin_radius_m: Number(f.checkin_radius_m),
    };
    // Ако админот сам не го сменил датумот, серверот става денешен при промена на цена/време.
    if (f.verified_at !== (p.verified_at ?? "") || !touchedChecked) payload.verified_at = f.verified_at || null;
    try {
      onSaved(await api<AdminPlace>(`/admin/places/${p.id}/`, { method: "PATCH", json: payload }));
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "Не е зачувано.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="subcard stack" onSubmit={save}>
      {err && <ErrorBox message={err} />}
      <div className="grid grid-5">
        <Field label="Цена (EUR)" hint="Празно = непозната"><input type="number" min={0} step="0.01" value={f.price_eur} onChange={set("price_eur")} /></Field>
        <Field label="Отвора"><input type="time" value={f.opening_time} onChange={set("opening_time")} /></Field>
        <Field label="Затвора"><input type="time" value={f.closing_time} onChange={set("closing_time")} /></Field>
        <Field label="Посета (мин)"><input type="number" min={5} value={f.visit_duration_min} onChange={set("visit_duration_min")} /></Field>
        <Field label="Проверено на"><input type="date" value={f.verified_at} onChange={set("verified_at")} /></Field>
      </div>
      <div className="grid grid-3">
        <Field label="Статус">
          <select value={f.status} onChange={set("status")}>{Object.entries(STATUS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        </Field>
        <Field label="Радиус за фото-посета (m)"><input type="number" min={50} max={2000} value={f.checkin_radius_m} onChange={set("checkin_radius_m")} /></Field>
        <div className="field"><span className="field-label">Листа „Град 100%“</span>
          <label className="check"><input type="checkbox" checked={f.is_required_landmark} onChange={(e) => setF({ ...f, is_required_landmark: e.target.checked })} />Задолжителна знаменитост</label>
        </div>
      </div>
      <Field label="Извор на податоците" hint="Задолжително, пр. официјална веб-страница на музејот, датум на проверка."><input value={f.source} onChange={set("source")} required /></Field>
      <Field label="Опис"><textarea rows={3} value={f.description} onChange={set("description")} /></Field>
      <div className="grid grid-2">
        <Field label="Фотографија (URL)"><input type="url" value={f.image_url} onChange={set("image_url")} /></Field>
        <Field label="Автор и лиценца на фотографијата"><input value={f.image_credit} onChange={set("image_credit")} /></Field>
      </div>
      <div className="row gap wrap">
        <button className="btn btn-primary" disabled={busy}>{busy ? "Се зачувува" : "Зачувај"}</button>
        <button type="button" className="btn btn-ghost" onClick={onClose}>Затвори</button>
      </div>
    </form>
  );
}

function NewPlace({ cities, onCreated }: { cities: City[]; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ city: "", name: "", category: "HISTORY", lat: "", lng: "", visit_duration_min: "60", source: "" });
  const [err, setErr] = useState<string | null>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  if (!open) return <button className="btn btn-ghost" onClick={() => setOpen(true)}><Icon name="plus" size={18} />Ново место</button>;
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await api("/admin/places/", { method: "POST", json: { ...f, city: Number(f.city || cities[0]?.id), lat: Number(f.lat), lng: Number(f.lng),
        visit_duration_min: Number(f.visit_duration_min), status: "UNVERIFIED" } });
      setOpen(false);
      onCreated();
    } catch (e2) { setErr(e2 instanceof Error ? e2.message : "Не е креирано."); }
  };
  return (
    <form className="subcard stack" onSubmit={submit}>
      <strong>Ново место</strong>
      {err && <ErrorBox message={err} />}
      <div className="grid grid-3">
        <Field label="Град"><select value={f.city || String(cities[0]?.id || "")} onChange={set("city")}>{cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
        <Field label="Име"><input value={f.name} onChange={set("name")} required /></Field>
        <Field label="Категорија"><select value={f.category} onChange={set("category")}>{CATEGORIES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
        <Field label="Ширина"><input inputMode="decimal" value={f.lat} onChange={set("lat")} required placeholder="41.11" /></Field>
        <Field label="Должина"><input inputMode="decimal" value={f.lng} onChange={set("lng")} required placeholder="20.80" /></Field>
        <Field label="Посета (мин)"><input type="number" min={5} value={f.visit_duration_min} onChange={set("visit_duration_min")} /></Field>
      </div>
      <Field label="Извор"><input value={f.source} onChange={set("source")} required /></Field>
      <p className="small muted" style={{ margin: 0 }}>Новото место е непроверено и не влегува во плановите додека не го означите како „Проверено“.</p>
      <div className="row gap"><button className="btn btn-primary">Креирај</button><button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}>Откажи</button></div>
    </form>
  );
}

export default function AdminPlaces() {
  const { data: cities } = useAsync(() => api<City[]>("/cities/"), []);
  const [city, setCity] = useState("");
  const [q, setQ] = useState("");
  const { data, error, loading, reload, setData } = useAsync(
    () => api<AdminPlace[]>(`/admin/places/?${new URLSearchParams({ ...(city ? { city } : {}), ...(q ? { q } : {}) })}`),
    [city, q],
  );
  const [editing, setEditing] = useState<number | null>(null);

  return (
    <section className="panel stack">
      <div className="row between wrap gap">
        <h2 style={{ margin: 0 }}>Каталог на места</h2>
        {cities && <NewPlace cities={cities} onCreated={reload} />}
      </div>
      <p className="small muted" style={{ margin: 0 }}>Цена и работно време се прикажуваат јавно само со извор и датум на проверка. Празно поле значи „непознато“.</p>
      <div className="row gap wrap">
        <select value={city} onChange={(e) => setCity(e.target.value)} aria-label="Град" style={{ width: "auto" }}>
          <option value="">Сите градови</option>
          {cities?.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
        </select>
        <input className="grow" placeholder="Пребарај по име" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Пребарај места" />
      </div>
      {loading && !data && <Loading />}
      {error && <ErrorBox message={error} />}
      <ul className="plain admin-places">
        {data?.map((p) => (
          <li key={p.id}>
            <div className="admin-place-row">
              <div>
                <Link to={`/places/${p.id}`}><strong>{p.name}</strong></Link>
                <div className="small muted">{p.city_name}{p.is_required_landmark ? ", знаменитост" : ""}</div>
              </div>
              <span className="small">{p.price_eur ? eur(p.price_eur) : <span className="muted">цена непозната</span>}</span>
              <span className="small">{p.opening_time ? `${hm(p.opening_time)} до ${hm(p.closing_time)}` : <span className="muted">време непознато</span>}</span>
              <span className="small muted">{p.verified_at ? `проверено ${fmtDate(p.verified_at)}` : "непроверено"}</span>
              <StatusPill status={p.status === "VERIFIED" ? "APPROVED" : p.status === "ARCHIVED" ? "CANCELLED" : "PENDING"} label={STATUS[p.status]} />
              <button className="btn btn-ghost btn-sm" onClick={() => setEditing(editing === p.id ? null : p.id)}>
                <Icon name="edit" size={16} />{editing === p.id ? "Затвори" : "Уреди"}
              </button>
            </div>
            {editing === p.id && (
              <PlaceEditor p={p} onClose={() => setEditing(null)}
                           onSaved={(x) => { setData((data || []).map((r) => (r.id === x.id ? x : r))); setEditing(null); }} />
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
