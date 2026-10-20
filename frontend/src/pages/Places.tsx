import { FormEvent, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, unwrap } from "../services/api";
import { fmtDate, useAsync } from "../hooks";
import { useAuth } from "../auth";
import { Empty, ErrorBox, Field, Loading, Meta, Progress } from "../components/ui";
import MapView from "../components/MapView";
import WeatherCard from "../components/Weather";
import PhotoImg from "../components/Photo";
import type { Badge, City, CityProgress, CheckIn, Photo, Place } from "../types";

export function PlaceList() {
  const [params, setParams] = useSearchParams();
  const city = params.get("city") || "ohrid";
  const { data: cities } = useAsync(() => api<City[]>("/cities/"), []);
  const { data: places, error, loading, reload } = useAsync(
    async () => unwrap(await api<Place[] | { results: Place[] }>(`/places/?city=${city}`)),
    [city],
  );

  const cityName = cities?.find((c) => c.slug === city)?.name;
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Места{cityName ? ` во ${cityName}` : ""}</h1>
          <p>Местата со златна точка се на официјалната листа за печатот „{cityName || "Град"} 100%“.</p>
        </div>
        <select value={city} onChange={(e) => setParams({ city: e.target.value })} aria-label="Град" style={{ width: "auto" }}>
          {cities?.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
        </select>
      </div>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {places && (
        <div className="split">
          <ul className="place-list">
            {places.map((p) => (
              <li key={p.id} className="place-item">
                <Link to={`/places/${p.id}`}>
                  <PhotoImg className="place-thumb" src={p.image_url} alt="" seed={p.id} />
                  <strong>{p.name}</strong>
                  {p.is_required_landmark ? <span className="landmark-mark">знаменитост</span> : <span />}
                  <Meta items={[p.category_label, `околу ${p.visit_duration_min} мин`, `${p.badge_holders ?? 0} печати`]} />
                </Link>
              </li>
            ))}
          </ul>
          <MapView points={places.map((p) => ({ lat: p.lat, lng: p.lng, label: p.name, sub: p.category_label,
                                                color: p.is_required_landmark ? "#c99a2e" : "#08415c" }))} height={600} />
        </div>
      )}
    </>
  );
}

export function PlaceDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data: place, error, loading } = useAsync(() => api<Place>(`/places/${id}/`), [id]);
  const gallery = useAsync(() => api<{ badge_holders: number; photos: Photo[] }>(`/places/${id}/gallery/`), [id]);

  if (loading) return <Loading />;
  if (error || !place) return <ErrorBox message={error || "Не постои."} />;

  return (
    <div className="stack-lg">
      <div className="place-banner">
        <PhotoImg src={place.image_url} alt={place.name} credit={place.image_credit} seed={place.id} eager showCredit />
        <div className="place-banner-text">
          <p className="kicker"><Link to={`/places?city=${place.city}`}>{place.city_name}</Link>, {place.category_label.toLowerCase()}</p>
          <h1>{place.name}</h1>
        </div>
      </div>
      <div className="place-hero">
        <div>
          <p className="muted" style={{ fontSize: "1.08rem", margin: 0 }}>{place.description}</p>
        </div>
        {place.is_required_landmark && (
          <div className="panel panel-lake">
            <span className="landmark-mark">Официјална знаменитост</span>
            <p className="small" style={{ margin: "6px 0 0" }}>Се брои за печатот „{place.city_name} 100%“. {gallery.data?.badge_holders ?? 0} туристи веќе го имаат печатот за ова место.</p>
          </div>
        )}
      </div>
      <div className="split">
        <div className="panel stack">
          <h2>Пред да тргнете</h2>
          <dl className="facts">
            <dt>Времетраење</dt><dd>околу {place.visit_duration_min} мин</dd>
            <dt>Цена</dt><dd>{place.price_eur ? `${place.price_eur} €` : "не е проверена, потврдете на лице место"}</dd>
            <dt>Работно време</dt><dd>{place.opening_time ? `${place.opening_time.slice(0, 5)} до ${place.closing_time?.slice(0, 5)}` : "не е проверено, потврдете пред посета"}</dd>
            <dt>Извор</dt><dd className="small">{place.source}{place.verified_at ? ` (проверено ${fmtDate(place.verified_at)})` : ""}</dd>
          </dl>
        </div>
        <div className="stack">
          <MapView points={[{ lat: place.lat, lng: place.lng, label: place.name }]} height={300} />
          <WeatherCard query={`place=${place.id}`} title={place.name} />
        </div>
      </div>

      {user ? <CheckInForm place={place} onDone={gallery.reload} /> : (
        <div className="checkin row between wrap gap">
          <span>Најавете се за да ја документирате посетата и да го добиете печатот.</span>
          <Link to="/login" className="btn btn-gold btn-sm">Најави се</Link>
        </div>
      )}

      <div className="section-head" style={{ marginBottom: 0 }}><h2>Фотографии од туристи</h2></div>
      {gallery.loading && <Loading />}
      {gallery.data && gallery.data.photos.length === 0 && <Empty title="Сè уште нема фотографии од ова место.">Првата одобрена фотографија ќе се појави тука.</Empty>}
      <div className="gallery">
        {gallery.data?.photos.map((ph) => <PhotoCard key={ph.id} photo={ph} canReport={!!user} />)}
      </div>
    </div>
  );
}

function PhotoCard({ photo, canReport }: { photo: Photo; canReport: boolean }) {
  const [reported, setReported] = useState(false);
  const report = async () => {
    const reason = window.prompt("Зошто е несоодветна фотографијата?");
    if (!reason) return;
    await api(`/photos/${photo.id}/report/`, { method: "POST", json: { reason } });
    setReported(true);
  };
  return (
    <figure className="photo">
      <img src={photo.image} alt={photo.caption || `Фотографија од ${photo.place_name}`} loading="lazy" />
      <figcaption>
        <Link to={`/u/${photo.photographer}`}>{photo.photographer}</Link>
        <span className="muted small">{fmtDate(photo.taken_at || photo.created_at)}</span>
        {photo.caption && <div className="small">{photo.caption}</div>}
        {canReport && (
          <button className="link-btn small" onClick={report} disabled={reported}>{reported ? "Пријавено" : "Пријави фотографија"}</button>
        )}
      </figcaption>
    </figure>
  );
}

interface CheckInResult {
  checkin: CheckIn;
  unlocked_badges: Badge[];
  city_progress: CityProgress | null;
}

function CheckInForm({ place, onDone }: { place: Place; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [geoMsg, setGeoMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CheckInResult | null>(null);

  const locate = () => {
    if (!navigator.geolocation) return setGeoMsg("Прелистувачот не поддржува локација.");
    setGeoMsg("Се бара локација");
    navigator.geolocation.getCurrentPosition(
      (p) => { setCoords({ lat: p.coords.latitude, lng: p.coords.longitude }); setGeoMsg("Локацијата е додадена."); },
      () => setGeoMsg("Без локација посетата ќе ја провери администратор."),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    const fd = new FormData();
    fd.append("image", file);
    fd.append("caption", caption);
    fd.append("is_public", String(isPublic));
    if (coords) { fd.append("lat", String(coords.lat)); fd.append("lng", String(coords.lng)); }
    try {
      setResult(await api<CheckInResult>(`/places/${place.id}/checkins/`, { method: "POST", body: fd }));
      setFile(null);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Грешка");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="checkin stack" onSubmit={submit}>
      <h2>Документирај ја посетата</h2>
      <p className="small muted">
        Фотографирајте го местото на лице место. Со дозволена локација (во радиус од {place.checkin_radius_m} m) печатот се отклучува веднаш;
        без неа фотографијата чека рачна проверка. Само EXIF податоците не се доволни.
      </p>
      {error && <ErrorBox message={error} />}
      <div className="grid grid-2">
        <Field label="Фотографија" hint="JPEG, PNG или WEBP, до 8 MB">
          <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
        </Field>
        <Field label="Опис (опционално)"><input value={caption} maxLength={300} onChange={(e) => setCaption(e.target.value)} /></Field>
      </div>
      <div className="row gap wrap">
        <button type="button" className="btn btn-ghost btn-sm" onClick={locate}>Користи ја мојата локација</button>
        <span className="small muted">{geoMsg}</span>
        <label className="check"><input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} /> Прикажи ја во галеријата на местото</label>
      </div>
      <div><button className="btn btn-gold" disabled={busy || !file}>{busy ? "Се прикачува" : "Прикачи фотографија"}</button></div>
      {result && (
        <div className={`alert ${result.checkin.status === "APPROVED" ? "alert-ok" : result.checkin.status === "PENDING" ? "alert-warn" : "alert-error"}`}>
          <div>
            <strong>
              {result.checkin.status === "APPROVED" ? "Посетата е потврдена!" : result.checkin.status === "PENDING" ? "Чека проверка од администратор." : "Посетата не е прифатена."}
            </strong>
            <ul className="small">{result.checkin.verification_notes.map((n) => <li key={n}>{n}</li>)}</ul>
            {result.unlocked_badges.length > 0 && (
              <div className="badges">{result.unlocked_badges.map((b) => <span key={b.code} className="badge-chip">{b.icon} {b.name}</span>)}</div>
            )}
            {result.city_progress && (
              <div className="small">
                {result.city_progress.city_name}: документирани {result.city_progress.documented_required} од {result.city_progress.required_total} знаменитости
                <Progress value={result.city_progress.percent} />
              </div>
            )}
          </div>
        </div>
      )}
    </form>
  );
}
