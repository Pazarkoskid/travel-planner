import { useState } from "react";
import { api } from "../services/api";
import { fmtDate, useAsync } from "../hooks";
import { Empty, ErrorBox, Loading, Meta } from "../components/ui";
import AdminPlaces from "./AdminPlaces";
import type { CheckIn, Photo, Review } from "../types";

const TYPE_LABEL: Record<string, string> = { ACCOMMODATION: "Сместување", RESTAURANT: "Ресторан", BOAT_TOUR: "Бродска тура", TAXI: "Такси" };

export default function AdminPanel() {
  const analytics = useAsync(() => api<Record<string, unknown>>("/admin/analytics/"), []);
  const checkins = useAsync(() => api<CheckIn[]>("/admin/checkins/"), []);
  const photoReports = useAsync(() => api<{ id: number; reason: string; reporter: string; photo: Photo }[]>("/admin/place-reports/"), []);
  const reviewReports = useAsync(() => api<{ id: number; reason: string; reporter: string; review: Review }[]>("/admin/review-reports/"), []);
  const businesses = useAsync(() => api<{ id: number; name: string; type: string; city: string; owner: string }[]>("/admin/businesses/pending/"), []);
  const [err, setErr] = useState<string | null>(null);

  const post = async (path: string, json: unknown, reload: () => void) => {
    setErr(null);
    try {
      await api(path, { method: "POST", json });
      reload();
      analytics.reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Грешка");
    }
  };

  const a = analytics.data as Record<string, number | Record<string, number> | null> | null;

  return (
    <div className="stack">
      <h1>Администрација</h1>
      {err && <ErrorBox message={err} />}
      {analytics.loading && <Loading />}
      {a && (
        <dl className="metrics panel">
          <div><dt>Патувања</dt><dd>{String(a.trips)}</dd></div>
          <div><dt>AI генерирања</dt><dd>{String(a.plan_runs)}</dd></div>
          <div><dt>Просечно генерирање</dt><dd>{String(a.avg_generation_ms ?? "—")} ms</dd></div>
          <div><dt>Просечно подобрување на рута</dt><dd>{String(a.avg_travel_improvement_pct ?? "—")}%</dd></div>
          <div><dt>Рецензии</dt><dd>{String(a.reviews)}</dd></div>
          <div><dt>Освоени печати</dt><dd>{String(a.badges_unlocked)}</dd></div>
        </dl>
      )}

      <section className="panel stack">
        <h2>Бизниси што чекаат одобрување</h2>
        {businesses.data?.length === 0 && <p className="muted">Нема.</p>}
        {businesses.data?.map((b) => (
          <div key={b.id} className="row between wrap">
            <span><strong>{b.name}</strong> <Meta items={[TYPE_LABEL[b.type] || b.type, b.city, `сопственик ${b.owner}`]} /></span>
            <span className="row gap">
              <button className="btn btn-primary btn-sm" onClick={() => post(`/admin/businesses/${b.id}/verify/`, { status: "APPROVED" }, businesses.reload)}>Одобри</button>
              <button className="btn btn-ghost btn-sm" onClick={() => post(`/admin/businesses/${b.id}/verify/`, { status: "REJECTED" }, businesses.reload)}>Одбиј</button>
            </span>
          </div>
        ))}
      </section>

      <section className="panel stack">
        <h2>Фото-посети за рачна проверка</h2>
        {checkins.data?.length === 0 && <Empty title="Нема фото-посети што чекаат." />}
        <div className="gallery">
          {checkins.data?.map((c) => (
            <figure key={c.id} className="photo">
              <img src={c.image} alt={`Фото-посета на ${c.place_name}`} />
              <figcaption className="stack">
                <strong>{c.place_name}</strong>
                <Meta items={[c.username, fmtDate(c.created_at), c.distance_m !== null ? `${Math.round(c.distance_m)} m од местото` : "без GPS"]} />
                <ul className="small">{c.verification_notes.map((n) => <li key={n}>{n}</li>)}</ul>
                <span className="row gap">
                  <button className="btn btn-primary btn-sm" onClick={() => post(`/admin/checkins/${c.id}/review/`, { action: "approve" }, checkins.reload)}>Одобри</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => post(`/admin/checkins/${c.id}/review/`, { action: "reject" }, checkins.reload)}>Одбиј</button>
                </span>
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="panel stack">
        <h2>Пријавени фотографии</h2>
        {photoReports.data?.length === 0 && <p className="muted">Нема.</p>}
        {photoReports.data?.map((r) => (
          <div key={r.id} className="row between wrap">
            <span className="row gap"><img src={r.photo.image} alt="" className="thumb" /> {r.photo.place_name}: „{r.reason}“ <span className="small muted">пријавил {r.reporter}</span></span>
            <span className="row gap">
              <button className="btn btn-primary btn-sm" onClick={() => post(`/admin/place-reports/${r.id}/resolve/`, { action: "hide" }, photoReports.reload)}>Скриј</button>
              <button className="btn btn-ghost btn-sm" onClick={() => post(`/admin/place-reports/${r.id}/resolve/`, { action: "dismiss" }, photoReports.reload)}>Отфрли</button>
            </span>
          </div>
        ))}
      </section>

      <section className="panel stack">
        <h2>Пријавени рецензии</h2>
        {reviewReports.data?.length === 0 && <p className="muted">Нема.</p>}
        {reviewReports.data?.map((r) => (
          <div key={r.id} className="row between wrap">
            <span>★{r.review.rating} „{r.review.comment}“ <span className="small">пријава: {r.reason}</span></span>
            <span className="row gap">
              <button className="btn btn-primary btn-sm" onClick={() => post(`/admin/review-reports/${r.id}/resolve/`, { action: "hide" }, reviewReports.reload)}>Скриј</button>
              <button className="btn btn-ghost btn-sm" onClick={() => post(`/admin/review-reports/${r.id}/resolve/`, { action: "dismiss" }, reviewReports.reload)}>Отфрли</button>
            </span>
          </div>
        ))}
      </section>
      <AdminPlaces />

      <p className="small muted">Бизнисите (профил, понуди, цени) ги уредувате од „Бизнис-табла“. Сè останато е достапно и во Django admin (/admin/).</p>
    </div>
  );
}
