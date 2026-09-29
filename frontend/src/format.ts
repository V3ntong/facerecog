/** Clock time for a moment inside a clip — 0:04, 1:12. */
export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  return `${minutes}:${String(total % 60).padStart(2, "0")}`;
}

/** A span inside a clip — 0:04–0:11. */
export function formatSpan(start: number, end: number): string {
  return `${formatClock(start)}–${formatClock(end)}`;
}

/** How sure the match is, as a whole percent. */
export function formatMatch(score: number): string {
  return `${Math.round(score * 100)}%`;
}
