"""
export_scenarios.py - STEP 3: turn the validated simulation into data a frontend can eat.

simulate_circuit.py proved the circuit works. This script runs that SAME circuit three
times with three different threat speeds and writes the spike times to plain JSON files in
exports/, one per scenario. No neuroscience runs in the browser: React just reads
"neuron 42 fired at 613.8 ms" and animates it.

Everything about the circuit is frozen - the real connectome weights, the LIF neurons, the
refractory periods, the per-neuron noise. The ONLY thing that changes between scenarios is
how fast the imaginary object is coming at the fly.

A reminder of what is being simulated (see simulate_circuit.py for the full explanation):
a neuron is a leaky bucket of voltage, it "spikes" when the level hits a threshold, and the
wiring is LC4_L + LPLC2_L (165 visual cells) -> DNp01_L (Giant Fiber) -> TTMn_L (jump).
"""

import json
import os
import numpy as np
from brian2 import (NeuronGroup, Synapses, SpikeMonitor, TimedArray, run, start_scope,
                    prefs, defaultclock, mV, ms)

prefs.codegen.target = "numpy"         # tiny circuit: no C++ compiler needed
defaultclock.dt = 0.1 * ms

GF_BODY_ID, TTMN_BODY_ID = 10010, 804642       # left hemisphere only, from step 1b

# --------------------------------------------------- the circuit, unchanged from step 2c
V_REST, V_THRESHOLD, V_RESET = -70 * mV, -50 * mV, -70 * mV
TAU = 10 * ms                          # how fast the bucket leaks back toward rest
SENSORY_REFRACTORY = 5 * ms            # sensory cells legitimately keep reporting
COMMAND_REFRACTORY = 175 * ms          # the command stage fires once per threat, not a buzz
SYNAPSE_TO_MV = 0.05 * mV              # one real synapse is worth this much voltage
GF_TO_MOTOR_MV = 25 * mV               # set by hand: that junction is electrical in the fly
PEAK_MV = 30                           # drive at the end of the ramp
EXCITABILITY_SPREAD = 0.15             # biological noise: no two neurons are identical

EQS_SENSORY = """
dv/dt = (V_REST - v + looming(t) * excitability) / TAU : volt (unless refractory)
excitability : 1
"""
EQS_QUIET = """
dv/dt = (V_REST - v) / TAU : volt (unless refractory)
"""
COMMON = dict(threshold="v > V_THRESHOLD", reset="v = V_RESET", method="exact")

with open("circuit_connectivity_v2.json", encoding="utf-8") as fh:
    _data = json.load(fh)
SENSORY_LINKS = [r for r in _data["connections"]["sensory_to_gf"]
                 if r["to_bodyId"] == GF_BODY_ID]
N_SENSORY = len(SENSORY_LINKS)


def run_scenario(ramp_duration_ms, ramp_steepness, label):
    """Run the escape circuit against one approaching object and return plain JSON data.

    ramp_duration_ms: how long the threat takes to grow from invisible to full size.
    ramp_steepness:   where the imaginary impact would happen, as a multiple of the ramp.
                      1.5 means the object would hit the fly 50% past the end of the window,
                      so the curve is still rising when we cut it; values closer to 1.0 put
                      the impact right at the end, which makes the final surge much more
                      violent. Smaller number = nastier, more sudden approach.
    """
    # start_scope() wipes Brian2's memory of previously built neurons. Without it the second
    # scenario would silently re-run the first scenario's objects as well.
    start_scope()
    np.random.seed(0)                  # same population of neurons in every scenario

    # The looming curve: angular size grows like 1/distance, and at constant speed distance
    # shrinks like (impact_time - t). Nearly flat early, exploding at the end - that is what
    # "getting closer" looks like on a retina. A SIMPLIFICATION, but the right shape.
    quiet_ms = 200                     # after the ramp we cut to zero: threat dodged
    impact_ms = ramp_duration_ms * ramp_steepness
    t_ms = np.arange(ramp_duration_ms, dtype=float)
    raw = 1.0 / (impact_ms - t_ms) - 1.0 / impact_ms
    ramp = PEAK_MV * raw / raw[-1]                       # rescale so the peak is PEAK_MV
    looming = TimedArray(np.concatenate([ramp, np.zeros(quiet_ms)]) * mV, dt=1 * ms)

    sensory = NeuronGroup(N_SENSORY, EQS_SENSORY, refractory=SENSORY_REFRACTORY, **COMMON)
    sensory.excitability = np.clip(
        np.random.normal(1.0, EXCITABILITY_SPREAD, N_SENSORY), 0.3, None)
    giant_fiber = NeuronGroup(1, EQS_QUIET, refractory=COMMAND_REFRACTORY, **COMMON)
    motor = NeuronGroup(1, EQS_QUIET, refractory=COMMAND_REFRACTORY, **COMMON)
    for group in (sensory, giant_fiber, motor):
        group.v = V_REST

    # Real connectome weights, one row per sensory cell, exactly as in step 2c.
    sensory_to_gf = Synapses(sensory, giant_fiber, model="w : volt", on_pre="v_post += w")
    sensory_to_gf.connect(i=np.arange(N_SENSORY), j=np.zeros(N_SENSORY, dtype=int))
    sensory_to_gf.w = [r["weight"] * SYNAPSE_TO_MV for r in SENSORY_LINKS]
    gf_to_motor = Synapses(giant_fiber, motor, model="w : volt", on_pre="v_post += w")
    gf_to_motor.connect(i=0, j=0)
    gf_to_motor.w = GF_TO_MOTOR_MV

    spikes_sensory = SpikeMonitor(sensory)
    spikes_gf = SpikeMonitor(giant_fiber)
    spikes_motor = SpikeMonitor(motor)
    run((ramp_duration_ms + quiet_ms) * ms)

    # Brian2 hands back numpy arrays with physical units attached. JSON understands neither,
    # so everything below is converted to plain Python ints and floats before it is saved.
    sensory_spikes = [{"neuron_index": int(i), "time_ms": round(float(t), 1)}
                      for i, t in zip(np.asarray(spikes_sensory.i),
                                      np.asarray(spikes_sensory.t / ms))]
    sensory_spikes.sort(key=lambda s: s["time_ms"])
    gf_times = [round(float(t), 1) for t in np.asarray(spikes_gf.t / ms)]
    motor_times = [round(float(t), 1) for t in np.asarray(spikes_motor.t / ms)]
    return {
        "scenario": label,
        "ramp_duration_ms": int(ramp_duration_ms),
        "sensory_spikes": sensory_spikes,
        # The escape trigger is the FIRST command spike; null means the fly never reacted.
        "giant_fiber_spike_ms": gf_times[0] if gf_times else None,
        "motor_spike_ms": motor_times[0] if motor_times else None,
        "total_sensory_neurons": int(N_SENSORY),
    }, len(gf_times)


# Three threats, same fly. Only the approach speed changes.
SCENARIOS = [("slow_approach", 1500, 1.5),      # a distant object drifting closer
             ("medium_approach", 800, 1.5),     # the run validated in step 2c
             ("fast_approach", 400, 1.5)]       # something lunging at the fly

os.makedirs("exports", exist_ok=True)
results = []
for label, duration, steepness in SCENARIOS:
    data, gf_count = run_scenario(duration, steepness, label)
    path = os.path.join("exports", label + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    results.append((label, duration, data, gf_count, path))
    print("wrote {} ({} sensory spikes)".format(path, len(data["sensory_spikes"])))

print("\n" + "=" * 78)
print("{:<17}{:>9}{:>11}{:>13}{:>12}{:>11}".format(
    "scenario", "ramp ms", "escape?", "trigger ms", "% of ramp", "sensory"))
print("-" * 78)
for label, duration, data, gf_count, _ in results:
    trigger = data["giant_fiber_spike_ms"]
    fired = "YES" if trigger is not None else "no escape"
    when = "{:.1f}".format(trigger) if trigger is not None else "-"
    pct = "{:.0f}%".format(100 * trigger / duration) if trigger is not None else "-"
    print("{:<17}{:>9}{:>11}{:>13}{:>12}{:>11}".format(
        label, duration, fired, when, pct, len(data["sensory_spikes"])))
print("-" * 78)
for label, duration, data, gf_count, _ in results:
    if data["giant_fiber_spike_ms"] is None:
        print("{}: the threat never looked dangerous enough - the pooled visual signal "
              "never crossed the Giant Fiber's threshold before the ramp ended.".format(label))
    else:
        delay = data["motor_spike_ms"] - data["giant_fiber_spike_ms"]
        print("{}: escape triggered {:.1f} ms into the approach, jump muscle {:.1f} ms "
              "later{}.".format(label, data["giant_fiber_spike_ms"], delay,
              "" if gf_count == 1 else
              " (note: {} command spikes fired, only the first is exported)".format(gf_count)))
