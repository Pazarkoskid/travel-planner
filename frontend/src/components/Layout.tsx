import { t } from "../i18n";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../auth";
import { api } from "../services/api";
import Icon from "./Icon";
import { InstallLink, PwaBanners } from "./PwaBar";
import LangSwitch from "./LangSwitch";
import { clearUserCache } from "../pwa";

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
      <header className={`topbar ${isHome && !scrolled && !open ? "topbar-over" : ""} ${scrolled ? "topbar-scrolled" : ""}`}>
        <div className="container topbar-inner">
          <NavLink to="/" className="brand">
            <img src="/favicon.svg" width={34} height={34} alt="" />
            <span className="brand-name">Travel Planner <span>{t("МК")}</span></span>
          </NavLink>

          <nav className="nav" aria-label={t("Главна навигација")}>
            <NavLink to="/places" className={link}>{t("Места")}</NavLink>
            <NavLink to="/stay" className={link}>{t("Сместување")}</NavLink>
            <NavLink to="/boat-tours" className={link}>{t("Бродски тури")}</NavLink>
            <NavLink to="/services" className={link}>{t("Ресторани и такси")}</NavLink>
            <NavLink to="/map" className={link}>{t("Мапа")}</NavLink>
          </nav>

          <div className="nav-end">
            <LangSwitch />
            {user ? (
              <>
                <NavLink to="/trips" className={link}>{t("Патувања")}</NavLink>
                <NavLink to="/reservations" className={link}>{t("Резервации")}</NavLink>
                <NavLink to="/friends" className={link}>{t("Пријатели")}</NavLink>
                {isBusiness && <NavLink to="/business" className={link}>{t("Бизнис")}</NavLink>}
                {user.role === "ADMIN" && <NavLink to="/admin" className={link}>{t("Админ")}</NavLink>}
                <NavLink to="/me" className="account" aria-label={t("Профил на {0}", { 0: user.username })}>
                  <span className="account-avatar">{user.username[0].toUpperCase()}</span>
                  {unread > 0 && <span className="dot" aria-label={t("{0} нови известувања", { 0: unread })}>{unread}</span>}
                </NavLink>
              </>
            ) : (
              <>
                <NavLink to="/login" className={link}>{t("Најава")}</NavLink>
                <NavLink to="/register" className="btn btn-green btn-sm">{t("Регистрација")}</NavLink>
              </>
            )}
          </div>

          <LangSwitch className="lang-mobile" />
          <button className="icon-btn menu-btn" aria-expanded={open} aria-controls="mobile-menu"
                  aria-label={open ? t("Затвори мени") : t("Отвори мени")} onClick={() => setOpen(!open)}>
            <Icon name={open ? "close" : "menu"} />
          </button>
        </div>
      </header>

      <PwaBanners />

      {open && (
        <div id="mobile-menu" className="sheet" role="dialog" aria-label={t("Мени")}>
          <div className="sheet-body">
            <p className="sheet-title">{t("Истражи")}</p>
            <NavLink to="/places" className="sheet-link"><Icon name="pin" />{t("Места")}</NavLink>
            <NavLink to="/stay" className="sheet-link"><Icon name="bed" />{t("Сместување")}</NavLink>
            <NavLink to="/boat-tours" className="sheet-link"><Icon name="boat" />{t("Бродски тури")}</NavLink>
            <NavLink to="/services" className="sheet-link"><Icon name="fork" />{t("Ресторани и такси")}</NavLink>
            <NavLink to="/map" className="sheet-link"><Icon name="map" />{t("Мапа")}</NavLink>
            <NavLink to="/badges" className="sheet-link"><Icon name="star" />{t("Беџови и колекција")}</NavLink>
            <InstallLink />
            {user ? (
              <>
                <p className="sheet-title">{t("Мој профил")}</p>
                <NavLink to="/trips" className="sheet-link"><Icon name="route" />{t("Патувања")}</NavLink>
                <NavLink to="/reservations" className="sheet-link"><Icon name="ticket" />{t("Резервации")}</NavLink>
                {isBusiness && <NavLink to="/business" className="sheet-link"><Icon name="briefcase" />{t("Бизнис-табла")}</NavLink>}
                {user.role === "ADMIN" && <NavLink to="/admin" className="sheet-link"><Icon name="shield" />{t("Администрација")}</NavLink>}
                <NavLink to="/friends" className="sheet-link"><Icon name="users" />{t("Пријатели")}</NavLink>
                <NavLink to="/me" className="sheet-link"><Icon name="user" />{t("Профил и печати")}{unread > 0 && <span className="dot">{unread}</span>}</NavLink>
                <button className="btn btn-ghost btn-block" onClick={() => { logout(); clearUserCache(); nav("/"); }}>{t("Одјави се")}</button>
              </>
            ) : (
              <div className="stack" style={{ marginTop: 16 }}>
                <NavLink to="/register" className="btn btn-primary btn-block">{t("Регистрација")}</NavLink>
                <NavLink to="/login" className="btn btn-ghost btn-block">{t("Најава")}</NavLink>
              </div>
            )}
          </div>
        </div>
      )}

      <main className={isHome ? "main main-home" : "container main"}>
        <div key={loc.pathname} className="page-enter"><Outlet /></div>
      </main>

      <footer className="footer">
        <div className="container">
          <div className="footer-cta">
            <div>
              <h2>{t("Подготвени за следното патување?")}</h2>
              <p>{t("Направете план за неколку секунди, па резервирајте кај локални домаќини.")}</p>
            </div>
            <NavLink to="/trips/new" className="btn btn-green">{t("Направи план")}</NavLink>
          </div>
          <div className="footer-grid">
            <div>
              <NavLink to="/" className="brand"><img src="/favicon.svg" width={34} height={34} alt="" /><span className="brand-name">Travel Planner <span>{t("МК")}</span></span></NavLink>
              <p className="footer-about">{t("Персонализирани планови низ Северна Македонија, само со проверени места и локални услуги.")}</p>
            </div>
            <div>
              <h3>{t("Истражи")}</h3>
              <NavLink to="/places">{t("Места")}</NavLink>
              <NavLink to="/stay">{t("Сместување")}</NavLink>
              <NavLink to="/boat-tours">{t("Бродски тури")}</NavLink>
              <NavLink to="/services">{t("Ресторани и такси")}</NavLink>
              <NavLink to="/map">{t("Мапа")}</NavLink>
              <NavLink to="/badges">{t("Беџови и колекција")}</NavLink>
            </div>
            <div>
              <h3>{t("Патници")}</h3>
              <NavLink to="/trips/new">{t("Ново патување")}</NavLink>
              <NavLink to="/reservations">{t("Мои резервации")}</NavLink>
              <NavLink to="/me">{t("Мој пасош со печати")}</NavLink>
              <NavLink to="/friends">{t("Пријатели")}</NavLink>
            </div>
            <div>
              <h3>{t("За проектот")}</h3>
              <NavLink to="/register">{t("Регистрирај бизнис")}</NavLink>
              <NavLink to="/credits">{t("Извори на фотографии")}</NavLink>
              <span>{t("Карта © OpenStreetMap contributors")}</span>
            </div>
          </div>
          <div className="footer-bottom">
            <span>{t("Travel Planner МК, дипломски прототип")}</span>
            <span>{t("Цени и работно време се прикажуваат само кога се проверени")}</span>
            {user && <button className="link-btn" onClick={() => { logout(); clearUserCache(); nav("/"); }}>{t("Одјави се")}</button>}
          </div>
        </div>
      </footer>

      <nav className="tabbar" aria-label={t("Брза навигација")}>
        <NavLink to="/" end className={tab}><Icon name="home" /><span>{t("Почетна")}</span></NavLink>
        <NavLink to="/map" className={tab}><Icon name="map" /><span>{t("Мапа")}</span></NavLink>
        <NavLink to={user ? "/trips" : "/trips/new"} className={tab}><Icon name="route" /><span>{t("Патувања")}</span></NavLink>
        {user ? (
          <>
            <NavLink to="/reservations" className={tab}><Icon name="ticket" /><span>{t("Резервации")}</span></NavLink>
            <NavLink to="/me" className={tab}>
              <Icon name="user" /><span>{t("Профил")}</span>
              {unread > 0 && <span className="tab-dot" aria-label={t("{0} нови известувања", { 0: unread })} />}
            </NavLink>
          </>
        ) : (
          <>
            <NavLink to="/stay" className={tab}><Icon name="bed" /><span>{t("Сместување")}</span></NavLink>
            <NavLink to="/login" className={tab}><Icon name="login" /><span>{t("Најава")}</span></NavLink>
          </>
        )}
      </nav>
    </div>
  );
}
