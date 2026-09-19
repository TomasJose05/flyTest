import { useState } from "react";
import { SCENARIOS, type ScenarioKey } from "./types";
import { useScenarioPlayback } from "./useScenarioPlayback";
import { DebugView } from "./components/DebugView";
import { FlyScene } from "./scene/FlyScene";
import "./App.css";

type ViewMode = "scene" | "debug";

export default function App() {
  const [scenarioKey, setScenarioKey] = useState<ScenarioKey>("medium_approach");
  const [view, setView] = useState<ViewMode>("scene");
  // The myth is a loop, so the scene replays forever by default. The debug view is easier to
  // read frozen on its final frame, so the switch is here for both to share.
  const [loop, setLoop] = useState(true);

  // ONE clock, ONE copy of the data, shared by both views. See useScenarioPlayback.
  const { data, error, totalMs, timeMs, isPlaying, play, pause, reset } =
    useScenarioPlayback(scenarioKey, loop);

  return (
    <main className="app">
      <header className="app-head">
        <h1>Fly escape circuit</h1>
        <p className="muted">
          Spike times from a Brian2 simulation of a real <i>Drosophila</i> connectome:
          LC4/LPLC2 &rarr; DNp01 (Giant Fiber) &rarr; TTMn. Nothing here is animated by
          hand - the fly jumps because the Giant Fiber fired.
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
        <div className="view-toggle">
          <button
            className={view === "scene" ? "is-active" : ""}
            onClick={() => setView("scene")}
          >
            3D scene
          </button>
          <button
            className={view === "debug" ? "is-active" : ""}
            onClick={() => setView("debug")}
          >
            Debug data
          </button>
        </div>
      </nav>

      {error && (
        <p className="error">
          Could not load {scenarioKey}.json: {error}
        </p>
      )}
      {!data && !error && <p className="muted">Loading scenario...</p>}

      {data && (
        <>
          <section className="transport">
            <button className="primary" onClick={isPlaying ? pause : play}>
              {isPlaying ? "Pause" : timeMs >= totalMs ? "Replay" : "Play"}
            </button>
            <button onClick={reset}>Reset</button>
            <label className="loop-toggle">
              <input
                type="checkbox"
                checked={loop}
                onChange={(e) => setLoop(e.target.checked)}
              />
              Loop
            </label>
            <span className="clock">{timeMs.toFixed(1)} ms</span>
            <span className="muted">of {totalMs} ms</span>
          </section>

          {view === "scene" ? (
            <>
              <FlyScene data={data} timeMs={timeMs} />
              <p className="muted scene-note">
                The boulder falls over the full {data.ramp_duration_ms} ms ramp.{" "}
                {data.giant_fiber_spike_ms === null
                  ? "In this scenario the Giant Fiber never fired, so the fly never moves."
                  : `The fly leaves the ground at ${data.giant_fiber_spike_ms} ms, the exact
                     moment DNp01 spiked in the simulation.`}
              </p>
            </>
          ) : (
            <DebugView data={data} timeMs={timeMs} totalMs={totalMs} />
          )}
        </>
      )}
    </main>
  );
}
