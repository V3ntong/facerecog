import type { RecognitionResult } from "../types";

interface Props {
  result: RecognitionResult;
}

const COLORS: Record<string, string> = {
  Pendang: "#6366f1",
  Urmenita: "#ec4899",
  Dajes: "#f59e0b",
  Moraleja: "#10b981",
  Pogoy: "#3b82f6",
  Maquilan: "#8b5cf6",
  unknown: "#94a3b8",
};

function getColor(name: string): string {
  return COLORS[name] || "#64748b";
}

export default function ResultCard({ result }: Props) {
  const { people, sentence, type, timeline } = result;
  const recognized = people.filter((p) => p.name !== "unknown");
  const unknowns = people.filter((p) => p.name === "unknown");

  return (
    <div className="mt-6 space-y-4">
      {/* Sentence */}
      <div
        className="rounded-2xl p-5"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <p className="text-base font-medium leading-relaxed" style={{ color: "var(--text-primary)" }}>
          {sentence}
        </p>
      </div>

      {/* Person chips */}
      {recognized.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {recognized.map((p, i) => (
            <div
              key={`${p.name}-${i}`}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
              style={{
                background: `color-mix(in srgb, ${getColor(p.name)} 12%, var(--bg-card))`,
                color: getColor(p.name),
                border: `1px solid color-mix(in srgb, ${getColor(p.name)} 20%, transparent)`,
              }}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: getColor(p.name) }}
              />
              {p.name}
              {p.score > 0 && (
                <span className="text-xs opacity-60">
                  {(p.score * 100).toFixed(0)}%
                </span>
              )}
              {p.doing && (
                <span className="text-xs opacity-80">
                  {p.doing}
                </span>
              )}
            </div>
          ))}
          {unknowns.length > 0 && (
            <div
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm"
              style={{
                background: "var(--bg-secondary)",
                color: "var(--text-muted)",
              }}
            >
              {unknowns.length} unknown
            </div>
          )}
        </div>
      )}

      {/* Timeline for video */}
      {timeline && timeline.length > 0 && (
        <div
          className="rounded-2xl p-5"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <h3 className="text-sm font-medium mb-3" style={{ color: "var(--text-secondary)" }}>
            Timeline
          </h3>
          <div className="space-y-2">
            {timeline.map((entry, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ background: getColor(entry.person) }}
                />
                <span
                  className="font-medium min-w-[80px]"
                  style={{ color: getColor(entry.person) }}
                >
                  {entry.person}
                </span>
                <span style={{ color: "var(--text-muted)" }}>
                  {formatTime(entry.first_seen)} — {formatTime(entry.last_seen)}
                </span>
                <span
                  className="ml-auto text-xs"
                  style={{ color: "var(--text-muted)" }}
                >
                  {(entry.confidence * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Face detail cards */}
      {recognized.length > 0 && type === "image" && (
        <div
          className="rounded-2xl p-5"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <h3 className="text-sm font-medium mb-3" style={{ color: "var(--text-secondary)" }}>
            Detected Faces
          </h3>
          <div className="space-y-2">
            {recognized.map((p, i) => (
              <div
                key={`${p.name}-${i}`}
                className="flex items-center justify-between px-3 py-2 rounded-lg"
                style={{ background: "var(--bg-secondary)" }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ background: getColor(p.name) }}
                  />
                  <span className="font-medium text-sm" style={{ color: "var(--text-primary)" }}>
                    {p.name}
                  </span>
                </div>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                  box: [{p.box.join(", ")}]
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
