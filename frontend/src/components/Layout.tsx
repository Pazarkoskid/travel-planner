import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../auth";
import { api } from "../services/api";
import Icon from "./Icon";

export default function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const isHome = loc.pathname === "/";

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!user) return;
    api<{ unread: number }>("/notifications/unread-count/").then((r) => setUnread(r.unread)).catch(() => undefined);
  }, [user, loc.pathname]);

  // Затвори го менито и скролај горе при промена на страница.
  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
  }, [loc.pathname]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
  }, [open]);

  const link = ({ isActive }: { isActive: boolean }) => (isActive ? "nav-link active" : "nav-link");
  const tab = ({ isActive }: { isActive: boolean }) => (isActive ? "tab-link active" : "tab-link");
  const isBusiness = user && (user.role === "BUSINESS" || user.role === "ADMIN");

  return (
    <div className="app">
      <header className={`topbar ${isHome && !scrolled && !open ? "topbar-over" : ""}`}>
        <div className="container topbar-inner">
          <NavLink to="/" className="brand">
            <img src="/favicon.svg" width={34} height={34} alt="" />
            <span className="brand-name">Travel Planner <span>МК</span></span>
          </NavLink>

          <nav className="nav" aria-label="Главна навигација">
            <NavLink to="/places" className={link}>Места</NavLink>
            <NavLink to="/stay" className={link}>Сместување</NavLink>
            <NavLink to="/boat-tours" className={link}>Бродски тури</NavLink>
            <NavLink to="/services" className={link}>Ресторани и такси</NavLink>
          </nav>

          <div className="nav-end">
            {user ? (
              <>
                <NavLink to="/trips" className={link}>Патувања</NavLink>
                <NavLink to="/reservations" className={link}>Резервации</NavLink>
                {isBusiness && <NavLink to="/business" className={link}>Бизнис</NavLink>}
                {user.role === "ADMIN" && <NavLink to="/admin" className={link}>Админ</NavLink>}
                <NavLink to="/me" className="account" aria-label={`Профил на ${user.username}`}>
                  <span className="account-avatar">{user.username[0].toUpperCase()}</span>
                  {unread > 0 && <span className="dot" aria-label={`${unread} нови известувања`}>{unread}</span>}
                </NavLink>
              </>
            ) : (
              <>
                <NavLink to="/login" className={link}>Најава</NavLink>
                <NavLink to="/register" className="btn btn-green btn-sm">Регистрација</NavLink>
              </>
            )}
          </div>

          <button className="icon-btn menu-btn" aria-expanded={open} aria-controls="mobile-menu"
                  aria-label={open ? "Затвори мени" : "Отвори мени"} onClick={() => setOpen(!open)}>
            <Icon name={open ? "close" : "menu"} />
          </button>
        </div>
      </header>

      {open && (
        <div id="mobile-menu" className="sheet" role="dialog" aria-label="Мени">
          <div className="sheet-body">
            <p className="sheet-title">Истражи</p>
            <NavLink to="/places" className="sheet-link"><Icon name="pin" />Места</NavLink>
            <NavLink to="/stay" className="sheet-link"><Icon name="bed" />Сместување</NavLink>
            <NavLink to="/boat-tours" className="sheet-link"><Icon name="boat" />Бродски тури</NavLink>
            <NavLink to="/services" className="sheet-link"><Icon name="fork" />Ресторани и такси</NavLink>
            <NavLink to="/badges" className="sheet-link"><Icon name="star" />Беџови и колекција</NavLink>
            {user ? (
              <>
                <p className="sheet-title">Мој профил</p>
                <NavLink to="/trips" className="sheet-link"><Icon name="route" />Патувања</NavLink>
                <NavLink to="/reservations" className="sheet-link"><Icon name="ticket" />Резервации</NavLink>
                {isBusiness && <NavLink to="/business" className="sheet-link"><Icon name="briefcase" />Бизнис-табла</NavLink>}
                {user.role === "ADMIN" && <NavLink to="/admin" className="sheet-link"><Icon name="shield" />Администрација</NavLink>}
                <NavLink to="/me" className="sheet-link"><Icon name="user" />Профил и печати{unread > 0 && <span className="dot">{unread}</span>}</NavLink>
                <button className="btn btn-ghost btn-block" onClick={() => { logout(); nav("/"); }}>Одјави се</button>
              </>
            ) : (
              <div className="stack" style={{ marginTop: 16 }}>
                <NavLink to="/register" className="btn btn-primary btn-block">Регистрација</NavLink>
                <NavLink to="/login" className="btn btn-ghost btn-block">Најава</NavLink>
              </div>
            )}
          </div>
        </div>
      )}

      <main className={isHome ? "main main-home" : "container main"}>
        <Outlet />
      </main>

      <footer className="footer">
        <div className="container">
          <div className="footer-cta">
            <div>
              <h2>Подготвени за следното патување?</h2>
              <p>Направете план за неколку секунди, па резервирајте кај локални домаќини.</p>
            </div>
            <NavLink to="/trips/new" className="btn btn-green">Направи план</NavLink>
          </div>
          <div className="footer-grid">
            <div>
              <NavLink to="/" className="brand"><img src="/favicon.svg" width={34} height={34} alt="" /><span className="brand-name">Travel Planner <span>МК</span></span></NavLink>
              <p className="footer-about">Персонализирани планови низ Северна Македонија, само со проверени места и локални услуги.</p>
            </div>
            <div>
              <h3>Истражи</h3>
              <NavLink to="/places">Места</NavLink>
              <NavLink to="/stay">Сместување</NavLink>
              <NavLink to="/boat-tours">Бродски тури</NavLink>
              <NavLink to="/services">Ресторани и такси</NavLink>
              <NavLink to="/badges">Беџови и колекција</NavLink>
            </div>
            <div>
              <h3>Патници</h3>
              <NavLink to="/trips/new">Ново патување</NavLink>
              <NavLink to="/reservations">Мои резервации</NavLink>
              <NavLink to="/me">Мој пасош со печати</NavLink>
            </div>
            <div>
              <h3>За проектот</h3>
              <NavLink to="/register">Регистрирај бизнис</NavLink>
              <NavLink to="/credits">Извори на фотографии</NavLink>
              <span>Карта © OpenStreetMap contributors</span>
            </div>
          </div>
          <div className="footer-bottom">
            <span>Travel Planner МК, дипломски прототип</span>
            <span>Цени и работно време се прикажуваат само кога се проверени</span>
            {user && <button className="link-btn" onClick={() => { logout(); nav("/"); }}>Одјави се</button>}
          </div>
        </div>
      </footer>

      <nav className="tabbar" aria-label="Брза навигација">
        <NavLink to="/" end className={tab}><Icon name="home" /><span>Почетна</span></NavLink>
        <NavLink to="/places" className={tab}><Icon name="pin" /><span>Места</span></NavLink>
        <NavLink to={user ? "/trips" : "/trips/new"} className={tab}><Icon name="route" /><span>Патувања</span></NavLink>
        {user ? (
          <>
            <NavLink to="/reservations" className={tab}><Icon name="ticket" /><span>Резервации</span></NavLink>
            <NavLink to="/me" className={tab}>
              <Icon name="user" /><span>Профил</span>
              {unread > 0 && <span className="tab-dot" aria-label={`${unread} нови известувања`} />}
            </NavLink>
          </>
        ) : (
          <>
            <NavLink to="/stay" className={tab}><Icon name="bed" /><span>Сместување</span></NavLink>
            <NavLink to="/login" className={tab}><Icon name="login" /><span>Најава</span></NavLink>
          </>
        )}
      </nav>
    </div>
  );
}
