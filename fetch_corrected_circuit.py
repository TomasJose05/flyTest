"""
fetch_corrected_circuit.py - STEP 1b: the circuit, corrected by the data.

Step 1 tested a guess and the connectome said no, twice. The trigger is not gravity but
VISION: LC4 and LPLC2 are "looming detectors", firing when something grows fast in the
visual field - what an approaching predator (or a hand) looks like - and they are the
Giant Fiber's loudest input by an order of magnitude. And the jump muscle's motor neuron
is TTMn, not "Tergotr. MN" (that one was an ordinary walking leg motor neuron).

So the corrected escape reflex, the one v1 of the simulation will use:

    LC4 + LPLC2  ->  DNp01 (Giant Fiber)  ->  TTMn  ->  jump
    "it's coming"    "JUMP, NOW"              the muscle that extends the leg

Weight = number of synapses between two cells = how loud one shouts at the other.
Still nothing is simulated: we only read the wiring diagram.
"""

import json, os, sys

# Norton intercepts HTTPS on this machine; use the Windows certificate store.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass
from dotenv import load_dotenv
from neuprint import Client
load_dotenv()
TOKEN = os.environ.get("NEUPRINT_TOKEN")
if not TOKEN:
    sys.exit("NEUPRINT_TOKEN is missing. Copy .env.example to .env and paste your token.")

SERVER, DATASET = "neuprint.janelia.org", "male-cns:v1.0"
client = Client(SERVER, dataset=DATASET, token=TOKEN)

SENSORY = ["LC4", "LPLC2"]        # visual looming detectors: the trigger
GIANT_FIBER = ["DNp01"]           # the command neuron, one per side
MOTOR = ["TTMn"]                  # the jump motor neuron
SECONDARY = ["GFC2", "GFC3", "GFC4"]   # optional branch, NOT used in v1
KNOWN_GF_BODY_IDS = [10001, 10010]     # from step 1, re-checked below
WEAK = 10                              # under this total weight a link is noise, not wiring

def neurons(types):
    """The individual cells of these types. bodyId identifies one physical neuron."""
    return client.fetch_custom(f"""
        MATCH (n:Neuron) WHERE n.type IN {json.dumps(types)}
        RETURN n.bodyId AS bodyId, n.type AS type, n.instance AS instance,
               n.consensusNt AS neurotransmitter
        ORDER BY n.type, n.instance""")

def links(src_types, dst_types):
    """Every individual connection src -> dst, one row per pair of cells (not a summary).
    (a)-[ConnectsTo]->(b) means a talks and b listens, so the arrow is the signal flow."""
    return client.fetch_custom(f"""
        MATCH (a:Neuron)-[w:ConnectsTo]->(b:Neuron)
        WHERE a.type IN {json.dumps(src_types)} AND b.type IN {json.dumps(dst_types)}
        RETURN a.bodyId AS from_bodyId, a.type AS from_type, a.instance AS from_instance,
               b.bodyId AS to_bodyId, b.type AS to_type, b.instance AS to_instance,
               w.weight AS weight
        ORDER BY w.weight DESC""")

def records(df):
    return json.loads(df.to_json(orient="records"))

groups = {"sensory": neurons(SENSORY), "giant_fiber": neurons(GIANT_FIBER),
          "motor": neurons(MOTOR)}
for name, df in groups.items():
    print(f"{name:12s}: {len(df):4d} neurons ({', '.join(sorted(df['type'].unique()))})")

# Sanity check that we are pointing at the same two Giant Fibers as last time.
found_ids = sorted(groups["giant_fiber"]["bodyId"].tolist())
print(f"Giant Fiber bodyIds {found_ids} "
      f"{'match' if found_ids == sorted(KNOWN_GF_BODY_IDS) else 'DO NOT MATCH'} step 1.\n")

stages = {"sensory_to_gf": links(SENSORY, GIANT_FIBER),
          "gf_to_motor": links(GIANT_FIBER, MOTOR),
          # Saved for later: the GF also drives GFC2/3/4, interneurons that spread the
          # escape signal further into the nerve cord. Real, but out of scope for v1.
          "gf_to_secondary_interneurons": links(GIANT_FIBER, SECONDARY)}

out = {"dataset": DATASET,
       "neurons": {k: records(v) for k, v in groups.items()},
       "connections": {k: records(v) for k, v in stages.items()},
       "notes": {"gf_to_secondary_interneurons":
                 "optional secondary pathway, not used in v1"}}
with open("circuit_connectivity_v2.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)

print("=" * 64)
for stage in ("sensory_to_gf", "gf_to_motor"):        # the two stages v1 depends on
    df = stages[stage]
    total = int(df["weight"].sum()) if len(df) else 0
    print(f"{stage:14s} {len(df):4d} connections, total weight {total:6d}"
          f"  -> {'OK' if total >= WEAK else 'STILL WEAK - flag it'}")
sec = stages["gf_to_secondary_interneurons"]
print(f"{'(secondary)':14s} {len(sec):4d} connections, total weight "
      f"{int(sec['weight'].sum()) if len(sec) else 0:6d}  -> stored, unused in v1")
print("Wrote circuit_connectivity_v2.json")
