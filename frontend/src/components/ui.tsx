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
export function BadgeArt({ badge, size = 112, locked = false }: { badge: Badge; size?: number; locked?: boolean }) {
  if (!badge.art) {
    return (
      <div className="stamp-ring" style={{ width: size, height: size }} aria-hidden>
        <span className="stamp-icon">{badge.icon}</span>
      </div>
    );
  }
  return <img className={locked ? "badge-art locked" : "badge-art"} src={badge.art} width={size} height={size} alt="" loading="lazy" />;
}

export function Stamp({ badge, date, locked = false }: { badge: Badge; date?: string; locked?: boolean }) {
  const cls = ["stamp", badge.art ? "stamp-has-art" : "", badge.kind === "LEVEL" ? "stamp-level" : "",
    badge.level === "CITY_MASTER" ? "stamp-master" : "", locked ? "stamp-locked" : ""].join(" ");
  return (
    <div className={cls} title={badge.description}>
      <span className="stamp-art-wrap">
        <BadgeArt badge={badge} locked={locked} />
        {locked && <span className="stamp-lock" aria-hidden>{badge.available === false ? "Наскоро" : "🔒"}</span>}
      </span>
      <span className="stamp-name">{badge.name}</span>
      {date && <span className="stamp-date">{fmtDate(date)}</span>}
      {locked && badge.kind !== "REGION" && <span className="stamp-date">{badge.description}</span>}
    </div>
  );
}
