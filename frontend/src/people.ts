/**
 * The six people this app can name.
 *
 * Recognition is closed-set: anyone else comes back as "unknown". So this list
 * is the boundary the whole interface is built around — the rail prints it on
 * every screen, and every mark, count and roster state is derived from it.
 * Change the roster here when the enrolled people change.
 */
export const PEOPLE = [
  "Aldrian Dajes",
  "Axl Moraleja",
  "Cristian Jim Pogoy",
  "Cui Pendang",
  "Jether Urmenita",
  "Melvin Maquilan",
] as const;

/** What the backend calls a face it cannot match. */
export const UNKNOWN = "unknown";

export function isEnrolled(name: string): boolean {
  return (PEOPLE as readonly string[]).includes(name);
}

/** The names this app can actually say, in the order they were detected. */
export function spottedNames(people: { name: string }[]): string[] {
  return [...new Set(people.map((p) => p.name).filter(isEnrolled))];
}
