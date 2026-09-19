import type { ScenarioData } from "../types";

interface Props {
  data: ScenarioData;
  timeMs: number;
  totalMs: number;
}

/**
 * A progress bar for the run, with the two important moments marked on it. Lets you see at
 * a glance WHERE in the approach the decision happens - about four fifths of the way in,
 * in every scenario, which is the whole point of the simulation.
 */
export function Timeline({ data, timeMs, totalMs }: Props) {
  const pct = (ms: number) => `${(100 * ms) / totalMs}%`;

  return (
    <div className="timeline">
      <div className="timeline-track">
        <div className="timeline-fill" style={{ width: pct(timeMs) }} />
        {/* The grey section is the 200 ms after the ramp, when the threat is gone. */}
        <div
          className="timeline-after"
          style={{ left: pct(data.ramp_duration_ms) }}
          title="threat gone"
        />
        {data.giant_fiber_spike_ms !== null && (
          <div
            className="marker marker-decision"
            style={{ left: pct(data.giant_fiber_spike_ms) }}
            title={`Giant Fiber ${data.giant_fiber_spike_ms} ms`}
          />
        )}
        {data.motor_spike_ms !== null && (
          <div
            className="marker marker-jump"
            style={{ left: pct(data.motor_spike_ms) }}
            title={`TTMn ${data.motor_spike_ms} ms`}
          />
        )}
      </div>
      <div className="timeline-labels">
        <span>0 ms</span>
        <span className="muted">ramp ends {data.ramp_duration_ms} ms</span>
        <span>{totalMs} ms</span>
      </div>
    </div>
  );
}
