const SELECTOR = [
  ".section-title", ".dest-card", ".offer-card", ".step-cards li", ".review-card", ".city-card",
  ".panel", ".card", ".stamp", ".photo", ".place-item", ".stop", ".person", ".weather",
  ".steps-visual", ".promo-card", ".empty", ".day-tab",
].join(",");

const SCROLLERS = ".carousel-track, .place-list, .day-tabs, .departure-grid";

const reduced = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export function initMotion() {
  if (typeof window === "undefined" || !("IntersectionObserver" in window) || reduced()) return;
  document.documentElement.classList.add("motion");

  const io = new IntersectionObserver((entries) => {

    const visible = entries.filter((e) => e.isIntersecting).map((e) => e.target as HTMLElement);
    const queue: HTMLElement[] = [];
    visible.forEach((el) => {

      const box = el.closest(SCROLLERS);
      const group = box ? Array.from(box.querySelectorAll<HTMLElement>(SELECTOR)) : [el];
      group.forEach((g) => { if (!g.classList.contains("in") && !queue.includes(g)) queue.push(g); });
    });
    queue.forEach((el, i) => {
      io.unobserve(el);
      window.setTimeout(() => el.classList.add("in"), Math.min(i, 8) * 70);
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

  const seen = new WeakSet<Element>();
  const scan = (root: ParentNode) => {
    root.querySelectorAll(SELECTOR).forEach((el) => {
      if (seen.has(el)) return;
      seen.add(el);
      io.observe(el);
    });
  };
  scan(document);
  new MutationObserver((muts) => {
    for (const m of muts) m.addedNodes.forEach((n) => { if (n instanceof HTMLElement) { if (n.matches(SELECTOR)) scan(n.parentElement || n); scan(n); } });
  }).observe(document.body, { childList: true, subtree: true });

  const counter = new IntersectionObserver((entries) => {
    entries.filter((e) => e.isIntersecting).forEach(({ target }) => {
      counter.unobserve(target);
      const el = target as HTMLElement;
      const end = Number(el.dataset.countup);
      if (!Number.isFinite(end) || end <= 0) return;
      const start = performance.now();
      const tick = (now: number) => {
        const p = Math.min(1, (now - start) / 900);
        el.textContent = String(Math.round(end * (1 - Math.pow(1 - p, 3))));
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }, { threshold: 0.5 });
  const scanCounters = () => document.querySelectorAll<HTMLElement>("[data-countup]:not([data-counted])").forEach((el) => {
    el.dataset.counted = "1";
    counter.observe(el);
  });
  scanCounters();
  new MutationObserver(scanCounters).observe(document.body, { childList: true, subtree: true });
}

export function celebrate(anchor?: HTMLElement | null) {
  if (reduced()) return;
  const host = document.createElement("div");
  host.className = "confetti";
  host.setAttribute("aria-hidden", "true");
  const rect = anchor?.getBoundingClientRect();
  host.style.left = `${rect ? rect.left + rect.width / 2 : window.innerWidth / 2}px`;
  host.style.top = `${rect ? rect.top + 20 : window.innerHeight / 3}px`;
  const colors = ["#1d9e6e", "#c99a2e", "#0f4c5c", "#2bb3b1", "#f0cf73", "#e2574c"];
  for (let i = 0; i < 36; i++) {
    const s = document.createElement("i");
    const angle = Math.random() * Math.PI * 2;
    const dist = 90 + Math.random() * 170;
    s.style.setProperty("--x", `${Math.cos(angle) * dist}px`);
    s.style.setProperty("--y", `${Math.sin(angle) * dist - 80}px`);
    s.style.setProperty("--r", `${Math.random() * 720 - 360}deg`);
    s.style.background = colors[i % colors.length];
    s.style.animationDelay = `${Math.random() * 120}ms`;
    host.appendChild(s);
  }
  document.body.appendChild(host);
  window.setTimeout(() => host.remove(), 1600);
}
