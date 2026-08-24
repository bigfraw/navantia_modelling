"""Calculate the Tier 1 open-loop jitter bound across the qualification band.

Commands:
    python scripts/tier1_openloop_bound.py           # print a table
    python scripts/tier1_openloop_bound.py --plot    # also save a figure

The mass properties below are PLACEHOLDERS. The concept gate (Config A/B) is
not closed. Change `MP` before you use the results.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

# --- Add the repository root to the path, to run without an installation --
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navantia_modelling import (  # noqa: E402
    MassProperties,
    displacement_band_bound,
    lever_arm,
    openloop_bound,
    spec,
)
from navantia_modelling.jitter import as_microrad  # noqa: E402

# -------------------------------------------------------------------------
# PLACEHOLDER range of the mass properties. These are NOT design values.
# Replace them when the concept gate closes and the envelope of the baseboard
# and the enclosure is frozen.
R_CG = 0.05            # m,   <-- PLACEHOLDER, the CG radius from the axis
PHASE_DEG = 0.0        # deg, <-- PLACEHOLDER, the slew angle of the maximum d
SLEW_LIMIT_DEG = 30.0  # deg, the slew range of the mount

MP = MassProperties(
    mass=8.0,                                   # kg      <-- PLACEHOLDER
    lever_arm=lever_arm(0.0, R_CG, PHASE_DEG),  # m, the value at boresight
    inertia=0.08,                               # kg m^2  <-- PLACEHOLDER
)
# -------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot", action="store_true", help="save a figure of the bound against frequency")
    args = parser.parse_args()

    f = np.linspace(spec.F_LOW, spec.F_HIGH, 981)
    theta = openloop_bound(f, MP)
    theta_urad = as_microrad(theta)

    plateau = displacement_band_bound(MP)
    i_cross = int(np.argmin(np.abs(f - spec.F_CROSS)))

    print("Tier 1 open-loop jitter bound (PLACEHOLDER mass properties)")
    print(f"  m = {MP.mass} kg, d = {MP.lever_arm} m, I = {MP.inertia} kg m^2")
    print(f"  static m*g*d holding torque = {MP.gravity_holding_torque():.3f} N m (use for motor sizing, not for jitter)")
    print()
    print(f"  plateau in the displacement band (2 to 13.2 Hz): {plateau*1e6:.2f} urad, constant with frequency")
    print(f"  value at crossover  ({spec.F_CROSS:.1f} Hz): {theta_urad[i_cross]:.2f} urad")
    print(f"  value at 30 Hz               : {as_microrad(openloop_bound(30.0, MP)):.2f} urad")
    print(f"  value at 100 Hz              : {as_microrad(openloop_bound(100.0, MP)):.2f} urad")
    print()
    print("  How to read this: the bound is constant below 13.2 Hz. Above 13.2 Hz")
    print("  it decreases as 1/f^2. This is the OPEN-loop peak, and it is at a low")
    print("  frequency. The closed-loop maximum stays at a high frequency, because")
    print("  the loop decreases the low plateau but does not change the high band.")

    # --- The envelope of d across the slew range --------------------------
    # The bound is linear in d, and its maximum against frequency is always at
    # crossover. Thus one evaluation at F_CROSS gives the peak at each angle.
    slew = np.linspace(-SLEW_LIMIT_DEG, SLEW_LIMIT_DEG, 13)
    d_slew = lever_arm(slew, R_CG, PHASE_DEG)
    peak = np.array(
        [as_microrad(openloop_bound(spec.F_CROSS, replace(MP, lever_arm=d))) for d in d_slew]
    )

    print()
    print(f"  Envelope of the lever arm d across a slew of +/-{SLEW_LIMIT_DEG:.0f} deg")
    print(f"  (r_cg = {R_CG} m, the maximum of d is at {PHASE_DEG:.0f} deg):")
    print("    slew [deg]   d [mm]   peak bound [urad]")
    for s, d, p in zip(slew, d_slew, peak):
        print(f"    {s:9.1f}   {d*1e3:6.2f}   {p:15.1f}")
    print(f"  d from {d_slew.min()*1e3:.2f} mm to {d_slew.max()*1e3:.2f} mm.")
    print(f"  The peak bound is from {peak.min():.1f} urad to {peak.max():.1f} urad.")
    print("  Use the maximum value as the bound. The value of PHASE_DEG sets which")
    print("  slew angle gives that maximum, and PHASE_DEG is a PLACEHOLDER.")

    if args.plot:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("\n[matplotlib is not installed. The script does not make the plot.]")
            return

        fig, ax = plt.subplots(figsize=(7, 4.2))
        # The bound is linear in d. Thus the slew range gives a band.
        scale_lo = d_slew.min() / MP.lever_arm
        scale_hi = d_slew.max() / MP.lever_arm
        ax.fill_between(
            f, theta_urad * scale_lo, theta_urad * scale_hi,
            alpha=0.25, label=f"slew +/-{SLEW_LIMIT_DEG:.0f} deg",
        )
        ax.loglog(f, theta_urad, lw=2, label="boresight")
        ax.axvline(spec.F_CROSS, ls="--", color="0.5", lw=1)
        ax.legend(fontsize=8)
        ax.text(spec.F_CROSS * 1.05, theta_urad.min() * 1.4, "13.2 Hz\ncrossover", fontsize=8, color="0.4")
        ax.set_xlabel("frequency [Hz]")
        ax.set_ylabel("open-loop angle bound [urad, 0-pk]")
        ax.set_title("Tier 1 open-loop jitter bound (PLACEHOLDER mass properties)")
        ax.grid(True, which="both", alpha=0.3)
        out = Path(__file__).resolve().parents[1] / "tier1_bound.png"
        fig.tight_layout()
        fig.savefig(out, dpi=140)
        print(f"\n  figure -> {out}")


if __name__ == "__main__":
    main()
