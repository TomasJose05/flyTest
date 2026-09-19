# flyTest

Driving a simulated fly with a **real connectome**: the MaleCNS v1.0 reconstruction of the
*Drosophila* nervous system, queried live through [neuPrint](https://neuprint.janelia.org).

Target behaviour: the **escape reflex**. Something looms, the fly jumps. Modelled as a
Sisyphus loop — startle, jump up, gravity pulls it down, startle again.

## The circuit

Every neuron and every connection weight below comes from the connectome, not from
guesswork. The chain was validated against the data before a single neuron was simulated.

```
LC4_L + LPLC2_L   ->   DNp01_L (Giant Fiber)   ->   TTMn_L   ->   jump
165 looming            1 command neuron             1 motor neuron
detector neurons       (bodyId 10010)               (bodyId 804642)
```

## Steps

| Step | What it does | Output |
|---|---|---|
| 0 | `explore_circuit.py` — is there a small, identifiable circuit at all? | [`circuit_candidates.md`](circuit_candidates.md) |
| 1 | `fetch_circuit_connectivity.py` — test the first hypothesis | [`circuit_connectivity.json`](circuit_connectivity.json) |
| 1b | `fetch_corrected_circuit.py` — the corrected circuit | [`circuit_connectivity_v2.json`](circuit_connectivity_v2.json) |
| 2 | `simulate_circuit.py` — spiking simulation in Brian2 | `escape_circuit_test.png` |
| 3 | `export_scenarios.py` — same circuit, three approach speeds, exported for the frontend | `exports/*.json` |

Step 1 is kept on purpose: it is the step where the connectome rejected the original guess.
The gravity-sensing neurons barely touch the Giant Fiber (weights of 2 and 4, i.e. noise),
and the motor neuron picked from its name turned out to be a walking neuron, not the jump
one. The real trigger is visual looming, and the real output is TTMn.

## Web viewer

`fly-escape-viewer/` is a Vite + React + TypeScript front end that replays the exported
spike times. It runs no neuroscience: it fetches `public/data/*.json` and drives every
flash off the recorded millisecond timestamps.

```bash
cd fly-escape-viewer
npm install
npm run dev
```

Pick a scenario, press Play, and the clock runs 1 ms of simulation per 1 ms of real time.
Refresh the copies in `fly-escape-viewer/public/data/` whenever `export_scenarios.py` is
re-run.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and paste your neuPrint token (Account -> Auth Token on the
website). `.env` is gitignored, so the token never leaves the machine.

```bash
python explore_circuit.py          # step 0
python fetch_corrected_circuit.py  # step 1b, refreshes the connectivity JSON
python simulate_circuit.py         # step 2, runs the simulation and writes the raster plot
python export_scenarios.py         # step 3, writes exports/*.json for the web frontend
```

### Windows / Norton note

Norton intercepts HTTPS on this machine, so `pip` and `requests` fail with
`CERTIFICATE_VERIFY_FAILED`. The scripts call `truststore.inject_into_ssl()` to use the
Windows certificate store instead. If `pip install` fails, export that store to a PEM file
and point `PIP_CERT` at it.
