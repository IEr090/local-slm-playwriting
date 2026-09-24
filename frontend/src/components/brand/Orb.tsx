import { cn } from "@/lib/utils";

interface OrbProps {
  /** "logo": 56px, slow ring (prompt screen). "mini": 48px, fast ring (card updating overlay). */
  variant?: "logo" | "mini";
  className?: string;
}

const SIZES = {
  logo: { box: 56, core: 36, inset: 10, letter: 20, dot: 1.8, ring: "animate-spin-slow" },
  mini: { box: 48, core: 30, inset: 9, letter: 17, dot: 2, ring: "animate-ring-fast" },
} as const;

/** The "A" mark: a dotted ring with an orbiting gold dot around a breathing core. */
export function Orb({ variant = "logo", className }: OrbProps) {
  const s = SIZES[variant];
  const c = s.box / 2;
  return (
    <span aria-hidden className={cn("relative block shrink-0", className)} style={{ width: s.box, height: s.box }}>
      <svg
        width={s.box}
        height={s.box}
        viewBox={`0 0 ${s.box} ${s.box}`}
        fill="none"
        className={cn("absolute inset-0 origin-center", s.ring)}
      >
        <circle cx={c} cy={c} r={c - 1} stroke="#4a4229" strokeWidth={1} strokeDasharray="1 5" />
        <circle cx={c} cy={1.5} r={s.dot} fill="#c9a24b" />
      </svg>
      <span
        className="orb-core absolute box-border flex animate-breathe items-center justify-center rounded-full border border-gold"
        style={{ left: s.inset, top: s.inset, width: s.core, height: s.core }}
      >
        <span className="font-serif font-medium italic leading-none text-gold" style={{ fontSize: s.letter }}>
          A
        </span>
      </span>
    </span>
  );
}
