import { useAutoGrow } from "@/shared/hooks/use-auto-grow";
import { cn } from "@/shared/lib/utils";

interface TextFieldProps {
  value: string;
  onChange(value: string): void;
  /** Minimum height in lines. */
  rows: number;
  label: string;
  placeholder?: string;
  /** Red placeholder: a required field left empty after CREATE / SAVE was pressed. */
  invalid?: boolean;
  /** Dotted underline, for a field that shares its card with something else and would not look editable. */
  lined?: boolean;
  readOnly?: boolean;
  className?: string;
}

/** Borderless textarea (`.txt`) that grows with its content. */
export function TextField({ value, onChange, rows, label, placeholder, invalid, lined, readOnly, className }: TextFieldProps) {
  const ref = useAutoGrow(value);
  return (
    <textarea
      ref={ref}
      rows={rows}
      value={value}
      aria-label={label}
      aria-invalid={invalid || undefined}
      placeholder={placeholder}
      readOnly={readOnly}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        "m-0 box-border block w-full resize-none overflow-hidden border-none bg-transparent p-0 font-sans text-[13px] leading-[1.55] text-ink placeholder:text-placeholder focus:outline-none",
        lined && "border-b border-dotted border-line-strong pb-1 transition-colors focus:border-gold",
        invalid && "placeholder:text-terracotta",
        lined && invalid && "border-terracotta",
        className,
      )}
    />
  );
}
