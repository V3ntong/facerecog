import type { RecognitionResult } from "../types";
import { UNKNOWN, spottedNames } from "../people";
import Slip from "./Slip";

interface Props {
  result: RecognitionResult;
  /** Changes with every result, so the print animation replays. */
  resultKey: number;
}

/**
 * The verdict, printed: the sentence the API wrote, exactly as it wrote it,
 * then each person's comeback attributed to them. The two halves are set in
 * different voices — the record in Archivo, the aside in Newsreader italic —
 * because they are genuinely said by different things: the matcher, and the
 * model paid to be rude about you.
 */
export default function Sightings({ result, resultKey }: Props) {
  const spotted = spottedNames(result.people);
  const comebacks = result.people.filter((person) => person.name !== UNKNOWN && person.doing);
  const attribute = spotted.length > 1;

  const direction =
    result.people.length === 0
      ? "Try a brighter, closer shot."
      : spotted.length === 0
        ? "Nobody in this one is on the list."
        : null;

  return (
    <section key={resultKey} className="mt-6">
      <h2 className="type-verdict verdict-print max-w-[24ch] text-[clamp(30px,5.2vw,46px)]">
        {result.sentence}
      </h2>

      {direction && <p className="type-ui mt-3 text-slate">{direction}</p>}

      {comebacks.length > 0 && (
        <div className="mt-4 border-t border-rule pt-4">
          {comebacks.map((person, index) => (
            <div key={`${person.name}-${index}`} className={index === 0 ? "" : "mt-4"}>
              {attribute && <p className="type-rollcall text-[17px] text-ink">{person.name}</p>}
              <p className="type-aside max-w-[52ch] text-ink">{person.doing}</p>
            </div>
          ))}
        </div>
      )}

      {result.notice && (
        <Slip kind="note" className="mt-4">
          {result.notice}
        </Slip>
      )}
    </section>
  );
}
