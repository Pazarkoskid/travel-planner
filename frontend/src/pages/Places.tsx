import { t } from "../i18n";
import { FormEvent, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, unwrap } from "../services/api";
import { fmtDate, useAsync } from "../hooks";
import { useAuth } from "../auth";
import { AccessBadge, Empty, ErrorBox, Field, Loading, Meta, Progress } from "../components/ui";
import MapView from "../components/MapView";
import Icon from "../components/Icon";
import WeatherCard from "../components/Weather";
import PhotoImg from "../components/Photo";
import type { Badge, City, CityProgress, CheckIn, Photo, Place } from "../types";

export function PlaceList() {
  const [params, setParams] = useSearchParams();
  const city = params.get("city") || "ohrid";
  const accessible = params.get("accessible") === "1";
  const { data: cities } = useAsync(() => api<City[]>("/cities/"), []);
  const { data: places, error, loading, reload } = useAsync(
    async () => unwrap(await api<Place[] | { results: Place[] }>(`/places/?city=${city}${accessible ? "&accessible=1" : ""}`)),
    [city, accessible],
  );

  const cityName = cities?.find((c) => c.slug === city)?.name;
  return (
    <>
      <div className="page-head">
        <div>
          <h1>{t("Места")}{cityName ? t(" во {0}", { 0: cityName }) : ""}</h1>
          <p>{t("Местата со златна точка се на официјалната листа за печатот „")}{cityName || t("Град")} 100%“.</p>
        </div>
        <div className="row gap wrap">
          <label className="check access-filter">
            <input type="checkbox" checked={accessible}
                   onChange={(e) => setParams(e.target.checked ? { city, accessible: "1" } : { city })} />
            <Icon name="accessible" size={18} />{t("Само пристапни")}
          </label>
          <select value={city} onChange={(e) => setParams(accessible ? { city: e.target.value, accessible: "1" } : { city: e.target.value })}
                  aria-label={t("Град")} style={{ width: "auto" }}>
            {cities?.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
          </select>
        </div>
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
                  {p.is_required_landmark ? <span className="landmark-mark">{t("знаменитост")}</span> : <span />}
                  <Meta items={[t(p.category_label), t("околу {0} мин", { 0: p.visit_duration_min }), t("{0} печати", { 0: p.badge_holders ?? 0 })]} />
                  {p.wheelchair !== "UNKNOWN" && <span className="place-access"><AccessBadge level={p.wheelchair} notes={p.accessibility_notes} compact /></span>}
                </Link>
              </li>
            ))}
          </ul>
          <MapView points={places.map((p) => ({ lat: p.lat, lng: p.lng, label: p.name, sub: t(p.category_label),
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
  if (error || !place) return <ErrorBox message={error || t("Не постои.")} />;

  return (
    <div className="stack-lg">
      <div className="place-banner">
        <PhotoImg src={place.image_url} alt={place.name} credit={place.image_credit} seed={place.id} eager showCredit />
        <div className="place-banner-text">
          <p className="kicker"><Link to={`/places?city=${place.city}`}>{place.city_name}</Link>, {t(place.category_label).toLowerCase()}</p>
          <h1>{place.name}</h1>
        </div>
      </div>
      <div className="place-hero">
        <div>
          <p className="muted" style={{ fontSize: "1.08rem", margin: 0 }}>{place.description}</p>
        </div>
        {place.is_required_landmark && (
          <div className="panel panel-lake">
            <span className="landmark-mark">{t("Официјална знаменитост")}</span>
            <p className="small" style={{ margin: "6px 0 0" }}>{t("Се брои за печатот „")}{place.city_name} 100%“. {gallery.data?.badge_holders ?? 0} {t("туристи веќе го имаат печатот за ова место.")}</p>
          </div>
        )}
      </div>
      <div className="split">
        <div className="panel stack">
          <h2>{t("Пред да тргнете")}</h2>
          <dl className="facts">
            <dt>{t("Времетраење")}</dt><dd>{t("околу")} {place.visit_duration_min} {t("мин")}</dd>
            <dt>{t("Цена")}</dt><dd>{place.price_eur ? `${place.price_eur} €` : t("не е проверена, потврдете на лице место")}</dd>
            <dt>{t("Работно време")}</dt><dd>{place.opening_time ? t("{0} до {1}", { 0: place.opening_time.slice(0, 5), 1: place.closing_time?.slice(0, 5) }) : t("не е проверено, потврдете пред посета")}</dd>
            <dt>{t("Пристапност")}</dt>
            <dd>
              <AccessBadge level={place.wheelchair} />
              {place.accessibility_notes && <div className="small muted" style={{ marginTop: 4 }}>{place.accessibility_notes}</div>}
            </dd>
            <dt>{t("Извор")}</dt><dd className="small">{place.source}{place.verified_at ? t(" (проверено {0})", { 0: fmtDate(place.verified_at) }) : ""}</dd>
          </dl>
        </div>
        <div className="stack">
          <MapView points={[{ lat: place.lat, lng: place.lng, label: place.name }]} height={300} />
          <WeatherCard query={`place=${place.id}`} title={place.name} />
        </div>
      </div>

      {user ? <CheckInForm place={place} onDone={gallery.reload} /> : (
        <div className="checkin row between wrap gap">
          <span>{t("Најавете се за да ја документирате посетата и да го добиете печатот.")}</span>
          <Link to="/login" className="btn btn-gold btn-sm">{t("Најави се")}</Link>
        </div>
      )}

      <div className="section-head" style={{ marginBottom: 0 }}><h2>{t("Фотографии од туристи")}</h2></div>
      {gallery.loading && <Loading />}
      {gallery.data && gallery.data.photos.length === 0 && <Empty title={t("Сè уште нема фотографии од ова место.")}>{t("Првата одобрена фотографија ќе се појави тука.")}</Empty>}
      <div className="gallery">
        {gallery.data?.photos.map((ph) => <PhotoCard key={ph.id} photo={ph} canReport={!!user} />)}
      </div>
    </div>
  );
}

function PhotoCard({ photo, canReport }: { photo: Photo; canReport: boolean }) {
  const [reported, setReported] = useState(false);
  const report = async () => {
    const reason = window.prompt(t("Зошто е несоодветна фотографијата?"));
    if (!reason) return;
    await api(`/photos/${photo.id}/report/`, { method: "POST", json: { reason } });
    setReported(true);
  };
  return (
    <figure className="photo">
      <img src={photo.image} alt={photo.caption || t("Фотографија од {0}", { 0: photo.place_name })} loading="lazy" />
      <figcaption>
        <Link to={`/u/${photo.photographer}`}>{photo.photographer}</Link>
        <span className="muted small">{fmtDate(photo.taken_at || photo.created_at)}</span>
        {photo.caption && <div className="small">{photo.caption}</div>}
        {canReport && (
          <button className="link-btn small" onClick={report} disabled={reported}>{reported ? t("Пријавено") : t("Пријави фотографија")}</button>
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
    if (!navigator.geolocation) return setGeoMsg(t("Прелистувачот не поддржува локација."));
    setGeoMsg(t("Се бара локација"));
    navigator.geolocation.getCurrentPosition(
      (p) => { setCoords({ lat: p.coords.latitude, lng: p.coords.longitude }); setGeoMsg(t("Локацијата е додадена.")); },
      () => setGeoMsg(t("Без локација посетата ќе ја провери администратор.")),
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
      setError(err instanceof Error ? err.message : t("Грешка"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="checkin stack" onSubmit={submit}>
      <h2>{t("Документирај ја посетата")}</h2>
      <p className="small muted">
        {t("Фотографирајте го местото на лице место. Со дозволена локација (во радиус од {0} m) печатот се отклучува веднаш; без неа фотографијата чека рачна проверка. Само EXIF податоците не се доволни.", { 0: place.checkin_radius_m })}
      </p>
      {error && <ErrorBox message={error} />}
      <div className="grid grid-2">
        <Field label={t("Фотографија")} hint={t("JPEG, PNG или WEBP, до 8 MB")}>
          <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
        </Field>
        <Field label={t("Опис (опционално)")}><input value={caption} maxLength={300} onChange={(e) => setCaption(e.target.value)} /></Field>
      </div>
      <div className="row gap wrap">
        <button type="button" className="btn btn-ghost btn-sm" onClick={locate}>{t("Користи ја мојата локација")}</button>
        <span className="small muted">{geoMsg}</span>
        <label className="check"><input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} /> {t("Прикажи ја во галеријата на местото")}</label>
      </div>
      <div><button className="btn btn-gold" disabled={busy || !file}>{busy ? t("Се прикачува") : t("Прикачи фотографија")}</button></div>
      {result && (
        <div className={`alert ${result.checkin.status === "APPROVED" ? "alert-ok" : result.checkin.status === "PENDING" ? "alert-warn" : "alert-error"}`}>
          <div>
            <strong>
              {result.checkin.status === "APPROVED" ? t("Посетата е потврдена!") : result.checkin.status === "PENDING" ? t("Чека проверка од администратор.") : t("Посетата не е прифатена.")}
            </strong>
            <ul className="small">{result.checkin.verification_notes.map((n) => <li key={n}>{n}</li>)}</ul>
            {result.unlocked_badges.length > 0 && (
              <div className="badges">{result.unlocked_badges.map((b) => (
                <span key={b.code} className="badge-chip">{b.art ? <img src={b.art} width={28} height={28} alt="" /> : b.icon} {b.name}</span>
              ))}</div>
            )}
            {result.city_progress && (
              <div className="small">
                {t("{0}: документирани {1} од {2} знаменитости", { 0: result.city_progress.city_name, 1: result.city_progress.documented_required, 2: result.city_progress.required_total })}
                <Progress value={result.city_progress.percent} />
              </div>
            )}
          </div>
        </div>
      )}
    </form>
  );
}
