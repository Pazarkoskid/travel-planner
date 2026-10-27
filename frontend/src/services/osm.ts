const MIRRORS = [
  "https://overpass-api.de/api/interpreter",
  "https://overpass.private.coffee/api/interpreter",
  "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
];
const SHOP_RE = "^(bakery|pastry|supermarket|convenience|greengrocer|kiosk|newsagent|tobacco)$";
const AMENITY_RE = "^(marketplace|bureau_de_change|atm|pharmacy)$";

type Tags = Record<string, string>;
interface El { type: string; id: number; lat?: number; lon?: number; center?: { lat: number; lon: number }; tags?: Tags }

export function osmCategory(t: Tags): string | null {
  const shop = t.shop, am = t.amenity;
  if (shop === "bakery" || shop === "pastry") return "bakery";
  if (["supermarket", "convenience", "greengrocer"].includes(shop) || am === "marketplace") return "market";
  if (am === "bureau_de_change") return "exchange";
  if (["kiosk", "newsagent", "tobacco"].includes(shop)) return "kiosk";
  if (am === "atm") return "atm";
  if (am === "pharmacy") return "pharmacy";
  return null;
}

export function parseOverpass(payload: { elements?: El[] }) {
  const seen = new Set<string>();
  const out = [];
  for (const el of payload.elements || []) {
    const t = el.tags || {};
    const cat = osmCategory(t);
    const lat = el.lat ?? el.center?.lat, lng = el.lon ?? el.center?.lon;
    const id = `${el.type}/${el.id}`;
    if (!cat || lat == null || lng == null || seen.has(id)) continue;
    seen.add(id);
    out.push({
      id, category: cat, lat, lng,
      name: t["name:mk"] || t.name || t.brand || t.operator || "",
      opening_hours: t.opening_hours || "",
      address: [t["addr:street"], t["addr:housenumber"]].filter(Boolean).join(" "),
      phone: t.phone || t["contact:phone"] || "",
      website: t.website || t["contact:website"] || "",
      osm_url: `https://www.openstreetmap.org/${id}`,
    });
  }
  return out;
}

const KEY = (lat: number, lng: number) => `tpm_osm_${lat.toFixed(3)}_${lng.toFixed(3)}`;

export async function fetchAmenitiesDirect(lat: number, lng: number, radius = 3000) {
  const around = `(around:${radius},${lat.toFixed(5)},${lng.toFixed(5)})`;
  const q = `[out:json][timeout:20];(nwr["shop"~"${SHOP_RE}"]${around};nwr["amenity"~"${AMENITY_RE}"]${around};);out center tags 500;`;
  try {
    const hit = JSON.parse(localStorage.getItem(KEY(lat, lng)) || "null");
    if (hit && Date.now() - hit.at < 12 * 3600 * 1000) return { items: hit.items, stale: false };
  } catch {  }
  for (const url of MIRRORS) {
    try {
      const ctrl = new AbortController();
      const timer = window.setTimeout(() => ctrl.abort(), 20000);
      const res = await fetch(url, { method: "POST", body: new URLSearchParams({ data: q }), signal: ctrl.signal });
      window.clearTimeout(timer);
      if (!res.ok) continue;
      const items = parseOverpass(await res.json());
      try { localStorage.setItem(KEY(lat, lng), JSON.stringify({ at: Date.now(), items })); } catch {  }
      return { items, stale: false };
    } catch {  }
  }
  throw new Error("osm_unavailable");
}
