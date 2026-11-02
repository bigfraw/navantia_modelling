"""Sweep the effective focal length f and give the MMF walk-off loss.

The fibre core is 105 um in diameter. The plot gives one curve for each fixed
zero-to-peak tilt. The spot offset is dx = f * theta, and the spot radius also
grows with f. Thus the walk-off loss rises with f. The script also prints the
Tier 1 open-loop peak tilt at crossover for each axis.

The walk-off loss uses the encircled-energy model of olb. The NA gate is a
separate flat loss, thus this script does not include it. The dashed line
shows the shortest f that the fibre NA accepts.

Tier 1 accuracy: above the detent resonance the tilt is a conservative bound.
At and below the detent resonance the tilt is NON-conservative. The mass
properties are PLACEHOLDER values from tier1_openloop_bound.
"""

from __future__ import annotations

import sys
from dataclasses import replace

import numpy as np

# The bridge adds D:/repos/optical_link_budget. Add the C: location too.
sys.path.insert(0, "C:/repos/optical_link_budget")

from vibration_to_coupling import (  # noqa: E402
    APERTURE_M,
    AXES,
    CORE_RADIUS_M,
    F_NA_MIN_M,
    FOCAL_LENGTH_M,
    MASS,
    PHASE_DEG,
    SLEW_LIMIT_DEG,
    WAVELENGTH_M,
    MassProperties,
    _mmf_encircled_efficiency,
    lever_arm,
    openloop_bound,
    spec,
)

F_M = np.linspace(5e-3, 200e-3, 400)  # m, the effective focal length sweep


def walkoff_loss_db(f_m, theta_rad):
    """Give the walk-off loss [dB] for a focal length f_m [m] and a tilt [rad]."""
    spot_m = WAVELENGTH_M * f_m / (np.pi * (APERTURE_M / 2.0))
    eta = _mmf_encircled_efficiency(f_m * theta_rad, spot_m, CORE_RADIUS_M)
    return -10.0 * np.log10(np.clip(eta, 1e-300, None))


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    print(f"Core diameter = {2*CORE_RADIUS_M*1e6:.0f} um, D = {APERTURE_M*1e3:.0f} mm")

    # The Tier 1 tilts are mrad values. They put the spot off the core at all
    # practical f. Thus the plot uses fixed tilts, and the script prints Tier 1.
    print("  Tier 1 peak tilt at crossover, and the f where the spot centre reaches the core edge:")
    for name, (rp, i_axis) in AXES.items():
        mp0 = MassProperties(mass=MASS, lever_arm=lever_arm(0.0, rp, PHASE_DEG), inertia=i_axis)
        for s in (0.0, SLEW_LIMIT_DEG):
            theta = float(openloop_bound(spec.F_CROSS, replace(mp0, lever_arm=lever_arm(s, rp, PHASE_DEG))))
            f_edge = CORE_RADIUS_M / theta * 1e3 if theta > 0 else np.inf
            print(f"    {name}, {s:2.0f} deg slew: {theta*1e6:7.0f} urad, a/theta = {f_edge:.1f} mm")

    print("  tilt [urad]   loss at design f [dB]")
    for theta_urad in (50, 100, 200, 300, 500, 1000):
        theta = theta_urad * 1e-6
        ax.plot(F_M * 1e3, walkoff_loss_db(F_M, theta), label=f"{theta_urad} urad")
        print(f"    {theta_urad:9d}   {float(walkoff_loss_db(FOCAL_LENGTH_M, theta)):.3f}")

    ax.axvline(F_NA_MIN_M * 1e3, color="k", ls=":", label=f"NA minimum f = {F_NA_MIN_M*1e3:.1f} mm")
    ax.axvline(FOCAL_LENGTH_M * 1e3, color="0.5", ls="-.", label=f"design f = {FOCAL_LENGTH_M*1e3:.1f} mm")
    ax.set_xlabel("effective focal length f [mm]")
    ax.set_ylabel("walk-off loss [dB]")
    ax.set_title("MMF walk-off loss against f, 105 um core, zero-to-peak tilt")
    ax.set_ylim(0, 10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("scripts/efl_walkoff_sweep.png", dpi=150)
    print("Saved scripts/efl_walkoff_sweep.png")


if __name__ == "__main__":
    main()
