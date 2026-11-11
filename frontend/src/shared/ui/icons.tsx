// Thin-stroke icons.

interface IconProps {
  size?: number;
  className?: string;
}

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  "aria-hidden": true,
});

export const ArrowRight = ({ size = 14, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.5} className={className}><path d="M5 12h14M13 6l6 6-6 6" /></svg>
);
export const ArrowLeft = ({ size = 14, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.5} className={className}><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
);
export const ChevronDown = ({ size = 10, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={2} className={className}><path d="M6 9l6 6 6-6" /></svg>
);
/** AI chat toggle / chat title icon. */
export const Spark = ({ size = 16, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.5} className={className}>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
    <circle cx="12" cy="12" r="4" />
  </svg>
);
export const Close = ({ size = 12, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.8} className={className}><path d="M6 6l12 12M18 6L6 18" /></svg>
);
export const Alert = ({ size = 18, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.5} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7.5v5.5" />
    <circle cx="12" cy="16.3" r=".6" fill="currentColor" />
  </svg>
);
export const ArrowUp = ({ size = 12, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.6} className={className}><path d="M12 19V5M6 11l6-6 6 6" /></svg>
);
export const ArrowDown = ({ size = 12, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.6} className={className}><path d="M12 5v14M6 13l6 6 6-6" /></svg>
);
/** Small pen for "edit this scene". */
export const Pen = ({ size = 12, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.6} className={className}><path d="M4 20h4L19 9l-4-4L4 16v4zM13.5 6.5l4 4" /></svg>
);
/** Closed padlock: the text is locked. */
export const Lock = ({ size = 16, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.5} className={className}><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>
);
/** Open padlock: the text can be edited. */
export const Unlock = ({ size = 16, className }: IconProps) => (
  <svg {...base(size)} strokeWidth={1.5} className={className}><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 7.6-1.8" /></svg>
);
