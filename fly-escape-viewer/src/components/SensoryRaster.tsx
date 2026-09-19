import { useMemo } from "react";
import type { ScenarioData } from "../types";

/** How long a neuron stays lit after it fires, in ms. Purely a readability choice: a real
 *  spike is far shorter than one screen frame, so without this you would never see it. */
const FLASH_MS = 70;

interface Props {
  data: ScenarioData;
  timeMs: number;
}

/**
 * One dot per visual neuron (165 of them). A dot lights up at the exact millisecond that
 * neuron fired in the Brian2 run, and fades out FLASH_MS later.
 *
 * This is the fly "seeing" the threat grow: nothing happens for most of the approach, then
 * dots start popping at random, then the whole field is crackling.
 */
export function SensoryRaster({ data, timeMs }: Props) {
  // Regroup the flat spike list into "for each neuron, the times it fired". Done once per
  // scenario with useMemo, not on every frame - there are up to ~1800 spikes in a file.
  const spikesByNeuron = useMemo(() => {
    const byNeuron: number[][] = Array.from(
      { length: data.total_sensory_neurons },
      () => [],
    );
    for (const spike of data.sensory_spikes) {
      byNeuron[spike.neuron_index]?.push(spike.time_ms);
    }
    return byNeuron;
  }, [data]);

  const firedSoFar = data.sensory_spikes.filter((s) => s.time_ms <= timeMs).length;

  return (
    <section className="panel">
      <header className="panel-head">
        <h2>Visual neurons</h2>
        <span className="muted">
          LC4_L + LPLC2_L &middot; {data.total_sensory_neurons} cells &middot;{" "}
          {firedSoFar}/{data.sensory_spikes.length} spikes elapsed
        </span>
      </header>
      <div className="raster">
        {spikesByNeuron.map((times, index) => {
          // Lit if this neuron fired within the last FLASH_MS of simulated time.
          const isLit = times.some((t) => timeMs >= t && timeMs - t < FLASH_MS);
          return (
            <span
              key={index}
              className={isLit ? "dot dot-lit" : "dot"}
              title={`neuron ${index}`}
            />
          );
        })}
      </div>
    </section>
  );
}
