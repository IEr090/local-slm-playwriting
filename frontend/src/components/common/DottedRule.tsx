import { cn } from "@/lib/utils";

/** `1px dotted #4a4229` divider. */
export function DottedRule({ className }: { className?: string }) {
  return <div aria-hidden className={cn("dotted-rule", className)} />;
}
