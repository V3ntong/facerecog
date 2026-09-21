interface Props {
  message: string;
  onDismiss: () => void;
}

export default function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div
      className="mb-4 px-4 py-3 rounded-xl flex items-center justify-between text-sm"
      style={{
        background: "color-mix(in srgb, var(--error) 10%, var(--bg-card))",
        color: "var(--error)",
        border: "1px solid color-mix(in srgb, var(--error) 20%, transparent)",
      }}
    >
      <span>{message}</span>
      <button
        onClick={onDismiss}
        className="ml-3 text-lg leading-none cursor-pointer"
        style={{ color: "var(--text-muted)" }}
      >
        x
      </button>
    </div>
  );
}
