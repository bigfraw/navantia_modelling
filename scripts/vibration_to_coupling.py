"""Convert the Tier 1 vibration jitter into a movement at an MMF tip, and then
into a coupling loss.

Command:
    python scripts/vibration_to_coupling.py

The chain:

    Tier 1 open-loop angle theta   [rad, zero to peak]  <- this repository
        -> movement at the fibre tip dx = f * theta     [m]
        -> MMF coupling loss                            [dB]  <- optical_link_budget

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

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

# --- Add the repository root and the olb repository to the path -----------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, "D:/repos/optical_link_budget")

from navantia_modelling import (  # noqa: E402
    MassProperties,
    lever_arm,
    openloop_bound,
    spec,
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
# PLACEHOLDER values. These are NOT design values.
R_CG = 0.05            # m,   <-- PLACEHOLDER, the CG radius from the axis
PHASE_DEG = 0.0        # deg, <-- PLACEHOLDER, the slew angle of the maximum d
SLEW_LIMIT_DEG = 30.0  # deg, the slew range of the mount

MP = MassProperties(
    mass=8.0,                                   # kg      <-- PLACEHOLDER
    lever_arm=lever_arm(0.0, R_CG, PHASE_DEG),  # m, the value at boresight
    inertia=0.08,                               # kg m^2  <-- PLACEHOLDER
)

APERTURE_M = 0.025      # m,  <-- PLACEHOLDER, the aperture diameter
WAVELENGTH_M = 1550e-9  # m
PATH_LENGTH_M = 1.0e3   # m,  the Phase 1 range
TX_WAIST_M = 0.008      # m,  <-- PLACEHOLDER, the Gaussian waist radius

CORE_RADIUS_M = 25e-6   # m,  <-- PLACEHOLDER, a 50 um core MMF
FIBRE_NA = 0.20         # -,  <-- PLACEHOLDER, the fibre numerical aperture

# The fibre NA sets the shortest focal length that the fibre accepts:
#     NA >= D / (2 f)   thus   f >= D / (2 NA)
# A short f gives a small movement at the tip for the same angle, because
# dx = f * theta. Thus the shortest allowed f gives the best jitter tolerance.
# The olb package does NOT model the NA limit, thus this script sets it here.
FOCAL_LENGTH_M = APERTURE_M / (2.0 * FIBRE_NA)

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
    print("Vibration jitter -> MMF coupling loss (PLACEHOLDER values)")
    print(f"  aperture D = {APERTURE_M*1e3:.1f} mm, core radius a = {CORE_RADIUS_M*1e6:.1f} um")
    print(f"  fibre NA = {FIBRE_NA}, thus f = D/(2 NA) = {FOCAL_LENGTH_M*1e3:.1f} mm")
    print(f"  focal spot radius w_s = {SPOT_RADIUS_M*1e6:.2f} um, thus the core is")
    print(f"  {CORE_RADIUS_M/SPOT_RADIUS_M:.1f} spot radii wide. The MMF has room to move.")
    print(f"  plate scale: {FOCAL_LENGTH_M:.4f} um of movement for each urad of tilt")
    print()

    # The Tier 1 peak is always at crossover, and the bound is linear in d.
    cases = [(0.0, "boresight"), (SLEW_LIMIT_DEG, f"{SLEW_LIMIT_DEG:.0f} deg slew")]

    print("  Open loop. The spot movement and the deterministic loss at the peak:")
    print("    case            theta_pk [urad]   dx_pk [um]   dx_pk/a   loss at peak [dB]")
    for s, label in cases:
        mp = replace(MP, lever_arm=lever_arm(s, R_CG, PHASE_DEG))
        theta_pk = float(openloop_bound(spec.F_CROSS, mp))
        dx_pk = FOCAL_LENGTH_M * theta_pk
        print(
            f"    {label:14s}  {theta_pk*1e6:13.1f}   {dx_pk*1e6:10.1f}   "
            f"{dx_pk/CORE_RADIUS_M:7.1f}   {fmt_db(static_loss_db(dx_pk)):>16s}"
        )

    print()
    print("  The loss against the offset. This shows the light-bucket behaviour:")
    print("    offset [um]   offset/a   loss [dB]")
    for frac in (0.0, 0.25, 0.5, 0.75, 0.9, 1.0, 1.25):
        dx = frac * CORE_RADIUS_M
        print(f"    {dx*1e6:11.1f}   {frac:8.2f}   {fmt_db(static_loss_db(dx))}")

    print()
    print("  The inverse. For each loss budget, this is the largest tilt, and the")
    print("  rejection that the mount must give at 13.2 Hz:")
    print("    budget [dB]   max theta_pk [urad]   max dx [um]   necessary rejection [dB]")
    theta_pk_openloop = float(openloop_bound(spec.F_CROSS, MP))
    for budget_db in (0.5, 1.0, 3.0):
        theta_max = max_tilt_for_loss(budget_db)
        rejection_db = 20.0 * np.log10(theta_pk_openloop / theta_max)
        print(
            f"    {budget_db:11.1f}   {theta_max*1e6:19.1f}   "
            f"{theta_max*FOCAL_LENGTH_M*1e6:11.1f}   {rejection_db:24.1f}"
        )
    print("  This is a Tier 2 requirement on the mount. It is not a value we set.")

    print()
    print("  For comparison only, the statistical result of olb. It puts")
    print("  sigma = theta_pk/sqrt(2) into a Gaussian tilt that we do not have:")
    theta_rms = theta_pk_openloop / np.sqrt(2.0)
    coupling, tx = olb_statistical_loss(theta_rms)
    print(f"    mean MMF coupling loss   = {fmt_db(coupling.mean_db).strip()} dB")
    print(f"    static (no tilt) loss    = {coupling.meta['static_loss_db']:.3f} dB")
    print(f"    transmit free-space loss = {fmt_db(tx.mean_db).strip()} dB")


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
