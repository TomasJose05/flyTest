"""
explore_circuit.py - STEP 0 (exploration only) of the "startle-induced climbing" project.

Goal: find out whether the MaleCNS v1.0 connectome contains a SMALL, IDENTIFIABLE circuit
for negative geotaxis (after being knocked down, the fly climbs upward).
This builds no simulation and downloads no connectivity: neuron metadata only.

The circuit as three links (same shape as a web pipeline: input -> controller -> output):

  1. SENSORS (mechanosensory): how the fly feels the knock and where "down" is.
     Bristles = touch; campaniform sensilla = load/force on the leg; chordotonal organ =
     stretch and vibration; Johnston's organ (wind_gravity) = the antenna, which senses
     gravity and wind. This is the INPUT of the reflex.
  2. DESCENDING NEURONS (DNs): ~1300 neurons running from the brain down to the ventral
     nerve cord. They are the bottleneck of the whole system: every motor command passes
     through them. This is the COMMAND layer.
  3. LEG MOTOR NEURONS (VNC): the final output that contracts the muscles of the 6 legs.

Why this matters: if link 2 turns out to be bilateral pairs of 2 neurons, the circuit is
simulable. If it were thousands, it would not be.
"""

import os
import sys

# Norton intercepts HTTPS on this machine and breaks certificate verification.
# truststore makes Python use the Windows certificate store (which does contain Norton's
# CA) instead of certifi's bundle. Harmless on other machines.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import pandas as pd
from dotenv import load_dotenv
from neuprint import Client

load_dotenv()                                  # reads the .env sitting next to this script
TOKEN = os.environ.get("NEUPRINT_TOKEN")       # never hardcoded: comes from the environment
if not TOKEN:
    sys.exit("NEUPRINT_TOKEN is missing. Copy .env.example to .env and paste your token.")

SERVER, DATASET = "neuprint.janelia.org", "male-cns:v1.0"
client = Client(SERVER, dataset=DATASET, token=TOKEN)

# Print the available datasets first, to confirm the EXACT dataset name: neuPrint keeps
# versions side by side, and "male-cns:v0.9" and "male-cns:v1.0" are different databases.
print(f"Datasets available on {SERVER}:")
for name in sorted(client.fetch_datasets()):
    print(f"   {'->' if name == DATASET else '  '} {name}")
print(f"\nUsing: {DATASET}\n")

# Cypher is Neo4j's SQL. In neuPrint every neuron is a node labelled :Neuron (:Neuron means
# reconstructed and human-proofread; there are millions of fragments WITHOUT that label and
# they are deliberately left out). We group by n.type = the "cell type": the name of the
# class of neuron, not of the individual cell. A type usually has 2 copies, one per brain
# hemisphere. Counting TYPES rather than neurons is what tells you if a circuit is tractable.
# We only ask for metadata (name, class, neurotransmitter, synapse counts) - no wiring table.
QUERY = """
MATCH (n:Neuron) WHERE {predicate}
RETURN coalesce(n.type, '(untyped)')           AS type,
       count(*)                                AS neurons,
       collect(DISTINCT n.class)[0..2]         AS class,
       collect(DISTINCT n.subclass)[0..3]      AS subclass,
       collect(DISTINCT n.somaNeuromere)[0..3] AS neuromere,
       collect(DISTINCT n.consensusNt)[0..2]   AS neurotransmitter,
       sum(n.pre) AS out_synapses, sum(n.post) AS in_synapses
ORDER BY neurons ASC, type ASC
"""

# Each category = (title, what I am asking in plain language, Cypher filter).
CATEGORIES = [
    ("A. Mechanosensory input (the knock)",
     "Neurons that detect touch, load on the leg, vibration and gravity. Filter: class "
     "starts with 'mechanosensory' and subclass is one of the sense organs classically "
     "involved in the righting reflex.",
     "n.class STARTS WITH 'mechanosensory' AND n.subclass IN "
     "['campaniform sensilla','chordotonal organ','hair plate','wind_gravity',"
     "'leg bristle','mechanosensory bristle','leg']"),

    ("B. Descending neurons (the command)",
     "Every DN: brain -> VNC. They are the command layer that decides walk/climb. "
     "Filter: superclass starts with 'descending'.",
     "n.superclass STARTS WITH 'descending'"),

    ("C. Leg motor neurons in the VNC (the output)",
     "VNC motor neurons whose subclass is fl/ml/hl = front/middle/hind leg. The last link: "
     "they fire and the muscle contracts.",
     "n.superclass = 'vnc_motor' AND n.subclass IN ['fl','ml','hl']"),

    ("D. Shortcut: DNs named in the escape / walking literature",
     "A short, explicit list of already-characterised DNs: DNp01 is the Giant Fiber "
     "(escape jump after a startle), DNa01/DNa02 steer while walking, MDN drives backward "
     "walking, DNp09 freezes. Useful to anchor the model to something known.",
     "n.type IN ['DNp01','DNa01','DNa02','DNa10','DNb02','DNg13','DNg100',"
     "'MDN','DNp07','DNp09','DNp10']"),
]


def as_markdown(df: pd.DataFrame) -> str:
    """DataFrame -> markdown table (avoids depending on 'tabulate')."""
    clean = df.map(lambda v: ", ".join(map(str, v)) if isinstance(v, list) else str(v))
    head = "| " + " | ".join(clean.columns) + " |\n|" + "---|" * len(clean.columns) + "\n"
    return head + "".join("| " + " | ".join(r) + " |\n" for r in clean.values)


report = [f"# Circuit candidates - negative geotaxis\n",
          f"Dataset: `{DATASET}` ({SERVER}) | metadata only, no connectivity.\n"]

for title, explanation, predicate in CATEGORIES:
    df = client.fetch_custom(QUERY.format(predicate=predicate))
    print(f"===== {title} =====")
    print(f"{len(df)} cell types, {df['neurons'].sum()} neurons in total")
    print(df.head(12).to_string(index=False), "\n")   # console: just a preview
    report += [f"\n## {title}\n", f"_{explanation}_\n",
               f"\n**{len(df)} cell types / {df['neurons'].sum()} neurons.** "
               f"Sorted fewest neurons first (top = most tractable).\n\n",
               as_markdown(df)]                       # the .md file: the full table

with open("circuit_candidates.md", "w", encoding="utf-8") as fh:
    fh.write("".join(report))
print("Wrote circuit_candidates.md")
