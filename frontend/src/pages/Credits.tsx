import { t } from "../i18n";
import { Link } from "react-router-dom";
import { api, unwrap } from "../services/api";
import { useAsync } from "../hooks";
import { Empty, Loading } from "../components/ui";
import type { City, Place } from "../types";

export default function Credits() {
  const cities = useAsync(() => api<City[]>("/cities/"), []);
  const places = useAsync(async () => unwrap(await api<Place[] | { results: Place[] }>("/places/")), []);
  const rows = [
    ...(cities.data || []).filter((c) => c.image_credit).map((c) => ({ key: `c${c.id}`, name: c.name, to: `/places?city=${c.slug}`, credit: c.image_credit, url: c.image_url })),
    ...(places.data || []).filter((p) => p.image_credit).map((p) => ({ key: `p${p.id}`, name: p.name, to: `/places/${p.id}`, credit: p.image_credit, url: p.image_url })),
  ];

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div>
          <h1>{t("Извори на фотографии")}</h1>
          <p>{t("Фотографиите се од Wikimedia Commons, под слободни лиценци. За секоја е наведен авторот и лиценцата.")}</p>
        </div>
      </div>
      {(cities.loading || places.loading) && <Loading />}
      {!cities.loading && !places.loading && rows.length === 0 && (
        <Empty title={t("Сè уште нема преземени фотографии.")}>
          {t("Администраторот ги презема со командата")} <code>python manage.py fetch_images</code>.
        </Empty>
      )}
      {rows.length > 0 && (
        <ul className="plain panel">
          {rows.map((r) => (
            <li key={r.key} className="credit-row">
              <Link to={r.to}><strong>{r.name}</strong></Link>
              <span className="small muted">{r.credit}</span>
              <a className="small" href={r.url} target="_blank" rel="noreferrer">{t("Оригинал")}</a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
