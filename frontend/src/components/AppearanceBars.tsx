import type { TimelineEntry } from "../types";
import { formatClock, formatMatch, formatSpan } from "../format";
import { isEnrolled } from "../people";

interface Props {
  timeline: TimelineEntry[];
}

/**
 * For a clip: when each person turned up and when they left, over a real time
 * axis. This is the one place in the app where a sequence genuinely exists, so
 * it gets an axis and a bar rather than numbered decoration.
 */
export default function AppearanceBars({ timeline }: Props) {
  const entries = timeline.filter((entry) => isEnrolled(entry.person));
  const unnamed = timeline.length - entries.length;
  if (entries.length === 0) return null;

  const duration = Math.max(1, ...entries.map((entry) => entry.last_seen));
  const ticks = duration >= 6 ? [0, duration / 2, duration] : [0, duration];

  return (
    <section className="mt-6 border-t border-rule pt-4">
      <div className="type-record flex justify-between text-slate">
        {ticks.map((tick, index) => (
          <span key={index}>{formatClock(tick)}</span>
        ))}
      </div>
      <div className="mt-1 border-t border-rule" />

      {entries.map((entry, index) => {
        const start = Math.min(100, (entry.first_seen / duration) * 100);
        const width = Math.min(100 - start, Math.max(1.5, ((entry.last_seen - entry.first_seen) / duration) * 100));
        return (
          <div
            key={`${entry.person}-${index}`}
            className={index === 0 ? "mt-4" : "mt-4 border-t border-rule pt-4"}
          >
            <div className="flex items-baseline justify-between gap-4">
              <span className="type-rollcall text-[17px] text-ink sm:text-[19px]">
                {entry.person}
              </span>
              <span className="type-record shrink-0 text-slate">
                {formatSpan(entry.first_seen, entry.last_seen)}{" "}
                <span className="text-mark-ink">{formatMatch(entry.confidence)}</span>
              </span>
            </div>

            <div className="mt-2 h-[6px] w-full bg-rule">
              <span
                className="block h-full bg-mark"
                style={{ marginLeft: `${start}%`, width: `${width}%` }}
              />
            </div>

            {entry.doing && (
              <p className="type-aside mt-3 max-w-[52ch] text-ink">{entry.doing}</p>
            )}
          </div>
        );
      })}

      {unnamed > 0 && (
        <p className="type-record mt-4 text-slate">
          {unnamed} {unnamed === 1 ? "face" : "faces"} it couldn't name.
        </p>
      )}
    </section>
  );
}
