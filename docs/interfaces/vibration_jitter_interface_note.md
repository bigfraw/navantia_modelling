# Interface Note — Vibration Environment → Pointing Jitter

**WBS:** 1.3.2 (Optomechanics) → 1.3.1.6 (PAT Tracking) interface
**Author:** Optomechanics & Atmospherics (WBS 1.3 lead)
**Status:** Revised after mount-side correction. The mount is an open-loop stepper, not a servoed gimbal. The disturbance-rejection framing has changed. See Section 0 and Sections 3–5.

---

## 0. Architecture correction (the record)

The earlier version of this note assumed the mount was a servoed gimbal with a controller C, a sensitivity function S = 1/(1+C·P), and a loop that rejected in-band disturbance. **That was wrong.**

The FLIR D48E is an **open-loop stepper**: a feedforward profile generator plus open-loop step execution. No block reads angle error and drives a correcting torque. Disturbance rejection is **passive** — the motor's magnetic detent stiffness, a spring — not the action of a servo loop. The encoder layer is event-triggered slip recovery only, and it stayed idle.

Two consequences carried through this note:
- **Pathway 3 below is re-described.** It was "finite disturbance rejection of the active gimbal." There is no active gimbal. It is now the passive detent spring plus the slip nonlinearity.
- **The three-tier ladder collapses.** Tiers 2 and 3 were defined by a loop shape and a compensator C. Neither exists. The real number now comes from a direct torque→angle measurement, not from a controller model.

---

## 1. Question this note answers

Can the ship-qualification vibration spec be used to infer the optical terminal's pointing jitter?

**Short answer:** Not directly. The spec is a disturbance *input*. Jitter is the *response* of the passive rotor-on-detent plant to that input. The standard says nothing about the plant. It lets us build the drive on paper. The response half must be **measured** on the mount, because the passive plant is not something we can derive from command data.

---

## 2. What the spec actually is

Swept-sine qualification profile:

- 2 Hz – 13.2 Hz at ±1 mm (displacement-controlled)
- 13.2 Hz – 100 Hz at 7 m/s² (acceleration-controlled)
- Crossover at 13.2 Hz (a ±1 mm sine gives ≈ 7 m/s² there)
- 2 h dwell on each resonance; else 2 h at 30 Hz, all three axes

Key properties for downstream use:

- It is a **deterministic swept sine**, *not* a random-vibration PSD. Evaluate it frequency-by-frequency, not as g²/Hz statistics.
- As a single acceleration curve via a = (2πf)²x, the input energy **climbs ∝ f² up to 13.2 Hz, then flattens** — concentrated in the *upper* band.
- Its purpose is qualification (survival/function), so levels are punishing, not operationally representative.

---

## 3. Physical chain (why jitter is not a read-off)

A rigid assembly translating with the deck produces **no** boresight tilt — translation alone never moves pointing angle. Jitter requires *deformation* or *relative motion between parts*. Three pathways:

1. Internal flexure of the terminal structure (optical train deflecting relative to itself).
2. Finite stiffness of the mount structure.
3. **Passive detent stiffness of the stepper** — the dominant rotor path. This is the corrected pathway. The disturbance torque works against the motor's magnetic holding spring, not against a servo loop.

For pathway 3, the chain is:

```
base accel a(f)  →  disturbance torque τ = m·r⊥·a(f)  →  reacts against the passive
                    rotor-on-detent plant 1/(I·s²+k_detent)  →  residual angle = jitter
```

There is **no loop and no sensitivity function** in this chain. Below the detent resonance √(k_detent/I) the spring holds and the residual is small and roughly flat. Above it the inertia dominates and the residual rolls off as 1/(I·s²). At the resonance there is a peak. At the slip threshold the behaviour goes hard-nonlinear and the CEC slip-recovery event may fire.

---

## 4. Division of labour (the interface)

| Owned by Optomechanics (1.3.2) | Owned by PAT / Mount (1.3.1) |
|---|---|
| Disturbance **drive** τ(f) = m·r⊥·a(f) from the standard | The **passive torque→angle response** P_dist = 1/(I·s²+k_detent), measured |
| Terminal **mass properties**: mass, CG, MOI — as an envelope | **Detent stiffness k_detent** and the detent resonance | 
| CG-to-axis lever arm *r⊥* over the pointing envelope | **Slip threshold** and near-null nonlinear behaviour |
| Payload inertia I (sets the inertia term) | External angle metrology for the measurement |

**Jitter = our drive operated on by their measured passive plant.** Neither half produces a number alone. The mount half is a **measurement**, not a controller model — because there is no controller.

---

## 5. Method (direct torque measurement — no loop to exploit)

The earlier method tried to re-read command-tracking data through a sensitivity function. That route is gone; there is no sensitivity function. The disturbance response must be measured directly.

1. Model the MOI/CG **envelope** from projected mass and centre of mass (design unfrozen → range, not a point).
2. Build the disturbance **torque input** τ(f) = m·r⊥·a(f) from the standard's acceleration curve.
3. The mount injects a **swept torque** at the shaft, full stack running, and measures the **residual angle** with **external metrology** (autocollimator — the mount's own 112/56 µrad telemetry cannot see sub-step elastic residuals).
4. The measured ratio residual-angle(f) / injected-torque(f) **is** P_dist across the band.
5. Residual angle = P_dist · τ_d = pointing-jitter estimate.

### 5a. What can be computed now, and what needs the measurement

The disturbance response is P_dist · τ_d. We own τ_d and I. We do **not** own k_detent. That single dependency sets the ceiling on what we can compute solo.

| Tier | Inputs | What it produces | Fidelity | Missing piece |
|---|---|---|---|---|
| **1 — Bare-inertia bound** | τ(f) and I (ours) | Integrate τ/I twice: response of a *pure inertia*, 1/(I·s²) | **Conservative above the detent resonance**; **non-conservative at and below it** | — (self-contained; ship as a bound with the caveat) |
| **2 — Measured plant** | Tier 1 **+** the mount's direct torque→angle measurement | The true P_dist, detent peak and all | The real number | Mount — the injected-torque test with external metrology |

**Reading of the tiers:**
- The old Tiers 2 and 3 (loop shape, compensator C) **do not exist** for this mount. There is no loop to shape and no controller to model. The ladder is now just: a bare-inertia bound, then the measured plant.
- **The bound flips sign near the detent resonance.** Tier 1 drops k_detent, so it under-predicts exactly where the detent spring resonates. Since √(k_detent/I) may sit inside the budget band, the bare-inertia bound is **not safe there** — only the measurement (Tier 2) captures the peak. This is the reverse of the old waterbed caution, and it must be flagged loudly.

**The honest plant is I·s² + k_detent.** τ/I is the k_detent → 0 limit.
- Below √(k_detent/I) the stiffness term dominates: the bare-inertia bound over-predicts the *displacement* but misses the *resonant amplification*.
- The inertia term grows ∝ ω² and dominates well above the resonance, where τ/I is a good bound again.
- **k_detent lives in the mount's hardware.** We supply I; they measure k. Same interface principle as before.

---

## 6. Caveats that must travel with the handoff

- **τ is a family, not a curve.** *r⊥* (and reflected inertia) vary over the pointing envelope, because slewing rotates the payload relative to its axes. Ship attitude does not change *r⊥*; only **gimbal slew** does. In closed tracking the ship's roll drives the slew that corrects it, so *r⊥* is effectively state-dependent over a roll cycle.
- **Swept-sine, not PSD** — label it so the mount evaluates frequency-by-frequency.
- **The detent resonance may sit in-band and moves with Config A/B.** √(k_detent/I) is payload-dependent. Pin a worst-case inertia, or measure at more than one, before trusting a single budget number.
- **Telemetry is blind to the residual.** Sub-step elastic deflection below the slip threshold does not appear in the mount's own position readback. External metrology is mandatory, and its procurement is on the budget's critical path.
- **Worst jitter still sits high.** The spec's energy piles up above 13.2 Hz. Whether the passive plant helps there depends on where the detent resonance falls relative to that band.
- **Gravity is a separate, static term.** m·g·r⊥ is a DC holding-torque / droop load (motor sizing), not a jitter source.
- **H is not the flight loop.** The command-response H is amplitude- and rate-dependent, and flight adds an unmeasured camera/PID outer loop. That outer loop is band-limited and likely below 13.2 Hz, so it does not help in the budget band.

---

## 7. Open scope

- **Internal-flexure path (pathway 1)** is *not* captured by the rigid-rotor torque measurement — see follow-on discussion.
- **Atmospheric angle-of-arrival wander** is a separate disturbance into the same pointing budget and forms the other half (links to 1.5.3). Treated separately.
- **External metrology procurement** (autocollimator) is the shared unlock for the disturbance measurement, backlash, encoder-liveness, and sub-step deflection. Flag as a schedule risk in its own right.
