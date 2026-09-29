import type { HealthResponse } from "../types";
import { PEOPLE } from "../people";
import { providerLabel } from "../format";

interface Props {
  health: HealthResponse | null;
  healthFailed: boolean;
  /** The people this app could name in the current result. */
  spotted: string[];
  /** Changes with every result, so the roster marks replay. */
  resultKey: number;
  dark: boolean;
  onToggleDark: () => void;
}

/**
 * The rail is the constant half of the page: it prints the six people this app
 * knows on every screen, so "who's missing" is readable at a glance and the
 * closed set is never a hidden fact. The colophon underneath is the desk's own
 * records — how many prints it holds, how sure it has to be, who writes the
 * comebacks.
 */
export default function Rail({
  health,
  healthFailed,
  spotted,
  resultKey,
  dark,
  onToggleDark,
}: Props) {
  return (
    <aside className="border-b border-rule lg:sticky lg:top-0 lg:h-screen lg:w-[19rem] lg:shrink-0 lg:overflow-y-auto lg:border-b-0 lg:border-r">
      <div className="px-5 py-5 lg:px-7 lg:py-8">
        <div className="flex items-baseline justify-between gap-4">
          <h1 className="type-nameplate text-[30px] lg:text-[34px]">Ohahay</h1>
          <button
            type="button"
            onClick={onToggleDark}
            aria-pressed={dark}
            className="type-record shrink-0 cursor-pointer text-slate underline decoration-dim underline-offset-4 hover:text-ink"
          >
            {dark ? "Light mode" : "Dark mode"}
          </button>
        </div>

        <section className="mt-5 border-t border-rule pt-4 lg:mt-7">
          <h2 className="type-record text-slate">Who it knows</h2>
          <ul className="mt-1.5">
            {PEOPLE.map((name) => {
              const present = spotted.includes(name);
              return (
                <li key={name} className="py-px">
                  <span className="relative inline-block">
                    <span
                      className={`type-rollcall text-[22px] lg:text-[26px] ${
                        present ? "text-ink" : "text-slate"
                      }`}
                    >
                      {name}
                    </span>
                    {present && (
                      <span
                        key={resultKey}
                        className="roster-mark absolute -bottom-0.5 left-0 h-[3px] w-full bg-mark"
                        style={{ animationDelay: "0.34s" }}
                      />
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="mt-5 border-t border-rule pt-4 lg:mt-7">
          {health ? (
            <ul className="type-record space-y-1 text-slate">
              <li>
                <span className="text-ink">{health.embeddings_loaded}</span> prints on file
              </li>
              <li>
                <span className="text-ink">{health.threshold.toFixed(2)}</span> and up counts as a
                match
              </li>
              <li>Comebacks by {providerLabel(health.ai_provider)}</li>
            </ul>
          ) : healthFailed ? (
            <p className="type-record max-w-[40ch] text-ink">
              The server isn't answering. Start the backend, then reload this page.
            </p>
          ) : (
            <p className="type-record text-slate">Checking the server…</p>
          )}
        </section>
      </div>
    </aside>
  );
}
