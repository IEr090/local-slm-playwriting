import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/** Large serif input used in row 1 (name, surname, age). */
export function SerifInput({ className, ...props }: ComponentProps<"input">) {
  return (
    <input
      type="text"
      className={cn(
        "m-0 box-border block w-full min-w-0 border-none bg-transparent p-0 font-serif text-xl font-medium text-ink placeholder:text-placeholder focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}
