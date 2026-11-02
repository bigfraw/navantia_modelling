"""Calculate the beacon power that a camera needs to see the beacon spot.

Commands:
    python scripts/beacon_camera_snr.py

The script extends beacon_divergence_loss.py. It takes the vacuum geometric
loss, adds a stack of safety margins, puts the received power on the camera,
and adds the sky background, the dark current, and the read noise. It then
solves for the transmit power that gives the target SNR in the PEAK pixel.

The camera is the NIT WiDy SenS 320V-ST (datasheet V1.3). The script runs
both CTIA gain modes. The dark current at 25 C and the low-gain well and read
noise are MEASURED on this camera. The lens, the filter, and the margins are
PLACEHOLDERS. The "day" case is a MEGA-SAFE background: a sunlit white
cloud (Lambertian, full sea-level solar irradiance) fills the pixel. The direct
sun or a sun glint in the pixel is a separate exclusion.

TO DO - FIDELITY-2 SIMULATIONS. The turbulence values of the pessimistic
budget are ASSUMED, not computed: FADE_MARGIN_DB (15 dB), BLUR_FACTOR (3x),
and the worst-case spot on a pixel corner. Run olb fidelity-2 terrestrial
campaigns (a diverged 2 mm beacon launch, 1 km and 10 km, maritime Cn2,
L0 = 25 m) with a Camera detector. Take the fade quantile of the received
irradiance and the spot size and spot motion (olb.waveoptics.camera
spot_metrics) from the campaigns. Then replace the three values.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "C:/repos/optical_link_budget")
sys.path.insert(0, "D:/repos/optical_link_budget")

from beacon_divergence_loss import DIVERGENCE_RAD, RANGES_M, WAIST_M, WAVELENGTH_M  # noqa: E402
from olb.beam import free_space_radius  # noqa: E402
from olb.models.geometric import geometric_loss_db  # noqa: E402

H, C = 6.62607015e-34, 2.99792458e8
E_PHOTON = H * C / WAVELENGTH_M          # J

# --- Camera: NIT WiDy SenS 320V-ST datasheet V1.3 ---------------------------
PIXEL_M = 15e-6          # m, the pixel pitch
N_PIX = (320, 256)       # the sensor format
QE = 0.70                # the datasheet gives "> 70 %"
# CTIA gain modes: (full well [e-], read noise [e- rms])
# High gain: datasheet. Low gain: MEASURED on this camera (Lin/Itr, Analog Gain
# Low, CDS off, 160 MHz), handover_beacon_P1_20261030_dark, at g = 23.6 e-/count
# (range 22.7 to 28.5). The well is the linear range: raw 10,750 minus the
# 1,641 offset. The datasheet 380 ke- is the ADC full scale, not the well.
MODES = {"CTIA high gain (CDS)": (17e3, 50.0),
         "CTIA low gain": (215e3, 203.0)}
T_MIN_S, T_MAX_S = 10e-6, 1e-3   # s, the minimum exposure; 1 ms keeps 1 kHz frames
# MEASURED: the factory lens-capped dark tables at 25 C (160MHz/LIN/Low), the
# median pixel slope. The capped run of 2026-10-30 gave 3.3e4. Pixel p90: 6.5e4.
DARK_REF_E_S = 3.0e4    # e-/s/pixel at 25 C
# The TEC holds the sensor 15 C below the housing (datasheet). A hot deck in
# the sun can put the housing at the 65 C operating limit.
HOUSING_T_C = 60.0       # C, <-- PLACEHOLDER, the worst-case housing temperature
TEC_DELTA_C = 15.0       # C, the datasheet cooling capacity
SENSOR_T_C = HOUSING_T_C - TEC_DELTA_C
# InGaAs dark current is diffusion-limited near room temperature:
# I ~ T^3 exp(-Eg / kT), Eg = 0.74 eV (Rogalski, DOI 10.1201/b10319).
# <-- THEORY: no temperature sweep was measured (test plan, Test A).
_EG_EV, _K_EV = 0.74, 8.617e-5
_T1, _T0 = SENSOR_T_C + 273.15, 298.15
DARK_E_S = DARK_REF_E_S * (_T1 / _T0) ** 3 * np.exp(-_EG_EV / _K_EV * (1 / _T1 - 1 / _T0))
WELL_BUDGET = 0.5        # <-- PLACEHOLDER, the background + dark may fill this fraction

# --- Log mode (photovoltaic, no integration well) ---------------------------
# The pixel reports code = LOG_LSB_DECADE * log10(I_total / I_floor). The
# datasheet gives the slope (600 LSB/decade), the 120 dB range, and a 10 ms
# maximum integration. It does NOT give the code noise in LSB or the floor.
LOG_MODE = "Log (ESTIMATED noise)"   # the name carries the warning into every table and plot
LOG_LSB_DECADE = 600.0   # LSB/decade, datasheet
LOG_RANGE_DECADES = 6.0  # 120 dB = 20 log10(1e6), datasheet
LOG_NOISE_LSB = 5.0      # LSB rms, <-- PLACEHOLDER, the temporal code noise. Ask NIT.
LOG_FPN_LSB = 5.0        # LSB rms, <-- PLACEHOLDER, the residual FPN after NUC (worse off 25 C)
# The floor current of the pixel. It follows the dark current with the
# temperature. <-- PLACEHOLDER: the dark rate is the floor.

# --- Receive lens: PLACEHOLDERS ---------------------------------------------
APERTURE_M = 0.025       # m, <-- PLACEHOLDER, the receive lens clear aperture
FOCAL_M = 0.140          # m, <-- PLACEHOLDER, 35 mm lens x 4 (owner, 2026-10-20)
SNR_TARGET = 10.0        # <-- PLACEHOLDER, the peak-pixel SNR for detection

# --- Filter and optics transmission: PLACEHOLDERS ---------------------------
FILTER_FWHM_UM = 0.010   # um, <-- PLACEHOLDER, 10 nm band-pass at 1550 nm
T_FILTER = 0.80          # <-- PLACEHOLDER, the filter peak transmission
T_OPTICS = 0.50          # <-- PLACEHOLDER, the lens, the window, and the dirt

# --- Sky background ---------------------------------------------------------
# A Lambertian cloud of albedo rho under the sea-level solar spectral
# irradiance E has the radiance L = rho E / pi. E is about 250 W/m^2/um at
# 1550 nm (Gueymard, DOI 10.1016/j.solener.2003.08.039).
SOLAR_E_W_M2_UM = 250.0
CLOUD_ALBEDO = 0.8
SKY_L = {"day": CLOUD_ALBEDO * SOLAR_E_W_M2_UM / np.pi}  # W/m^2/sr/um

# --- Link safety margins [dB]: PLACEHOLDERS, deliberately large -------------
# Extinction: Kim et al. visibility model, 5 km haze, q = 0.16 V + 0.34,
# alpha = (3.91/V) (lambda/550 nm)^-q (DOI 10.1117/12.417512).
_V_KM = 5.0
EXT_DB_KM = 4.343 * 3.91 / _V_KM * (1550 / 550) ** -(0.16 * _V_KM + 0.34)
FADE_MARGIN_DB = 15.0    # <-- PLACEHOLDER, ASSUMED. TO DO: fidelity-2 fade quantile
# Beacon pointing error: a FIXED angle that the mount sets, not a fraction of
# the divergence (docs/interfaces/beacon_divergence_spec_note.md). A Gaussian
# beam loses exp(-2 (theta_e/theta)^2) (Toyoshima et al.,
# DOI 10.1364/JOSAA.19.000567). With the far-field 1/theta^2 spread, the
# required power is a minimum at theta = sqrt(2) theta_e (half angle).
THETA_E_RAD = {"tracking": 0.2e-3,     # rad, <-- PLACEHOLDER, mount tracking residual
               "acquisition": 2.0e-3}  # rad, <-- PLACEHOLDER, open-loop uncertainty
# The 2 mm waist cannot make a beam narrower than its diffraction limit.
THETA_DIFF_RAD = WAVELENGTH_M / (np.pi * WAIST_M)
EXTRA_MARGIN_DB = 6.0    # <-- PLACEHOLDER, the unknown unknowns

# --- Spot on the sensor -----------------------------------------------------
# A Gaussian fit to the Airy pattern has sigma = 0.21 lambda / NA, with
# NA = D / (2 f), so the 1/e^2 radius is w = 0.84 lambda f / D (Zhang et al.,
# DOI 10.1364/AO.46.001819). BLUR_FACTOR covers the turbulence blur, the
# defocus, and the lens aberration.
BLUR_FACTOR = 3.0        # <-- PLACEHOLDER, ASSUMED. TO DO: fidelity-2 spot_metrics
SPOT_W_M = BLUR_FACTOR * 0.84 * WAVELENGTH_M * FOCAL_M / APERTURE_M
# The worst case puts the spot centre on a pixel corner. Then one pixel holds
# [0.5 erf(sqrt(2) p / w)]^2 of the spot power (the Gaussian integral).
PEAK_FRAC = (0.5 * erf(np.sqrt(2) * PIXEL_M / SPOT_W_M)) ** 2


def margins_db(z_m: float) -> float:
    """Give the sum of the link safety margins at the range z_m [dB]."""
    return EXT_DB_KM * z_m / 1e3 + FADE_MARGIN_DB + EXTRA_MARGIN_DB


def mispoint_db(theta_half, theta_e: float):
    """Give the beacon mispointing loss [dB] at the 1/e^2 half angle theta_half.

    The loss is 10 log10(e) 2 (theta_e / theta)^2 (Toyoshima et al.,
    DOI 10.1364/JOSAA.19.000567).
    """
    return 10 * np.log10(np.e) * 2 * (theta_e / np.asarray(theta_half)) ** 2


def signal_rate(p_w):
    """Give the peak-pixel electron rate [e-/s] for the power p_w at the aperture."""
    return p_w * PEAK_FRAC * T_FILTER * T_OPTICS * QE / E_PHOTON


def background_rate(radiance: float) -> float:
    """Give the background electron rate in one pixel [e-/s].

    P = L dlambda A (p/f)^2 T, the radiance through the aperture into the pixel
    solid angle (the etendue, Howell, DOI 10.1017/CBO9780511807909).
    """
    area = np.pi * APERTURE_M ** 2 / 4
    p_bg = radiance * FILTER_FWHM_UM * area * (PIXEL_M / FOCAL_M) ** 2 * T_FILTER * T_OPTICS
    return p_bg * QE / E_PHOTON


def exposure_s(bg_rate: float, full_well: float) -> float:
    """Give the longest exposure that keeps background + dark under WELL_BUDGET.

    In the background-limited case the required power falls as 1/sqrt(t), so
    the longest exposure that does not fill the well is the best.
    """
    return float(np.clip(WELL_BUDGET * full_well / (bg_rate + DARK_E_S), T_MIN_S, T_MAX_S))


def required_signal_e(noise0_e2: float) -> float:
    """Give the signal electrons S that give SNR_TARGET.

    SNR = S / sqrt(S + N0), with N0 = B + D t + R^2 (the CCD equation, Howell,
    DOI 10.1017/CBO9780511807909). Solve S^2 = k^2 (S + N0) for S.
    """
    k2 = SNR_TARGET ** 2
    return 0.5 * (k2 + np.sqrt(k2 ** 2 + 4 * k2 * noise0_e2))


def log_required_rate(bg_rate: float) -> float:
    """Give the peak-pixel signal rate [e-/s] that the log mode can detect.

    The spot raises the code above the next pixels by
    dcode = LOG_LSB_DECADE log10(1 + S / (B + D)). Detection needs
    dcode >= SNR_TARGET sigma, with sigma the temporal and the FPN code noise
    in quadrature. Solve for S. The detection threshold is a contrast, so the
    required signal scales with the background. The model ignores any change
    of the noise with the signal level.
    """
    sigma = np.hypot(LOG_NOISE_LSB, LOG_FPN_LSB)
    return (bg_rate + DARK_E_S) * (10 ** (SNR_TARGET * sigma / LOG_LSB_DECADE) - 1)


def receive_requirements(radiance: float = SKY_L["day"]) -> dict:
    """Give the receive requirement for each camera mode (stage 1).

    Returns {mode: (p_rx_dbm, t_int_s or None)}. p_rx_dbm is the power at the
    receive aperture that gives SNR_TARGET in the peak pixel, against the sky
    radiance [W/m^2/sr/um]. It does not depend on the beacon, the divergence,
    or the range.
    """
    b_rate = background_rate(radiance)
    out = {}
    for mode, (fw, read) in MODES.items():
        t = exposure_s(b_rate, fw)
        s = required_signal_e(b_rate * t + DARK_E_S * t + read ** 2)
        out[mode] = (10 * np.log10(s / (t * signal_rate(1.0)) * 1e3), t)
    out[LOG_MODE] = (10 * np.log10(log_required_rate(b_rate) / signal_rate(1.0) * 1e3), None)
    return out


def required_ptx_dbm(p_rx_dbm: float, z_m: float, theta_half, theta_e: float):
    """Give the beacon power [dBm] for the receive requirement p_rx_dbm.

    P_tx = P_rx + geometric loss + margins + mispointing loss, all in dB.
    """
    theta_half = np.atleast_1d(theta_half)
    geo = np.array([geometric_loss_db(z_m, WAIST_M, APERTURE_M, WAVELENGTH_M, divergence_rad=t)
                    for t in theta_half])
    return p_rx_dbm + geo + margins_db(z_m) + mispoint_db(theta_half, theta_e)


def main() -> None:
    ifov = PIXEL_M / FOCAL_M
    print("Beacon camera model: NIT WiDy SenS 320V-ST, PLACEHOLDER lens, filter and margins")
    print(f"  lens D = {APERTURE_M*1e3:.0f} mm, f = {FOCAL_M*1e3:.0f} mm, pixel = {PIXEL_M*1e6:.0f} um, "
          f"IFOV = {ifov*1e6:.0f} urad, FOV = {N_PIX[0]*ifov*1e3:.0f} x {N_PIX[1]*ifov*1e3:.0f} mrad")
    print(f"  spot 1/e^2 radius = {SPOT_W_M*1e6:.1f} um (blur x{BLUR_FACTOR:g}), "
          f"worst-case peak-pixel fraction = {PEAK_FRAC:.3f}")
    print(f"  filter {FILTER_FWHM_UM*1e3:g} nm x {T_FILTER}, optics {T_OPTICS} "
          f"-> {-10*np.log10(T_FILTER*T_OPTICS):.1f} dB")
    print(f"  sensor {SENSOR_T_C:.0f} C (housing {HOUSING_T_C:.0f} C - TEC {TEC_DELTA_C:.0f} C): dark "
          f"{DARK_E_S:.2g} e-/s = {DARK_E_S/DARK_REF_E_S:.1f}x the measured 25 C value (temperature law is THEORY)")
    print(f"  margins: extinction {EXT_DB_KM:.2f} dB/km, fade {FADE_MARGIN_DB:g} dB, "
          f"extra {EXTRA_MARGIN_DB:g} dB; the mispointing loss is per divergence")
    for z in RANGES_M:
        print(f"    total margin at {z/1e3:.0f} km = {margins_db(z):.1f} dB")
    print("  TO DO: the fade margin and the blur factor are ASSUMED. Run fidelity-2 sims"
          " (see the module docstring).")
    print(f"  diffraction floor of the 2 mm beam: {THETA_DIFF_RAD*1e3:.3f} mrad half angle "
          f"({2*THETA_DIFF_RAD*1e3:.2f} mrad full)")

    # Stage 1: the camera. The beacon irradiance at the receive aperture that
    # gives SNR_TARGET in the peak pixel. E_ap = P_rx / A. The peak pixel
    # receives E_pix = P_rx T PEAK_FRAC / p^2.
    rx = receive_requirements()
    area = np.pi * APERTURE_M ** 2 / 4
    print(f"\nSTAGE 1 - camera requirement (sky {SKY_L['day']:.0f} W/m^2/sr/um, SNR {SNR_TARGET:g}):")
    print("  mode                 | E at aperture [W/m^2] | E on peak pixel [W/m^2] | "
          "e-/s in peak pixel | P_rx [dBm] | t_int")
    for mode, (p, t) in rx.items():
        p_w = 10 ** (p / 10) * 1e-3
        e_pix = p_w * T_FILTER * T_OPTICS * PEAK_FRAC / PIXEL_M ** 2
        exp = f"{t*1e6:.0f} us" if t else "-"
        print(f"  {mode:20} | {p_w/area:21.3g} | {e_pix:23.3g} | {signal_rate(p_w):18.3g} | "
              f"{p:10.1f} | {exp}")
    print(f"  WARNING: the log row is an ESTIMATE. The datasheet gives no log code noise or floor.\n"
          f"  The values are guesses: {LOG_NOISE_LSB:g} LSB temporal + {LOG_FPN_LSB:g} LSB FPN, "
          f"floor = dark current.\n  Replace them with the bench results "
          f"(docs/lab/log_mode_noise_test_plan.md, Tests A and B).")
    print("\nSTAGE 2 - beacon power to deliver that irradiance (P_tx = E_ap A x losses):")

    half = DIVERGENCE_RAD / 2
    ptx = {(m, ph, z): required_ptx_dbm(p, z, half, te)
           for m, (p, _) in rx.items() for ph, te in THETA_E_RAD.items() for z in RANGES_M}

    for ph, te in THETA_E_RAD.items():
        opt = np.sqrt(2) * te
        print(f"\n{ph}: theta_e = {te*1e3:.2f} mrad, optimum half angle sqrt(2) theta_e = "
              f"{opt*1e3:.2f} mrad ({2*opt*1e3:.2f} mrad full)")
        if opt < THETA_DIFF_RAD:
            print(f"  THE OPTIMUM IS BELOW THE DIFFRACTION FLOOR. The 2 mm beam cannot reach it. "
                  f"Use a larger launch waist (w0 >= {WAVELENGTH_M/(np.pi*opt)*1e3:.1f} mm) "
                  f"or accept the floor.")
        keys = [k for k in ptx if k[1] == ph]
        print("  full [mrad] | " + " | ".join(f"2w {z/1e3:2.0f}km [m]" for z in RANGES_M) + " | "
              + " | ".join(f"{ {LOG_MODE: 'logE'}.get(m, m[5:9]):4} {z/1e3:2.0f}km" for m, _, z in keys))
        for i in range(0, len(DIVERGENCE_RAD), 10):
            cols = " | ".join(f"{2*free_space_radius(WAIST_M, z, half[i], WAVELENGTH_M):12.2f}"
                              for z in RANGES_M) + " | " + " | ".join(f"{ptx[k][i]:9.1f}" for k in keys)
            print(f"  {DIVERGENCE_RAD[i]*1e3:11.1f} | {cols}")
        for k in keys:
            j = int(np.argmin(ptx[k]))
            print(f"  minimum {k[0]}, {k[2]/1e3:.0f} km: {ptx[k][j]:.1f} dBm at "
                  f"{DIVERGENCE_RAD[j]*1e3:.1f} mrad full")

    # Saturation check at the short range: a clear, calm day, perfect pointing,
    # the spot centred on one pixel. The peak signal is then the requirement
    # times all the margins and the mispointing allowance. At the optimum the
    # allowance is exp(-1) = 4.3 dB, at every theta_e.
    z0 = RANGES_M[0]
    centre_gain = erf(PIXEL_M / (np.sqrt(2) * SPOT_W_M)) ** 2 / PEAK_FRAC
    allow_db = margins_db(z0) + 10 * np.log10(np.e)
    print(f"\nSaturation check at {z0/1e3:.0f} km, at the optimum divergence, no margins used, "
          f"spot centred on a pixel:")
    b_rate = background_rate(SKY_L["day"])
    for mode, (fw, _) in MODES.items():
        p, t = rx[mode]
        e = (signal_rate(10 ** ((p + allow_db) / 10) * 1e-3) * centre_gain + b_rate + DARK_E_S) * t
        print(f"  {mode}: {e/fw:.0f}x full well at t_int {t*1e6:.0f} us. The exposure "
              f"control must cut t by this factor (floor {T_MIN_S*1e6:.0f} us).")
    # The log mode has no well. It clips when the total current passes the
    # floor by more than the datasheet range.
    tot = signal_rate(10 ** ((rx[LOG_MODE][0] + allow_db) / 10) * 1e-3) * centre_gain + b_rate + DARK_E_S
    print(f"  {LOG_MODE}: {np.log10(tot / DARK_E_S):.1f} decades above the floor, "
          f"of {LOG_RANGE_DECADES:g} available.")

    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(THETA_E_RAD), figsize=(12, 4.8), sharey=True)
    for ax, (ph, te) in zip(axes, THETA_E_RAD.items()):
        for (m, p, z), y in ptx.items():
            if p != ph:
                continue
            c = "C0" if z == RANGES_M[0] else "C1"
            ax.plot(DIVERGENCE_RAD * 1e3, y, color=c,
                    ls={LOG_MODE: ":", "CTIA low gain": "--"}.get(m, "-"), label=f"{z/1e3:.0f} km, {m}")
            j = int(np.argmin(y))
            ax.plot(DIVERGENCE_RAD[j] * 1e3, y[j], "*", color=c, ms=9)
        ax.axvline(2 * np.sqrt(2) * te * 1e3, color="grey", lw=0.8, ls=":")
        ax.axvspan(0, 2 * THETA_DIFF_RAD * 1e3, color="grey", alpha=0.15)
        ax.set_xlim(DIVERGENCE_RAD[0] * 1e3 * 0.9, DIVERGENCE_RAD[-1] * 1e3)
        ax.set_title(f"{ph}: theta_e = {te*1e3:g} mrad (dotted: optimum)")
        ax.set_xlabel("Beacon divergence, 1/e$^2$ full angle [mrad]")
        ax.grid(True, alpha=0.3)
    axes[0].set_ylim(top=40)   # the acquisition curve runs away below its optimum
    axes[0].set_ylabel(f"Beacon power for peak-pixel SNR {SNR_TARGET:g} [dBm]")
    axes[0].legend(fontsize=7)
    fig.suptitle("WiDy SenS 320V-ST beacon camera, day, mega-safe margins, log noise ESTIMATED (shaded: below the "
                 "diffraction floor; star: minimum)")
    fig.tight_layout()
    out = Path(__file__).resolve().parents[1] / "figures" / "beacon_camera_power.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"\nFigure: {out}")

    # Stage 1 figure: the required aperture irradiance against the sky radiance.
    radiances = np.logspace(-2, 2, 81)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for m in rx:
        e_ap = [10 ** (receive_requirements(r)[m][0] / 10) * 1e-3 / area for r in radiances]
        ax.loglog(radiances, e_ap, ls={LOG_MODE: ":", "CTIA low gain": "--"}.get(m, "-"), label=m)
    ax.axvline(SKY_L["day"], color="grey", lw=0.8, ls=":")
    ax.text(SKY_L["day"], ax.get_ylim()[0], " sunlit cloud\n (design)", fontsize=8, va="bottom")
    ax.set_xlabel("Sky radiance in the pixel at 1550 nm [W/m$^2$/sr/um]")
    ax.set_ylabel(f"Beacon irradiance at the aperture for SNR {SNR_TARGET:g} [W/m$^2$]")
    ax.set_title(f"Stage 1: camera requirement, log mode ESTIMATED (f = {FOCAL_M*1e3:.0f} mm, D = {APERTURE_M*1e3:.0f} mm, "
                 f"{FILTER_FWHM_UM*1e3:g} nm filter)", fontsize=10)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = out.with_name("beacon_camera_irradiance.png")
    fig.savefig(out, dpi=150)
    print(f"Figure: {out}")


if __name__ == "__main__":
    main()
