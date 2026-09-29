import type { ReactNode } from "react";

/**
 * A paper slip. Used for anything the machine has to say back that isn't the
 * verdict: a failure, a partial-failure note from the API, or the confirmation
 * that a face was registered.
 */
type Kind = "failure" | "note" | "added";

interface Props {
  kind: Kind;
  children: ReactNode;
  onDismiss?: () => void;
  className?: string;
}

const EDGE: Record<Kind, string> = {
  failure: "border-l-ink",
  note: "border-l-dim",
  added: "border-l-mark",
};

const TONE: Record<Kind, string> = {
  failure: "text-ink",
  note: "text-slate",
  added: "text-ink",
};

export default function Slip({ kind, children, onDismiss, className = "" }: Props) {
  return (
    <div
      role={kind === "failure" ? "alert" : "status"}
      className={`flex items-start justify-between gap-4 border border-l-[3px] border-rule bg-flash px-3.5 py-2.5 ${EDGE[kind]} ${TONE[kind]} ${className}`}
    >
      <p className="type-ui max-w-[62ch]">{children}</p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="type-record shrink-0 cursor-pointer text-slate underline decoration-dim underline-offset-4 hover:text-ink"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}
