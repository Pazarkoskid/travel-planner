import { useState } from "react";
import { api } from "../services/api";
import { t } from "../i18n";
import type { Person, Relation } from "../types";
import Icon from "./Icon";

/** Копче според односот: Додај → Испратено (откажи) → Прифати/Одбиј → Пријатели (отстрани). */
export default function FriendButton({ username, relation, requestId, onChange }: {
  username: string; relation: Relation; requestId: number | null; onChange?: (p: Partial<Person>) => void;
}) {
  const [rel, setRel] = useState<Relation>(relation);
  const [reqId, setReqId] = useState(requestId);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (fn: () => Promise<Partial<Person> | void>, fallback: Relation) => {
    setBusy(true);
    setErr(null);
    try {
      const p = (await fn()) || {};
      const next = (p.relation as Relation) || fallback;
      setRel(next);
      setReqId(p.request_id ?? null);
      onChange?.({ ...p, relation: next });
    } catch (e) {
      setErr(e instanceof Error ? e.message : t("Грешка"));
    } finally {
      setBusy(false);
    }
  };
  const add = () => run(() => api<Person>("/friends/requests/", { method: "POST", json: { username } }), "outgoing");
  const remove = (confirmText: string) => {
    if (confirmText && !window.confirm(confirmText)) return;
    run(() => api(`/friends/${encodeURIComponent(username)}/`, { method: "DELETE" }).then(() => undefined), "none");
  };
  const accept = () => run(() => api<Person>(`/friends/requests/${reqId}/accept/`, { method: "POST" }), "friends");
  const decline = () => run(() => api<Person>(`/friends/requests/${reqId}/decline/`, { method: "POST" }), "none");

  return (
    <div className="friend-actions">
      {rel === "none" && <button className="btn btn-primary btn-sm" disabled={busy} onClick={add}><Icon name="plus" size={16} />{t("Додај пријател")}</button>}
      {rel === "outgoing" && <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => remove("")}>{t("Испратено · откажи")}</button>}
      {rel === "incoming" && (
        <>
          <button className="btn btn-primary btn-sm" disabled={busy} onClick={accept}><Icon name="check" size={16} />{t("Прифати")}</button>
          <button className="btn btn-ghost btn-sm" disabled={busy} onClick={decline}>{t("Одбиј")}</button>
        </>
      )}
      {rel === "friends" && (
        <button className="btn btn-ghost btn-sm friend-on" disabled={busy}
                onClick={() => remove(t("Да се отстрани {0} од пријателите?", { 0: username }))}>
          <Icon name="check" size={16} />{t("Пријатели")}
        </button>
      )}
      {err && <span className="small warn-text">{err}</span>}
    </div>
  );
}
