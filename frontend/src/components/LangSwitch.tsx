import { lang, setLang, t } from "../i18n";

/** Избор на јазик (MK/EN). Изборот се памти во прелистувачот. */
export default function LangSwitch({ className = "" }: { className?: string }) {
  return (
    <div className={`lang-switch ${className}`} role="group" aria-label={t("Јазик")}>
      {(["mk", "en"] as const).map((l) => (
        <button key={l} type="button" lang={l} aria-pressed={lang === l} className={lang === l ? "on" : ""} onClick={() => setLang(l)}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
