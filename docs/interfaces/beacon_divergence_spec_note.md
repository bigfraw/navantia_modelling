# Design Note — Beacon Divergence Specification

**WBS:** 1.3.2 (Optomechanics & Atmospherics) → 1.3.1.6 (PAT and tracking) interface
**Author:** Optomechanics & Atmospherics (WBS 1.3 lead)
**Status:** Design note. It records the method to specify the beacon divergence.
It also records the necessary changes to `scripts/beacon_camera_snr.py`. It is
not an interface agreement with the mount.

---

## 0. Purpose of this note

This note answers one question. How do we specify the beacon divergence?

The beacon is a Gaussian beam at 1550 nm. The mount points the beacon. The
far terminal detects the beacon on a camera and tracks it. The first proposal
was to set the beacon divergence as a factor larger than the mount pointing
requirement. The fibre sets that pointing requirement. This proposal gave a
high beacon power.

The direction of the proposal is correct. The beam must be wider than the
pointing error. But the proposal uses the incorrect reference angle. Also, the
current script cannot find the best divergence. Sections 1 to 4 give the
corrections.

---

## 1. The primary principle

**The beacon divergence must cover the beacon pointing error. It must not
cover the fibre pointing requirement.**

The fibre requirement limits the receive line of sight of this terminal. The
beacon divergence must cover the error in the transmit direction of the
beacon. These two angles are equal in one condition only. The table gives each
condition.

| Phase and configuration | Beacon pointing error | Equal to the fibre requirement? |
|---|---|---|
| Tracking, Config A (the mount does all the pointing) | the mount tracking residual | approximately yes, if the mount meets the fibre requirement |
| Tracking, Config B (the FSM corrects the fibre) | the mount residual, if the beacon does not go through the FSM | **no, it is larger** |
| Acquisition (no loop is closed) | the open-loop uncertainty | **no, it is much larger** |

In Config B, the FSM corrects the angle at the fibre. It does not correct the
beacon, unless the beacon path goes through the FSM. Thus the beacon sees the
larger mount residual.

In acquisition, the beacon pointing error includes these terms:

- the ship attitude uncertainty
- the navigation and GPS position uncertainty
- the mount open-loop pointing error
- the ship motion

A beacon that has a divergence from the fibre requirement is too narrow in
Config B and in acquisition. Then the link does not close. This failure is the
opposite of the high-power problem.

### 1.1 The vibration jitter goes into the beacon

The vibration jitter is above the bandwidth of any camera tracking loop. Thus
the jitter goes directly into the beacon pointing error during tracking. Use
the Tier 2 jitter for this term. The Tier 1 bound is non-conservative at and
below the detent resonance. See CLAUDE.md §4. If you use a Tier 1 value, give
this accuracy statement with it.

---

## 2. The best divergence

In the far field, the on-axis received power changes as `1/theta^2`. The
symbol `theta` is the 1/e² half-angle divergence. A pointing error `theta_e`
gives the Gaussian loss factor `exp(-2 theta_e^2 / theta^2)` (Toyoshima et al.,
DOI 10.1364/JOSAA.19.000567). The received power is the product:

```
P(theta) ∝ (1/theta^2) · exp(-2 theta_e^2 / theta^2)
```

Set `x = 1/theta^2`. Then `P ∝ x · exp(-2 theta_e^2 x)`. The derivative is zero
at `x = 1/(2 theta_e^2)`. Thus:

```
theta_opt = sqrt(2) · theta_e          (deterministic pointing error)
```

At `theta_opt`, the mispointing loss is `exp(-1)`, or 4.3 dB.

- A divergence wider than `theta_opt` loses power to the beam spread.
- A divergence narrower than `theta_opt` loses power to the mispointing.

Thus the "factor larger" is correct. For a fixed error, the factor is
approximately 1.4. For a random error with an outage-probability target, the
factor moves to approximately 2 to 3 times the 1-sigma error. Calculate this
factor from the error distribution and the outage target. Do not set it by
judgement.

---

## 3. The error in the current script

`scripts/beacon_camera_snr.py` sets `TX_MISPOINT_FRAC = 0.5`. This value is a
**fraction of the divergence**. It has two effects:

1. The mispointing loss is a constant 2.17 dB at each divergence.
2. The pointing error increases when the beam becomes wider.

The second effect is not physical. The mount sets the pointing error. The
beacon divergence does not change it. Because of these effects, the script
cannot show the best divergence. The required power appears to increase
monotonically with the divergence.

### 3.1 The necessary change

Do these steps in `scripts/beacon_camera_snr.py`:

1. Replace `TX_MISPOINT_FRAC` with a fixed angle `THETA_E_RAD`. Mark it as a
   PLACEHOLDER. It is a mount input and a budget input. Do not invent a design
   value.
2. Calculate the mispointing loss at each divergence point:
   `10·log10(e) · 2 · (THETA_E_RAD / theta)^2` dB, with `theta` the 1/e²
   half angle.
3. Remove the constant `TX_MISPOINT_DB` from `margins_db`. Add the per-point
   loss in its place.
4. Find the divergence that gives the minimum required power. Report it.
   Plot it on the power curve.
5. Check that the minimum is at `sqrt(2) · THETA_E_RAD` (half angle). Write a
   test for this value.
6. Sweep at least two `THETA_E_RAD` values: one for tracking and one for
   acquisition.

Use the `/ponytail` skill for this change. See CLAUDE.md §0.

---

## 4. The divergence is not the primary power driver

The current SNR script stacks these margins on the link:

- a 15 dB fade margin
- a 6 dB extra margin
- the haze extinction over 10 km (a 5 km visibility)
- a 3× blur factor on the spot
- the spot centre on a pixel corner (the worst case)
- a sunlit white cloud that fills the pixel

Each of these values is a PLACEHOLDER. Their sum is larger than the effect of
a factor of 2 in divergence. A factor of 2 in divergence is 6 dB. Thus examine
the margin stack before you make the divergence narrower to decrease the
power. Also examine the 1 km case. The 10 km case is not the baseline range.

---

## 5. The specification method

Use this method to specify the beacon divergence:

1. Write the beacon pointing error budget for each phase and configuration.
   Use the four conditions in §1: acquisition, tracking in Config A, and
   tracking in Config B. If possible, write each term as a distribution.
2. For each condition, find the divergence that gives the minimum required
   power for the outage-probability target.
3. Specify acquisition and tracking separately. If the two divergences are
   very different, examine these options:
   - a wider acquisition beacon
   - a scan of a narrower beacon
   - a separate acquisition source
   Do not size one beam for the two phases without a trade study.
4. Keep the beacon path as a parameter. The beacon can go through the FSM or
   not. In Config B, this choice sets the pointing error that the beacon sees.
   See CLAUDE.md §6.

---

## 6. Open inputs

| Input | Owner | Status |
|---|---|---|
| the mount open-loop pointing error | mount (1.3.1) | request |
| the mount tracking residual, Config A and Config B | mount (1.3.1) | request |
| the Tier 2 vibration jitter (with the detent peak) | mount measurement + 1.3.2 | needs `k_detent` |
| the ship attitude and navigation uncertainty | ship systems | request |
| the beacon path (through the FSM or not) | 1.3.2 + 1.3.1.6 | open trade |
| the outage-probability target for detection | system | open |
