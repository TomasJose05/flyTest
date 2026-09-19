import { useCallback, useEffect, useRef, useState } from "react";

/**
 * The simulation clock.
 *
 * It answers one question, sixty times a second: "how many milliseconds into the
 * simulation are we right now?" Everything else on screen is derived from that number.
 *
 * WHY requestAnimationFrame AND NOT setInterval
 * ---------------------------------------------
 * setInterval(fn, 16) asks the browser to run something roughly every 16 ms. "Roughly" is
 * the problem: the timer is not synced to the screen, so some frames get two updates and
 * some get none, which shows up as stutter. It also keeps firing when the tab is hidden,
 * burning battery on animation nobody is watching.
 *
 * requestAnimationFrame instead says "call me right before the next repaint". The browser
 * decides when that is, so the work lands exactly once per frame, at whatever rate the
 * monitor actually runs (60 Hz, 120 Hz, whatever), and it pauses automatically in a
 * background tab.
 *
 * The other half of the trick: rAF hands your callback a high-precision timestamp, and we
 * derive elapsed time from that instead of counting frames. Counting frames (t += 16) would
 * drift as soon as one frame runs late - and with real spike times to hit, drift is exactly
 * what we cannot afford.
 *
 * WHY THE LOOP KEEPS ITS STATE IN LOCAL VARIABLES
 * -----------------------------------------------
 * Everything the running loop needs (`startedAt`, `frame`, `cancelled`) is declared INSIDE
 * the effect, not in a ref shared across effect runs. That matters more than it looks: in
 * development React deliberately mounts effects twice to expose exactly this class of bug,
 * and if two loops share one ref for "the frame I scheduled", the cleanup of one cancels
 * the other's frame while both keep scheduling - the clock then jumps backwards or freezes.
 * With locals, each loop owns its own bookkeeping and the `cancelled` flag stops it dead.
 */
export function useSimulationClock(durationMs: number, loop = false) {
  const [timeMs, setTimeMs] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // The one thing that must outlive a single loop: how far into the simulation we are, so
  // that Pause -> Play resumes instead of restarting. useRef survives re-renders without
  // causing one when it changes.
  const elapsedRef = useRef(0);

  useEffect(() => {
    if (!isPlaying) return;

    let frame = 0;
    let cancelled = false;
    // `let`, not `const`: looping rewinds these two rather than restarting the effect.
    let startedAt = performance.now(); // wall-clock moment this play began
    let startOffset = elapsedRef.current; // simulated time already played

    const tick = (now: number) => {
      if (cancelled) return;

      // rAF's timestamp belongs to the start of the frame, which can be a hair EARLIER than
      // the performance.now() we captured above - hence the clamp, or the first frame would
      // report a negative time.
      let elapsed = Math.max(0, now - startedAt) + startOffset;

      if (elapsed >= durationMs) {
        if (loop) {
          // Straight back to the top without stopping: the threat comes round again, which
          // is the whole point of the Sisyphus scene.
          startedAt = now;
          startOffset = 0;
          elapsed = 0;
        } else {
          elapsedRef.current = durationMs;
          setTimeMs(durationMs);
          setIsPlaying(false); // reached the end, stop on the last frame
          return;
        }
      }
      elapsedRef.current = elapsed; // keep this current so Pause needs no extra work
      setTimeMs(elapsed);
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
    };
  }, [isPlaying, durationMs, loop]);

  const play = useCallback(() => {
    // Pressing Play at the very end replays from the top rather than doing nothing.
    if (elapsedRef.current >= durationMs) {
      elapsedRef.current = 0;
      setTimeMs(0);
    }
    setIsPlaying(true);
  }, [durationMs]);

  // Pause and reset only flip the switch: the loop's cleanup does the actual stopping.
  const pause = useCallback(() => setIsPlaying(false), []);

  const reset = useCallback(() => {
    elapsedRef.current = 0;
    setTimeMs(0);
    setIsPlaying(false);
  }, []);

  return { timeMs, isPlaying, play, pause, reset };
}
