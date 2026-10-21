import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../services/api";
import { fmtDate, useAsync } from "../hooks";
import { useAuth } from "../auth";
import { Empty, ErrorBox, Field, Loading, Progress, Stamp, StatusPill } from "../components/ui";
import type { Badge, CheckIn, CityProgress, Photo } from "../types";

interface PublicProfile {
  username: string;
  first_name: string;
  last_name: string;
  bio: string;
  avatar: string | null;
  badges: { badge: Badge; unlocked_at: string }[];
  city_progress: CityProgress[];
  photos: Photo[];
  visited_places: { id: number; name: string; city__name: string }[];
  favorite_places: { id: number; name: string; city__name: string }[];
  saved_trips: number | null;
}

interface Notification {
  id: number;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
}

function BadgeGrid({ badges }: { badges: { badge: Badge; unlocked_at: string }[] }) {
  if (badges.length === 0) return <Empty title="Пасошот е уште празен.">Отворете место и документирајте ја посетата со фотографија.</Empty>;
  return (
    <div className="stamps">
      {badges.map(({ badge, unlocked_at }) => <Stamp key={badge.code} badge={badge} date={unlocked_at} />)}
    </div>
  );
}

function CityProgressList({ items }: { items: CityProgress[] }) {
  return (
    <div className="city-progress">
      {items.map((c) => (
        <div key={c.city} className="city-progress-row">
          <div className="row between wrap">
            <strong>{c.city_name}</strong>
            <span className="small">{c.documented_required} од {c.required_total} знаменитости, {c.percent}%</span>
          </div>
          <Progress value={c.percent} label={`Истраженост на ${c.city_name}`} />
        </div>
      ))}
    </div>
  );
}

export function PublicProfilePage() {
  const { username } = useParams();
  const { data: p, error, loading } = useAsync(() => api<PublicProfile>(`/users/${username}/`), [username]);
  if (loading) return <Loading />;
  if (error || !p) return <ErrorBox message={error || "Не постои."} />;
  return (
    <div className="stack">
      <div className="profile-head">
        <div className="avatar" aria-hidden>{p.avatar ? <img src={p.avatar} alt="" /> : p.username[0].toUpperCase()}</div>
        <div>
          <h1>{p.first_name || p.username} {p.last_name}</h1>
          <p className="muted" style={{ margin: 0 }}>@{p.username}</p>
          {p.bio && <p style={{ margin: "4px 0 0" }}>{p.bio}</p>}
        </div>
      </div>
      <section className="panel"><h2>Печати</h2><BadgeGrid badges={p.badges} /></section>
      {p.city_progress.length > 0 && <section className="panel"><h2>Истраженост по град</h2><CityProgressList items={p.city_progress} /></section>}
      <section className="panel">
        <h2>Посетени знаменитости</h2>
        {p.visited_places.length === 0 ? <p className="muted">Уште нема документирани посети.</p> : (
          <div className="chips">{p.visited_places.map((v) => <Link className="chip" key={v.id} to={`/places/${v.id}`}>{v.name}</Link>)}</div>
        )}
      </section>
      <section>
        <h2>Фотографии</h2>
        <div className="gallery">
          {p.photos.map((ph) => (
            <figure key={ph.id} className="photo">
              <img src={ph.image} alt={ph.caption || ph.place_name} loading="lazy" />
              <figcaption><Link to={`/places/${ph.place}`}>{ph.place_name}</Link></figcaption>
            </figure>
          ))}
        </div>
      </section>
    </div>
  );
}

export function MyProfile() {
  const { user, reload: reloadUser } = useAuth();
  const g = useAsync(() => api<{ badges: { badge: Badge; unlocked_at: string }[]; city_progress: CityProgress[]; checkins: CheckIn[] }>("/me/gamification/"), []);
  const notes = useAsync(async () => {
    const r = await api<Notification[] | { results: Notification[] }>("/notifications/");
    return Array.isArray(r) ? r : r.results;
  }, []);
  const [bio, setBio] = useState(user?.bio || "");
  const [isPublic, setIsPublic] = useState(user?.is_profile_public ?? true);
  const [saved, setSaved] = useState(false);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    await api("/auth/me/", { method: "PATCH", json: { bio, is_profile_public: isPublic } });
    await reloadUser();
    setSaved(true);
  };

  if (!user) return null;
  return (
    <div className="stack">
      <div className="row between wrap">
        <h1>Мој профил</h1>
        <Link to={`/u/${user.username}`} className="btn btn-ghost btn-sm">Јавен приказ</Link>
      </div>
      <form className="panel stack" onSubmit={save}>
        <Field label="Кратка биографија"><input value={bio} maxLength={500} onChange={(e) => { setBio(e.target.value); setSaved(false); }} /></Field>
        <label className="check"><input type="checkbox" checked={isPublic} onChange={(e) => { setIsPublic(e.target.checked); setSaved(false); }} /> Профилот е јавен</label>
        <div className="row gap"><button className="btn btn-primary btn-sm">Зачувај</button>{saved && <span className="small">Зачувано.</span>}</div>
      </form>
      {g.loading && <Loading />}
      {g.data && (
        <>
          <section className="panel">
            <div className="row between wrap gap"><h2>Мој пасош</h2><Link to="/badges" className="btn btn-ghost btn-sm">Целата колекција</Link></div>
            <BadgeGrid badges={g.data.badges} />
          </section>
          <section className="panel"><h2>Истраженост по град</h2><CityProgressList items={g.data.city_progress} /></section>
          <section className="panel">
            <h2>Мои фото-посети</h2>
            {g.data.checkins.length === 0 ? <p className="muted">Нема. Отворете место и документирајте посета.</p> : (
              <ul className="plain">
                {g.data.checkins.map((c) => (
                  <li key={c.id} style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) auto auto", gap: 16, alignItems: "center" }}>
                    <Link to={`/places/${c.place}`}>{c.place_name}</Link>
                    <span className="small muted">{fmtDate(c.created_at)}</span>
                    <StatusPill status={c.status} label={c.status === "APPROVED" ? "одобрено" : c.status === "PENDING" ? "чека проверка" : "одбиено"} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
      <section className="panel">
        <div className="row between">
          <h2>Известувања</h2>
          <button className="btn btn-ghost btn-sm" onClick={async () => { await api("/notifications/read-all/", { method: "POST" }); notes.reload(); }}>Означи прочитано</button>
        </div>
        <ul className="plain">
          {notes.data?.slice(0, 20).map((n) => (
            <li key={n.id} className={n.read_at ? "muted" : ""}>
              <strong>{n.title}</strong> <span className="small">{n.body}</span> <span className="small muted">{fmtDate(n.created_at)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
