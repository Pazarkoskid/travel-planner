import { FormEvent, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, unwrap } from "../services/api";
import { eur, isoDate, useAsync } from "../hooks";
import Icon from "../components/Icon";
import Photo from "../components/Photo";
import type { AccommodationResult, BoatTour, City, Place, Review } from "../types";

const INTERESTS: [string, string][] = [
  ["", "Сите активности"],
  ["history", "Историја"],
  ["religion", "Цркви и манастири"],
  ["nature", "Природа"],
  ["beach", "Плажи"],
  ["culture", "Култура"],
  ["museums", "Музеи"],
  ["local_food", "Локална храна"],
];

function SearchBar({ cities }: { cities: City[] }) {
  const nav = useNavigate();
  const [city, setCity] = useState("");
  const [interest, setInterest] = useState("");
  const [start, setStart] = useState(isoDate(7));
  const [guests, setGuests] = useState("2");
  const cityId = city || String(cities.find((c) => c.slug === "ohrid")?.id || cities[0]?.id || "");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const p = new URLSearchParams({ city: cityId, start_date: start, guests, days: "3" });
    if (interest) p.set("interest", interest);
    nav(`/trips/new?${p}`);
  };

  return (
    <form className="searchbar" onSubmit={submit} aria-label="Пребарај патување">
      <label className="sb-field">
        <Icon name="pin" />
        <span className="sb-text">
          <span className="sb-label">Дестинација</span>
          <select value={cityId} onChange={(e) => setCity(e.target.value)}>
            {cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </span>
      </label>
      <label className="sb-field">
        <Icon name="route" />
        <span className="sb-text">
          <span className="sb-label">Активност</span>
          <select value={interest} onChange={(e) => setInterest(e.target.value)}>
            {INTERESTS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </span>
      </label>
      <label className="sb-field">
        <Icon name="calendar" />
        <span className="sb-text">
          <span className="sb-label">Датум на поаѓање</span>
          <input type="date" min={isoDate(0)} value={start} onChange={(e) => setStart(e.target.value)} required />
        </span>
      </label>
      <label className="sb-field">
        <Icon name="user" />
        <span className="sb-text">
          <span className="sb-label">Гости</span>
          <select value={guests} onChange={(e) => setGuests(e.target.value)}>
            {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => <option key={n} value={n}>{n} {n === 1 ? "гостин" : "гости"}</option>)}
          </select>
        </span>
      </label>
      <button className="btn btn-green sb-submit" disabled={!cityId}><Icon name="search" size={18} />Пребарај</button>
    </form>
  );
}

function Carousel({ places }: { places: Place[] }) {
  const track = useRef<HTMLDivElement>(null);
  const [page, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(places.length / 4));

  const go = (dir: number) => {
    const el = track.current;
    if (!el) return;
    el.scrollBy({ left: dir * el.clientWidth, behavior: "smooth" });
  };
  const onScroll = () => {
    const el = track.current;
    if (el) setPage(Math.round(el.scrollLeft / Math.max(1, el.clientWidth)));
  };

  return (
    <div className="carousel">
      <div className="carousel-track" ref={track} onScroll={onScroll}>
        {places.map((p, i) => (
          <Link key={p.id} to={`/places/${p.id}`} className="dest-card">
            <Photo src={p.image_url} alt={p.name} credit={p.image_credit} seed={i} />
            <div className="dest-info">
              <span className="dest-badge"><Icon name="camera" size={13} />{p.badge_holders ?? 0}</span>
              <strong>{p.name}</strong>
              <span>{p.city_name}, {p.visit_duration_min} мин</span>
            </div>
          </Link>
        ))}
      </div>
      <div className="carousel-nav">
        <button className="round-btn" aria-label="Претходни" onClick={() => go(-1)}><Icon name="left" size={18} /></button>
        <div className="dots" aria-hidden>
          {Array.from({ length: pages }, (_, i) => <span key={i} className={i === Math.min(page, pages - 1) ? "on" : ""} />)}
        </div>
        <button className="round-btn" aria-label="Следни" onClick={() => go(1)}><Icon name="right" size={18} /></button>
      </div>
    </div>
  );
}

export default function Home() {
  const { data: cities } = useAsync(() => api<City[]>("/cities/"), []);
  const { data: places } = useAsync(async () => unwrap(await api<Place[] | { results: Place[] }>("/places/?required=1")), []);
  const { data: tours } = useAsync(async () => unwrap(await api<BoatTour[] | { results: BoatTour[] }>("/boat-tours/")), []);
  const { data: stays } = useAsync(() => api<AccommodationResult[]>("/accommodations/"), []);
  const { data: reviews } = useAsync(() => api<(Review & { business_name: string })[]>("/reviews/latest/"), []);

  const heroPlace = places?.find((p) => p.slug === "kaneo" && p.image_url);
  const ohrid = cities?.find((c) => c.slug === "ohrid");
  const heroImg = heroPlace?.image_url || ohrid?.image_url || "";
  const heroCredit = heroPlace?.image_credit || ohrid?.image_credit || "";
  const sideImg = places?.find((p) => p.slug === "sv-naum");
  const ohridTotal = ohrid?.required_landmarks || 10;

  const offers = useMemo(() => [
    ...(tours || []).map((t) => ({
      key: `t${t.id}`, to: "/boat-tours", img: t.business.image_url || sideImg?.image_url || t.business.city_image_url,
      place: t.business.city_name, title: t.title, meta: `${Math.round(t.duration_min / 60)} часа, од ${t.departure_point}`,
      price: `${eur(t.price_per_person)}`, unit: "по лице",
    })),
    ...(stays || []).map((s) => ({
      key: `s${s.id}`, to: "/stay", img: s.business.image_url || s.business.city_image_url, place: s.business.city_name,
      title: s.title, meta: `${s.type_label}, до ${s.max_guests} гости`, price: "Цена по датум", unit: "",
    })),
  ].slice(0, 4), [tours, stays, sideImg]);

  return (
    <>
      <section className="hero-full">
        <Photo className="hero-bg" src={heroImg} alt="Црквата Св. Јован Канео над Охридското Езеро" eager seed={1} />
        <div className="hero-shade" aria-hidden />
        <div className="container hero-inner">
          <p className="hero-script-small">Истражи ја</p>
          <h1 className="hero-script">Македонија</h1>
          <div className="hero-side">
            <p>Планови само со проверени места, оптимизирана рута и резервации кај локални домаќини.</p>
            <Link to="/trips/new" className="btn btn-white">Направи план</Link>
          </div>
        </div>
        {heroCredit && <span className="hero-credit">{heroCredit}</span>}
      </section>

      <div className="container search-wrap">
        {cities && <SearchBar cities={cities} />}
      </div>

      <section className="container home-section">
        <header className="section-title">
          <h2>Популарни <span>знаменитости</span></h2>
          <p>Местата од официјалната листа за печатите „Град 100%“. Посетете ги, фотографирајте ги и соберете го градот.</p>
        </header>
        {places && <Carousel places={places} />}
      </section>

      {offers.length > 0 && (
        <section className="band">
          <div className="container home-section">
            <header className="section-title">
              <h2>Бродски тури и <span>сместување</span></h2>
              <p>Локални понуди со јасна цена. Барањето го потврдува домаќинот, а рецензија пишува само тој што ја користел услугата.</p>
            </header>
            <div className="offer-grid">
              {offers.map((o, i) => (
                <Link key={o.key} to={o.to} className="offer-card">
                  <Photo src={o.img} alt={o.title} seed={i + 2} />
                  <div className="offer-body">
                    <span className="offer-place"><Icon name="pin" size={14} />{o.place}</span>
                    <strong>{o.title}</strong>
                    <span className="small muted">{o.meta}</span>
                    <div className="offer-foot">
                      <span><b>{o.price}</b> {o.unit && <span className="muted small">/ {o.unit}</span>}</span>
                      <span className="offer-cta">Резервирај</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="container home-section steps-section">
        <div className="steps-copy">
          <h2>3 лесни чекори до вашето следно патување</h2>
          <Link to="/badges" className="promo-card">
            <span className="promo-small">Соберете ги сите</span>
            <span className="promo-big">{ohridTotal}</span>
            <span className="promo-small">печати во Охрид</span>
          </Link>
        </div>
        <ol className="step-cards">
          <li><span className="step-num">1</span><div><strong>Изберете дестинација</strong><span>Град, датуми, гости, буџет и интереси.</span></div></li>
          <li><span className="step-num">2</span><div><strong>Добијте план по денови</strong><span>Места на карта, време за движење и ручек на патот.</span></div></li>
          <li><span className="step-num">3</span><div><strong>Резервирајте и тргнете</strong><span>Сместување и тури кај локални домаќини.</span></div></li>
        </ol>
        <div className="steps-visual" aria-hidden>
          <Photo src={sideImg?.image_url} alt="" seed={3} className="steps-photo" />
          <div className="stamp-float">
            <span>📸</span>
            <b>Св. Наум</b>
          </div>
        </div>
      </section>

      {reviews && reviews.length > 0 && (
        <section className="band">
          <div className="container home-section">
            <header className="section-title">
              <h2>Искуства од <span>туристите</span></h2>
              <p>Секоја рецензија е поврзана со завршена резервација.</p>
            </header>
            <div className="review-grid">
              {reviews.slice(0, 3).map((r) => (
                <figure key={r.id} className="review-card">
                  <span className="quote" aria-hidden>“</span>
                  <blockquote>{r.comment || "Без коментар."}</blockquote>
                  <figcaption>
                    <span className="review-avatar">{r.username[0].toUpperCase()}</span>
                    <span>
                      <strong>{r.username}</strong>
                      <span className="small muted">{r.business_name}</span>
                    </span>
                    <span className="review-stars" aria-label={`${r.rating} од 5`}>{"★".repeat(r.rating)}</span>
                  </figcaption>
                  {r.is_verified_booking && <span className="verified">Проверена резервација</span>}
                </figure>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="container home-section">
        <header className="section-title">
          <h2>Каде <span>одите?</span></h2>
          <p>Три града за почеток. Секој има свој пасош со знаменитости.</p>
        </header>
        <div className="city-cards">
          {cities?.map((c, i) => (
            <Link key={c.id} to={`/trips/new?city=${c.id}`} className="city-card">
              <Photo src={c.image_url} alt={c.name} credit={c.image_credit} seed={i} />
              <div className="city-overlay">
                <strong>{c.name}</strong>
                <span>{c.place_count} места, {c.required_landmarks} печати</span>
                <span className="city-go">Планирај</span>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
