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
from pathlib import Path

import numpy as np

# --- Add the repository root to the path, to run without an installation --
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navantia_modelling import (  # noqa: E402
    MassProperties,
    displacement_band_bound,
    openloop_bound,
    spec,
)
from navantia_modelling.jitter import as_microrad  # noqa: E402

# -------------------------------------------------------------------------
# PLACEHOLDER range of the mass properties. These are NOT design values.
# Replace them when the concept gate closes and the envelope of the baseboard
# and the enclosure is frozen.
MP = MassProperties(
    mass=8.0,        # kg      <-- PLACEHOLDER
    lever_arm=0.05,  # m       <-- PLACEHOLDER (near the maximum slew value)
    inertia=0.08,    # kg m^2  <-- PLACEHOLDER
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

    if args.plot:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("\n[matplotlib is not installed. The script does not make the plot.]")
            return

        fig, ax = plt.subplots(figsize=(7, 4.2))
        ax.loglog(f, theta_urad, lw=2)
        ax.axvline(spec.F_CROSS, ls="--", color="0.5", lw=1)
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
