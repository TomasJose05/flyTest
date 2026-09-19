import { useEffect, useState } from "react";
import { SCENARIOS, type ScenarioData, type ScenarioKey } from "./types";
import { useSimulationClock } from "./useSimulationClock";
import { SensoryRaster } from "./components/SensoryRaster";
import { EventIndicator } from "./components/EventIndicator";
import { Timeline } from "./components/Timeline";
import "./App.css";

/** The simulation keeps running for 200 ms after the ramp ends (the threat passes). */
const TAIL_MS = 200;

export default function App() {
  const [scenarioKey, setScenarioKey] = useState<ScenarioKey>("medium_approach");
  const [data, setData] = useState<ScenarioData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const totalMs = data ? data.ramp_duration_ms + TAIL_MS : 0;
  const { timeMs, isPlaying, play, pause, reset } = useSimulationClock(totalMs);

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

  return (
    <main className="app">
      <header className="app-head">
        <h1>Fly escape circuit</h1>
        <p className="muted">
          Spike times from a Brian2 simulation of a real <i>Drosophila</i> connectome:
          LC4/LPLC2 &rarr; DNp01 (Giant Fiber) &rarr; TTMn. Nothing here is animated by
          hand - every flash is a recorded spike.
        </p>
      </header>

      <nav className="scenarios">
        {SCENARIOS.map((s) => (
          <button
            key={s.key}
            className={s.key === scenarioKey ? "scenario is-active" : "scenario"}
            onClick={() => setScenarioKey(s.key)}
          >
            <strong>{s.label}</strong>
            <span className="muted">{s.hint}</span>
          </button>
        ))}
      </nav>

      {error && <p className="error">Could not load {scenarioKey}.json: {error}</p>}
      {!data && !error && <p className="muted">Loading scenario...</p>}

      {data && (
        <>
          <section className="transport">
            <button className="primary" onClick={isPlaying ? pause : play}>
              {isPlaying ? "Pause" : timeMs >= totalMs ? "Replay" : "Play"}
            </button>
            <button onClick={reset}>Reset</button>
            <span className="clock">{timeMs.toFixed(1)} ms</span>
            <span className="muted">of {totalMs} ms</span>
          </section>

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
      )}
    </main>
  );
}
