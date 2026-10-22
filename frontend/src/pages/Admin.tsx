import { t } from "../i18n";
import { useState } from "react";
import { api } from "../services/api";
import { fmtDate, useAsync } from "../hooks";
import { Empty, ErrorBox, Loading, Meta } from "../components/ui";
import AdminPlaces from "./AdminPlaces";
import type { CheckIn, Photo, Review } from "../types";

const TYPE_LABEL: Record<string, string> = { ACCOMMODATION: t("Сместување"), RESTAURANT: t("Ресторан"), BOAT_TOUR: t("Бродска тура"), TAXI: t("Такси") };

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
      setErr(e instanceof Error ? e.message : t("Грешка"));
    }
  };

  const a = analytics.data as Record<string, number | Record<string, number> | null> | null;

  return (
    <div className="stack">
      <h1>{t("Администрација")}</h1>
      {err && <ErrorBox message={err} />}
      {analytics.loading && <Loading />}
      {a && (
        <dl className="metrics panel">
          <div><dt>{t("Патувања")}</dt><dd>{String(a.trips)}</dd></div>
          <div><dt>{t("AI генерирања")}</dt><dd>{String(a.plan_runs)}</dd></div>
          <div><dt>{t("Просечно генерирање")}</dt><dd>{String(a.avg_generation_ms ?? "—")} ms</dd></div>
          <div><dt>{t("Просечно подобрување на рута")}</dt><dd>{String(a.avg_travel_improvement_pct ?? "—")}%</dd></div>
          <div><dt>{t("Рецензии")}</dt><dd>{String(a.reviews)}</dd></div>
          <div><dt>{t("Освоени печати")}</dt><dd>{String(a.badges_unlocked)}</dd></div>
        </dl>
      )}

      <section className="panel stack">
        <h2>{t("Бизниси што чекаат одобрување")}</h2>
        {businesses.data?.length === 0 && <p className="muted">{t("Нема.")}</p>}
        {businesses.data?.map((b) => (
          <div key={b.id} className="row between wrap">
            <span><strong>{b.name}</strong> <Meta items={[TYPE_LABEL[b.type] || b.type, b.city, t("сопственик {0}", { 0: b.owner })]} /></span>
            <span className="row gap">
              <button className="btn btn-primary btn-sm" onClick={() => post(`/admin/businesses/${b.id}/verify/`, { status: "APPROVED" }, businesses.reload)}>{t("Одобри")}</button>
              <button className="btn btn-ghost btn-sm" onClick={() => post(`/admin/businesses/${b.id}/verify/`, { status: "REJECTED" }, businesses.reload)}>{t("Одбиј")}</button>
            </span>
          </div>
        ))}
      </section>

      <section className="panel stack">
        <h2>{t("Фото-посети за рачна проверка")}</h2>
        {checkins.data?.length === 0 && <Empty title={t("Нема фото-посети што чекаат.")} />}
        <div className="gallery">
          {checkins.data?.map((c) => (
            <figure key={c.id} className="photo">
              <img src={c.image} alt={t("Фото-посета на {0}", { 0: c.place_name })} />
              <figcaption className="stack">
                <strong>{c.place_name}</strong>
                <Meta items={[c.username, fmtDate(c.created_at), c.distance_m !== null ? t("{0} m од местото", { 0: Math.round(c.distance_m) }) : t("без GPS")]} />
                <ul className="small">{c.verification_notes.map((n) => <li key={n}>{n}</li>)}</ul>
                <span className="row gap">
                  <button className="btn btn-primary btn-sm" onClick={() => post(`/admin/checkins/${c.id}/review/`, { action: "approve" }, checkins.reload)}>{t("Одобри")}</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => post(`/admin/checkins/${c.id}/review/`, { action: "reject" }, checkins.reload)}>{t("Одбиј")}</button>
                </span>
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="panel stack">
        <h2>{t("Пријавени фотографии")}</h2>
        {photoReports.data?.length === 0 && <p className="muted">{t("Нема.")}</p>}
        {photoReports.data?.map((r) => (
          <div key={r.id} className="row between wrap">
            <span className="row gap"><img src={r.photo.image} alt="" className="thumb" /> {r.photo.place_name}: „{r.reason}“ <span className="small muted">{t("пријавил")} {r.reporter}</span></span>
            <span className="row gap">
              <button className="btn btn-primary btn-sm" onClick={() => post(`/admin/place-reports/${r.id}/resolve/`, { action: "hide" }, photoReports.reload)}>{t("Скриј")}</button>
              <button className="btn btn-ghost btn-sm" onClick={() => post(`/admin/place-reports/${r.id}/resolve/`, { action: "dismiss" }, photoReports.reload)}>{t("Отфрли")}</button>
            </span>
          </div>
        ))}
      </section>

      <section className="panel stack">
        <h2>{t("Пријавени рецензии")}</h2>
        {reviewReports.data?.length === 0 && <p className="muted">{t("Нема.")}</p>}
        {reviewReports.data?.map((r) => (
          <div key={r.id} className="row between wrap">
            <span>★{r.review.rating} „{r.review.comment}“ <span className="small">{t("пријава:")} {r.reason}</span></span>
            <span className="row gap">
              <button className="btn btn-primary btn-sm" onClick={() => post(`/admin/review-reports/${r.id}/resolve/`, { action: "hide" }, reviewReports.reload)}>{t("Скриј")}</button>
              <button className="btn btn-ghost btn-sm" onClick={() => post(`/admin/review-reports/${r.id}/resolve/`, { action: "dismiss" }, reviewReports.reload)}>{t("Отфрли")}</button>
            </span>
          </div>
        ))}
      </section>
      <AdminPlaces />

      <p className="small muted">{t("Бизнисите (профил, понуди, цени) ги уредувате од „Бизнис-табла“. Сè останато е достапно и во Django admin (/admin/).")}</p>
    </div>
  );
}
