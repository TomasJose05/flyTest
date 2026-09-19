interface Props {
  title: string;
  subtitle: string;
  /** The millisecond this event happens, or null if it never happened in this scenario. */
  eventMs: number | null;
  timeMs: number;
  /** How long the "firing" flash lasts on screen, in simulated ms. Short enough that the
   *  run always ends in the "fired at X ms" state rather than frozen mid-flash. */
  holdMs?: number;
  tone: "decision" | "jump";
}

/**
 * A single big indicator for a one-off event: the Giant Fiber's decision, or the jump.
 *
 * It has four possible states, and the null case matters as much as the others: in a
 * scenario where the threat came too fast, the fly genuinely never reacted, and the UI has
 * to say so rather than render a broken or permanently-dark circle.
 */
export function EventIndicator({
  title,
  subtitle,
  eventMs,
  timeMs,
  holdMs = 250,
  tone,
}: Props) {
  const never = eventMs === null;
  const isFiring = !never && timeMs >= eventMs && timeMs - eventMs < holdMs;
  const hasFired = !never && timeMs >= eventMs;

  const state = never ? "never" : isFiring ? "firing" : hasFired ? "fired" : "waiting";
  const caption = {
    never: "no escape triggered",
    waiting: `waits until ${eventMs?.toFixed(1)} ms`,
    firing: "FIRING",
    fired: `fired at ${eventMs?.toFixed(1)} ms`,
  }[state];

  return (
    <section className="panel indicator-panel">
      <header className="panel-head">
        <h2>{title}</h2>
        <span className="muted">{subtitle}</span>
      </header>
      <div className={`indicator indicator-${tone} is-${state}`} />
      <p className={never ? "caption caption-never" : "caption"}>{caption}</p>
    </section>
  );
}
