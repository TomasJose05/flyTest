/**
 * The exact shape of the files in public/data/, written by export_scenarios.py.
 *
 * Every number is a plain millisecond timestamp measured from the start of the
 * simulation. There are no units and no nesting: the Python side already flattened
 * everything, so what we get here is what we animate.
 */

/** One spike: sensory neuron `neuron_index` fired at `time_ms`. */
export interface SensorySpike {
  neuron_index: number;
  time_ms: number;
}

export interface ScenarioData {
  scenario: string;
  /** How long the threat took to grow from invisible to full size. */
  ramp_duration_ms: number;
  /** Every spike from the 165 visual neurons, already sorted by time. */
  sensory_spikes: SensorySpike[];
  /** When the Giant Fiber decided to escape - or null if the fly never reacted. */
  giant_fiber_spike_ms: number | null;
  /** When the jump motor neuron fired - or null. */
  motor_spike_ms: number | null;
  total_sensory_neurons: number;
}

/** The three files we ship in public/data/. */
export const SCENARIOS = [
  { key: "slow_approach", label: "Slow approach", hint: "1500 ms ramp" },
  { key: "medium_approach", label: "Medium approach", hint: "800 ms ramp" },
  { key: "fast_approach", label: "Fast approach", hint: "400 ms ramp" },
] as const;

export type ScenarioKey = (typeof SCENARIOS)[number]["key"];
