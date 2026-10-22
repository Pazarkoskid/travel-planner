// PWA: регистрација на service worker, инсталирање, офлајн и нова верзија.
import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferred: BeforeInstallPromptEvent | null = null;
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((l) => l());
let updateReady: ServiceWorker | null = null;

export function registerServiceWorker() {
  if (!("serviceWorker" in navigator) || !import.meta.env.PROD) return;
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferred = e as BeforeInstallPromptEvent;
    notify();
  });
  window.addEventListener("appinstalled", () => { deferred = null; notify(); });
  window.addEventListener("load", async () => {
    try {
      const reg = await navigator.serviceWorker.register("/sw.js");
      reg.addEventListener("updatefound", () => {
        const sw = reg.installing;
        sw?.addEventListener("statechange", () => {
          if (sw.state === "installed" && navigator.serviceWorker.controller) { updateReady = sw; notify(); }
        });
      });
    } catch { /* PWA е дополнување; апликацијата работи и без неа */ }
  });
  let reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!reloading) { reloading = true; window.location.reload(); }
  });
}

export function clearUserCache() {
  navigator.serviceWorker?.controller?.postMessage("clear-user-data");
}

export const isStandalone = () =>
  window.matchMedia?.("(display-mode: standalone)").matches || (navigator as unknown as { standalone?: boolean }).standalone === true;

const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent);

export function usePwa() {
  const [, force] = useState(0);
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  useEffect(() => {
    const l = () => force((n) => n + 1);
    listeners.add(l);
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => { listeners.delete(l); window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);
  return {
    canInstall: !!deferred,
    iosHint: isIos() && !isStandalone(),
    installed: isStandalone(),
    online,
    updateReady: !!updateReady,
    install: async () => {
      if (!deferred) return;
      await deferred.prompt();
      await deferred.userChoice;
      deferred = null;
      notify();
    },
    applyUpdate: () => updateReady?.postMessage("skip-waiting"),
  };
}
