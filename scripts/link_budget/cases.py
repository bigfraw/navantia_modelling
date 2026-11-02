"""The cases of the 10 km terrestrial MMF evaluation, and the shared reads.

THE SPACE. A 10 km (and a 1 km) horizontal path at 1550 nm, constant Cn2 of 1e-15, 5e-15
and 1e-14 m^-2/3, outer scale 25 m. The two terminals are the same (a
symmetric link). Each terminal launches a collimated Gaussian and focuses the
received beam onto a 105 um core, NA 0.22, multimode fibre (MMF). A terminal
is monostatic, so the launch beam sets the focal length: f is the telescope
magnification times the collimator focal length.

| Case            | Launch 1/e^2 diameter | Aperture      | f         |
| --------------- | --------------------- | ------------- | --------- |
| b9_1in_circle   | 4 x 2.27 = 9.08 mm    | 1 in, circle  | 50.24 mm  |
| b9_1in_ellipse  | 4 x 2.27 = 9.08 mm    | 1 in, 45 deg  | 50.24 mm  |
| b18_1in_circle  | 4 x 4.65 = 18.6 mm    | 1 in, circle  | 70 mm     |
| b18_1in_ellipse | 4 x 4.65 = 18.6 mm    | 1 in, 45 deg  | 70 mm     |
| b18_2in_circle  | 8 x 2.27 = 18.2 mm    | 2 in, circle  | 100.48 mm |
| b36_2in_circle  | 16 x 2.27 = 36.3 mm   | 2 in, circle  | 200.96 mm |

The 36.3 mm 2 in case is a benchmark only. The 18.2 mm 2 in case (10 km only)
has half that launch; its f NA = 22.1 mm is under the 25.4 mm aperture
radius, so the NA gate clips the outer pupil. A "45 deg" aperture is the circle seen at
45 deg: an ellipse of semi-axes a (y) and a cos 45 (x). The launch clip and
the receive mask both use it (`olb.terminal.Transmitter.tilt_deg`).

THE RECORDS. Some cells already ran in the olb study
`validation/terrestrial_mmf_tiptilt` (LEGACY below). This module opens them
read-only with the same key. The new cells go to `data/` next to this file.
On bigfraw that is `D:\\repos\\navantia_modelling\\scripts\\link_budget\\data`.

THE READ (`read`). It takes the stored crop of the receive field (1.5
aperture radii), Fourier-upsamples it (the olb MMF auto factor), and builds
the terminal mask on the fine grid. It gives the bucket ratio, the MMF eta
open and with a perfect receive G-tilt removed, and the sensed G-tilt and
Z-tilt angles (Noll, DOI 10.1364/JOSA.66.000207; Tyler,
DOI 10.1364/JOSAA.11.000358). The fibre power of a trial is

    P_fibre / P_telescope = launch_fraction * collected * ratio * eta
"""

import dataclasses
import os

import numpy as np

import olb
from olb.geometry import HorizontalPath
from olb.scenario import TerrestrialChannel, TerrestrialScenario
from olb.terminal import MMF, Terminal, Transmitter
from olb.waveoptics.compensation.modal import ApertureModes
from olb.waveoptics.compensation.slopes import wrapped_gradient
from olb.waveoptics.field import Field
from olb.waveoptics.mmf import (_resolve_auto_factor, _upsampled_field,
                                mmf_coupling_efficiency)
from olb.waveoptics.turbulence import Campaign
from olb.waveoptics.turbulence.run import SLOPE_MIN_MODES
from olb.waveoptics.turbulence.sampling import turbulent_grid

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OLB_CAMPAIGNS = os.path.join(os.path.dirname(os.path.dirname(olb.__file__)),
                             "validation", "terrestrial_mmf_tiptilt",
                             "campaigns")

LAM = 1550e-9
PATHS = (10e3, 1e3)
CN2 = (1e-15, 5e-15, 1e-14)
CORE_RADIUS_M = 105e-6 / 2
NA = 0.22
SEED = 20261005
PRESET = "standard"
BLOCK = 50
TILT_DEG = 45.0
# The focal length that the legacy 9.08 mm campaigns RAN with (the removed
# optimal_focus rule). It sets only the in-run scalar mmf_eta, but it is in
# the campaign key, so it stays to reopen them. The same expression as the
# olb study, so the float is the same.
F_RUN_B9 = np.pi * (0.0254 / 2) * CORE_RADIUS_M / (1.12 * LAM)


@dataclasses.dataclass(frozen=True)
class Case:
    waist_m: float           # launch 1/e^2 radius
    aperture_m: float        # aperture diameter, both ends
    tilt_deg: object         # None (circle) or 45 (ellipse)
    f_read: float            # the coupler of record
    f_run: float             # the in-run MMF f (campaign key only)
    n_px: int                # pinned pixel count on the sized side, 10 km


CASES = {
    "b9_1in_circle": Case(4 * 2.27e-3 / 2, 0.0254, None, 4 * 12.56e-3,
                          F_RUN_B9, 4096),
    "b9_1in_ellipse": Case(4 * 2.27e-3 / 2, 0.0254, TILT_DEG, 4 * 12.56e-3,
                           4 * 12.56e-3, 4096),
    "b18_1in_circle": Case(4 * 4.65e-3 / 2, 0.0254, None, 4 * 17.5e-3,
                           4 * 17.5e-3, 4096),
    "b18_1in_ellipse": Case(4 * 4.65e-3 / 2, 0.0254, TILT_DEG, 4 * 17.5e-3,
                            4 * 17.5e-3, 4096),
    "b18_2in_circle": Case(8 * 2.27e-3 / 2, 0.0508, None, 8 * 12.56e-3,
                           8 * 12.56e-3, 4096),
    "b36_2in_circle": Case(16 * 2.27e-3 / 2, 0.0508, None, 16 * 12.56e-3,
                           4 * 12.56e-3, 2048),
}

# The pixel rule of a cropped grid: 4 pixels across the launch waist radius
# (the olb edge rule, grid.PIXELS_PER_FEATURE). The b9 cells of record
# have about 1 pixel across it, because n = 4096 spreads over 8 to 9 m.
PIXELS_PER_WAIST = 4

# Every case runs at 1024 px at 1 km (the 45 deg study's value): 0.23 to
# 0.78 mm, 23 to 220 px across the aperture, a side over 3 vacuum radii.
N_PX_1KM = 1024

# (case, Cn2, path) -> the folder of a legacy campaign under OLB_CAMPAIGNS.
LEGACY = {
    **{("b9_1in_circle", c, 10e3): f"cn2{c:.0e}_standard_focal_n4096"
       for c in (1e-15, 5e-15)},
    ("b18_1in_circle", 1e-15, 10e3):
        "ell45_L10km_cn21e-15_standard_n4096_txcircle",
    **{("b18_1in_ellipse", c, 10e3):
       f"ell45_L10km_cn2{c:.0e}_standard_n4096_txellipse" for c in CN2},
    **{("b36_2in_circle", c, 10e3): f"cn2{c:.0e}_standard_focal_n2048_ap2in"
       for c in CN2},
    **{(f"b18_1in_{tx}", c, 1e3):
       f"ell45_L1km_cn2{c:.0e}_standard_n1024_tx{tx}"
       for c in CN2 for tx in ("circle", "ellipse")},
}


def key(name, cn2, path_m=10e3, crop=None):
    """The cell name (a 10 km cell keeps the name of the first run)."""
    tag = "" if path_m == 10e3 else f"_L{path_m / 1e3:g}km"
    return f"{name}{tag}_cn2{cn2:.0e}" + ("" if crop is None else f"_crop{crop:g}")


def build_scenario(case, cn2, path_m):
    """The symmetric link of one case: near launches, far receives."""
    near = Terminal(aperture_m=case.aperture_m, wavelength_m=LAM,
                    transmitter=Transmitter(waist_m=case.waist_m,
                                            tilt_deg=case.tilt_deg))
    mmf = MMF(core_radius_m=CORE_RADIUS_M, numerical_aperture=NA,
              focal_length_m=case.f_run)
    far = Terminal(aperture_m=case.aperture_m, wavelength_m=LAM, detector=mmf)
    channel = TerrestrialChannel(path_length_m=path_m,
                                 attenuation_db_per_km=0.0, cn2=cn2)
    return (TerrestrialScenario(near=near, far=far, channel=channel),
            HorizontalPath(path_m))


def campaign(name, cn2, path_m, fft_backend="cupy", crop=None):
    """The campaign of one cell: the legacy record, or a new one in DATA.

    crop is None for the grid of record. A float is the side [m] of a
    CROPPED grid (validation/terrestrial_grid_crop in olb). Its pixel is the
    finer of the pixel of record and PIXELS_PER_WAIST across the launch
    waist. A cropped cell is a new campaign, so it takes the olb terrestrial
    absorber (band 0.25, strength 16). Its beam moments are not valid.
    """
    case = CASES[name]
    scn, geo = build_scenario(case, cn2, path_m)
    grid, plan = turbulent_grid(scn, geo, preset=PRESET,
                                L0_m=scn.channel.site.outer_scale_m)[:2]
    grid = dataclasses.replace(
        grid, n=case.n_px if path_m == 10e3 else N_PX_1KM)
    if crop is not None:
        dx = min(grid.pixel_m, case.waist_m / PIXELS_PER_WAIST)
        grid = dataclasses.replace(
            grid, size_m=float(crop), n=int(np.ceil(crop / dx / 256)) * 256)
        root = os.path.join(DATA, key(name, cn2, path_m, crop))
        return Campaign(scn, geo, root, seed=SEED, preset=PRESET,
                        block_size=BLOCK, grid=grid, plan=plan,
                        fft_backend=fft_backend)
    legacy = LEGACY.get((name, cn2, path_m))
    root = (os.path.join(OLB_CAMPAIGNS, legacy) if legacy
            else os.path.join(DATA, key(name, cn2, path_m)))
    return Campaign(scn, geo, root, seed=SEED, preset=PRESET,
                    block_size=BLOCK, grid=grid, plan=plan,
                    fft_backend=fft_backend)


def mask(X, Y, case):
    """The terminal aperture on a grid: the circle, or its 45 deg ellipse."""
    a = case.aperture_m / 2
    b = a if case.tilt_deg is None else a * np.cos(np.radians(case.tilt_deg))
    return (X / b) ** 2 + (Y / a) ** 2 <= 1


def launch_fraction(case, n=4096):
    """The launch power inside the launch mask (the clip loss).

    A fine numerical integral of exp(-2 r^2 / w^2) over the mask. The runner
    divides the collected power by the CLIPPED start power, so this factor
    references the loss to the telescope output.
    """
    x = (np.arange(n) - n // 2) * (2 * case.aperture_m / n)
    X, Y = np.meshgrid(x, x)
    g = np.exp(-2 * (X ** 2 + Y ** 2) / case.waist_m ** 2)
    return float(g[mask(X, Y, case)].sum() / g.sum())


def vacuum_radius(case, path_m):
    """The vacuum 1/e^2 radius of the launch at the far end (Gaussian beam)."""
    z_r = np.pi * case.waist_m ** 2 / LAM
    return case.waist_m * np.hypot(1.0, path_m / z_r)


READ_COLS = ("ratio", "eta", "eta_g", "tgx", "tgy", "tzx", "tzy")


def read(F, case, ctx):
    """The receive read of one crop field F; see READ_COLS and the docstring.

    ratio is P_fine(terminal mask) / P_coarse(circle): it turns the coarse
    in-run collected power into the fine-mask bucket. ctx caches the modal
    basis (the grid is the same in each trial of a cell).
    """
    F = Field.copy(F)
    F.field = F.field.astype(np.complex128)
    Y, X = F.mgrid_cartesian
    p_coarse = np.sum(np.abs(F.field[X ** 2 + Y ** 2
                                     <= (case.aperture_m / 2) ** 2]) ** 2)
    M = _resolve_auto_factor("auto", F, case.aperture_m, CORE_RADIUS_M,
                             case.f_read, NA, None)
    Fu = _upsampled_field(F, M) if M > 1 else F
    if Fu.N not in ctx:
        Yu, Xu = Fu.mgrid_cartesian
        ctx[Fu.N] = ApertureModes(SLOPE_MIN_MODES, Fu.N, mask(Xu, Yu, case))
    modes = ctx[Fu.N]
    m = modes.mask

    def eta(G):
        return mmf_coupling_efficiency(G, case.aperture_m, CORE_RADIUS_M,
                                       case.f_read, numerical_aperture=NA,
                                       mask=m, upsample=1)

    to_rad = LAM / (2 * np.pi * Fu.dx)          # rad per pixel -> rad
    co_g = modes.estimate_gtilt(Fu.field)
    sx, sy = wrapped_gradient(Fu.field, mask=m)
    co_z = modes.estimate_from_slopes(sx, sy)
    Fc = Field.copy(Fu)
    Fc.field = modes.apply(Fu.field, co_g)
    # Z2 = 2 x / R (Noll), so the mean gradient is 2 a2 / R.
    return np.array([np.sum(np.abs(Fu.field[m]) ** 2) / M ** 2 / p_coarse,
                     eta(Fu), eta(Fc),
                     *(2 * co_g[1:3] / modes.radius_px * to_rad),
                     *(2 * co_z[1:3] / modes.radius_px * to_rad)])


def db(x):
    return -10 * np.log10(x)


def stats(p, etas, B=2000, seed=1):
    """Loss statistics (positive dB), each [value, bootstrap SE]."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, p.size, (B, p.size))

    def both(fn):
        return [float(fn(np.arange(p.size))),
                float(np.std([fn(i) for i in idx]))]

    out = {}
    for name, eta in etas.items():
        loss = db(p * eta)
        out[name] = {
            "mean_db": both(lambda i: db(np.mean(p[i] * eta[i]))),
            "median_db": both(lambda i: np.median(loss[i])),
            "p95_db": both(lambda i: np.percentile(loss[i], 95)),
            "p99_db": both(lambda i: np.percentile(loss[i], 99)),
            "mean_eta": both(lambda i: np.mean(eta[i]))}
    out["bucket_mean_db"] = both(lambda i: db(np.mean(p[i])))
    return out


if __name__ == "__main__":
    # Self-check: the masks, the launch clip and the vacuum radius.
    c18e = CASES["b18_1in_ellipse"]
    assert abs(db(launch_fraction(c18e)) - 0.392) < 0.005     # ellipse45 value
    assert abs(db(launch_fraction(CASES["b18_1in_circle"])) - 0.106) < 0.005
    assert db(launch_fraction(CASES["b9_1in_circle"])) < 0.001
    assert abs(vacuum_radius(c18e, 10e3) - 0.5306) < 1e-3          # wander_split
    x = np.linspace(-0.02, 0.02, 801)
    X, Y = np.meshgrid(x, x)
    ratio = mask(X, Y, c18e).sum() / mask(X, Y, CASES["b18_1in_circle"]).sum()
    assert abs(ratio - np.cos(np.radians(45))) < 0.01
    for name, case in CASES.items():
        print(f"{name:16s} clip {db(launch_fraction(case)):.3f} dB, "
              f"W(10 km) {vacuum_radius(case, 10e3):.3f} m, "
              f"W(1 km) {vacuum_radius(case, 1e3):.3f} m")
    print("cases.py self-check OK")
