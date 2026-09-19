import { useEffect, useState } from "react";
import type { ScenarioData, ScenarioKey } from "./types";
import { useSimulationClock } from "./useSimulationClock";

/** The simulation keeps running for 200 ms after the ramp ends (the threat passes). */
export const TAIL_MS = 200;

/**
 * One source of truth for "which scenario, and how far into it are we".
 *
 * Both views - the debug data view and the 3D scene - call nothing but this. That is the
 * point of pulling it out of App: there is exactly ONE clock and ONE copy of the scenario
 * data, so the boulder cannot possibly fall on a different timeline than the one the debug
 * markers report. If the two ever disagree on screen, the bug is in a view, never in a
 * second clock that drifted.
 */
export function useScenarioPlayback(scenarioKey: ScenarioKey, loop: boolean) {
  const [data, setData] = useState<ScenarioData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const totalMs = data ? data.ramp_duration_ms + TAIL_MS : 0;
  const clock = useSimulationClock(totalMs, loop);
  const { reset } = clock;

  // Load the chosen scenario from public/data/. These are static files served by Vite -
  // there is no backend, and no neuroscience runs in the browser: Python already did it.
  useEffect(() => {
    let cancelled = false;
    reset();
    setData(null);
    setError(null);

    fetch(`${import.meta.env.BASE_URL}data/${scenarioKey}.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<ScenarioData>;
      })
      .then((json) => {
        // `cancelled` guards against a slow response arriving after the user already
        // clicked a different scenario, which would otherwise overwrite the newer data.
        if (!cancelled) setData(json);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });

    return () => {
      cancelled = true;
    };
  }, [scenarioKey, reset]);

  return { data, error, totalMs, ...clock };
}
