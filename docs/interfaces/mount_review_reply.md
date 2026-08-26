# Reply to Mount-Side Review — Architecture Correction Accepted

**WBS:** 1.3.2 (Optomechanics) → 1.3.1.6 (PAT Tracking) interface
**From:** Optomechanics & Atmospherics (WBS 1.3 lead)
**Re:** Mount-side review of the plant-characterisation proposal

---

## 1. Correction accepted

You are right, and the correction reaches deeper than the proposal — it reaches our two brain-side notes as well. The premise that the mount is a unity-feedback servo was wrong. The D48E is an open-loop stepper: a feedforward trajectory generator plus open-loop step execution. No block reads angle error and drives a correcting torque. The encoder layer (CEC) is event-triggered slip recovery only, and stayed idle (0 events).

We accept this not just on authority. The feedforward model predicts three things the loop model could not:
- The amplitude-dependent phase you measured (0.1° vs 0.5° at 1.5 Hz). A linear feedback loop does not do that in its linear range; an accel-limited profile generator does. This also refutes our earlier "pure transport delay" reading — part of that phase is profile transit.
- Command grid = step grid, so commands cannot address sub-step motion — which is why near-null needs torque dither, not command dither.
- Telemetry quantized at 112/56 µrad, so sub-step elastic residuals are invisible internally.

A model that explains what puzzled us has earned the update.

## 2. What this retracts on our side

- **S = 1 − H is withdrawn as a disturbance-rejection factor.** With no loop, there is no sensitivity function. Our S / L / P algebra assumed a topology that does not exist.
- **Request 1 (controller model) is withdrawn.** There is no error-feedback law to model, from FLIR or anyone. We accept your offer of the full profile-generator parameterisation instead — it models H (command response), not the disturbance plant.
- **The 1/(I·s²) plant is corrected** to the rotor-on-detent form 1/(I·s² + k_detent): stiffness-dominated below the detent resonance √(k_detent/I), inertia-dominated above, resonant at it, hard-nonlinear at slip. We note √(k_detent/I) is payload-dependent and may sit inside our >13.2 Hz budget band, which couples it to the Config A/B mass decision.

## 3. What we confirm and adopt

- **Direct torque→angle measurement is the only route, not a fallback.** Agreed. With no feedback law, the disturbance response is not recoverable from H by any algebra.
- **External metrology is mandatory.** We will add an autocollimator (or equivalent) to the test-equipment plan. We flag this loudly: the same instrument unblocks three of our own open caveats (backlash, encoder-liveness, sub-step deflection), so its procurement is on the budget's critical path.
- **Near-null must be torque dither, not command dither.** Agreed — the command grid is the step grid. This merges with the swept-torque test into one rig session.
- **Band split accepted.** Command response is yours to ~12 Hz (pan) / ~9 Hz (tilt), limited by excitation fidelity and the accel-ceiling box. Torque→angle above 13.2 Hz is ours via the injection rig, which sweeps to ~100 Hz with none of the command-path limits.
- **"The loop that flies" caveat accepted.** Flight adds an unmeasured camera/PID outer loop, and H is rate/amplitude-dependent. We will use the H curve matching the flight configuration once fixed.

## 4. Supply list (agreed)

We supply: payload inertia I (Config-dependent — worst-case or two values), the vibration spec resolved to a torque spectrum at the mount interface, and the external angle metrology.

You supply: full profile-generator parameterisation, H(f) at 50 Hz (two amplitudes) and 200 Hz labelled by rate/amplitude, slip-boundary map, step-response transients, and live slip telemetry (CPEC/CTEC) during the torque tests.
