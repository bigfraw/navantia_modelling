# navantia_modelling

This package converts the vibration environment into a pointing jitter for the
Phase 1 optical terminal (Navantia-UWA Maritime FSOC, **WBS 1.3**). It
implements the chain from `vibration_jitter_interface_note.md`.

All text in this repository uses ASD-STE100 Simplified Technical English. Keep
this style when you change a file. Read `CLAUDE.md` before you write code.

## What the package calculates

This is the disturbance chain for a servoed gimbal (pathway 3):

```
base acceleration a(f) -> disturbance torque tau = m*d*a(f)
                       -> the loop rejects the in-band part (sensitivity S)
                       -> the residual angle is the pointing jitter
```

The vibration standard is a disturbance **input**. It is not a jitter output.
The jitter is the result of that input and the sensitivity function of the
tracking loop. The standard gives no data about the loop. Thus the model has a
division at the interface:

| We own (optomechanics, 1.3.2) | The mount owns (PAT, 1.3.1) |
|---|---|
| the drive `tau(f) = m*d*a(f)` | the sensitivity function `S = 1/(1+C·P)` |
| the mass properties `m, d, I` (a range) | the loop bandwidth and the rejection against frequency |
| the plant `P = 1/(I·s²)` | the compensator `C` |

### The three model tiers

| Tier | Necessary inputs | Result | Status |
|---|---|---|---|
| **1 — open-loop bound** | `tau(f)`, `I` (our data only) | the residual if the loop does nothing: `tau/I` with two integrations | **complete** |
| **2 — input and rejection** | Tier 1, and the loop shape of the mount | the leakage of the disturbance | needs the Bode target of the mount |
| **3 — full closed loop** | Tier 1, and the compensator `C` of the mount | the true residual, with the waterbed peak | needs the compensator of the mount |

Tier 1 is the only tier that optomechanics can calculate alone. It is **exact
above the loop bandwidth**, where the largest jitter occurs. It is
**conservative below the loop bandwidth**. It is too small only in the narrow
waterbed band immediately above crossover. Use Tier 2 or Tier 3 to get that
peak.

## Layout

```
navantia_modelling/
├── navantia_modelling/     # the package
│   ├── spec.py             # the swept-sine standard: a(f), x(f)
│   ├── drive.py            # MassProperties and disturbance_torque tau(f)
│   └── jitter.py           # the Tier 1 open-loop bound
├── scripts/
│   └── tier1_openloop_bound.py   # a frequency sweep, with an optional plot
└── tests/
    └── test_tier1.py       # tests that are also a record of the physics
```

## How to run the model

```bash
pip install -e .            # or: pip install -r requirements.txt
python scripts/tier1_openloop_bound.py --plot
pytest                      # optional
```

## ⚠ Placeholder values

The mass properties `m`, `d`, and `I` in `scripts/tier1_openloop_bound.py` are
**placeholders**. They are not design values. The Config A/B division, and the
open baseboard and enclosure envelope, make the true mass properties a
**range**. The range stays open until the concept gate closes at the end of
Concept Development, in August or September 2026. Replace these values before
you use the output. Also make `d` a function of the state in the pointing
envelope.

## What this package does not include

- **The internal flexure path.** The rigid-mass torque model does not show it.
- **The atmospheric angle-of-arrival movement.** This is a different
  disturbance into the same loop. It is the second part of the jitter budget,
  and it has a link to WBS 1.5.3.
