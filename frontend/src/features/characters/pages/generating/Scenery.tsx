// Background loops of the generating screen: fog, stars, axis with sparks, orrery.
// Plain CSS keyframes for these infinite loops.

/** Stars from a seeded generator, so they always sit in the same places. */
function makeStars() {
  let seed = 7;
  const rnd = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
  return Array.from({ length: 28 }, () => ({
    x: Math.round(rnd() * 1260),
    y: Math.round(rnd() * 780),
    d: Number((rnd() * 3).toFixed(2)),
  }));
}
const STARS = makeStars();

export function Fog() {
  return (
    <>
      <div className="pointer-events-none absolute -inset-[10%] animate-drift bg-[radial-gradient(ellipse_700px_420px_at_30%_60%,#2a2114_0%,transparent_70%)]" />
      <div
        className="pointer-events-none absolute -inset-[10%] animate-drift bg-[radial-gradient(ellipse_600px_380px_at_72%_35%,#1f190f_0%,transparent_70%)]"
        style={{ animationDelay: "-7s" }}
      />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_1400px_900px_at_50%_50%,transparent_35%,#000000_100%)] opacity-60" />
    </>
  );
}

export function Stars() {
  return (
    <>
      {STARS.map((s, i) => (
        <div
          key={i}
          className="absolute size-[2px] animate-twinkle rounded-full bg-gold-soft"
          style={{ left: s.x, top: s.y, animationDelay: `${s.d}s` }}
        />
      ))}
    </>
  );
}

function SideNode({ side }: { side: "left" | "right" }) {
  return (
    <div
      className="absolute top-[340px] box-border flex size-10 items-center justify-center rounded-full border border-line-strong"
      style={{ [side]: 180 }}
    >
      <div className="size-[6px] rounded-full bg-gold opacity-70" />
    </div>
  );
}

export function Axis() {
  return (
    <>
      <div className="absolute top-[360px] left-0 h-px w-[1280px] bg-[linear-gradient(90deg,transparent_0%,#4a4229_20%,#4a4229_80%,transparent_100%)]">
        {[0, -2].map((delay) => (
          <div
            key={delay}
            className="absolute -top-[2px] size-[5px] animate-travel rounded-full bg-gold shadow-[0_0_10px_#c9a24b]"
            style={{ animationDelay: `${delay}s` }}
          />
        ))}
      </div>
      <SideNode side="left" />
      <SideNode side="right" />
    </>
  );
}

/** The central "orrery": three rings turning at different speeds and a breathing core with "A". */
export function Orrery() {
  return (
    <div className="absolute top-[160px] left-[440px] size-[400px]">
      <div className="absolute inset-[90px] animate-glow rounded-full bg-[radial-gradient(circle,#c9a24b55_0%,transparent_70%)]" />
      <svg width="400" height="400" viewBox="0 0 400 400" fill="none" className="absolute inset-0 origin-center animate-ring-a">
        <circle cx="200" cy="200" r="196" stroke="#3c3627" strokeWidth="1" />
        <circle cx="200" cy="200" r="196" stroke="#c9a24b" strokeWidth="1" strokeDasharray="1 10" opacity=".6" />
        <circle cx="200" cy="4" r="4" fill="#c9a24b" />
        <circle cx="396" cy="200" r="2.5" fill="#c9a24b" opacity=".6" />
      </svg>
      <svg width="400" height="400" viewBox="0 0 400 400" fill="none" className="absolute inset-0 origin-center animate-ring-b">
        <circle cx="200" cy="200" r="150" stroke="#4a4229" strokeWidth="1" strokeDasharray="40 14 2 14" />
        <circle cx="50" cy="200" r="3.5" fill="#c9a24b" />
      </svg>
      <svg width="400" height="400" viewBox="0 0 400 400" fill="none" className="absolute inset-0 origin-center animate-ring-c">
        <path d="M200 106 A94 94 0 0 1 294 200" stroke="#c9a24b" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M200 294 A94 94 0 0 1 106 200" stroke="#c9a24b" strokeWidth="1" strokeLinecap="round" opacity=".5" />
      </svg>
      <div className="orb-core absolute top-[140px] left-[140px] box-border flex size-[120px] animate-breathe items-center justify-center rounded-full border border-gold">
        <span className="font-serif text-[44px] font-medium text-gold italic">A</span>
      </div>
    </div>
  );
}
