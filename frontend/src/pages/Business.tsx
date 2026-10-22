import { t } from "../i18n";
import { Link } from "react-router-dom";
import { useState } from "react";
import { api } from "../services/api";
import { eur, useAsync } from "../hooks";
import { Empty, ErrorBox, Loading, StatusPill } from "../components/ui";
import { when } from "./Reservations";
import type { Reservation } from "../types";

interface DashboardRow {
  id: number;
  name: string;
  type: string;
  verification_status: string;
  reservations_total: number;
  pending: number;
  confirmation_rate_pct: number | null;
  avg_rating: number | null;
  review_count: number;
}

const VERIFICATION: Record<string, string> = { APPROVED: t("Одобрен"), PENDING: t("Чека одобрување"), REJECTED: t("Одбиен"), SUSPENDED: t("Суспендиран") };

const ACTIONS: Record<string, [string, string][]> = {
  PENDING: [["confirm", t("Прифати")], ["reject", t("Одбиј")]],
  CONFIRMED: [["start", t("Во тек")], ["complete", t("Заврши")], ["cancel", t("Откажи")]],
  IN_PROGRESS: [["complete", t("Заврши")]],
};

export default function BusinessDashboard() {
  const dash = useAsync(() => api<{ businesses: DashboardRow[] }>("/business/dashboard/"), []);
  const [filter, setFilter] = useState("PENDING");
  const list = useAsync(() => api<Reservation[]>(`/business/reservations/${filter ? `?status=${filter}` : ""}`), [filter]);
  const [err, setErr] = useState<string | null>(null);

  const act = async (r: Reservation, action: string) => {
    setErr(null);
    const json: Record<string, unknown> = { action };
    if (action === "propose") {
      const v = window.prompt(t("Нов термин (YYYY-MM-DD HH:MM):"));
      if (!v) return;
      json.proposed_datetime = new Date(v.replace(" ", "T")).toISOString();
    }
    if (action === "quote") {
      const v = window.prompt(t("Цена на понудата (EUR):"));
      if (!v) return;
      json.quoted_price = v;
    }
    if (action === "reject" || action === "cancel") json.note = window.prompt(t("Порака до гостинот (опционално):")) || "";
    try {
      await api(`/business/reservations/${r.id}/`, { method: "PATCH", json });
      list.reload();
      dash.reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : t("Грешка"));
    }
  };

  const actionsFor = (r: Reservation) => {
    const out: [string, string][] = [...(ACTIONS[r.status] || [])];
    if (r.status === "PENDING" && ["RESTAURANT", "TAXI"].includes(r.service_type)) out.push(["propose", t("Друг термин")]);
    if (r.status === "PENDING" && r.service_type === "TAXI") out.push(["quote", t("Испрати понуда")]);
    return out;
  };

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>{t("Бизнис-табла")}</h1>
          <p>{t("Барањата што чекаат одговор се прикажани први.")}</p>
        </div>
        <Link className="btn btn-primary" to="/business/new">{t("Додај бизнис")}</Link>
      </div>
      {dash.loading && <Loading />}
      {dash.data?.businesses.length === 0 && <Empty title={t("Немате бизниси.")}><Link className="btn btn-primary btn-sm" to="/business/new">{t("Додај бизнис")}</Link></Empty>}
      <div className="grid grid-3">
        {dash.data?.businesses.map((b) => (
          <div key={b.id} className="panel panel-tight">
            <strong>{b.name}</strong> <StatusPill status={b.verification_status === "APPROVED" ? "APPROVED" : b.verification_status === "PENDING" ? "PENDING" : "REJECTED"} label={VERIFICATION[b.verification_status] || b.verification_status} />
            <dl className="metrics">
              <div><dt>{t("Барања")}</dt><dd>{b.reservations_total}</dd></div>
              <div><dt>{t("Чекаат")}</dt><dd>{b.pending}</dd></div>
              <div><dt>{t("Потврдени")}</dt><dd>{b.confirmation_rate_pct === null ? t("нема") : `${b.confirmation_rate_pct}%`}</dd></div>
              <div><dt>{t("Оценка")}</dt><dd>{b.avg_rating ?? t("нема")} ({b.review_count})</dd></div>
            </dl>
            <Link className="btn btn-ghost btn-sm btn-block" style={{ marginTop: 12 }} to={`/business/${b.id}/edit`}>
              {t("Уреди оглас, цени и работно време")}
            </Link>
          </div>
        ))}
      </div>
      <div className="row between wrap">
        <h2 style={{ margin: 0 }}>{t("Резервации")}</h2>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label={t("Филтер по статус")} style={{ width: "auto" }}>
          <option value="PENDING">{t("Чекаат одговор")}</option>
          <option value="CONFIRMED">{t("Потврдени")}</option>
          <option value="IN_PROGRESS">{t("Во тек")}</option>
          <option value="COMPLETED">{t("Завршени")}</option>
          <option value="">{t("Сите")}</option>
        </select>
      </div>
      {err && <ErrorBox message={err} />}
      {list.loading && <Loading />}
      {list.data?.length === 0 && <Empty title={t("Нема резервации со овој статус.")} />}
      {list.data && list.data.length > 0 && (
        <div className="table-wrap">
          <table className="table table-cards">
            <thead><tr><th>#</th><th>{t("Гостин")}</th><th>{t("Услуга")}</th><th>{t("Термин")}</th><th>{t("Цена")}</th><th>{t("Статус")}</th><th>{t("Акции")}</th></tr></thead>
            <tbody>
              {list.data.map((r) => (
                <tr key={r.id}>
                  <td data-label="#">{r.id}</td>
                  <td data-label={t("Гостин")}>{r.user_name}<div className="small muted">{r.guests} {t("лица")}</div></td>
                  <td data-label={t("Услуга")}>{r.business_name}<div className="small muted">{r.unit_name || t(r.service_label)}{r.pickup && t(", од {0} до {1}", { 0: r.pickup, 1: r.destination })}</div></td>
                  <td data-label={t("Термин")}>{when(r)}</td>
                  <td data-label={t("Цена")}>{eur(r.total_price ?? r.quoted_price)}</td>
                  <td data-label={t("Статус")}><StatusPill status={r.status} label={t(r.status_label)} /></td>
                  <td className="td-actions">
                    {actionsFor(r).map(([a, label]) => (
                      <button key={a} className={a === "confirm" ? "btn btn-primary btn-sm" : "btn btn-ghost btn-sm"} onClick={() => act(r, a)}>{label}</button>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
