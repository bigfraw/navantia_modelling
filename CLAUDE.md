# CLAUDE.md — navantia_modelling

This file gives the context and the work rules for this repository. Read this
file before you write code. It records the physics and the interface limits
that the code must obey.

---

## 0. Two rules that control all work here

### Rule 1 — Write all text in Simplified Technical English

Write all documentation, all code comments, all docstrings, all output text,
and all commit messages in ASD-STE100 Simplified Technical English (STE).

Obey these STE rules:

- Write short sentences. Use a maximum of 20 words in an instruction.
- Use a maximum of 25 words in a descriptive sentence.
- Write one idea in each sentence.
- Use the active voice. Do not use the passive voice.
- Write an instruction as a command. Put the verb at the start.
- Use the simple present tense, the simple past tense, or the simple future
  tense.
- Use one word for one meaning. Do not use a different word for the same thing.
- Do not use idioms, metaphors, slang, or jokes.
- Do not remove the articles "the", "a", or "an" to make a sentence shorter.
- Do not put more than three nouns together.
- Use a vertical list for complex data.
- Write a maximum of six sentences in a paragraph.

Technical names and technical verbs of this field are permitted. Examples:
gimbal, sensitivity function, crossover, waterbed effect, phase screen. Give
the definition of each technical name one time, then always use the same name.

When you change a file, write the new text in STE. Do not keep the old style in
the file.

### Rule 2 — Use the ponytail skill for all code

Use the `/ponytail` skill each time you write new code or change existing code
in this repository. The skill makes you write the smallest solution that
operates correctly. Do not write code in this repository without it.

---

## 1. The purpose of this repository

This repository holds the modelling work for the Phase 1 optical terminal of
the Navantia-UWA Maritime FSOC project. The terminal gives bidirectional
ship-to-ship laser communication at 1 Gb/s or more, over 1 km. The owner is
responsible for WBS 1.3 optomechanics and atmospheric modelling. There is an
active interface to WBS 1.3.1.6 PAT and tracking.

The repository contains two modelling threads:

1. **Vibration to pointing jitter.** This thread is complete. It converts the
   ship qualification vibration standard into a residual pointing angle.
2. **End-to-end FSOC coupling simulation.** The full closed-loop propagation
   model has no code. It uses two agents. The fibre coupling efficiency is a
   result of the turbulence physics. The model does not set the coupling
   efficiency directly. A first one-way bridge now exists. It maps the Tier 1
   jitter to an MMF coupling loss with the `optical_link_budget` package. It
   has no turbulence and no closed loop. See §6.

This repository is the location of the code, the runs, the tests, and the
commits. The derivation history, the specification decisions, and the design
gate logic are in the owner's project workspace. They are also in two reference
documents: `vibration_jitter_interface_note.md` and
`claude_Optical_Terminal_Roadmap.md`. Use those two documents for physics
questions. Use this file for operational questions.

---

## 2. The primary principle

**A vibration specification is a disturbance input. It is not a jitter
output.** The standard gives the base acceleration that the terminal receives.
The jitter is the result of that input and the sensitivity function of the
tracking loop. The standard gives no data about the tracking loop. Thus you
cannot get the jitter from the vibration standard alone. Prevent this error in
the code and in the comments.

This is the chain for a servoed gimbal:

```
base acceleration a(f) -> disturbance torque tau = m*d*a(f)
                       -> the loop rejects the in-band part (sensitivity S)
                       -> the residual angle is the pointing jitter
```

---

## 3. Interface ownership

The model has a division at the WBS interface. Keep this division visible in
the code. You can calculate our blocks now. The blocks of the mount are inputs.
Request those inputs. Do not invent them.

| We own (optomechanics, 1.3.2) | The mount owns (PAT, 1.3.1) |
|---|---|
| the drive `tau(f) = m*d*a(f)` | the sensitivity `S = 1/(1 + C·P)` |
| the mass properties `m, d, I` (a **range**, not one value) | the loop bandwidth and the rejection against frequency |
| the plant `P = 1/(I·s²)` | the compensator `C` |
| the lever arm `d` in the pointing range | the residual tracking error (the jitter value) |

If a task needs `S`, the loop shape, or `C`, then that value is a **mount
input**. Write a stub for the interface. Record the dependency. Do not invent a
compensator to get a value.

---

## 4. The three model tiers (jitter thread)

| Tier | Necessary inputs | Result | Status |
|---|---|---|---|
| **1 — open-loop bound** | `tau(f)`, `I` (our data only) | the residual if the loop does nothing: `tau/I` with two integrations | **complete** (`jitter.openloop_bound`) |
| **2 — input and rejection** | Tier 1, and the loop shape or the Bode target of the mount | the leakage of the disturbance against frequency | needs a mount input |
| **3 — full closed loop** | Tier 1, and the compensator `C` of the mount | the true residual from `S`, with the waterbed peak | needs a mount input |

The accuracy of Tier 1:

- **Above the loop bandwidth, Tier 1 is exact.** The largest jitter occurs in
  this band.
- **Below the loop bandwidth, Tier 1 is conservative.** The bound is larger
  than the true value.
- **Immediately above crossover, Tier 1 is too small.** The true sensitivity
  `S` is more than 1 in this narrow band. This is the waterbed effect. Only
  Tier 2 and Tier 3 show this peak.

Give this accuracy statement with each Tier 1 result that you supply as a
bound.

---

## 5. Physics facts. Do not violate them

- **Below crossover, the open-loop bound is constant.** The term
  `a = (2πf)²·x` removes the two integrations. Thus `theta = m·d·x0/I`. This
  value does not change with frequency between 2 Hz and 13.2 Hz. Above
  crossover the torque is constant and the angle decreases as `1/f²`. Thus the
  open-loop peak is at a low frequency. But the closed-loop maximum stays at a
  high frequency. The loop decreases the low-frequency plateau and does not
  change the high band.
- **High-frequency jitter occurs because the loop bandwidth is too low.** It
  does not occur because the motor torque is too low. Above the bandwidth the
  controller stops the correction commands. The necessary torque increases with
  `f²`, but the loop does not respond. Do not model the high-band failure as a
  torque limit.
- **Inertia does not decrease the jitter at high frequency.** The inertia `I`
  opposes the disturbance torque and the correction torque by the same
  quantity. The inertia is a low-pass filter on the angular response. It is not
  additional loop rejection.
- **`tau/I` is the limit of the correct plant `I·s² + c·s + k`, when `c` and
  `k` decrease to zero.** The terms `c` and `k` are the bearing friction, the
  back-EMF damping, and the detent stiffness or cable stiffness. In the high
  band the inertia term is much larger than `c` and `k`. Thus the bound is
  conservative in that band. There is one exception. Detent torque and Coulomb
  friction are non-linear. They can add torque ripple at the small residual
  angles that a fibre-coupling budget uses. Thus they are also a disturbance
  source, and not only a loss. Report this to the mount. The values of `c` and
  `k` are mount inputs.
- **The lever arm `d` is a range of values, not one value.** A slew moves the
  centre of gravity in relation to the axis. Thus `tau` is also a range of
  values in the pointing envelope. The ship attitude does not change `d`,
  because the rigid mass turns as one body. Only a gimbal slew changes `d`. In
  closed-loop tracking, the ship roll causes the slew that corrects the roll.
  Thus `d` changes with the state during a roll cycle.
- **The CG offset is a vector, not one distance.** The offset from the gimbal
  centre to the centre of gravity is a 3-vector `(ox, oy, oz)`. Each gimbal
  axis sees only the part perpendicular to it. Thus each axis has its own arm
  `r_perp` and its own inertia. An offset along an axis gives `r_perp = 0`, and
  that axis has no vibration torque. Do not use one distance for all axes.
- **The inertia resists the torque; the arm makes it.** The open-loop angle is
  `theta ∝ r_perp / (I_cg + m·r_perp²)`. For a uniform body `I_cg = m·k²`, thus
  the mass cancels and `theta` depends only on the geometry. The radius of
  gyration `k` is the geometry. The jitter is a maximum when `r_perp` equals
  `k`. A larger offset then decreases the jitter. Thus the mass placeholder
  does not change the open-loop jitter of a uniform block. It changes the
  holding torque.
- **Gravity is a different load.** The term `m·g·d` is a static holding torque
  and a droop load. Use it for motor sizing. Do not put it in the jitter
  calculation.
- **Use a swept sine, not a PSD.** Calculate the result at each frequency. Do
  not use the standard as a `g²/Hz` random-vibration statistic.

---

## 6. The architecture of the coupling simulation

The closed-loop simulation has no code. A one-way bridge exists in
`scripts/vibration_to_coupling.py`. The bridge maps the Tier 1 jitter to an
MMF coupling loss. It uses the `optical_link_budget` package (`olb`) from
`D:/repos/optical_link_budget`. It has no turbulence and no closed loop. The
bridge gives two results:

- The deterministic loss at the peak offset. The swept sine is zero to peak,
  thus this is the primary result. It is the worst instantaneous coupling.
- The statistical mean loss from `olb`. This is for comparison only. The `olb`
  package uses a per-axis 1-sigma Gaussian tilt and a Rayleigh offset. Our
  input is a deterministic swept sine, thus the statistic does not match. Do
  not put `theta_pk / sqrt(2)` into `olb` and treat the result as correct.

The bridge also inverts the loss. For a coupling-loss budget, it gives the
necessary loop rejection at 13.2 Hz. This rejection is a **Tier 2 requirement
on the mount**. It is not a value we set. The bridge does not invent the loop
sensitivity `S`.

When you write the closed-loop code, use this architecture:

- **Use one common terminal interface and two alternative backends.**
  - *(a) The analytical backend.* The terminal receives an angle-of-arrival
    sample from a spectrum, and a scalar coupling-efficiency value. This
    backend is fast. Use it for controller iteration.
  - *(b) The numerical backend.* The terminal receives a full electric field
    from a split-step phase-screen propagation. Calculate the coupling with the
    overlap integral.
  - The **same controller code** must operate with each backend.
- **Use a closed loop with two agents.** At each timestep, propagate A to B and
  B to A through the current turbulence realisation. Each controller
  calculates its own correction from the **received tilt only**. The
  controllers do not share data. Then apply the corrections, advance the
  atmosphere, and do the next timestep.
- **The delay data is critical.** Each terminal must use the field from the
  **previous** timestep. Shared state or same-step feedback gives the
  controller data from the future, and makes the result incorrect. This is a
  correctness invariant. Write a test for it.
- **The split-step method is necessary.** An aperture of approximately 25 mm at
  a range of 1 km to 5 km is near the Rayleigh range. Thus you cannot use the
  plane-wave approximation or the spherical-wave approximation.
- **Use a coaxial fine-steering mirror.** In one movement it removes the
  received angle of arrival, and it steers the transmitted beam reciprocally. A
  correction on the transmit side gives an effective increase of the aperture.
  A correction on one side only is sufficient for an infinite aperture, but not
  for a real aperture.
- **Make the beacon path and the beacon wavelength a parameter.** The
  simulation must show if a shared path or a separate path is better. Do not
  set this value in the code.

The atmospheric angle-of-arrival movement is the second part of the jitter
budget. It has a link to WBS 1.5.3. It is an input to the same tracking loop as
the vibration disturbance.

---

## 7. Conventions

- **Make each placeholder easy to see.** The values `m`, `d`, and `I`, and all
  other mass properties, are a **range**. The range stays open until the
  Config A/B concept gate closes at the end of Concept Development, in August
  or September 2026. Mark each placeholder in the adjacent comment. Do not let
  an invented value become a design value.
- **The Config A/B division.** Config A is passive. Config B has active optics
  with a fine-steering mirror and disturbance rejection. Where the behaviour is
  different, write the two conditions and give each one a tag. Do not put only
  one condition in the code. If it is possible, write the requirement at the
  functional level. An example is the coupling efficiency against the
  distributions of pointing error and incidence angle. Then the requirement
  applies to Config A and to Config B.
- **Units.** Use SI units in all code: rad, N·m, kg·m², Hz. Convert to
  microradians only when you report a result.
- **Give the direction of each bound.** State if the approximation is larger or
  smaller than the true value, and in which frequency band. A bound without its
  direction is not usable.
- **Imports.** The package must import without an installation, because the
  scripts add the repository root to the path. But `pip install -e .` is the
  correct method.

---

## 8. Layout

```
navantia_modelling/          # the package
  spec.py                    # the swept-sine standard: a(f), x(f)
  drive.py                   # MassProperties and disturbance_torque tau(f)
  jitter.py                  # the Tier 1 open-loop bound
scripts/
  tier1_openloop_bound.py    # a frequency sweep, with an optional plot
  vibration_to_coupling.py   # the jitter-to-MMF-loss bridge (needs olb)
tests/
  test_tier1.py              # tests that are also a record of the physics
```

The block, the CG offset vector, and the axis inertias live in
`tier1_openloop_bound.py`. The bridge imports them. Thus there is one source of
truth for the mass properties. The bridge also needs the `optical_link_budget`
package at `D:/repos/optical_link_budget`.

Commands: `python scripts/tier1_openloop_bound.py --plot`,
`python scripts/vibration_to_coupling.py --plot`, and `pytest`
