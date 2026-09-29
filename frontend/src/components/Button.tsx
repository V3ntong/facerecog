import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "quiet";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  /** A wax-pencil dot, for the actions the machine is watching. */
  mark?: boolean;
  children: ReactNode;
}

const BASE = "type-ui inline-flex items-center gap-2 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink px-4 py-2 text-paper hover:opacity-90",
  secondary: "border border-ink px-4 py-2 text-ink hover:bg-flash",
  quiet: "px-1 py-2 text-slate underline decoration-dim underline-offset-4 hover:text-ink",
};

export default function Button({
  variant = "primary",
  mark = false,
  children,
  className = "",
  ...rest
}: Props) {
  return (
    <button type="button" className={`${BASE} ${VARIANTS[variant]} ${className}`} {...rest}>
      {mark && <span aria-hidden="true" className="h-2 w-2 shrink-0 rounded-full bg-mark" />}
      {children}
    </button>
  );
}
