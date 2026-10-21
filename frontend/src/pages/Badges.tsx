import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { useAsync } from "../hooks";
import { useAuth } from "../auth";
import { ErrorBox, Loading, Progress, Stamp } from "../components/ui";
import type { Badge } from "../types";

type Filter = "all" | "earned" | "open";

const FILTERS: [Filter, string][] = [
  ["all", "Сите"],
  ["earned", "Освоени"],
  ["open", "Неосвоени"],
];

function Section({ title, hint, badges, earned, filter }: {
  title: string; hint: string; badges: Badge[]; earned: Map<string, string>; filter: Filter;
}) {
  const shown = badges.filter((b) => filter === "all" || (filter === "earned") === earned.has(b.code));
  const got = badges.filter((b) => earned.has(b.code)).length;
  return (
    <section className="panel stack">
      <div className="row between wrap gap">
        <div>
          <h2 style={{ margin: 0 }}>{title}</h2>
          <p className="muted small" style={{ margin: 0 }}>{hint}</p>
        </div>
        <span className="pill pill-info">{got} од {badges.length}</span>
      </div>
      {shown.length === 0 ? <p className="muted">Нема беџови за овој филтер.</p> : (
        <div className="stamps stamps-art">
          {shown.map((b) => <Stamp key={b.code} badge={b} date={earned.get(b.code)} locked={!earned.has(b.code)} />)}
        </div>
      )}
    </section>
  );
}

export default function BadgesPage() {
  const { user } = useAuth();
  const [filter, setFilter] = useState<Filter>("all");
  const all = useAsync(() => api<Badge[]>("/badges/"), []);
  const mine = useAsync(
    async () => (user ? (await api<{ badges: { badge: Badge; unlocked_at: string }[] }>("/me/gamification/")).badges : []),
    [user?.id],
  );

  const earned = useMemo(() => new Map((mine.data || []).map((x) => [x.badge.code, x.unlocked_at])), [mine.data]);
  const groups = useMemo(() => {
    const list = all.data || [];
    return {
      achievements: list.filter((b) => b.art && (b.kind === "CATEGORY" || b.kind === "LEVEL")),
      regions: list.filter((b) => b.kind === "REGION"),
      places: list.filter((b) => b.kind === "PLACE"),
    };
  }, [all.data]);

  if (all.loading) return <Loading />;
  if (all.error) return <ErrorBox message={all.error} />;

  const collectable = [...groups.achievements, ...groups.regions].filter((b) => b.available !== false);
  const got = collectable.filter((b) => earned.has(b.code)).length;
  const percent = collectable.length ? Math.round((got / collectable.length) * 100) : 0;

  return (
    <div className="stack-lg">
      <header className="badges-hero">
        <div>
          <p className="kicker">Колекција „Македонија“</p>
          <h1>Беџови и печати</h1>
          <p className="muted">
            Документирајте ја посетата со фотографија на лице место и беџот се отклучува автоматски.
            Беџовите означени со „Наскоро“ ќе се отворат кога местата ќе влезат во проверениот каталог.
          </p>
        </div>
        <div className="badges-score">
          {user ? (
            <>
              <strong>{got} <span>од {collectable.length}</span></strong>
              <span className="small">освоени беџови</span>
              <Progress value={percent} label="Колекција" />
            </>
          ) : (
            <>
              <strong className="small-strong">Вашата колекција</strong>
              <span className="small">Најавете се за да ги видите освоените беџови.</span>
              <Link to="/login" className="btn btn-green btn-sm">Најава</Link>
            </>
          )}
        </div>
      </header>

      {user && (
        <div className="chips" role="group" aria-label="Филтер">
          {FILTERS.map(([k, label]) => (
            <button key={k} type="button" className={filter === k ? "chip on" : "chip"} onClick={() => setFilter(k)}>{label}</button>
          ))}
        </div>
      )}

      <Section title="Достигнувања" hint="Нивоа, теми и „Град 100%“." badges={groups.achievements} earned={earned} filter={filter} />
      <Section title="Градови и предели" hint="40 локации низ Македонија, нумерирани како во албум." badges={groups.regions}
               earned={earned} filter={filter} />
      {groups.places.length > 0 && (
        <details className="panel">
          <summary><h2 style={{ margin: 0 }}>Печати за знаменитости</h2><span className="pill pill-muted">{groups.places.filter((b) => earned.has(b.code)).length} од {groups.places.length}</span></summary>
          <div className="stamps" style={{ marginTop: 16 }}>
            {groups.places.filter((b) => filter === "all" || (filter === "earned") === earned.has(b.code))
              .map((b) => <Stamp key={b.code} badge={b} date={earned.get(b.code)} locked={!earned.has(b.code)} />)}
          </div>
        </details>
      )}
    </div>
  );
}
