"""Show what the receive focal length changes in the beacon camera model.

Commands:
    python scripts/beacon_focal_sweep.py

The script sweeps the focal length with the aperture held at the value in
beacon_camera_snr.py. It uses the day (sunlit cloud) background and the same
margins. It plots six panels: the required beacon power, the sky background
per pixel, the spot on the pixels, the field of view, the centroid error, and
the saturation at 1 km.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import beacon_camera_snr as bc  # noqa: E402

FOCALS_M = np.linspace(0.025, 0.300, 111)
DIVS_FULL_RAD = (3e-3, 10e-3)
Z_FAR, Z_NEAR = bc.RANGES_M[-1], bc.RANGES_M[0]


def at_focal(f_m: float) -> dict:
    """Set the focal length in bc and give the camera quantities for each mode."""
    bc.FOCAL_M = f_m
    bc.SPOT_W_M = bc.BLUR_FACTOR * 0.84 * bc.WAVELENGTH_M * f_m / bc.APERTURE_M
    bc.PEAK_FRAC = (0.5 * erf(np.sqrt(2) * bc.PIXEL_M / bc.SPOT_W_M)) ** 2
    b_rate = bc.background_rate(bc.SKY_L["day"])
    out = {"b_rate": b_rate, "peak": bc.PEAK_FRAC, "spot_px": 2 * bc.SPOT_W_M / bc.PIXEL_M}
    for mode, (fw, read) in bc.MODES.items():
        t = bc.exposure_s(b_rate, fw)
        s = bc.required_signal_e(b_rate * t + bc.DARK_E_S * t + read ** 2)
        p_rx_w = s / (t * bc.signal_rate(1.0))          # W at the aperture
        # Saturation at the short range: no margins, the spot centred on a pixel,
        # the SHORTEST exposure. A value above 1 cannot be cured by the exposure.
        centre = erf(bc.PIXEL_M / (np.sqrt(2) * bc.SPOT_W_M)) ** 2
        clear_e = (p_rx_w * 10 ** (bc.margins_db(Z_NEAR) / 10) * bc.signal_rate(1.0) / bc.PEAK_FRAC
                   * centre + b_rate + bc.DARK_E_S) * bc.T_MIN_S
        # Centroid error at the required SNR. The spot term is sigma_spot / SNR
        # (Winick, DOI 10.1364/JOSAA.3.001809); the pixel adds p^2 / 12 of
        # variance (the uniform pixel response). SNR is the peak-pixel SNR, so
        # this is a pessimistic proxy, not a full centroid estimator.
        nea = np.sqrt((bc.SPOT_W_M / 2) ** 2 + bc.PIXEL_M ** 2 / 12) / f_m / bc.SNR_TARGET
        out[mode] = {"p_rx_dbm": 10 * np.log10(p_rx_w * 1e3), "sat": clear_e / fw, "nea": nea}
    out[bc.LOG_MODE] = {"p_rx_dbm": 10 * np.log10(bc.log_required_rate(b_rate) / bc.signal_rate(1.0) * 1e3)}
    return out


def main() -> None:
    rows = [at_focal(f) for f in FOCALS_M]
    f_mm = FOCALS_M * 1e3
    loss = {th: bc.geometric_loss_db(Z_FAR, bc.WAIST_M, bc.APERTURE_M, bc.WAVELENGTH_M,
                                     divergence_rad=th / 2) for th in DIVS_FULL_RAD}

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 3, figsize=(15, 8.5))
    ax = ax.ravel()
    styles = dict(zip(bc.MODES, ("-", "--")))

    for mode, ls in {**styles, bc.LOG_MODE: ":"}.items():
        for th, c in zip(DIVS_FULL_RAD, ("C0", "C1")):
            p = [r[mode]["p_rx_dbm"] for r in rows] + loss[th] + bc.margins_db(Z_FAR)
            ax[0].plot(f_mm, p, ls=ls, color=c, label=f"{th*1e3:g} mrad, {mode}")
    ax[0].set(title=f"(a) Beacon power at {Z_FAR/1e3:.0f} km, no mispointing loss", ylabel="P_tx [dBm]")

    ax[1].semilogy(f_mm, [r["b_rate"] for r in rows], color="C2")
    ax[1].set(title="(b) Sky background per pixel (sunlit cloud)", ylabel="electrons / s / pixel")

    ax[2].plot(f_mm, [r["peak"] for r in rows], color="C3", label="peak-pixel fraction (corner)")
    tw = ax[2].twinx()
    tw.plot(f_mm, [r["spot_px"] for r in rows], color="C4", label="spot 1/e$^2$ diameter")
    tw.set_ylabel("spot diameter [pixels]", color="C4")
    ax[2].set(title="(c) Spot on the pixels", ylabel="fraction of the beacon in one pixel")
    ax[2].legend(loc="upper center")

    ax[3].plot(f_mm, bc.N_PIX[0] * bc.PIXEL_M / FOCALS_M * 1e3, label="horizontal")
    ax[3].plot(f_mm, bc.N_PIX[1] * bc.PIXEL_M / FOCALS_M * 1e3, label="vertical")
    ax[3].set(title="(d) Field of view (acquisition)", ylabel="FOV [mrad]")

    for mode, ls in styles.items():
        ax[4].plot(f_mm, [r[mode]["nea"] * 1e6 for r in rows], ls=ls, color="C5", label=mode)
        ax[5].semilogy(f_mm, [r[mode]["sat"] for r in rows], ls=ls, color="C6", label=mode)
    ax[4].set(title=f"(e) Centroid error at SNR {bc.SNR_TARGET:g} (proxy)", ylabel="1-sigma [urad]")
    ax[5].axhline(1, color="k", lw=0.8)
    ax[5].set(title=f"(f) Peak pixel at {Z_NEAR/1e3:.0f} km, clear day, {bc.T_MIN_S*1e6:.0f} us exposure",
              ylabel="charge / full well (> 1 saturates)")

    for a in ax:
        a.axvline(140, color="grey", lw=0.8, ls=":")
        a.set_xlabel("Effective focal length [mm]")
        a.grid(True, alpha=0.3)
        if a is not ax[2] and a.get_legend_handles_labels()[0]:
            a.legend(fontsize=8)
    fig.suptitle(f"Beacon camera: what the focal length changes (D = {bc.APERTURE_M*1e3:.0f} mm, "
                 f"WiDy SenS 320V-ST, day; dotted line = 140 mm)")
    fig.tight_layout()
    out = Path(__file__).resolve().parents[1] / "figures" / "beacon_focal_sweep.png"
    fig.savefig(out, dpi=150)
    print(f"Figure: {out}")


if __name__ == "__main__":
    main()
