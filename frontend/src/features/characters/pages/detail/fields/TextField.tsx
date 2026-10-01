import { useAutoGrow } from "@/shared/hooks/use-auto-grow";
import { cn } from "@/shared/lib/utils";

interface TextFieldProps {
  value: string;
  onChange(value: string): void;
  /** Minimum height in lines. */
  rows: number;
  label: string;
  className?: string;
}

/** Borderless textarea (`.txt`) that grows with its content. */
export function TextField({ value, onChange, rows, label, className }: TextFieldProps) {
  const ref = useAutoGrow(value);
  return (
    <textarea
      ref={ref}
      rows={rows}
      value={value}
      aria-label={label}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        "m-0 box-border block w-full resize-none overflow-hidden border-none bg-transparent p-0 font-sans text-[13px] leading-[1.55] text-ink placeholder:text-placeholder focus:outline-none",
        className,
      )}
    />
  );
}
