/* Service worker — Travel Planner Македонија (PWA).
 *
 * Стратегии:
 *  - страници (navigation): прво мрежа, офлајн → зачуван index.html (SPA)
 *  - /assets/*, /badges/*, /brand/*, фонтови, икони: прво кеш (имињата на /assets/ се со hash)
 *  - GET /api/v1/* (освен auth): прво мрежа, офлајн → последниот зачуван одговор
 *  - фотографии (Wikimedia, Supabase) и OSM плочки: кеш со ограничен број записи
 *  - POST/PATCH/DELETE: секогаш мрежа (резервации, check-in не смеат да се „лажат“ офлајн)
 */
const VERSION = "v3";
const SHELL = `tpm-shell-${VERSION}`;
const STATIC = `tpm-static-${VERSION}`;
const API = "tpm-api";
const MEDIA = `tpm-media-${VERSION}`; // нова верзија ги брише старите (и погрешно зачуваните) плочки
const SHELL_FILES = ["/", "/index.html", "/manifest.webmanifest", "/favicon.svg", "/icon-192.png", "/icon-512.png"];
const LIMITS = { [MEDIA]: 250, [API]: 150 };

self.addEventListener("install", (event) => {
  self.skipWaiting(); // новата верзија веднаш ја заменува старата
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_FILES)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keep = new Set([SHELL, STATIC, API, MEDIA]);
    for (const key of await caches.keys()) if (!keep.has(key)) await caches.delete(key);
    await self.clients.claim();
  })());
});

self.addEventListener("message", (event) => {
  if (event.data === "skip-waiting") self.skipWaiting();
  if (event.data === "clear-user-data") caches.delete(API); // при одјава
});

async function trim(cacheName) {
  const max = LIMITS[cacheName];
  if (!max) return;
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - max; i++) await cache.delete(keys[i]);
}

async function cacheFirst(request, cacheName, allowOpaque = true) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok || (allowOpaque && response.type === "opaque")) {
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone()).then(() => trim(cacheName));
  }
  return response;
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone()).then(() => trim(cacheName));
    }
    return response;
  } catch (err) {
    // ignoreVary: одговорите од API имаат Vary (Accept-Language, Authorization, Origin)
    const cached = await caches.match(request, { ignoreVary: true });
    if (cached) return cached;
    throw err;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(async () => (await caches.match("/index.html")) || Response.error()));
    return;
  }
  if (url.pathname.includes("/api/v1/")) {
    if (url.pathname.includes("/auth/") || url.searchParams.has("format")) return; // токени и извоз — само мрежа
    event.respondWith(networkFirst(request, API));
    return;
  }
  if (url.origin === self.location.origin &&
      /^\/(assets|badges|brand)\/|\.(woff2?|png|svg|webp|webmanifest)$/.test(url.pathname)) {
    event.respondWith(cacheFirst(request, STATIC));
    return;
  }
  if (/(^|\.)tile\.openstreetmap\.org$/.test(url.hostname)) {
    // плочките се бараат со CORS → се зачувуваат само успешните (не грешка 403/429 засекогаш)
    event.respondWith(cacheFirst(request, MEDIA, false).catch(() => fetch(request)));
    return;
  }
  if (/(^|\.)(wikimedia\.org|supabase\.co|openweathermap\.org)$/.test(url.hostname)) {
    event.respondWith(cacheFirst(request, MEDIA));
  }
});
