"""Convert the Tier 1 vibration jitter into a movement at an MMF tip, and then
into a coupling loss.

Command:
    python scripts/vibration_to_coupling.py

The chain:

    Tier 1 open-loop angle theta   [rad, zero to peak]  <- this repository
        -> movement at the fibre tip dx = f * theta     [m]
        -> MMF coupling loss                            [dB]  <- optical_link_budget

The block mass properties come from `tier1_openloop_bound`. That script owns
the solid aluminium block and the axis inertias. This script imports them, so
the two scripts cannot drift apart. Change the block in one place only.

example layout
            z (2 cm, thin — plate normal)
            │
            │
            │      ______________________
            │     /                     /│
            │    /                     / │
            └── /_____________________/  /  ── y (18 cm, long edge)
               |                     |  /
               |                     | /
               |_____________________|/
              /
             /
            x (13 cm)

This script uses the `olb` package from D:/repos/optical_link_budget. There is
NO turbulence in this calculation. The flag `turbulence=False` removes it, thus
the only disturbance is the mechanical jitter.

THE STATISTIC DOES NOT MATCH, AND THIS IS IMPORTANT. The Tier 1 result is a
deterministic swept sine, and the value is ZERO TO PEAK. The `olb` package
wants a PER-AXIS 1-SIGMA RMS value of a 2-D Gaussian, and it averages the loss
across a Rayleigh distribution of the offset. The MMF model of `olb` is an
encircled-energy model, and the loss is NOT a square-law function of the
offset. Thus an equal variance does NOT give an equal mean loss, and you
cannot simply put theta_pk/sqrt(2) into `olb` and get the correct answer.

This script gives two results:
  1. The DETERMINISTIC loss at the peak offset. The spot is at the largest
     excursion of the sine. This is the correct primary result, because the
     input is deterministic. It is the worst instantaneous coupling.
  2. The STATISTICAL mean loss from `olb`, with sigma = theta_pk/sqrt(2). This
     is for comparison only. It assumes a Gaussian tilt that we do not have.

All values marked PLACEHOLDER are not design values.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

# --- Add the repository root, the scripts directory, and the olb repository -
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
# This script needs the olb commit effac02ea48669cc94a430dbf49fa27e27d4f37a.
# A different olb version changes the coupling interface. Do not use another
# commit until the NA limit lands in olb.
# sys.path.insert(0, "D:/repos/optical_link_budget")
sys.path.insert(0, "D:\\repos\\olb_TEMP\\optical_link_budget")# TEMP - add 'D:\repos\olb_TEMP\optical_link_budget' to path to import olb

from navantia_modelling import (  # noqa: E402
    MassProperties,
    lever_arm,
    openloop_bound,
    spec,
)

# The block, the axis inertias, and the slew range come from the tier1 script.
# This keeps one source of truth for the mass properties.
from tier1_openloop_bound import (  # noqa: E402
    AXES,
    CG_OFFSET,
    MASS,
    PHASE_DEG,
    SLEW_LIMIT_DEG,
)

from olb import (  # noqa: E402
    HorizontalPath,
    Terminal,
    TerrestrialChannel,
    TerrestrialScenario,
    Transmitter,
)

# `_mmf_encircled_efficiency` is private, but it is the only route to a
# deterministic single-offset loss. The public `mmf_coupling_term` always
# averages across a Rayleigh distribution. Do not reimplement the Marcum Q
# function here; use the model of olb.
from olb.models.coupling import (  # noqa: E402
    _mmf_encircled_efficiency,
    mmf_coupling_term,
)
from olb.models.pointing import pointing_loss_term  # noqa: E402
from olb.terminal import MMF  # noqa: E402

# -------------------------------------------------------------------------
# PLACEHOLDER optical values. These are NOT design values. The mechanical
# values (mass, inertia, slew) come from tier1_openloop_bound.
APERTURE_M = 0.025      # m,  <-- PLACEHOLDER, the aperture diameter
WAVELENGTH_M = 1550e-9  # m
PATH_LENGTH_M = 1.0e3   # m,  the Phase 1 range
TX_WAIST_M = 0.1      # m,  <-- PLACEHOLDER, the Gaussian waist radius

CORE_RADIUS_M = 52.5e-6   # m,  <-- PLACEHOLDER, a 50 um core MMF
FIBRE_NA = 0.20         # -,  <-- PLACEHOLDER, the fibre numerical aperture

# The fibre NA sets the shortest focal length that the fibre accepts:
#     NA >= D / (2 f)   thus   f >= D / (2 NA)
# A short f gives a small movement at the tip for the same angle, because
# dx = f * theta. Thus the shortest allowed f gives the best jitter tolerance.
# The olb package does NOT model the NA limit, thus this script sets it here.
F_NA_MIN_M = APERTURE_M / (2.0 * FIBRE_NA)  # the shortest f that the NA accepts
FOCAL_LENGTH_M = 12.56e-3 * 4 # 100 mm lens and 25 mm lens

# The focal spot radius, with the same equation that olb uses.
SPOT_RADIUS_M = WAVELENGTH_M * FOCAL_LENGTH_M / (np.pi * (APERTURE_M / 2.0))
# -------------------------------------------------------------------------


def static_loss_db(offset_m):
    """Give the MMF coupling loss [dB] when the spot centre is offset_m off axis.

    This is a deterministic result at one offset. It uses the encircled-energy
    model of olb: the core is a hard disk, and the fibre collects all the spot
    power inside it.
    """
    eta = np.clip(_mmf_encircled_efficiency(offset_m, SPOT_RADIUS_M, CORE_RADIUS_M), 1e-300, None)
    return -10.0 * np.log10(eta)


def fmt_db(loss_db: float) -> str:
    """Format a loss [dB]. A very large value means that no light couples.

    The encircled energy goes below the floating-point range when the spot is
    fully off the core. Then the loss value has no meaning.
    """
    return "  no light" if loss_db > 300.0 else f"{loss_db:9.2f}"


def max_tilt_for_loss(budget_db: float) -> float:
    """Give the largest zero-to-peak tilt [rad] for a coupling loss budget [dB].

    This inverts `static_loss_db` against the offset, then divides by the focal
    length. The loss increases with the offset, thus the solution is unique.
    """
    offset = brentq(
        lambda dx: static_loss_db(dx) - budget_db, 0.0, 4.0 * CORE_RADIUS_M, xtol=1e-12
    )
    return offset / FOCAL_LENGTH_M


def olb_statistical_loss(theta_rms_rad: float):
    """Give the mean MMF coupling term and the transmit pointing term from olb.

    The tilt goes on both terminals, because both ships have the same vibration
    environment. The transmit tilt and the receive tilt drive different physics,
    and olb keeps them separate:
      - the transmit tilt moves the beam off the far aperture (a free-space loss),
      - the receive tilt moves the spot across the fibre core (the coupling loss).
    """
    scenario = TerrestrialScenario(
        near=Terminal(
            aperture_m=APERTURE_M,
            wavelength_m=WAVELENGTH_M,
            pointing_jitter_rad=theta_rms_rad,   # the transmit tilt
            transmitter=Transmitter(waist_m=TX_WAIST_M),
        ),
        far=Terminal(
            aperture_m=APERTURE_M,
            wavelength_m=WAVELENGTH_M,
            pointing_jitter_rad=theta_rms_rad,   # the receive tilt
            detector=MMF(core_radius_m=CORE_RADIUS_M, focal_length_m=FOCAL_LENGTH_M),
        ),
        channel=TerrestrialChannel(
            path_length_m=PATH_LENGTH_M, attenuation_db_per_km=0.0, cn2=1e-14
        ),
    )
    path = HorizontalPath(PATH_LENGTH_M)
    return (
        mmf_coupling_term(scenario, path, turbulence=False),
        pointing_loss_term(scenario, path),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot", action="store_true", help="save a figure of the open-loop loss against frequency")
    args = parser.parse_args()

    print("Vibration jitter -> MMF coupling loss (PLACEHOLDER values)")
    print(f"  block mass m = {MASS:.4f} kg, CG offset vector = "
          f"({CG_OFFSET[0]*1e3:.0f}, {CG_OFFSET[1]*1e3:.0f}, {CG_OFFSET[2]*1e3:.0f}) mm (from tier1)")
    print(f"  aperture D = {APERTURE_M*1e3:.1f} mm, core radius a = {CORE_RADIUS_M*1e6:.1f} um")
    print(f"  fibre NA = {FIBRE_NA}, effective f = {FOCAL_LENGTH_M*1e3:.1f} mm "
          f"(NA minimum = {F_NA_MIN_M*1e3:.1f} mm)")
    if FOCAL_LENGTH_M < F_NA_MIN_M:
        # ponytail: a print warning only; the olb package will model the NA limit later
        print(f"  WARNING: f is less than D/(2 NA) = {F_NA_MIN_M*1e3:.1f} mm. The cone "
              f"overfills the fibre NA ({APERTURE_M/(2*FOCAL_LENGTH_M):.3f} > {FIBRE_NA}).")
        print("  The olb model does not see this limit, thus the acceptance and the")
        print("  coupling results are optimistic.")
    print(f"  focal spot radius w_s = {SPOT_RADIUS_M*1e6:.2f} um, thus the core is")
    print(f"  {CORE_RADIUS_M/SPOT_RADIUS_M:.1f} spot radii wide. The MMF has room to move.")
    print(f"  plate scale: {FOCAL_LENGTH_M:.4f} um of movement for each urad of tilt")
    print()

    # The loss against the offset is axis-independent. Show it one time.
    print("  The loss against the offset. This shows the light-bucket behaviour:")
    print("    offset [um]   offset/a   loss [dB]")
    for frac in (0.0, 0.25, 0.5, 0.75, 0.9, 1.0, 1.25):
        dx = frac * CORE_RADIUS_M
        print(f"    {dx*1e6:11.1f}   {frac:8.2f}   {fmt_db(static_loss_db(dx))}")
    print()

    # The Tier 1 peak is always at crossover, and the bound is linear in d.
    cases = [(0.0, "boresight"), (SLEW_LIMIT_DEG, f"{SLEW_LIMIT_DEG:.0f} deg slew")]

    for name, (rp, i_axis) in AXES.items():
        mp0 = MassProperties(mass=MASS, lever_arm=lever_arm(0.0, rp, PHASE_DEG), inertia=i_axis)
        theta_pk_openloop = float(openloop_bound(spec.F_CROSS, mp0))

        print(f"=== {name}: r_perp = {rp*1e3:.1f} mm, I_axis = {i_axis:.5f} kg m^2 ===")
        print("  Open loop. The spot movement and the deterministic loss at the peak:")
        print("    case            theta_pk [urad]   dx_pk [um]   dx_pk/a   loss at peak [dB]")
        for s, label in cases:
            mp = replace(mp0, lever_arm=lever_arm(s, rp, PHASE_DEG))
            theta_pk = float(openloop_bound(spec.F_CROSS, mp))
            dx_pk = FOCAL_LENGTH_M * theta_pk
            print(
                f"    {label:14s}  {theta_pk*1e6:13.1f}   {dx_pk*1e6:10.1f}   "
                f"{dx_pk/CORE_RADIUS_M:7.1f}   {fmt_db(static_loss_db(dx_pk)):>16s}"
            )

        # An axis with r_perp = 0 has no vibration torque. Thus it needs no
        # attenuation, and the log ratio is undefined. Skip the inverse there.
        print("  Inverse. The largest tilt for a loss budget, and the attenuation")
        print("  that the passive plant must give at 13.2 Hz (a Tier 2 requirement):")
        print("    budget [dB]   max theta_pk [urad]   max dx [um]   necessary attenuation [dB]")
        for budget_db in (0.5, 1.0, 3.0):
            theta_max = max_tilt_for_loss(budget_db)
            # The necessary attenuation is an ANGLE quantity, not a received
            # power. It is the ratio of two tilt amplitudes (the bare-inertia
            # bound over the largest allowed tilt) in the 20*log10 amplitude
            # convention. The loss and budget columns are received optical
            # power in the 10*log10 convention. The two share the unit dB but
            # are different physics. A 3 dB power budget is NOT 3 dB of angle,
            # because the encircled-energy map from angle to coupling is
            # non-linear. Do not read the attenuation as a power.
            atten_db = 20.0 * np.log10(theta_pk_openloop / theta_max) if theta_pk_openloop > theta_max else 0.0
            print(
                f"    {budget_db:11.1f}   {theta_max*1e6:19.1f}   "
                f"{theta_max*FOCAL_LENGTH_M*1e6:11.1f}   {atten_db:26.1f}"
            )

        theta_rms = theta_pk_openloop / np.sqrt(2.0)
        coupling, tx = olb_statistical_loss(theta_rms)
        print("  For comparison only, the statistical olb result (a Gaussian tilt")
        print("  with sigma = theta_pk/sqrt(2), a distribution we do not have):")
        print(
            f"    mean MMF coupling loss = {fmt_db(coupling.mean_db).strip()} dB, "
            f"transmit free-space loss = {fmt_db(tx.mean_db).strip()} dB"
        )
        print()

    print("  The necessary attenuation is a Tier 2 requirement. The passive detent")
    print("  plant, and any Config B active optics, must give it. The mount is an")
    print("  open-loop stepper, so this is not a loop rejection. Only the measured")
    print("  P_dist shows if it is met. It is not a value we set. The worst axis")
    print("  sets the requirement.")
    print("  Note on the dB columns: the loss and the budget are received optical")
    print("  power (10*log10). The necessary attenuation is an ANGLE amplitude")
    print("  ratio (20*log10). The two are different physics. A 3 dB power budget")
    print("  is not 3 dB of angle.")

    if args.plot:
        plot_bound_vs_acceptance()


def plot_bound_vs_acceptance() -> None:
    """Save the open-loop jitter bound with the MMF acceptance angle overlaid.

    Each panel is one gimbal axis. The panel shows a family of bound curves for
    the CG offset r_perp from 0 to 50 mm, with the axis centroid inertia fixed.
    A larger r_perp raises the torque arm but also raises the parallel-axis
    inertia, thus the family is not evenly spaced. The acceptance angle is the
    tilt that moves the focal spot by one core radius: theta_accept = a / f.
    Above the black line the spot walks off the core, thus no light couples.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n[matplotlib is not installed. The script does not make the plot.]")
        return

    theta_accept_urad = CORE_RADIUS_M / FOCAL_LENGTH_M * 1e6
    f = np.linspace(spec.F_LOW, spec.F_HIGH, 981)
    top = theta_accept_urad * 3.0            # urad, the top of each panel
    r_sweep = np.linspace(0.0, 0.05, 11)     # m, the CG offset family 0 to 50 mm
    cmap = plt.get_cmap("viridis")

    fig, axs = plt.subplots(1, len(AXES), figsize=(4.2 * len(AXES), 4.4), sharey=True)
    for ax, (name, (rp, i_axis)) in zip(axs, AXES.items()):
        i_cg = i_axis - MASS * rp ** 2       # back out the fixed centroid inertia
        k_mm = np.sqrt(i_cg / MASS) * 1e3     # radius of gyration, for the title
        for r in r_sweep:
            mp = MassProperties(mass=MASS, lever_arm=r, inertia=i_cg + MASS * r ** 2)
            ax.loglog(f, openloop_bound(f, mp) * 1e6, lw=1.3, color=cmap(r / 0.05))
        ax.axhline(theta_accept_urad, color="k", lw=1.5)
        ax.axhspan(theta_accept_urad, top, color="0.85", alpha=0.5, zorder=0)
        ax.axvline(spec.F_CROSS, ls="--", color="0.5", lw=1)
        ax.set_xlim(spec.F_LOW, spec.F_HIGH)
        # ax.set_ylim(1e2, top)
        ax.set_title(f"{name}\nk = {k_mm:.0f} mm", fontsize=9)
        ax.set_xlabel("frequency [Hz]")
        ax.grid(True, which="both", alpha=0.3)

    axs[0].set_ylabel("open-loop angle bound [urad, 0-pk]")
    axs[0].text(spec.F_LOW, theta_accept_urad, f" acceptance a/f = {theta_accept_urad:.0f} urad",
                fontsize=7, va="bottom")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 50))
    fig.colorbar(sm, ax=axs, fraction=0.02, pad=0.02, label="CG offset r_perp [mm]")
    fig.suptitle("Open-loop jitter bound vs MMF acceptance (PLACEHOLDER values)", y=1.05)
    out = Path(__file__).resolve().parents[1] / "bound_vs_acceptance.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print(f"\n  figure -> {out}")


def _selfcheck() -> None:
    """Check that max_tilt_for_loss inverts static_loss_db."""
    for budget_db in (0.5, 1.0, 3.0):
        theta = max_tilt_for_loss(budget_db)
        got = static_loss_db(theta * FOCAL_LENGTH_M)
        assert abs(got - budget_db) < 1e-6, (budget_db, got)
    # No tilt gives no walk-off loss, and a large tilt gives no light.
    assert static_loss_db(0.0) < 1e-9
    assert static_loss_db(4.0 * CORE_RADIUS_M) > 300.0


if __name__ == "__main__":
    _selfcheck()
    main()
