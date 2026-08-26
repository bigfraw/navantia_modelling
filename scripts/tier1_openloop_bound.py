"""Calculate the Tier 1 open-loop jitter bound across the qualification band.

Commands:
    python scripts/tier1_openloop_bound.py           # print a table
    python scripts/tier1_openloop_bound.py --plot    # also save a figure

The block below is a solid aluminium PLACEHOLDER. The concept gate (Config A/B)
is not closed. Change the primitives (SIDES, RHO, R_CG) to play with the
values. The mass and the two axis inertias are DERIVED from those primitives.
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
# PLACEHOLDER solid aluminium block. These are NOT design values. Change the
# primitives and the derived values follow. Replace them when the concept gate
# closes and the envelope of the baseboard and the enclosure is frozen.
RHO = 2700.0                   # kg/m^3, aluminium density
SIDES = (0.13, 0.18, 0.02)     # m, the block edges (x, y, z)
CG_OFFSET = (0, 0, 0.02)   # m, <-- PLACEHOLDER, the CG offset vector (ox, oy, oz)
PHASE_DEG = 0.0                # deg, <-- PLACEHOLDER, the slew angle of the maximum d
SLEW_LIMIT_DEG = 30.0          # deg, the slew range of the mount

MASS_DERIVED = RHO * SIDES[0] * SIDES[1] * SIDES[2]   # kg, from the geometry
MASS = 3.0  # kg, set to MASS_DERIVED for the aluminium value, or override here


def r_perp(axis: int) -> float:
    """Give the perpendicular distance from the CG to a coordinate axis [m].

    The parameter `axis` is 0, 1, or 2 for the x, y, or z axis. The distance
    uses the two CG offset components that are NOT along the axis. Thus an
    offset along the axis gives zero, and that axis has no vibration torque.
    """
    off = [CG_OFFSET[i] for i in (0, 1, 2) if i != axis]
    return float(np.hypot(off[0], off[1]))


def axis_inertia(axis: int) -> float:
    """Give I about the offset gimbal axis [kg m^2].

    The parameter `axis` is 0, 1, or 2 for the x, y, or z axis. The first term
    is the centroid inertia of a solid cuboid. It uses the two block edges
    perpendicular to the axis. The term m*r_perp^2 is the parallel-axis shift
    to the offset gimbal axis. The offset distance is constant, so a slew does
    not change this inertia.
    """
    perp = [SIDES[i] for i in (0, 1, 2) if i != axis]
    i_cg = MASS * (perp[0] ** 2 + perp[1] ** 2) / 12.0
    return i_cg + MASS * r_perp(axis) ** 2


# The three gimbal axes. The name gives the block edge that is the axis. Each
# axis has its own perpendicular CG distance r_perp and its own inertia.
# Value = (r_perp [m], I_axis [kg m^2]).
AXES = {
    "13 cm edge axis": (r_perp(0), axis_inertia(0)),  # axis along x
    "18 cm edge axis": (r_perp(1), axis_inertia(1)),  # axis along y
    "2 cm edge axis": (r_perp(2), axis_inertia(2)),   # axis along z
}
# -------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot", action="store_true", help="save a figure of the bound against frequency")
    args = parser.parse_args()

    f = np.linspace(spec.F_LOW, spec.F_HIGH, 981)
    i_cross = int(np.argmin(np.abs(f - spec.F_CROSS)))

    print("Tier 1 open-loop jitter bound (PLACEHOLDER aluminium block)")
    print(f"  block {SIDES[0]*100:.0f} x {SIDES[1]*100:.0f} x {SIDES[2]*100:.0f} cm, rho = {RHO:.0f} kg/m^3")
    print(f"  m = {MASS:.4f} kg, CG offset vector = "
          f"({CG_OFFSET[0]*1e3:.0f}, {CG_OFFSET[1]*1e3:.0f}, {CG_OFFSET[2]*1e3:.0f}) mm")
    print()

    curves = {}
    for name, (rp, i_axis) in AXES.items():
        d0 = lever_arm(0.0, rp, PHASE_DEG)   # m, the boresight lever arm for this axis
        mp = MassProperties(mass=MASS, lever_arm=d0, inertia=i_axis)
        theta_urad = as_microrad(openloop_bound(f, mp))
        curves[name] = theta_urad
        print(f"=== {name}: r_perp = {rp*1e3:.1f} mm, I_axis = {i_axis:.5f} kg m^2 ===")
        print(f"  plateau (2 to 13.2 Hz), flat : {displacement_band_bound(mp)*1e6:8.1f} urad")
        print(f"  value at crossover 13.2 Hz   : {theta_urad[i_cross]:8.1f} urad")
        print(f"  value at 30 Hz               : {as_microrad(openloop_bound(30.0, mp)):8.1f} urad")
        print(f"  value at 100 Hz              : {as_microrad(openloop_bound(100.0, mp)):8.1f} urad")
        print(f"  static m*g*d holding torque  : {mp.gravity_holding_torque():8.3f} N m (motor sizing only)")

        # The bound is linear in d, and the peak against frequency is at
        # crossover. Thus the slew range gives a peak-bound range.
        d_slew = lever_arm(np.array([-SLEW_LIMIT_DEG, PHASE_DEG, SLEW_LIMIT_DEG]), rp, PHASE_DEG)
        peak = as_microrad(openloop_bound(spec.F_CROSS, replace(mp, lever_arm=d_slew)))
        print(f"  slew +/-{SLEW_LIMIT_DEG:.0f} deg -> d {d_slew.min()*1e3:.1f} to {d_slew.max()*1e3:.1f} mm, "
              f"peak {peak.min():.1f} to {peak.max():.1f} urad")
        print()

    print("How to read this: the bare-inertia bound is constant below 13.2 Hz.")
    print("Above 13.2 Hz it decreases as 1/f^2. This is the shape of a pure")
    print("inertia, not the real plant. The mount is an open-loop stepper, so the")
    print("real plant is 1/(I*s^2 + k_detent): flat and small below the detent")
    print("resonance sqrt(k_detent/I), a peak at it, and 1/(I*s^2) above it.")
    print("Bound direction: CONSERVATIVE above the detent resonance, where the")
    print("inertia dominates. NON-CONSERVATIVE at and below it, because this bound")
    print("drops k_detent and misses the peak. Only the Tier 2 measurement shows")
    print("that peak. The resonance may sit inside the >13.2 Hz budget band.")

    if args.plot:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("\n[matplotlib is not installed. The script does not make the plot.]")
            return

        fig, ax = plt.subplots(figsize=(7, 4.2))
        for name, theta_urad in curves.items():
            ax.loglog(f, theta_urad, lw=2, label=name)
        ax.axvline(spec.F_CROSS, ls="--", color="0.5", lw=1)
        ax.text(spec.F_CROSS * 1.05, min(c.min() for c in curves.values()) * 1.4,
                "13.2 Hz\ncrossover", fontsize=8, color="0.4")
        ax.legend(fontsize=8)
        ax.set_xlabel("frequency [Hz]")
        ax.set_ylabel("open-loop angle bound [urad, 0-pk]")
        ax.set_title("Tier 1 open-loop jitter bound (PLACEHOLDER aluminium block)")
        ax.grid(True, which="both", alpha=0.3)
        out = Path(__file__).resolve().parents[1] / "tier1_bound.png"
        fig.tight_layout()
        fig.savefig(out, dpi=140)
        print(f"\n  figure -> {out}")


if __name__ == "__main__":
    main()
