import type { ScenarioData } from "../types";
import { SensoryRaster } from "./SensoryRaster";
import { EventIndicator } from "./EventIndicator";
import { Timeline } from "./Timeline";

interface Props {
  data: ScenarioData;
  timeMs: number;
  totalMs: number;
}

/**
 * The original data view, unchanged: the timeline with both spike moments marked, the 165
 * sensory dots, and the two event indicators.
 *
 * It is worth keeping next to the 3D scene rather than replacing it. This view shows the
 * NUMBERS the animation is obeying, so when the fly jumps you can flip over here and check
 * that it jumped on the millisecond the simulation recorded.
 */
export function DebugView({ data, timeMs, totalMs }: Props) {
  return (
    <>
      <Timeline data={data} timeMs={timeMs} totalMs={totalMs} />
      <div className="stages">
        <SensoryRaster data={data} timeMs={timeMs} />
        <EventIndicator
          title="Giant Fiber"
          subtitle="DNp01_L &middot; the decision"
          eventMs={data.giant_fiber_spike_ms}
          timeMs={timeMs}
          tone="decision"
        />
        <EventIndicator
          title="Jump"
          subtitle="TTMn_L &middot; the motor output"
          eventMs={data.motor_spike_ms}
          timeMs={timeMs}
          tone="jump"
        />
      </div>
    </>
  );
}
