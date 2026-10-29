"""Calculate the vacuum link loss of a beacon beam against its divergence.

Commands:
    python scripts/beacon_divergence_loss.py                  # table and figure
    python scripts/beacon_divergence_loss.py --aperture-mm 50

The beacon is a Gaussian beam with a 2 mm 1/e^2 waist DIAMETER at 1550 nm.
The divergence axis is the FULL 1/e^2 angle (2 theta). olb takes the HALF
angle, so the script divides by 2. Use --half-angle to read the axis as the
half angle.

The loss is the geometric spread loss only: the fraction of the Gaussian
power inside the receive aperture. There is no turbulence, no extinction and
no pointing error. The beam is in the far field at every point of the sweep
(z / z_R > 300), so the closed form is exact and a wave-optics vacuum solve
adds nothing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "C:/repos/optical_link_budget")
sys.path.insert(0, "D:/repos/optical_link_budget")

from olb.beam import free_space_radius  # noqa: E402
from olb.models.geometric import geometric_loss_db  # noqa: E402

WAVELENGTH_M = 1550e-9
WAIST_M = 1e-3                  # m, 1/e^2 RADIUS (2 mm diameter)
RANGES_M = (1e3, 10e3)
DIVERGENCE_RAD = np.linspace(1e-3, 10e-3, 91)   # the plot axis


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aperture-mm", type=float, default=25.0,
                        help="receive aperture diameter [mm] (default 25, the project baseline)")
    parser.add_argument("--half-angle", action="store_true",
                        help="read the divergence axis as the 1/e^2 half angle")
    args = parser.parse_args()

    d_rx = args.aperture_mm * 1e-3
    half = DIVERGENCE_RAD if args.half_angle else DIVERGENCE_RAD / 2
    label = "half" if args.half_angle else "full"
    theta_min = WAVELENGTH_M / (np.pi * WAIST_M)
    print(f"Beacon: w0 = {WAIST_M*1e3:.1f} mm, lambda = {WAVELENGTH_M*1e9:.0f} nm, "
          f"diffraction half angle = {theta_min*1e3:.3f} mrad")
    print(f"Receive aperture D = {args.aperture_mm:.1f} mm. Divergence axis = {label} angle.")

    # olb.beam.virtual_waist takes a scalar divergence, so loop.
    loss = {z: np.array([geometric_loss_db(z, WAIST_M, d_rx, WAVELENGTH_M, divergence_rad=t)
                         for t in half]) for z in RANGES_M}

    print(f"\n{label} angle [mrad] | " + " | ".join(
        f"w({z/1e3:.0f} km) [m]  loss [dB]" for z in RANGES_M))
    for i in range(0, len(DIVERGENCE_RAD), 10):
        cols = " | ".join(
            f"{free_space_radius(WAIST_M, z, half[i], WAVELENGTH_M):10.3f}  {loss[z][i]:9.2f}"
            for z in RANGES_M)
        print(f"{DIVERGENCE_RAD[i]*1e3:16.1f} | {cols}")

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for z in RANGES_M:
        ax.plot(DIVERGENCE_RAD * 1e3, loss[z], label=f"{z/1e3:.0f} km")
    ax.set_xlabel(f"Beacon divergence, 1/e$^2$ {label} angle [mrad]")
    ax.set_ylabel("Geometric link loss [dB]")
    ax.set_title(f"Beacon vacuum loss: w0 = 1 mm, 1550 nm, D$_{{rx}}$ = {args.aperture_mm:.0f} mm")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = Path(__file__).resolve().parents[1] / "figures" / (
        f"beacon_divergence_loss_D{args.aperture_mm:.0f}mm_{label}.png")
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"\nFigure: {out}")


if __name__ == "__main__":
    main()
