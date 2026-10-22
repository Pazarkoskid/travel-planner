import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { useAsync } from "../hooks";
import { t } from "../i18n";
import { Empty, ErrorBox, Loading } from "../components/ui";
import FriendButton from "../components/FriendButton";
import Icon from "../components/Icon";
import type { Person } from "../types";

interface Lists { friends: Person[]; incoming: Person[]; outgoing: Person[] }

function PersonRow({ p, onChange }: { p: Person; onChange: () => void }) {
  return (
    <li className="person">
      <Link to={`/u/${p.username}`} className="person-link">
        <span className="person-avatar" aria-hidden>{p.username[0].toUpperCase()}</span>
        <span className="person-text">
          <strong>{p.name || p.username}</strong>
          <span className="small muted">@{p.username}{p.badges ? ` · ${t("{0} печати", { 0: p.badges })}` : ""}</span>
          {p.bio && <span className="small person-bio">{p.bio}</span>}
        </span>
      </Link>
      <FriendButton username={p.username} relation={p.relation} requestId={p.request_id} onChange={onChange} />
    </li>
  );
}

export default function FriendsPage() {
  const lists = useAsync(() => api<Lists>("/friends/"), []);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Person[] | null>(null);
  const [searching, setSearching] = useState(false);

  // Пребарување со мало доцнење додека се пишува.
  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) { setResults(null); return; }
    setSearching(true);
    const id = window.setTimeout(async () => {
      try { setResults(await api<Person[]>(`/people/search/?q=${encodeURIComponent(term)}`)); }
      catch { setResults([]); }
      finally { setSearching(false); }
    }, 300);
    return () => window.clearTimeout(id);
  }, [q]);

  const refresh = () => lists.reload();

  return (
    <div className="stack-lg">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>{t("Пријатели")}</h1>
          <p>{t("Најдете патници по име и споделувајте печати и фотографии.")}</p>
        </div>
      </div>

      <section className="panel stack">
        <label className="search-people">
          <Icon name="search" size={20} />
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("Пребарај по име или корисничко име")}
                 aria-label={t("Пребарај корисници")} autoComplete="off" />
        </label>
        {q.trim().length > 0 && q.trim().length < 2 && <p className="small muted">{t("Внесете барем 2 знаци.")}</p>}
        {searching && <Loading label={t("Се пребарува")} />}
        {results && !searching && (results.length === 0
          ? <p className="muted">{t("Нема корисници со тоа име (приватните профили не се прикажуваат).")}</p>
          : <ul className="people">{results.map((p) => <PersonRow key={p.username} p={p} onChange={refresh} />)}</ul>)}
      </section>

      {lists.loading && <Loading />}
      {lists.error && <ErrorBox message={lists.error} onRetry={lists.reload} />}
      {lists.data && (
        <>
          {lists.data.incoming.length > 0 && (
            <section className="panel stack">
              <h2>{t("Барања за пријателство")} <span className="dot">{lists.data.incoming.length}</span></h2>
              <ul className="people">{lists.data.incoming.map((p) => <PersonRow key={p.username} p={p} onChange={refresh} />)}</ul>
            </section>
          )}
          <section className="panel stack">
            <h2>{t("Мои пријатели")} <span className="pill pill-info">{lists.data.friends.length}</span></h2>
            {lists.data.friends.length === 0
              ? <Empty title={t("Сè уште немате пријатели.")}>{t("Пребарајте патници погоре и испратете барање.")}</Empty>
              : <ul className="people">{lists.data.friends.map((p) => <PersonRow key={p.username} p={p} onChange={refresh} />)}</ul>}
          </section>
          {lists.data.outgoing.length > 0 && (
            <section className="panel stack">
              <h2>{t("Испратени барања")}</h2>
              <ul className="people">{lists.data.outgoing.map((p) => <PersonRow key={p.username} p={p} onChange={refresh} />)}</ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
