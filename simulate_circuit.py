"""
simulate_circuit.py - STEP 2: the circuit makes a decision.

The wiring comes from the connectome (steps 0-1b) and never changes here:

    LC4_L + LPLC2_L  ->  DNp01_L (Giant Fiber)  ->  TTMn_L  ->  jump
    165 visual cells     1 command cell            1 muscle driver

WHAT A SPIKING SIMULATION IS. A neuron is a leaky bucket of voltage. Other neurons pour
voltage in; the bucket leaks back toward its resting level all the time. If the level
reaches a threshold the neuron "spikes" (fires a pulse to everyone downstream) and the
bucket empties back to rest. That is the whole model: Leaky Integrate-and-Fire (LIF).
BRIAN2 is a library where you describe that with a one-line equation and it runs the clock
for you. Its party trick is UNITS: write 10*ms and -70*mV and it refuses to add them.

WHAT CHANGED. The stimulus now grows like an approaching object instead of switching on and
off, every sensory cell is slightly different from its neighbours, and the command stage has
a long refractory period so it fires ONCE per threat. None of it touches the wiring.
"""

import json
import numpy as np
import matplotlib
matplotlib.use("Agg")                  # draw into a file, not into a window
import matplotlib.pyplot as plt
from brian2 import (NeuronGroup, Synapses, SpikeMonitor, TimedArray, run, prefs,
                    defaultclock, mV, ms)

prefs.codegen.target = "numpy"         # tiny circuit: no C++ compiler needed
defaultclock.dt = 0.1 * ms             # the simulation advances in steps of 0.1 ms
np.random.seed(0)                      # same "random" neurons on every run, so results repeat

GF_BODY_ID, TTMN_BODY_ID = 10010, 804642       # left hemisphere only, from step 1b

# ---------------------------------------------------------------- 1. load the real wiring
with open("circuit_connectivity_v2.json", encoding="utf-8") as fh:
    data = json.load(fh)

sensory_links = [r for r in data["connections"]["sensory_to_gf"]
                 if r["to_bodyId"] == GF_BODY_ID]       # each sensory cell contacts one GF
gf_link = [r for r in data["connections"]["gf_to_motor"]
           if r["from_bodyId"] == GF_BODY_ID and r["to_bodyId"] == TTMN_BODY_ID][0]
sensory_types = [r["from_type"] for r in sensory_links]
n_sensory = len(sensory_links)
print("Left-hemisphere sensory subset: {} neurons ({} LC4_L + {} LPLC2_L)".format(
    n_sensory, sensory_types.count("LC4"), sensory_types.count("LPLC2")))

# ------------------------------------------------------- 2. the looming stimulus, as a ramp
# An object coming at you does not grow steadily on your retina: it creeps for a long time,
# then explodes in size at the end. Its angular size goes like 1/distance, and at constant
# speed the distance shrinks like (T_collision - t), so 1/(T_collision - t) is the cheapest
# honest stand-in for "getting closer". A SIMPLIFICATION: a real looming model tracks angular
# size and its rate of change on a curved eye. We only need the shape: slow, then sudden.
RAMP_MS, QUIET_MS, T_COLLISION_MS = 800, 200, 1200     # virtual impact would be at 1200 ms
PEAK_MV = 30                           # current at the end of the ramp, in mV

t_ms = np.arange(RAMP_MS, dtype=float)
raw = 1.0 / (T_COLLISION_MS - t_ms) - 1.0 / T_COLLISION_MS   # 0 at t=0, accelerating after
ramp = PEAK_MV * raw / raw[-1]                               # rescale so the peak is PEAK_MV
# Then cut to zero: threat dodged. TimedArray = Brian2's "value at time t", one entry per ms.
looming = TimedArray(np.concatenate([ramp, np.zeros(QUIET_MS)]) * mV, dt=1 * ms)
# ------------------------------------------------------------- 3. the neurons themselves
V_REST, V_THRESHOLD, V_RESET = -70 * mV, -50 * mV, -70 * mV
TAU = 10 * ms                          # how fast the bucket leaks back toward rest
# REFRACTORY = dead time right after a spike. Firing dumps the ions the neuron had stacked
# up, and until the pumps restore them it cannot fire again: input arrives and is ignored,
# however strong. Brian2 freezes the voltage at reset and runs no threshold check meanwhile.
SENSORY_REFRACTORY = 5 * ms            # sensory cells legitimately keep reporting: stays short
# The command stage gets a far longer one. The pooled drive stays above threshold for the
# last ~165 ms of the ramp (636-800 ms), so the dead time has to outlast THAT window for the
# Giant Fiber to fire only once per threat. Measured: 100 ms and 150 ms both let a second
# spike through; 175 ms is the first value that gives a single clean trigger.
COMMAND_REFRACTORY = 175 * ms

# LIF, term by term: v is the level in the bucket; (V_REST - v) is the leak pulling it back
# down; the stimulus pours voltage in; / TAU sets how fast; ": volt" is Brian2's unit
# declaration; "(unless refractory)" freezes v during the silence after a spike.
# BIOLOGICAL VARIABILITY: each sensory neuron gets its own "excitability", a multiplier on
# how hard the same stimulus hits it. Real neurons are not clones - they differ in size, in
# receptors, in their own membrane noise - so they never cross threshold on the same tick.
# That messiness is the whole reason the circuit is a funnel: no single detector is
# trustworthy, so the Giant Fiber POOLS 165 unreliable, out-of-step opinions into one call.
EQS_SENSORY = """
dv/dt = (V_REST - v + looming(t) * excitability) / TAU : volt (unless refractory)
excitability : 1
"""
EQS_QUIET = """
dv/dt = (V_REST - v) / TAU : volt (unless refractory)
"""                                    # GF and motor are driven only by their synapses
COMMON = dict(threshold="v > V_THRESHOLD", reset="v = V_RESET", method="exact")
CMD = dict(refractory=COMMAND_REFRACTORY, **COMMON)      # only DNp01 and TTMn get the long one
sensory = NeuronGroup(n_sensory, EQS_SENSORY, name="sensory",
                      refractory=SENSORY_REFRACTORY, **COMMON)
sensory.excitability = np.clip(np.random.normal(1.0, 0.15, n_sensory), 0.3, None)
giant_fiber = NeuronGroup(1, EQS_QUIET, name="giant_fiber", **CMD)
motor = NeuronGroup(1, EQS_QUIET, name="motor", **CMD)
for group in (sensory, giant_fiber, motor):
    group.v = V_REST                   # everyone starts at rest, bucket empty
# --------------------------------------------------------------------- 4. the connections
# MODELING DECISION (the connectome cannot tell us this). A synapse count is not a voltage,
# so we choose what one synapse is worth in mV. The gap from rest to threshold is 20 mV, so
# at 0.05 mV per synapse an average connection (~39 synapses) delivers ~2 mV: about ten
# sensory neurons must agree within one time constant to set the Giant Fiber off.
SYNAPSE_TO_MV = 0.05 * mV
sensory_to_gf = Synapses(sensory, giant_fiber, model="w : volt", on_pre="v_post += w")
sensory_to_gf.connect(i=np.arange(n_sensory), j=np.zeros(n_sensory, dtype=int))
sensory_to_gf.w = [r["weight"] * SYNAPSE_TO_MV for r in sensory_links]
# THE GIANT FIBER -> TTMn WEIGHT IS SET BY HAND, ON PURPOSE.
# neuPrint counts 20 chemical synapses here, far fewer than the sensory connections, which
# would make the last step of an escape reflex its weakest link. That is wrong: in the real
# fly this junction is largely ELECTRICAL - a gap junction, a direct hole between the cells -
# and a connectome built from chemical synapse counts cannot see it at all. Physiology shows
# it is one-to-one and near failure-proof: one GF spike, one motor spike, ~1 ms later. Hence
# 25 mV, just over the 20 mV needed to fire: "this connection does not fail", not a count.
GF_TO_MOTOR_MV = 25 * mV
gf_to_motor = Synapses(giant_fiber, motor, model="w : volt", on_pre="v_post += w")
gf_to_motor.connect(i=0, j=0)
gf_to_motor.w = GF_TO_MOTOR_MV
# --------------------------------------------------------------------------- 5. run it
# A SpikeMonitor records which neuron fired and when. Each needs its own plain variable:
# run() builds the network from objects it sees by name, so one hidden in a dict is ignored.
spikes_sensory = SpikeMonitor(sensory)
spikes_gf = SpikeMonitor(giant_fiber)
spikes_motor = SpikeMonitor(motor)
run((RAMP_MS + QUIET_MS) * ms)
# ------------------------------------------------------------------------- 6. raster plot
fig, ax = plt.subplots(figsize=(11, 5))
for label, mon, offset, colour in [("sensory (LC4_L + LPLC2_L)", spikes_sensory, 0, "#4c72b0"),
        ("giant fiber (DNp01_L)", spikes_gf, n_sensory + 6, "#dd8452"),
        ("motor (TTMn_L)", spikes_motor, n_sensory + 14, "#55a868")]:
    ax.plot(mon.t / ms, np.asarray(mon.i) + offset, "|", color=colour, markersize=5, label=label)
ax.set_xlim(0, RAMP_MS + QUIET_MS)
ax.set_xlabel("time (ms)"), ax.set_ylabel("neuron")
ax.set_title("Escape circuit: looming ramp 0-800 ms, single-shot trigger at threshold")
ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
# Second y-axis: the stimulus itself, so you can see WHERE on the ramp the decision happened.
ax2 = ax.twinx()
ax2.plot(np.arange(RAMP_MS + QUIET_MS), np.concatenate([ramp, np.zeros(QUIET_MS)]),
         color="#c44e52", linewidth=1.6, alpha=0.7)
ax2.set_ylabel("looming drive (mV)", color="#c44e52")
fig.savefig("escape_circuit_test.png", dpi=140, bbox_inches="tight")
# ------------------------------------------------------------------------ 7. did it work?
# spike_trains() lists, per neuron, when it fired; we want each cell's FIRST spike only.
firsts = np.array([float(t[0] / ms) for t in spikes_sensory.spike_trains().values() if len(t)])
gf_t = np.asarray(spikes_gf.t / ms, dtype=float)
motor_t = np.asarray(spikes_motor.t / ms, dtype=float)

print("\n" + "=" * 66)
print("1. ASYNCHRONY: {}/{} sensory neurons fired, first spikes spread from {:.1f} to {:.1f}"
      " ms (window {:.0f} ms, std {:.1f} ms).".format(len(firsts), n_sensory, firsts.min(),
      firsts.max(), firsts.max() - firsts.min(), firsts.std()))
if len(gf_t):
    pct = 100 * gf_t[0] / RAMP_MS
    print("2. DECISION POINT: Giant Fiber first fired at {:.1f} ms = {:.0f}% into the ramp "
          "({} in the approach).".format(gf_t[0], pct,
          "early" if pct < 33 else "mid" if pct < 66 else "late"))
    verdict = ("a single clean escape trigger" if len(gf_t) == 1 else
               "close enough to single-shot" if len(gf_t) <= 2 else
               "still a burst - raise COMMAND_REFRACTORY above {:.0f} ms".format(
                   gf_t[-1] - gf_t[0] + 10))
    print("3. DECISIVENESS: DNp01 fired {} time(s) at {} ms - {}.".format(
        len(gf_t), ", ".join("{:.1f}".format(t) for t in gf_t[:5]), verdict))
else:
    print("2-3. The Giant Fiber never fired: pooled input never crossed threshold.")
print("4. MOTOR OUTPUT: TTMn fired {} time(s) at {} ms{}.".format(
    len(motor_t), ", ".join("{:.1f}".format(t) for t in motor_t[:5]),
    ", first {:.1f} ms after the Giant Fiber".format(motor_t[0] - gf_t[0])
    if len(motor_t) and len(gf_t) else ""))
print("Wrote escape_circuit_test.png")
