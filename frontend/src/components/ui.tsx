import { ReactNode } from "react";
import { fmtDate } from "../hooks";
import type { Badge } from "../types";

export const Loading = ({ label = "Се вчитува" }: { label?: string }) => (
  <div className="state" role="status">
    <span className="spinner" aria-hidden /> {label}
  </div>
);

export const ErrorBox = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div className="alert alert-error" role="alert">
    <span>{message}</span>
    {onRetry && (
      <button className="btn btn-ghost btn-sm" onClick={onRetry}>
        Вчитај повторно
      </button>
    )}
  </div>
);

export const Empty = ({ title, children }: { title: string; children?: ReactNode }) => (
  <div className="empty">
    <strong>{title}</strong>
    {children && <div className="muted">{children}</div>}
  </div>
);

/** Мета-информации без интерпункциски сепаратори — само простор. */
export const Meta = ({ items }: { items: (ReactNode | false | null | undefined)[] }) => (
  <div className="meta">
    {items.filter(Boolean).map((it, i) => (
      <span key={i}>{it}</span>
    ))}
  </div>
);

const STATUS_TONE: Record<string, string> = {
  PENDING: "warn",
  QUOTED: "info",
  ALTERNATIVE_PROPOSED: "info",
  CONFIRMED: "ok",
  IN_PROGRESS: "info",
  COMPLETED: "ok",
  REJECTED: "bad",
  CANCELLED: "muted",
  APPROVED: "ok",
};

export const StatusPill = ({ status, label }: { status: string; label?: string }) => (
  <span className={`pill pill-${STATUS_TONE[status] || "muted"}`}>{label || status}</span>
);

export const Progress = ({ value, label }: { value: number; label?: string }) => (
  <div className="progress" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
    {value > 0 && <div className="progress-fill" style={{ width: `${Math.max(3, Math.min(100, value))}%` }} />}
  </div>
);

export const Stars = ({ value, count }: { value: number | null; count?: number }) =>
  value ? (
    <span className="stars" aria-label={`${value.toFixed(1)} од 5`}>
      ★ {value.toFixed(1)}
      {count !== undefined && <span className="muted small"> ({count})</span>}
    </span>
  ) : (
    <span className="muted small">Сè уште нема оценки</span>
  );

export const Field = ({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) => (
  <label className="field">
    <span className="field-label">{label}</span>
    {children}
    {hint && <span className="field-hint">{hint}</span>}
  </label>
);

/** Беџ во форма на печат од пасош. */
export function Stamp({ badge, date }: { badge: Badge; date?: string }) {
  const cls = ["stamp", badge.kind === "LEVEL" ? "stamp-level" : "", badge.level === "CITY_MASTER" ? "stamp-master" : ""].join(" ");
  return (
    <div className={cls} title={badge.description}>
      <div className="stamp-ring" aria-hidden>
        <span className="stamp-icon">{badge.icon}</span>
      </div>
      <span className="stamp-name">{badge.name}</span>
      {date && <span className="stamp-date">{fmtDate(date)}</span>}
    </div>
  );
}
