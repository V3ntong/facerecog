interface Props {
  dark: boolean;
  onToggleDark: () => void;
}

export default function Header({ dark, onToggleDark }: Props) {
  return (
    <header
      className="sticky top-0 z-50 backdrop-blur-md border-b px-4 py-3"
      style={{
        background: "color-mix(in srgb, var(--bg-primary) 85%, transparent)",
        borderColor: "var(--border)",
      }}
    >
      <div className="max-w-3xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
            style={{ background: "var(--accent)" }}
          >
            W
          </div>
          <span className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            WhoIsThere
          </span>
        </div>
        <button
          onClick={onToggleDark}
          className="p-2 rounded-lg transition-colors cursor-pointer"
          style={{ color: "var(--text-secondary)" }}
          title={dark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {dark ? "☀️" : "🌙"}
        </button>
      </div>
    </header>
  );
}
