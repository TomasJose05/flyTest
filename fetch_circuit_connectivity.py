"""
fetch_circuit_connectivity.py - STEP 1 of the "startle-jump" project.

Step 0 picked a candidate three-layer escape circuit. This script asks the connectome
whether those three layers are ACTUALLY WIRED TOGETHER:

    JO-* (wind_gravity)  ->  DNp01 / Giant Fiber  ->  Tergotr. MN
    "the world moved"        "JUMP, NOW"              the jump muscle

Biology in one paragraph. A synapse is a contact where one neuron dumps chemical onto
another; neuPrint counts them, and that count is the `weight` of a connection. Weight is
roughly "how loud" one neuron shouts at another: weight 2 is a whisper that may well be a
reconstruction artefact, weight 90 is a command. The Giant Fiber is the most studied
neuron in the fly: one huge axon per side, built for speed, that turns a scary stimulus
into a jump in ~5 ms - too fast for the fly to think about it. That is exactly the
"startle" of our Sisyphus loop.

Nothing is simulated here. We only read the wiring diagram, and we check our assumptions
instead of trusting them: if a link is missing, the script says so loudly (step 5).
"""

import json
import os
import sys

# Norton intercepts HTTPS on this machine; use the Windows certificate store.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import pandas as pd
from dotenv import load_dotenv
from neuprint import Client

load_dotenv()
TOKEN = os.environ.get("NEUPRINT_TOKEN")
if not TOKEN:
    sys.exit("NEUPRINT_TOKEN is missing. Copy .env.example to .env and paste your token.")

SERVER, DATASET = "neuprint.janelia.org", "male-cns:v1.0"
client = Client(SERVER, dataset=DATASET, token=TOKEN)

# The three layers, as Cypher filters. Scoped to these neurons only - we never pull the
# whole connectome, just the handful of cells in this circuit.
SENSORY = "n.class = 'mechanosensory' AND n.subclass = 'wind_gravity'"  # Johnston's organ
GIANT_FIBER = "n.type = 'DNp01'"                                        # the Giant Fiber
MOTOR = "n.type = 'Tergotr. MN'"                                        # jump muscle MN?

# Below this total synapse count we treat a link as "not really there". A couple of
# synapses between two cells is within the noise of automated reconstruction; a real
# reflex pathway carries tens to hundreds.
WEAK = 10
warnings = []


def neurons(predicate):
    """The individual cells (bodyId = the ID of one physical neuron), not just the type."""
    return client.fetch_custom(f"""
        MATCH (n:Neuron) WHERE {predicate}
        RETURN n.bodyId AS bodyId, n.type AS type, n.instance AS instance,
               n.consensusNt AS neurotransmitter, n.somaSide AS side
        ORDER BY n.type, n.instance""")


def links(src, dst):
    """Direct synaptic connections src -> dst. The arrow direction is the signal flow:
    (a)-[ConnectsTo]->(b) means a talks, b listens."""
    return client.fetch_custom(f"""
        MATCH (a:Neuron)-[w:ConnectsTo]->(b:Neuron)
        WHERE ({src.replace('n.', 'a.')}) AND ({dst.replace('n.', 'b.')})
        RETURN a.bodyId AS from_bodyId, a.instance AS from_instance,
               b.bodyId AS to_bodyId, b.instance AS to_instance, w.weight AS weight
        ORDER BY w.weight DESC""")


def strongest_partners(upstream, limit=12):
    """Fallback for step 5: who REALLY talks to (or listens to) the Giant Fiber, whatever
    their type. Upstream = the neurons that could trigger the jump; downstream = the ones
    that carry the order out. This is how we discover a missing middle-man."""
    pattern = ("(p:Neuron)-[w:ConnectsTo]->(n:Neuron)" if upstream
               else "(n:Neuron)-[w:ConnectsTo]->(p:Neuron)")
    return client.fetch_custom(f"""
        MATCH {pattern} WHERE {GIANT_FIBER}
        RETURN coalesce(p.type, '(untyped)') AS partner_type,
               coalesce(p.superclass, '') AS superclass, coalesce(p.class, '') AS class,
               sum(w.weight) AS weight, count(*) AS connections
        ORDER BY weight DESC LIMIT {limit}""")


def records(df):
    """DataFrame -> plain JSON (pandas handles the numpy int types for us)."""
    return json.loads(df.to_json(orient="records"))


groups = {"sensory": neurons(SENSORY), "giant_fiber": neurons(GIANT_FIBER),
          "motor": neurons(MOTOR)}
for name, df in groups.items():
    print(f"{name:12s}: {len(df):3d} neurons, {df['type'].nunique()} type(s)")

stages = {"sensory_to_gf": links(SENSORY, GIANT_FIBER),
          "gf_to_motor": links(GIANT_FIBER, MOTOR)}
fallback, broken = {}, []

for stage, df in stages.items():
    total = int(df["weight"].sum()) if len(df) else 0
    print(f"\n{stage}: {len(df)} connection(s), total weight {total}")
    if len(df):
        print(df.to_string(index=False))
    if total < WEAK:                                   # step 5: never fail silently
        broken.append(stage)
        warnings.append(f"{stage}: only {len(df)} connection(s) / total weight {total} - "
                        f"below the {WEAK} threshold, treat this link as ABSENT.")

if broken:
    # A link is missing, so our guess about the wiring was wrong somewhere. Ask the
    # connectome who the Giant Fiber REALLY talks to, ignoring our assumptions.
    print(f"\n!! NO REAL CONNECTION at: {', '.join(broken)}")
    print("   Strongest actual partners of DNp01 - the missing hop hides here:")
    for side, up in (("upstream", True), ("downstream", False)):
        partners = strongest_partners(up)
        fallback[side] = records(partners)
        print(f"   -- {side} --")
        print(partners.to_string(index=False))
    warnings.append("An intermediate neuron is probably needed: see fallback_partners.")

out = {"dataset": DATASET,
       "neurons": {k: records(v) for k, v in groups.items()},
       "connections": {k: records(v) for k, v in stages.items()},
       "fallback_partners": fallback, "warnings": warnings}
with open("circuit_connectivity.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)

print("\n" + "=" * 70)
for stage, df in stages.items():
    total = int(df["weight"].sum()) if len(df) else 0
    print(f"{stage:15s} {len(df):3d} connection(s), weight {total:5d}"
          f"  -> {'OK' if total >= WEAK else 'BROKEN, needs an extra hop'}")
print("Circuit intact end to end." if not broken else
      f"Circuit NOT intact: {len(broken)} broken link(s), {len(warnings)} warnings in the JSON.")
print("Wrote circuit_connectivity.json")
