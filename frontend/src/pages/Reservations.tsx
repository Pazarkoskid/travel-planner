import { FormEvent, useState } from "react";
import { api } from "../services/api";
import { eur, fmtDate, fmtDateTime, useAsync } from "../hooks";
import { Empty, ErrorBox, Field, Loading, Meta, StatusPill } from "../components/ui";
import type { Reservation } from "../types";

const DIMENSIONS: Record<string, [string, string][]> = {
  ACCOMMODATION: [["cleanliness", "Чистота"], ["location", "Локација"], ["comfort", "Удобност"], ["value", "Вредност за парите"], ["communication", "Комуникација"]],
  RESTAURANT: [["food", "Храна"], ["service", "Услуга"], ["atmosphere", "Атмосфера"], ["value", "Вредност за парите"]],
  BOAT_TOUR: [["safety", "Безбедност"], ["punctuality", "Точност"], ["service", "Услуга"], ["communication", "Комуникација"], ["overall", "Целокупно"]],
  TAXI: [["punctuality", "Точност"], ["safety", "Безбедност"], ["service", "Услуга"], ["communication", "Комуникација"], ["overall", "Целокупно"]],
};

export function when(r: Reservation) {
  if (r.check_in) return `${fmtDate(r.check_in)} до ${fmtDate(r.check_out)}`;
  if (r.departure_at) return fmtDateTime(r.departure_at);
  return fmtDateTime(r.reserved_for);
}

export default function MyReservations() {
  const { data, error, loading, reload } = useAsync(() => api<Reservation[]>("/reservations/mine/"), []);
  const [actionErr, setActionErr] = useState<string | null>(null);
  const [reviewFor, setReviewFor] = useState<number | null>(null);

  const act = async (path: string) => {
    setActionErr(null);
    try {
      await api(path, { method: "POST", json: {} });
      reload();
    } catch (e) {
      setActionErr(e instanceof Error ? e.message : "Грешка");
    }
  };

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Мои резервации</h1>
          <p>По завршена услуга можете да оставите проверена рецензија.</p>
        </div>
      </div>
      {actionErr && <ErrorBox message={actionErr} />}
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data?.length === 0 && <Empty title="Немате резервации.">Резервирајте сместување или бродска тура од менито горе.</Empty>}
      {data?.map((r) => (
        <article key={r.id} className={`panel panel-tight reservation s-${r.status}`}>
          <div className="stack" style={{ gap: 12 }}>
          <div className="row between wrap">
            <div>
              <h3 style={{ margin: 0 }}>{r.business_name}</h3>
              <Meta items={[`#${r.id}`, r.service_label, r.unit_name, when(r), `${r.guests} лица`]} />
            </div>
            <StatusPill status={r.status} label={r.status_label} />
          </div>
          {r.total_price && <div className="small">Вкупно, по цената во моментот на барањето: <strong>{eur(r.total_price)}</strong></div>}
          {r.business_message && <div className="small">Порака од бизнисот: {r.business_message}</div>}
          {r.status === "ALTERNATIVE_PROPOSED" && (
            <div className="alert alert-warn">Предложен нов термин: <strong>{fmtDateTime(r.proposed_datetime)}</strong></div>
          )}
          {r.status === "QUOTED" && <div className="alert alert-warn">Понуда за превоз: <strong>{eur(r.quoted_price)}</strong></div>}
          <div className="row gap wrap">
            {["ALTERNATIVE_PROPOSED", "QUOTED"].includes(r.status) && (
              <button className="btn btn-primary btn-sm" onClick={() => act(`/reservations/${r.id}/accept/`)}>Прифати</button>
            )}
            {["PENDING", "ALTERNATIVE_PROPOSED", "QUOTED", "CONFIRMED"].includes(r.status) && (
              <button className="btn btn-ghost btn-sm" onClick={() => window.confirm("Да се откаже резервацијата?") && act(`/reservations/${r.id}/cancel/`)}>Откажи</button>
            )}
            {r.can_review && <button className="btn btn-primary btn-sm" onClick={() => setReviewFor(r.id)}>Остави рецензија</button>}
            {r.has_review && <span className="pill pill-ok">Рецензијата е објавена</span>}
          </div>
          {reviewFor === r.id && <ReviewForm reservation={r} onDone={() => { setReviewFor(null); reload(); }} />}
          <details className="small">
            <summary>Историја на статуси</summary>
            <ul>{r.history.map((h, i) => <li key={i}>{fmtDateTime(h.created_at)}: {h.to_status}{h.note && `, ${h.note}`}</li>)}</ul>
          </details>
          </div>
        </article>
      ))}
    </div>
  );
}

function ReviewForm({ reservation, onDone }: { reservation: Reservation; onDone: () => void }) {
  const dims = DIMENSIONS[reservation.service_type] || [];
  const [rating, setRating] = useState(5);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api(`/reservations/${reservation.id}/review/`, { method: "POST", json: { rating, dimension_scores: scores, comment } });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Грешка");
    }
  };

  return (
    <form className="subcard stack" onSubmit={submit}>
      {error && <ErrorBox message={error} />}
      <Field label="Вкупна оценка">
        <select value={rating} onChange={(e) => setRating(Number(e.target.value))}>
          {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{"★".repeat(n)} ({n})</option>)}
        </select>
      </Field>
      <div className="grid grid-3">
        {dims.map(([k, label]) => (
          <Field key={k} label={label}>
            <select value={scores[k] || ""} onChange={(e) => setScores({ ...scores, [k]: Number(e.target.value) })}>
              <option value="">—</option>
              {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </Field>
        ))}
      </div>
      <Field label="Коментар"><textarea rows={3} maxLength={3000} value={comment} onChange={(e) => setComment(e.target.value)} /></Field>
      <button className="btn btn-primary btn-sm">Објави</button>
    </form>
  );
}
