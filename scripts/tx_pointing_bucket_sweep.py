"""Calculate the vacuum bucket power against the transmit pointing error and divergence.

Commands:
    python scripts/tx_pointing_bucket_sweep.py
    python scripts/tx_pointing_bucket_sweep.py --range-km 1 --aperture-mm 50.8

The transmit beam is a Gaussian beam with a 9.08 mm 1/e^2 waist RADIUS at
1550 nm. The divergence axis is the far-field 1/e^2 HALF angle. A divergence
above the diffraction limit is a defocused beam from the same aperture, the
olb virtual-waist model.

The bucket power is the fraction of the transmit power inside the receive
aperture. The beam centre is offset by L*theta_err from the aperture centre.
The closed form is the noncentral chi-square CDF (the Marcum Q function). It
is exact for any offset and any aperture. There is no turbulence and no
extinction. The beam is in the far field (L/z_R ~ 60 at 10 km).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.stats import ncx2

sys.path.insert(0, "C:/repos/optical_link_budget")
sys.path.insert(0, "D:/repos/optical_link_budget")

from olb.beam import free_space_radius, w0_to_div  # noqa: E402

WAVELENGTH_M = 1550e-9
WAIST_M = 9.08e-3                               # m, 1/e^2 RADIUS at the Tx aperture
THETA_MIN = w0_to_div(WAIST_M, WAVELENGTH_M)    # rad, the diffraction half angle
DIVERGENCE_RAD = np.array([THETA_MIN, 75e-6, 100e-6, 150e-6, 200e-6, 300e-6])
POINTING_RAD = np.linspace(0, 400e-6, 401)      # the plot axis


def bucket_loss_db(w_rx, offset_m, a_rx):
    """Return the loss [dB] of the Gaussian power inside a circle of radius a_rx.

    The beam has the 1/e^2 radius w_rx and its centre is offset_m from the
    circle centre. Each axis of the beam has sigma = w_rx/2. The value is inf
    where the CDF underflows, beyond approximately 300 dB.
    """
    sigma = w_rx / 2
    return -10 / np.log(10) * ncx2.logcdf((a_rx / sigma) ** 2, 2, (offset_m / sigma) ** 2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--range-km", type=float, default=10.0, help="link range [km] (default 10)")
    parser.add_argument("--aperture-mm", type=float, default=50.8,
                        help="receive aperture diameter [mm] (default 50.8, 2 in)")
    args = parser.parse_args()

    L = args.range_km * 1e3
    a_rx = args.aperture_mm * 1e-3 / 2
    w_rx = np.array([free_space_radius(WAIST_M, L, t, WAVELENGTH_M) for t in DIVERGENCE_RAD])
    loss = bucket_loss_db(w_rx[:, None], L * POINTING_RAD[None, :], a_rx)

    print(f"Tx: w0 = {WAIST_M*1e3:.2f} mm, lambda = {WAVELENGTH_M*1e9:.0f} nm, "
          f"diffraction half angle = {THETA_MIN*1e6:.1f} urad")
    print(f"Rx: D = {args.aperture_mm:.1f} mm at L = {args.range_km:.1f} km. "
          "Bucket loss = -10 log10(P_bucket / P_tx), vacuum.\n")
    cols = [0, 25, 50, 75, 100, 150, 200, 300, 400]
    print("theta_div [urad]  w(L) [m] | loss [dB] at pointing error [urad]")
    print(" " * 27 + "|" + "".join(f"{c:7d}" for c in cols))
    for t, w, row in zip(DIVERGENCE_RAD, w_rx, loss):
        print(f"{t*1e6:16.1f}  {w:8.3f} |" + "".join(f"{row[c]:7.1f}" for c in cols))

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for t, row in zip(DIVERGENCE_RAD, loss):
        ax.plot(POINTING_RAD * 1e6, row, label=f"{t*1e6:.0f} urad")
    ax.plot(POINTING_RAD * 1e6, loss.min(axis=0), "k--", lw=1, label="best of the set")
    ax.set_xlabel("Tx pointing error [urad]")
    ax.set_ylabel("Bucket loss, Tx to Rx aperture [dB]")
    ax.set_title(f"Vacuum bucket loss: w0 = 9.08 mm, 1550 nm, L = {args.range_km:.0f} km, "
                 f"D = {args.aperture_mm:.1f} mm")
    ax.set_ylim(top=min(loss.max(), 80))
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)
    ax.legend(title="Tx half angle")
    fig.tight_layout()
    out = Path(__file__).resolve().parents[1] / "figures" / (
        f"tx_pointing_bucket_L{args.range_km:.0f}km_D{args.aperture_mm:.0f}mm.png")
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"\nFigure: {out}")


if __name__ == "__main__":
    main()
