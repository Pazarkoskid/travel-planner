/** Стилизирана карта на Охридското Езеро со пример-рута по источниот брег.
 *  Обликот е приближен (илустрација), не географски точна карта. */
const STOPS: { x: number; y: number; label: string; dx: number }[] = [
  { x: 236, y: 92, label: "Канео", dx: -56 },
  { x: 258, y: 74, label: "Самуилова тврдина", dx: 14 },
  { x: 279, y: 176, label: "Лагадин", dx: 14 },
  { x: 274, y: 250, label: "Залив на коските", dx: 14 },
  { x: 214, y: 404, label: "Св. Наум", dx: 14 },
];

const ROUTE = "M236 92 C 244 84, 250 78, 258 74 C 280 100, 282 140, 279 176 C 277 205, 276 228, 274 250 C 268 320, 246 378, 214 404";

export default function LakeMap() {
  return (
    <figure className="lake-panel" aria-label="Пример-рута: Канео, Самуилова тврдина, Лагадин, Залив на коските, Св. Наум">
      <svg viewBox="0 0 440 450" role="img" aria-hidden>
        <g transform="translate(14 0)">
        <path
          className="lake-water"
          d="M70 70 C 120 38, 210 40, 262 66 C 290 112, 288 196, 282 258 C 276 330, 252 392, 212 420 C 166 440, 118 418, 96 372 C 70 320, 54 240, 50 170 C 46 116, 50 86, 70 70 Z"
        />
        <path className="lake-ripple" d="M90 120 C 130 104, 190 104, 240 122" />
        <path className="lake-ripple" d="M78 200 C 128 186, 196 186, 258 204" />
        <path className="lake-ripple" d="M82 290 C 132 278, 196 280, 256 296" />
        <path className="lake-ripple" d="M108 366 C 146 356, 192 358, 232 370" />
        <path className="lake-route-draw" d={ROUTE} />
        <path className="lake-route" d={ROUTE} />
        <text className="lake-label dim" x="36" y="56">Струга</text>
        <text className="lake-label dim" x="270" y="48">Охрид</text>
        <text className="lake-label dim" x="110" y="250">Охридско Езеро</text>
        {STOPS.map((s, i) => (
          <g key={s.label}>
            <circle className="lake-stop" cx={s.x} cy={s.y} r={11} />
            <text className="lake-stop-num" x={s.x} y={s.y + 0.5}>{i + 1}</text>
            <text className="lake-label" x={s.x + s.dx} y={s.y + 4}>{s.label}</text>
          </g>
        ))}
        </g>
      </svg>
      <figcaption className="lake-caption">
        <span>Пример-рута по источниот брег</span>
        <span>Илустрација, не точна карта</span>
      </figcaption>
    </figure>
  );
}
