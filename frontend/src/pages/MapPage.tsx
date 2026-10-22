import { useEffect, useMemo, useRef, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import type { CircleMarker as LCircleMarker } from "leaflet";
import "leaflet/dist/leaflet.css";
import { Link, useSearchParams } from "react-router-dom";
import { api, unwrap } from "../services/api";
import { fetchAmenitiesDirect } from "../services/osm";
import { useAsync } from "../hooks";
import { t } from "../i18n";
import { ErrorBox, Loading } from "../components/ui";
import Icon from "../components/Icon";
import type { City, Place } from "../types";

interface Amenity {
  id: string;
  category: Cat;
  name: string;
  lat: number;
  lng: number;
  opening_hours: string;
  address: string;
  phone: string;
  website: string;
  osm_url: string;
}
type Cat = "bakery" | "market" | "exchange" | "kiosk" | "atm" | "pharmacy" | "landmark";

const CATS: { key: Cat; label: string; color: string; on: boolean }[] = [
  { key: "bakery", label: t("Пекари"), color: "#c27b2c", on: true },
  { key: "market", label: t("Маркети"), color: "#1d9e6e", on: true },
  { key: "exchange", label: t("Менувачници"), color: "#7a2f86", on: true },
  { key: "kiosk", label: t("Трафики"), color: "#e2574c", on: true },
  { key: "atm", label: t("Банкомати"), color: "#1b64a8", on: false },
  { key: "pharmacy", label: t("Аптеки"), color: "#0f8a8a", on: false },
  { key: "landmark", label: t("Знаменитости"), color: "#c99a2e", on: false },
];
const COLOR = Object.fromEntries(CATS.map((c) => [c.key, c.color])) as Record<Cat, string>;
const LABEL = Object.fromEntries(CATS.map((c) => [c.key, c.label])) as Record<Cat, string>;

const km = (a: [number, number], b: [number, number]) => {
  const R = 6371, dLat = ((b[0] - a[0]) * Math.PI) / 180, dLng = ((b[1] - a[1]) * Math.PI) / 180;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos((a[0] * Math.PI) / 180) * Math.cos((b[0] * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
};
const fmtKm = (d: number) => (d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(1)} km`);

function Controller({ center, focus, me }: { center: [number, number]; focus: Amenity | null; me: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    // картата се појавува во анимација / менува големина → Leaflet мора да ја пресмета повторно
    const fix = () => map.invalidateSize();
    const timers = [100, 400, 1000].map((ms) => window.setTimeout(fix, ms));
    const ro = new ResizeObserver(fix);
    ro.observe(map.getContainer());
    return () => { timers.forEach(clearTimeout); ro.disconnect(); };
  }, [map]);
  useEffect(() => { map.setView(center, 15); }, [map, center[0], center[1]]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (focus) map.flyTo([focus.lat, focus.lng], Math.max(map.getZoom(), 17), { duration: 0.6 }); }, [map, focus]);
  useEffect(() => { if (me) map.flyTo(me, 16, { duration: 0.6 }); }, [map, me]);
  return null;
}

export default function MapPage() {
  const [params, setParams] = useSearchParams();
  const citySlug = params.get("city") || "ohrid";
  const { data: cities } = useAsync(() => api<City[]>("/cities/"), []);
  const city = cities?.find((c) => c.slug === citySlug);
  const amen = useAsync(async () => {
    try {
      return await api<{ items: Amenity[]; stale: boolean }>(`/amenities/?city=${citySlug}`);
    } catch (err) {
      // backend-от не добил одговор од OSM → прелистувачот прашува директно
      const c = (cities || await api<City[]>("/cities/")).find((x) => x.slug === citySlug);
      if (!c) throw err;
      try { return (await fetchAmenitiesDirect(c.center_lat, c.center_lng)) as { items: Amenity[]; stale: boolean }; }
      catch { throw new Error(t("Податоците од OpenStreetMap моментално не се достапни. Обидете се повторно.")); }
    }
  }, [citySlug]);
  const landmarks = useAsync(async () => unwrap(await api<Place[] | { results: Place[] }>(`/places/?city=${citySlug}`)), [citySlug]);

  const [active, setActive] = useState<Set<Cat>>(() => new Set(CATS.filter((c) => c.on).map((c) => c.key)));
  const [q, setQ] = useState("");
  const [focus, setFocus] = useState<Amenity | null>(null);
  const [me, setMe] = useState<[number, number] | null>(null);
  const [locErr, setLocErr] = useState<string | null>(null);
  const markers = useRef<Record<string, LCircleMarker | null>>({});

  const all: Amenity[] = useMemo(() => {
    const lm: Amenity[] = (landmarks.data || []).map((p) => ({
      id: `place/${p.id}`, category: "landmark", name: p.name, lat: p.lat, lng: p.lng, opening_hours: "",
      address: "", phone: "", website: "", osm_url: `/places/${p.id}`,
    }));
    return [...(amen.data?.items || []), ...lm];
  }, [amen.data, landmarks.data]);

  const counts = useMemo(() => all.reduce<Record<string, number>>((m, a) => ({ ...m, [a.category]: (m[a.category] || 0) + 1 }), {}), [all]);

  const shown = useMemo(() => {
    const term = q.trim().toLowerCase();
    let rows = all.filter((a) => active.has(a.category) && (!term || `${a.name} ${a.address}`.toLowerCase().includes(term)));
    const origin: [number, number] | null = me || (city ? [city.center_lat, city.center_lng] : null);
    if (origin) rows = rows.map((a) => ({ ...a, _d: km(origin, [a.lat, a.lng]) })).sort((x, y) => (x as never as { _d: number })._d - (y as never as { _d: number })._d);
    return rows as (Amenity & { _d?: number })[];
  }, [all, active, q, me, city]);

  const toggle = (k: Cat) => setActive((s) => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n; });
  const select = (a: Amenity) => { setFocus(a); window.setTimeout(() => markers.current[a.id]?.openPopup(), 650); };

  const locate = () => {
    setLocErr(null);
    if (!navigator.geolocation) { setLocErr(t("Прелистувачот не поддржува локација.")); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => setMe([pos.coords.latitude, pos.coords.longitude]),
      () => setLocErr(t("Не можам да ја добијам вашата локација.")),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const center: [number, number] = city ? [city.center_lat, city.center_lng] : [41.1172, 20.8016];

  return (
    <div className="map-page">
      <div className="map-head">
        <div>
          <h1>{t("Мапа")}</h1>
          <p className="muted">{t("Пекари, маркети, менувачници и трафики во близина — податоци од OpenStreetMap.")}</p>
        </div>
        <div className="row gap wrap">
          <button className="btn btn-ghost btn-sm" onClick={locate}><Icon name="pin" size={16} />{t("Најблиску до мене")}</button>
          <select value={citySlug} onChange={(e) => { setParams({ city: e.target.value }); setFocus(null); }} aria-label={t("Град")} style={{ width: "auto" }}>
            {cities?.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
          </select>
        </div>
      </div>

      <div className="map-cats" role="group" aria-label={t("Категории")}>
        {CATS.map((c) => (
          <button key={c.key} type="button" className={active.has(c.key) ? "map-cat on" : "map-cat"} aria-pressed={active.has(c.key)}
                  onClick={() => toggle(c.key)} style={{ ["--c" as string]: c.color }}>
            <span className="map-dot" />{c.label}{counts[c.key] ? <span className="map-count">{counts[c.key]}</span> : null}
          </button>
        ))}
      </div>
      {locErr && <p className="small warn-text">{locErr}</p>}
      {amen.error && <ErrorBox message={amen.error} onRetry={amen.reload} />}
      {amen.data?.stale && <p className="small muted">{t("Прикажани се последно зачуваните податоци.")}</p>}

      <div className="map-layout">
        <aside className="map-list">
          <label className="search-people">
            <Icon name="search" size={18} />
            <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("Филтрирај по име или улица")} aria-label={t("Филтрирај")} />
          </label>
          {amen.loading && <Loading label={t("Се вчитуваат објектите од OpenStreetMap")} />}
          {!amen.loading && shown.length === 0 && <p className="muted small">{t("Нема објекти за избраните категории.")}</p>}
          <ul>
            {shown.slice(0, 200).map((a) => (
              <li key={a.id}>
                <button type="button" className={focus?.id === a.id ? "map-item on" : "map-item"} onClick={() => select(a)}>
                  <span className="map-dot" style={{ background: COLOR[a.category] }} />
                  <span className="map-item-text">
                    <strong>{a.name || LABEL[a.category]}</strong>
                    <span className="small muted">{LABEL[a.category]}{a.address ? ` · ${a.address}` : ""}</span>
                  </span>
                  {a._d !== undefined && <span className="small map-dist">{fmtKm(a._d)}</span>}
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <div className="map-canvas">
          <MapContainer center={center} zoom={15} style={{ height: "100%", width: "100%" }} preferCanvas>
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                       url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" crossOrigin="" />
            <Controller center={center} focus={focus} me={me} />
            {me && <CircleMarker center={me} radius={9} pathOptions={{ color: "#fff", weight: 3, fillColor: "#2b6cf0", fillOpacity: 1 }}><Popup>{t("Вие сте тука")}</Popup></CircleMarker>}
            {shown.map((a) => (
              <CircleMarker key={a.id} center={[a.lat, a.lng]} radius={focus?.id === a.id ? 11 : 7}
                            ref={(r) => { markers.current[a.id] = r; }}
                            pathOptions={{ color: "#fff", weight: 2, fillColor: COLOR[a.category], fillOpacity: 0.95 }}
                            eventHandlers={{ click: () => setFocus(a) }}>
                <Popup>
                  <div className="map-pop">
                    <strong>{a.name || LABEL[a.category]}</strong>
                    <span className="map-pop-cat" style={{ color: COLOR[a.category] }}>{LABEL[a.category]}</span>
                    {a.address && <span>{a.address}</span>}
                    {a.opening_hours && <span><Icon name="clock" size={13} /> {a.opening_hours}</span>}
                    {a.phone && <a href={`tel:${a.phone.replace(/\s+/g, "")}`}><Icon name="phone" size={13} /> {a.phone}</a>}
                    <span className="map-pop-links">
                      <a href={`https://www.google.com/maps/dir/?api=1&destination=${a.lat},${a.lng}`} target="_blank" rel="noreferrer">{t("Насоки")}</a>
                      {a.category === "landmark"
                        ? <Link to={a.osm_url}>{t("Детали")}</Link>
                        : <a href={a.osm_url} target="_blank" rel="noreferrer">OSM</a>}
                    </span>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      </div>
      <p className="small muted" style={{ marginTop: 8 }}>
        {t("Податоци © OpenStreetMap contributors (ODbL). Работното време и податоците ги внесуваат волонтери — проверете на лице место.")}
      </p>
    </div>
  );
}
