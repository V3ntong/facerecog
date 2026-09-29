import { useEffect, useState } from "react";
import type { RecognizedPerson } from "../types";
import { UNKNOWN } from "../people";
import { formatMatch } from "../format";

export interface Evidence {
  url: string;
  kind: "image" | "video";
}

interface Props {
  evidence: Evidence;
  /** Faces to mark. Video results carry no boxes, so this can be empty. */
  people: RecognizedPerson[];
}

const TAU = Math.PI * 2;

/** The API sends boxes as [x1, y1, x2, y2] in original pixels — and omits them
 *  entirely for clips. Read it defensively rather than trusting the type. */
function boxOf(person: RecognizedPerson): number[] | null {
  const box = person.box as unknown as number[] | undefined;
  return Array.isArray(box) && box.length === 4 ? box : null;
}

/** Deterministic wobble: the stroke looks hand-drawn but is identical on every
 *  render, so nothing shimmers and a re-render never redraws a different mark. */
function seeded(seed: number): () => number {
  let state = seed * 0x6d2b79f5 + 0x9e3779b9;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let r = Math.imul(state ^ (state >>> 15), 1 | state);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

/** A ring around a face, as a path in image pixels, with a little overshoot
 *  where the pencil comes back round — the way a person circles a print. */
function waxRing(
  box: number[],
  seed: number,
  { scale, sweep, wobble }: { scale: number; sweep: number; wobble: number }
): string {
  const [x1, y1, x2, y2] = box;
  const pad = Math.max(6, (x2 - x1) * 0.18);
  const cx = (x1 + x2) / 2;
  const cy = (y1 + y2) / 2;
  const rx = ((x2 - x1) / 2 + pad) * scale;
  const ry = ((y2 - y1) / 2 + pad * 1.2) * scale;
  const random = seeded(seed);
  const start = -Math.PI / 2 + (random() - 0.5) * 0.6;
  const steps = 34;
  let path = "";

  for (let i = 0; i <= steps; i += 1) {
    const angle = start + (i / steps) * TAU * sweep;
    const jitter = 1 + (random() - 0.5) * wobble;
    const px = cx + Math.cos(angle) * rx * jitter;
    const py = cy + Math.sin(angle) * ry * jitter;
    path += `${i === 0 ? "M" : "L"}${px.toFixed(1)} ${py.toFixed(1)}`;
  }

  return path;
}

/**
 * The evidence: the photo it just read, on a mat, with the marks on it. Names
 * live where the faces are, so there is no separate row of chips repeating what
 * the print already shows. For a clip there is nothing to mark, so the plate is
 * the clip itself and the timeline carries the detail.
 */
export default function EvidencePlate({ evidence, people }: Props) {
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);

  // A new print gets measured from scratch — never draw the last one's marks.
  useEffect(() => {
    setSize(null);
  }, [evidence.url]);

  if (evidence.kind === "video") {
    return (
      <figure className="border border-rule bg-flash p-2">
        <video
          src={evidence.url}
          controls
          playsInline
          className="block max-h-[58vh] w-full bg-paper"
        />
      </figure>
    );
  }

  const marks = people
    .map((person) => ({ person, box: boxOf(person) }))
    .sort((a, b) => (a.box?.[0] ?? 0) - (b.box?.[0] ?? 0));

  return (
    <figure className="border border-rule bg-flash p-2 sm:p-3">
      <div className="relative inline-block max-w-full">
        <img
          src={evidence.url}
          alt="The photo being checked"
          className="block h-auto max-h-[58vh] w-auto max-w-full"
          onLoad={(event) =>
            setSize({
              w: event.currentTarget.naturalWidth,
              h: event.currentTarget.naturalHeight,
            })
          }
        />

        {size && (
          <svg
            aria-hidden="true"
            viewBox={`0 0 ${size.w} ${size.h}`}
            className="pointer-events-none absolute inset-0 h-full w-full"
          >
            {marks.map(({ person, box }, index) =>
              box ? (
                <WaxRing
                  key={`ring-${index}`}
                  box={box}
                  index={index}
                  named={person.name !== UNKNOWN}
                />
              ) : null
            )}
          </svg>
        )}

        {size &&
          marks.map(({ person, box }, index) =>
            box ? (
              <MarkLabel
                key={`label-${index}`}
                box={box}
                size={size}
                name={person.name}
                score={person.score}
                named={person.name !== UNKNOWN}
              />
            ) : null
          )}
      </div>
    </figure>
  );
}

function WaxRing({ box, index, named }: { box: number[]; index: number; named: boolean }) {
  const [x1, y1, x2, y2] = box;
  const width = x2 - x1;
  const stroke = Math.max(2.5, width * 0.05);

  // A face it cannot name gets a dashed slate box, never a wax ring: the ring is
  // the mark that means "that's someone I know".
  if (!named) {
    return (
      <rect
        x={x1}
        y={y1}
        width={width}
        height={y2 - y1}
        fill="none"
        stroke="var(--slate)"
        strokeWidth={Math.max(2, width * 0.02)}
        strokeDasharray="7 7"
      />
    );
  }

  const delay = index * 0.12;

  return (
    <g>
      <path
        d={waxRing(box, index * 977 + 13, { scale: 1, sweep: 1.02, wobble: 0.05 })}
        fill="none"
        stroke="var(--mark)"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        className="wax-stroke"
        style={{ animationDelay: `${delay}s` }}
      />
      <path
        d={waxRing(box, index * 977 + 41, { scale: 1.07, sweep: 0.34, wobble: 0.09 })}
        fill="none"
        stroke="var(--mark)"
        strokeWidth={stroke * 0.7}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.45}
        pathLength={1}
        className="wax-stroke"
        style={{ animationDelay: `${delay + 0.16}s` }}
      />
    </g>
  );
}

function MarkLabel({
  box,
  size,
  name,
  score,
  named,
}: {
  box: number[];
  size: { w: number; h: number };
  name: string;
  score: number;
  named: boolean;
}) {
  const [x1, y1, x2, y2] = box;
  // Near the top of the frame there is no room above the head, so the caption
  // goes underneath instead.
  const above = y1 / size.h > 0.18;

  return (
    <span
      className={`type-rollcall absolute whitespace-nowrap border-l-2 bg-flash px-1.5 py-[3px] text-[13px] sm:text-[14px] ${
        named ? "border-mark text-ink" : "border-slate text-slate"
      }`}
      style={{
        left: `${Math.max(0, (x1 / size.w) * 100)}%`,
        top: `${((above ? y1 : y2) / size.h) * 100}%`,
        transform: above ? "translateY(calc(-100% - 5px))" : "translateY(5px)",
      }}
    >
      {named ? name : "Not on the list"}
      {named && <span className="type-record ml-2 text-mark-ink">{formatMatch(score)}</span>}
    </span>
  );
}
