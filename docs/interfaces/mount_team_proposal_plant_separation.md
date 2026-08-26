# Interface Note to Mount Team — Plant Characterisation for the Pointing-Jitter Budget

**WBS:** 1.3.2 (Optomechanics) → 1.3.1.6 (PAT Tracking) interface
**From:** Optomechanics & Atmospherics (WBS 1.3 lead)
**Subject:** Agreed division of labour and tests to close the disturbance response for the pointing-jitter budget
**Status:** Converged after mount-side review. Two earlier drafts are superseded — one assumed a removable secondary controller, the next assumed an untouchable controller law. Both were wrong. See Section 2.

---

## 1. What the command-response data gives us

The mount measured the command-tracking response H on the bench. It is clean and coherent from about 0.01 Hz to 1.8 Hz (50 Hz waypoints), with 200 Hz sweeps extending to ~12 Hz (pan) / ~9 Hz (tilt).

H is a **feedforward** command response. It is amplitude- and rate-dependent, so each curve is labelled with its rate and amplitude. It characterises command-following. It does **not** give the disturbance response, and there is no algebra that converts it into one (Section 2).

## 2. Why the disturbance response cannot come from H

The mount is an **open-loop stepper** (FLIR D48E): a feedforward profile generator plus open-loop step execution. No block reads angle error and drives a correcting torque. So:

- **S = 1 − H is not a disturbance-rejection factor.** There is no feedback loop whose sensitivity it could be. Our earlier S / L / P algebra assumed a unity-feedback structure this machine does not have.
- **There is no controller law to model.** Disturbance rejection is passive — the motor's magnetic detent stiffness, a spring. So "provide the controller model" is unanswerable in principle, not just in practice.

Command response and disturbance response are **decoupled** in this architecture. The disturbance response must therefore be measured directly.

## 3. Requests

**Request 1 — Measure the torque→angle response directly.** This is the **only** route, not a fallback. Inject a **swept torque** at the shaft, full stack running, and measure the residual angle:

```
   residual angle(f) / injected torque(f) = P_dist(f) = 1 / (I·s² + k_detent)
```

- Inject as a swept sinusoid across frequency, not a static load. A hung weight tests only DC and also changes I and CG.
- **External angle metrology is mandatory.** The mount's own position readback quantizes at 112/56 µrad (pan/tilt). Sub-step elastic residuals below the slip threshold are invisible internally. Please include an **autocollimator** (or equivalent) in the test-equipment plan. *This procurement is on the budget's critical path.*
- **Live slip telemetry** (CPEC/CTEC) gives a free crossed-the-threshold flag per condition. Please capture it.
- This measures **k_detent** and the detent resonance √(k_detent/I) — the unknown that FLIR does not specify and that may sit inside the >13.2 Hz budget band.

**Request 2 — Near-null characterisation, merged into the same rig.** The jitter budget lives near a fixed pointing angle, where the axis barely moves. There, stiction and detent dominate and are nonlinear. Excite a **small-amplitude torque dither** around a **fixed** angle. It must be **torque** dither, not command dither — the command grid is the step grid, so commands cannot address sub-step motion at all. This reaches the stiction/detent regime only through the injected-torque path, so it is one rig session with Request 1.

**Request 3 — Own the band above ~12 Hz on the torque path.** The command path is limited to ~12 Hz (pan) / ~9 Hz (tilt), not by Nyquist but by excitation fidelity (50 Hz waypoints give too few samples per cycle) and an accel-ceiling-vs-amplitude box. Above 13.2 Hz the command path is the wrong object anyway — the budget quantity there is torque→angle. The injected-torque rig can sweep to ~100 Hz with none of the command-path limits. Clean division: **command response to ~12 Hz is the mount's; torque→angle above that is the jitter budget's, via this rig.**

## 4. Supply list (agreed)

**Mount supplies:**
- Full profile-generator parameterisation (accel / speed / ceilings, measured).
- H(f) at 50 Hz (two amplitudes) and 200 Hz, each labelled with rate and amplitude.
- Slip-boundary map and step-response transients.
- Live slip telemetry during the torque tests.

**Optomechanics supplies:**
- Payload inertia I. **Config-dependent (A/B)** — pin a worst-case value or supply two, because the detent resonance moves with I.
- The vibration spec resolved to a **torque spectrum at the mount interface**, τ_d = m·r⊥·a(f).
- The external angle metrology (autocollimator) for Requests 1 and 2.

## 5. Caveats on record

- **"The loop we measured is the loop that flies" is false, twice.** Flight adds an unmeasured camera/PID outer loop, and H is amplitude- and rate-dependent. Budget calcs use the H curve matching the flight configuration once it is fixed.
- **The bare-inertia bound flips sign at the detent resonance.** τ/I is conservative above √(k_detent/I) but non-conservative at and below it. Only the direct measurement captures the peak.

---

*Priority: Requests 1 and 2 are one rig session and produce the budget number directly. The autocollimator procurement gates all of it and should be raised as a standalone schedule risk.*
