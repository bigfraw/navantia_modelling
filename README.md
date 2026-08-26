# navantia_modelling

This package converts the vibration environment into a pointing jitter for the
Phase 1 optical terminal (Navantia-UWA Maritime FSOC, **WBS 1.3**). It
implements the chain from `vibration_jitter_interface_note.md`.

All text in this repository uses ASD-STE100 Simplified Technical English. Keep
this style when you change a file. Read `CLAUDE.md` before you write code.

## What the package calculates

The mount is an **open-loop stepper**, not a servoed gimbal. This is the
disturbance chain (pathway 3), which reacts against a passive plant:

```
base acceleration a(f) -> disturbance torque tau = m*d*a(f)
                       -> reacts against the passive rotor-on-detent plant
                          P_dist = 1/(I*s^2 + k_detent)
                       -> the residual angle is the pointing jitter
```

The vibration standard is a disturbance **input**. It is not a jitter output.
The jitter is the response of the passive plant to that input. There is no
feedback loop and no sensitivity function `S`. The disturbance rejection is
passive: the motor magnetic detent stiffness `k_detent`. The standard gives no
data about the plant. Thus the model has a division at the interface:

| We own (optomechanics, 1.3.2) | The mount owns (PAT, 1.3.1) |
|---|---|
| the drive `tau(f) = m*d*a(f)` | the measured passive plant `P_dist = 1/(I·s² + k_detent)` |
| the mass properties `m, d, I` (a range) | the detent stiffness `k_detent` and the detent resonance |
| the payload inertia `I` | the external angle metrology for the measurement |

### The two model tiers

| Tier | Necessary inputs | Result | Status |
|---|---|---|---|
| **1 — bare-inertia bound** | `tau(f)`, `I` (our data only) | the response of a pure inertia: `tau/I` with two integrations | **complete** |
| **2 — measured plant** | Tier 1, and the mount direct torque→angle measurement | the true `P_dist`, with the detent peak | needs a mount measurement |

Tier 1 is the only tier that optomechanics can calculate alone. The bound
direction flips at the detent resonance `√(k_detent/I)`. It is **conservative
above the resonance**, where the inertia dominates. It is **non-conservative at
and below the resonance**, because it drops `k_detent` and misses the peak. The
resonance may sit inside the >13.2 Hz budget band, and it moves with the Config
A/B mass decision. Only the Tier 2 measurement captures the peak.

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
  disturbance into the same pointing budget. It is the second part of the
  jitter budget, and it has a link to WBS 1.5.3.
