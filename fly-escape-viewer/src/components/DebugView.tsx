import type { ScenarioData } from "../types";
import { SensoryRaster } from "./SensoryRaster";
import { EventIndicator } from "./EventIndicator";

interface Props {
  data: ScenarioData;
  timeMs: number;
}

/**
 * The data side of the screen: the 165 sensory dots, and the two event indicators.
 *
 * It sits next to the 3D scene rather than replacing it, because this is where the NUMBERS
 * are. When the fly leaps you can glance right and see that the Giant Fiber card lit up on
 * the same frame - the animation and the evidence for it, side by side.
 *
 * The shared timeline lives one level up in App, spanning both panels: it belongs to the
 * whole screen, not to this half of it.
 */
export function DebugView({ data, timeMs }: Props) {
  return (
    <>
      <SensoryRaster data={data} timeMs={timeMs} />
      <div className="indicator-pair">
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
