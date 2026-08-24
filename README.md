# navantia_modelling

Vibration-environment → pointing-jitter modelling for the Phase 1 optical
terminal (Navantia–UWA Maritime FSOC, **WBS 1.3**). This repo implements the
chain worked out in `vibration_jitter_interface_note.md`.

## What this computes

The disturbance chain for a servoed gimbal (pathway 3):

```
base accel a(f)  ->  disturbance torque tau = m*d*a(f)
                 ->  loop rejects what's in-band (sensitivity S)
                 ->  residual angle = pointing jitter
```

The vibration standard is a disturbance **input**, not a jitter output. Jitter
is that input operated on by the tracking loop's sensitivity function — which
the standard says nothing about. So the model splits along the interface:

| We own (optomechanics, 1.3.2) | Mount owns (PAT, 1.3.1) |
|---|---|
| drive `tau(f) = m*d*a(f)` | sensitivity function `S = 1/(1+C·P)` |
| mass properties `m, d, I` (envelope) | loop bandwidth / rejection vs frequency |
| plant `P = 1/(I·s²)` | compensator `C` |

### The three-tier ladder

| Tier | Needs | Produces | Status |
|---|---|---|---|
| **1 — open-loop bound** | `tau(f)`, `I` (ours alone) | residual if the loop did nothing: integrate `tau/I` twice | **implemented** |
| **2 — input × rejection** | Tier 1 + mount's loop shape | where the disturbance leaks through | needs mount's Bode target |
| **3 — full closed-loop** | Tier 1 + mount's `C` | true residual, waterbed peak and all | needs mount's compensator |

Tier 1 is the only rung optomechanics can compute solo. It is **exact above
loop bandwidth** (where the worst jitter lives) and **conservative below** it.
It under-predicts only in the narrow waterbed band just above crossover — that
peak needs Tier 2/3.

## Layout

```
navantia_modelling/
├── navantia_modelling/     # the package
│   ├── spec.py             # the swept-sine standard: a(f), x(f)
│   ├── drive.py            # MassProperties + disturbance_torque tau(f)
│   └── jitter.py           # Tier 1 open-loop bound
├── scripts/
│   └── tier1_openloop_bound.py   # sweep + optional plot
└── tests/
    └── test_tier1.py       # sanity checks that double as physics notes
```

## Run it

```bash
pip install -e .            # or: pip install -r requirements.txt
python scripts/tier1_openloop_bound.py --plot
pytest                      # optional
```

## ⚠ Placeholders

The mass properties in `scripts/tier1_openloop_bound.py` (`m`, `d`, `I`) are
**placeholders**, not design values. The Config A/B fork and the unfrozen
baseboard/enclosure mean the real mass properties are an **envelope** until the
concept gate closes (end of Concept Development, Aug–Sep 2026). Replace them —
and treat `d` as state-dependent over the pointing envelope — before reading
anything into the output.

## Not in scope here

- **Internal-flexure path** — the rigid-lump torque handoff doesn't capture it.
- **Atmospheric angle-of-arrival wander** — a separate disturbance into the same
  loop, the other half of the jitter budget (links to 1.5.3).
