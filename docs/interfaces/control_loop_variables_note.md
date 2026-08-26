# Command-Path Variables — Feedforward Stepper, Not a Feedback Loop

**WBS:** 1.3.2 (Optomechanics) ↔ 1.3.1.6 (PAT Tracking) interface
**Purpose:** Fix the meaning of the variables used in the mount command-response analysis. State which physics applies to the D48E and which does not. Keep the superseded loop framing on record so it is not re-derived.
**Status:** Revised after mount-side correction. The earlier version modelled this as a unity-feedback loop. That was wrong. See Section 0.

---

## 0. Architecture correction (the record)

**What we assumed.** We modelled the mount as a unity-feedback servo: plant P, controller C, loop gain L = P·C, with S = 1/(1+L) and T = L/(1+L). We read H as the complementary sensitivity T, and we claimed S = 1 − H as the disturbance-rejection factor.

**What the machine actually is.** The FLIR D48E is an **open-loop stepper**. The internal stack is a feedforward trajectory generator (trapezoidal profile) plus open-loop step generation. **Nothing reads angle error and drives a correcting torque.** The encoder layer (CEC) is event-triggered slip recovery only, and it stayed idle (0 events) throughout.

**Why the correction is accepted, not just deferred to.** The feedforward model predicts three things the loop model could not explain:
- **Amplitude-dependent phase.** The mount measured different phase at 1.5 Hz between 0.1° and 0.5° sweeps. A linear feedback loop does not do that in its linear range. An accel-limited profile generator does. This also refutes our earlier "pure transport delay" reading — part of that phase is profile transit, not dead time.
- **Command grid = step grid.** Commands cannot address sub-step motion. This is why near-null excitation must be torque, not command.
- **Telemetry blindness.** Position readback quantizes at 112/56 µrad (pan/tilt). Vibration residuals below the slip threshold are elastic sub-step deflections, invisible internally.

A model that explains what puzzled us has earned the update.

**Consequence.** The loop algebra below (Section 3) does not apply to this mount. S = 1 − H is **not** a sensitivity function, because there is no loop whose sensitivity it could be.

---

## 1. What the machine is

The command path is a feedforward chain:

```
   command → command discretization → profile generator → open-loop step execution → angle
```

- **No error feedback.** No block reads (r − y) and corrects it. The steps go out open-loop.
- **Disturbance rejection is passive.** A disturbance torque is resisted by the motor's magnetic **detent / holding stiffness** — a passive spring — not by any controller.
- **Command response and disturbance response are decoupled.** They share no loop. One is the feedforward chain; the other is the passive rotor-on-detent. This is the central structural fact.

---

## 2. Variables that apply

These describe the real machine.

| Symbol | Name | What it is | Form | Owner |
|---|---|---|---|---|
| **H** | Command response | measured angle / commanded angle | feedforward chain response; **amplitude- and rate-dependent** | measured on bench (mount) |
| **P_dist** | Disturbance plant | torque → angle, passive | 1 / (I·s² + k_detent), to first order | mount hardware (k_detent), us (I) |
| **τ_d** | Disturbance torque | base-vibration drive | τ_d = m·r⊥·a(f) | Optomechanics (ours) |
| **I** | Moment of inertia | payload inertia about the axis | Config-dependent (A/B) | Optomechanics (ours) |
| **k_detent** | Detent stiffness | motor magnetic holding spring | unspecified by FLIR | mount — must be measured |
| **a(f)** | Base acceleration | from the vibration spec | frequency by frequency | Optomechanics (ours) |

**Two facts about H.** It is a feedforward response, not a sensitivity. And it carries a label: the amplitude and command rate it was measured at. Budget work must use the curve matching the flight configuration once that is fixed.

**The disturbance plant is not a pure inertia.** It is a rotor on the detent spring:

```
   P_dist = 1 / (I·s² + k_detent)
```

- **Below the detent resonance** √(k_detent/I): stiffness-dominated, roughly flat.
- **Above it:** inertia-dominated, rolls off as 1/(I·s²).
- **At it:** a resonant peak.
- **At the slip threshold:** hard-nonlinear.

The detent resonance √(k_detent/I) is **payload-inertia-dependent**, plausibly tens of Hz — i.e. possibly **inside the >13.2 Hz budget band**. Because it moves with I, it moves with the Config A/B mass decision. The jitter budget is therefore coupled to the concept gate through this resonance.

---

## 3. Variables that do NOT apply (superseded — retained so they are not re-derived)

The following loop framing was our first model. It is wrong for this mount. It is kept here only to close the question, not as current physics.

| Symbol | Loop meaning | Why it fails here |
|---|---|---|
| **C** | error → torque controller | There is no error-feedback law. Nothing to model. |
| **L = P·C** | loop gain | No loop. |
| **T = L/(1+L)** | command → output | H is a feedforward response, not T. |
| **S = 1/(1+L)** | disturbance → error | **No loop, so no sensitivity.** S = 1 − H is meaningless here. |
| **S + T = 1** | the "lock" | Holds only for a unity-feedback loop. Not this topology. |
| **P = L/C** | back out the plant | Assumes a controller law that does not exist. Unanswerable in principle. |

**Do not** compute S = 1 − H, L = H/(1−H), or P = L/C for the D48E. They encode a machine we do not have.

---

## 4. The corrected disturbance path

Open-loop stepper, so there is no S factor to beat the disturbance down. The residual angle is the disturbance torque acting on the passive plant directly:

```
   residual angle(f) = P_dist(f) · τ_d(f)

                     = [ 1 / (I·(2πf)² + k_detent) ] · [ m·r⊥·a(f) ]
                          \________ mount k, our I ________/    \___ ours ___/
```

- **τ_d is ours.** m·r⊥·a is upstream of the machine, built from the vibration spec.
- **P_dist must be measured directly.** With no feedback law, torque → angle is not recoverable from H by any algebra. It has to be measured by injecting a swept torque and reading the residual angle.
- **The sensor cannot be the mount's own telemetry.** Sub-step elastic residuals are invisible to a 112/56 µrad readback. This needs external metrology — an autocollimator or equivalent.

---

## 5. Where this leaves the two paths

- **Command path (H):** mount-owned, nearly closed. Feedforward response, labelled by amplitude and rate. Useful for command-following behaviour. It does **not** give the disturbance response.
- **Disturbance path (P_dist·τ_d):** where the jitter budget lives. Needs direct torque injection with external metrology. This is the only route. It is immune to there being no controller model, because it never asks for one.

Two things no command test can give, even perfect and in-band:
- The base-acceleration → torque step (τ_d = m·r⊥·a). It is ours, upstream of the machine.
- Internal flexure (structural, outside the rigid rotor). No command test sees it.

One flight caveat: the flying configuration adds a camera/PID **outer** loop, unmeasured on this bench. Its bandwidth is limited by frame rate and the same slow command path, so it likely sits **below** 13.2 Hz. Above its bandwidth it rejects nothing. In the budget band, therefore, the passive detent plant is the operative response, and the camera loop only buys margin lower down.
