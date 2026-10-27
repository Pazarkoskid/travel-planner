import { t } from "../i18n";
import { useState } from "react";
import { usePwa } from "../pwa";
import Icon from "./Icon";

const DISMISS_KEY = "tpm_install_dismissed";

function readDismissed() {
  try { return localStorage.getItem(DISMISS_KEY) === "1"; } catch { return false; }
}

export function PwaBanners() {
  const pwa = usePwa();
  const [dismissed, setDismissed] = useState(readDismissed);
  const dismiss = () => {
    setDismissed(true);
    try { localStorage.setItem(DISMISS_KEY, "1"); } catch {  }
  };
  return (
    <>
      {!pwa.online && (
        <div className="pwa-bar pwa-offline" role="status">
          <Icon name="close" size={16} /> {t("Офлајн сте. Се прикажуваат последно зачуваните податоци; резервации и фото-посети чекаат интернет.")}
        </div>
      )}
      {pwa.updateReady && (
        <div className="pwa-bar pwa-update" role="status">
          {t("Достапна е нова верзија на апликацијата.")}
          <button className="btn btn-white btn-sm" onClick={pwa.applyUpdate}>{t("Освежи")}</button>
        </div>
      )}
      {!dismissed && !pwa.installed && (pwa.canInstall || pwa.iosHint) && (
        <div className="pwa-install" role="dialog" aria-label={t("Инсталирај ја апликацијата")}>
          <img src="/icon-192.png" width={44} height={44} alt="" />
          <div className="pwa-install-text">
            <strong>{t("Travel Planner на почетниот екран")}</strong>
            <span>{pwa.canInstall
              ? t("Инсталирајте ја како апликација: брзо отворање и план достапен и без интернет.")
              : t("Во Safari: Сподели → „Додај на почетен екран“.")}</span>
          </div>
          {pwa.canInstall && <button className="btn btn-green btn-sm" onClick={pwa.install}>{t("Инсталирај")}</button>}
          <button className="icon-btn" aria-label={t("Затвори")} onClick={dismiss}><Icon name="close" size={18} /></button>
        </div>
      )}
    </>
  );
}

export function InstallLink({ className = "sheet-link" }: { className?: string }) {
  const pwa = usePwa();
  if (pwa.installed || !pwa.canInstall) return null;
  return (
    <button type="button" className={className} onClick={pwa.install}>
      <Icon name="plus" />{t("Инсталирај апликација")}
    </button>
  );
}
