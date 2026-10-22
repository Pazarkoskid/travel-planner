import { useState } from "react";

const TONES = [
  ["#165563", "#2a8a7a"],
  ["#0e3b44", "#1d9e6e"],
  ["#1d4e63", "#3e8fa8"],
  ["#2d5a4a", "#7fae7a"],
];

/** Фотографија со автор/лиценца и уреден fallback кога сликата ја нема или не се вчитува. */
export default function Photo({ src, alt, credit, seed = 0, className = "", eager = false, showCredit = false }: {
  src?: string;
  alt: string;
  credit?: string;
  seed?: number;
  className?: string;
  eager?: boolean;
  showCredit?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const [a, b] = TONES[Math.abs(seed) % TONES.length];
  const ok = src && !failed;
  return (
    <div className={`photo-box ${className}`} style={ok ? undefined : { background: `linear-gradient(150deg, ${a}, ${b})` }}>
      {ok ? (
        <img src={src} alt={alt} loading={eager ? "eager" : "lazy"} referrerPolicy="no-referrer" onError={() => setFailed(true)} title={credit || undefined} />
      ) : (
        <svg className="photo-fallback" viewBox="0 0 200 120" aria-hidden preserveAspectRatio="xMidYMax slice">
          <path d="M0 90 L45 52 L70 72 L110 30 L150 70 L170 58 L200 80 V120 H0Z" fill="rgba(255,255,255,0.14)" />
          <path d="M0 102 C 40 94, 80 110, 120 100 S 180 96, 200 104 V120 H0Z" fill="rgba(255,255,255,0.18)" />
          <circle cx="160" cy="28" r="10" fill="rgba(255,255,255,0.22)" />
        </svg>
      )}
      {ok && credit && showCredit && <span className="photo-credit">{credit}</span>}
    </div>
  );
}
