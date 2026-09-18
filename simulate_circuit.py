"""
simulate_circuit.py - STEP 2: the circuit finally does something.

We have the wiring (steps 0-1b). Now we turn it into neurons that actually fire, and watch
whether a simulated "something is coming at me" makes the fly's jump command go off.

    LC4_L + LPLC2_L  ->  DNp01_L (Giant Fiber)  ->  TTMn_L  ->  jump
    165 visual cells     1 command cell            1 muscle driver

WHAT A SPIKING SIMULATION IS, if you have never seen one. A neuron is a leaky bucket of
voltage. Signals from other neurons pour voltage in; the bucket leaks back toward its
resting level all the time. If the level ever reaches a threshold, the neuron "spikes"
(fires a pulse to everyone downstream) and its bucket is instantly emptied back to rest.
That is the whole model, and it is called Leaky Integrate-and-Fire (LIF): integrate the
input, leak, fire, reset.

WHAT BRIAN2 IS. A library where you describe a neuron with a one-line equation and it runs
the clock for you. Its party trick is UNITS: you write 10*ms and -70*mV, and it refuses to
run if you ever add a voltage to a time. You never write the time loop yourself.
"""

import json
import numpy as np
import matplotlib
matplotlib.use("Agg")                  # draw into a file, not into a window
import matplotlib.pyplot as plt
from brian2 import (NeuronGroup, Synapses, SpikeMonitor, run, prefs, defaultclock, mV, ms)

# Brian2 can compile C++ for speed. This circuit is tiny, so we use plain numpy and avoid
# needing a compiler installed on Windows.
prefs.codegen.target = "numpy"
defaultclock.dt = 0.1 * ms             # the simulation advances in steps of 0.1 ms

GF_BODY_ID, TTMN_BODY_ID = 10010, 804642       # left hemisphere only, from step 1b

# ---------------------------------------------------------------- 1. load the real wiring
with open("circuit_connectivity_v2.json", encoding="utf-8") as fh:
    data = json.load(fh)

# Keep only the connections landing on the LEFT Giant Fiber. Each sensory neuron contacts
# exactly one Giant Fiber, so this cleanly selects the left-hemisphere subset.
sensory_links = [r for r in data["connections"]["sensory_to_gf"]
                 if r["to_bodyId"] == GF_BODY_ID]
gf_link = [r for r in data["connections"]["gf_to_motor"]
           if r["from_bodyId"] == GF_BODY_ID and r["to_bodyId"] == TTMN_BODY_ID][0]

sensory_types = [r["from_type"] for r in sensory_links]     # one row per sensory neuron
n_sensory = len(sensory_links)
n_lc4 = sensory_types.count("LC4")
print("Left-hemisphere sensory subset: {} neurons ({} LC4_L + {} LPLC2_L)".format(
    n_sensory, n_lc4, sensory_types.count("LPLC2")))
print("Raw synapse weights: sensory->GF {}-{}, GF->TTMn {}".format(
    min(r["weight"] for r in sensory_links),
    max(r["weight"] for r in sensory_links), gf_link["weight"]))

# ------------------------------------------------------------- 2. the neurons themselves
V_REST, V_THRESHOLD, V_RESET = -70 * mV, -50 * mV, -70 * mV
TAU = 10 * ms                          # how fast the bucket leaks back toward rest
REFRACTORY = 5 * ms                    # forced silence right after a spike

# The LIF equation, term by term:
#   v            = membrane potential, the level in the bucket
#   (V_REST - v) = the leak: when v sits above rest this is negative and drags it back down
#   I_stim       = injected input, our stand-in for "the eye is being stimulated"
#   / TAU        = how fast all of that happens (a big tau means a sluggish neuron)
#   : volt       = Brian2 unit declaration - v is measured in volts
# "(unless refractory)" freezes the voltage during the silent window after a spike.
EQS = """
dv/dt = (V_REST - v + I_stim) / TAU : volt (unless refractory)
I_stim : volt
"""
COMMON = dict(model=EQS, threshold="v > V_THRESHOLD", reset="v = V_RESET",
              refractory=REFRACTORY, method="exact")

sensory = NeuronGroup(n_sensory, name="sensory", **COMMON)
giant_fiber = NeuronGroup(1, name="giant_fiber", **COMMON)
motor = NeuronGroup(1, name="motor", **COMMON)
for group in (sensory, giant_fiber, motor):
    group.v = V_REST                   # everyone starts at rest, bucket empty

# --------------------------------------------------------------------- 3. the connections
# MODELING DECISION (the connectome does not tell us this one). A synapse count is not a
# voltage, so we have to choose what one synapse is worth in mV. The gap from rest to
# threshold is 20 mV, so at 0.05 mV per synapse an average connection (~39 synapses)
# delivers ~2 mV: roughly ten sensory neurons must agree within one time constant to set
# the Giant Fiber off. That matches what the real cell does - it ignores single detectors
# and fires when a large part of the visual field shouts "incoming" at once.
SYNAPSE_TO_MV = 0.05 * mV

sensory_to_gf = Synapses(sensory, giant_fiber, model="w : volt", on_pre="v_post += w")
sensory_to_gf.connect(i=np.arange(n_sensory), j=np.zeros(n_sensory, dtype=int))
sensory_to_gf.w = [r["weight"] * SYNAPSE_TO_MV for r in sensory_links]

# THE GIANT FIBER -> TTMn WEIGHT IS SET BY HAND, ON PURPOSE.
# neuPrint counts 20 chemical synapses here, far fewer than the sensory connections. Taken
# literally that would make the last step of an escape reflex its weakest link, which is
# wrong. In the real fly this junction is largely ELECTRICAL - a gap junction, a direct
# hole between the two cells - and a connectome built from chemical synapse counts cannot
# see that at all. Electrophysiology shows the connection is effectively one-to-one and
# near failure-proof: one Giant Fiber spike, one motor spike, about 1 ms later. So we give
# it 25 mV, just over the 20 mV needed to fire, encoding "this connection does not fail"
# rather than the raw count of 20.
GF_TO_MOTOR_MV = 25 * mV
gf_to_motor = Synapses(giant_fiber, motor, model="w : volt", on_pre="v_post += w")
gf_to_motor.connect(i=0, j=0)
gf_to_motor.w = GF_TO_MOTOR_MV

# ------------------------------------------------------------------------- 4-5. run it
# A SpikeMonitor is a tape recorder: it stores which neuron fired and at what time.
# Each one needs its own plain variable: run() builds the network out of the Brian objects
# it can see by name here, so a monitor that only exists inside a dict is silently left out
# of the simulation and records nothing.
spikes_sensory = SpikeMonitor(sensory)
spikes_gf = SpikeMonitor(giant_fiber)
spikes_motor = SpikeMonitor(motor)
monitors = {"sensory": spikes_sensory, "giant_fiber": spikes_gf, "motor": spikes_motor}

# The looming stimulus: for 500 ms we inject enough current into every visual neuron to
# push it past threshold repeatedly - "an object is growing in my field of view". Then we
# switch it off and watch the circuit fall silent again.
STIMULUS_MV, STIM_MS, QUIET_MS = 25 * mV, 500 * ms, 300 * ms
sensory.I_stim = STIMULUS_MV
run(STIM_MS)
sensory.I_stim = 0 * mV
run(QUIET_MS)

# -------------------------------------------------------------------------- 6. raster plot
# One tick per spike: x = when it fired, y = which neuron. The bottom band is the 165
# sensory cells, then the Giant Fiber, then the motor neuron on top.
fig, ax = plt.subplots(figsize=(11, 5))
rows = [("sensory (LC4_L + LPLC2_L)", monitors["sensory"], 0, "#4c72b0"),
        ("giant fiber (DNp01_L)", monitors["giant_fiber"], n_sensory + 3, "#dd8452"),
        ("motor (TTMn_L)", monitors["motor"], n_sensory + 7, "#55a868")]
for label, mon, offset, colour in rows:
    ax.plot(mon.t / ms, np.asarray(mon.i) + offset, "|", color=colour, markersize=4,
            label=label)
ax.axvspan(0, STIM_MS / ms, color="grey", alpha=0.12)
ax.text(STIM_MS / ms / 2, n_sensory + 11, "looming stimulus ON", ha="center", fontsize=9)
ax.set_xlim(0, float((STIM_MS + QUIET_MS) / ms))   # show the silent tail too
ax.text(float(STIM_MS / ms) + 150, n_sensory + 11, "stimulus OFF", ha="center", fontsize=9)
ax.set_xlabel("time (ms)")
ax.set_ylabel("neuron")
ax.set_title("Escape circuit: LC4/LPLC2_L -> Giant Fiber -> TTMn_L")
ax.legend(loc="lower right", fontsize=9, framealpha=0.95)
fig.subplots_adjust(top=0.90)
fig.savefig("escape_circuit_test.png", dpi=140, bbox_inches="tight")

# ------------------------------------------------------------------------ 7. did it work?
print("\n" + "=" * 62)
chain = True
for label, mon in (("sensory (165 cells)", monitors["sensory"]),
                   ("giant fiber DNp01_L", monitors["giant_fiber"]),
                   ("motor TTMn_L", monitors["motor"])):
    n_spikes = len(mon.t)
    chain = chain and n_spikes > 0
    first = "{:.1f} ms".format(float(min(mon.t / ms))) if n_spikes else "NEVER FIRED"
    print("{:22s} {:6d} spikes, first at {}".format(label, n_spikes, first))
print("Chain reaction complete: stimulus -> vision -> Giant Fiber -> jump muscle."
      if chain else "CHAIN BROKEN: some layer never fired.")
print("Wrote escape_circuit_test.png")
