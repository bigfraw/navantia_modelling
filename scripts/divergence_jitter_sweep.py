"""Calculate the turbulent bucket power against the Tx divergence and the Tx pointing jitter.

Commands (run the cells on bigfraw, with the GPU venv and PYTHONPATH set to olb):
    python scripts/divergence_jitter_sweep.py vacuum
    python scripts/divergence_jitter_sweep.py turb --trials 1000
    python scripts/divergence_jitter_sweep.py report

THE LINK. A 10 km horizontal path at 1550 nm, with constant Cn2 = 5e-15
m^-2/3. The transmit beam is a Gaussian with a 9.08 mm 1/e^2 waist RADIUS.
The far-field 1/e^2 half angle theta_div is a parameter (the olb
virtual-waist model). The receiver is a 50.8 mm circular bucket.

THE POINTING ERROR. A Tx pointing error theta_err moves the beam by
L * theta_err at the receiver. The beam keeps its size. For homogeneous
turbulence, a fixed beam read at the offset -L * theta_err has the same
statistics as a tilted beam read on axis. Thus each trial runs ONE on-axis
launch. The script then convolves the receive intensity with the aperture
disc. This gives the bucket power at each receiver position (the bucket map).
It stores the map on a lattice of pitch MAP_PITCH_M out to 0.75 theta_div L.
That is 3 sigma for a jitter of sigma = 0.25 theta_div on each axis. The
offsets of one trial share one atmosphere, so they are paired.

THE GRID. The cropped grid of olb validation/terrestrial_grid_crop, with the
olb terrestrial absorber (band 0.25, strength 16). The receiver region must
stay in the flat part of the mask, with the scatter region around it:
side = (0.75 theta_div L + 0.5 m) / 0.375. The pixel is the finer of 1.30 mm
and lambda / (4 theta_div), so the phase at the largest offset is sampled.

THE GATES. "vacuum" compares the map with the closed-form offset bucket (the
noncentral chi-square CDF of tx_pointing_bucket_sweep.py). "turb" compares the
on-axis value of the first GATE_TRIALS trials with the olb runner, trial for
trial (the same seed, grid, plan and absorber).

This script uses private olb functions (_start_field, _screen_builder,
_screen_seed, _boundary), as link_budget/tt_pass.py does.
"""
from __future__ import annotations

import argparse
import dataclasses
import glob
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("C:/repos/optical_link_budget", "D:/repos/optical_link_budget"):
    sys.path.insert(0, p)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from olb.beam import free_space_radius  # noqa: E402
from olb.geometry import HorizontalPath  # noqa: E402
from olb.scenario import TerrestrialChannel, TerrestrialScenario  # noqa: E402
from olb.terminal import Aperture, Terminal, Transmitter  # noqa: E402
from tx_pointing_bucket_sweep import THETA_MIN, bucket_loss_db  # noqa: E402

DATA = os.path.join(ROOT, "scripts", "divergence_jitter_data")
FIG = os.path.join(ROOT, "figures", "divergence_jitter_sweep.png")

LAM = 1550e-9
L = 10e3
CN2 = 5e-15
WAIST = 9.08e-3                    # m, 1/e^2 radius at the Tx aperture
AP = 0.0508                        # m, both apertures (2 in)
DIV_URAD = (54, 75, 100, 150, 200, 300)
DX_MAX = 1.30e-3                   # m, the validated pixel
MAP_PITCH_M = AP / 2               # m, the lattice pitch of the stored map
REACH = 0.75                       # map half-width, in units of theta_div L
SEED = 20261028
GATE_TRIALS = 3
GATE_RTOL = 1e-3
JITTER = (0.0, 0.1, 0.25)          # sigma / theta_div, on each axis


def theta(div_urad):
    return THETA_MIN if div_urad == 54 else div_urad * 1e-6


def scenario(div_urad):
    t = None if div_urad == 54 else div_urad * 1e-6
    near = Terminal(aperture_m=AP, wavelength_m=LAM,
                    transmitter=Transmitter(waist_m=WAIST, divergence_rad=t))
    far = Terminal(aperture_m=AP, wavelength_m=LAM, detector=Aperture())
    ch = TerrestrialChannel(path_length_m=L, attenuation_db_per_km=0.0, cn2=CN2)
    return TerrestrialScenario(near=near, far=far, channel=ch), HorizontalPath(L)


def grid_of(div_urad):
    """The sizer plan, on the cropped grid of this divergence."""
    from olb.waveoptics.turbulence.sampling import turbulent_grid
    scn, geo = scenario(div_urad)
    grid, plan = turbulent_grid(scn, geo, preset="standard",
                                L0_m=scn.channel.site.outer_scale_m)[:2]
    side = (REACH * theta(div_urad) * L + 0.5) / 0.375
    dx = min(DX_MAX, LAM / (4 * theta(div_urad)))
    n = int(np.ceil(side / dx / 256)) * 256
    return scn, geo, dataclasses.replace(grid, size_m=side, n=n), plan


def run_cell(kind, div_urad, n_trials):
    from olb.waveoptics.field import Power, field_dtype
    from olb.waveoptics.propagators import set_fft_backend
    from olb.waveoptics.turbulence.run import (
        _boundary, _resolve_seed, _screen_builder, _screen_seed, _start_field,
        propagate_turbulent_scenario, resolve_absorber)
    from olb.waveoptics.turbulence.sampling import PRESETS
    from olb.waveoptics.turbulence.splitstep import split_step

    scn, geo, grid, plan = grid_of(div_urad)
    path = os.path.join(DATA, f"{kind}_div{div_urad}_n{grid.n}.npz")
    if os.path.exists(path):
        print(f"skip {path}")
        return
    if kind == "vacuum":
        plan = dataclasses.replace(plan, r0_m=np.full_like(plan.r0_m, 1e6))
        n_trials = 1
    absorber = resolve_absorber("auto", scn)
    L0 = scn.channel.site.outer_scale_m
    print(f"{kind} {div_urad} urad: {grid.n} px x {grid.size_m:.2f} m "
          f"({grid.pixel_m * 1e3:.2f} mm), {plan.z_m.size} screens, "
          f"absorber {absorber}", flush=True)

    # The map lattice: the pixel offsets of the stored points.
    step = max(1, int(round(MAP_PITCH_M / grid.pixel_m)))
    half = int(REACH * theta(div_urad) * L / grid.pixel_m / step) * step
    idx = np.arange(-half, half + 1, step)
    off_m = idx * grid.pixel_m

    previous = set_fft_backend("cupy")
    try:
        import cupy as xp
        cdtype = field_dtype("single")
        mask, _ = _boundary(grid.n, PRESETS["standard"], absorber)
        F0 = _start_field(scn, grid, LAM, False, dtype=cdtype)
        p_ref = float(Power(F0)) / grid.pixel_m ** 2   # Power integrates |E|^2 dx^2
        c = grid.n // 2
        x = (np.arange(grid.n) - c) * grid.pixel_m
        disc = (x[:, None] ** 2 + x[None, :] ** 2 <= (AP / 2) ** 2)
        disc_ft = xp.fft.rfft2(xp.asarray(np.fft.ifftshift(disc), dtype=xp.float32))
        rows = xp.asarray(c + idx)
        build = _screen_builder("olb", grid, L0, True, dtype=cdtype, n_draw=grid.n)
        factory = build.factory
        entropy = _resolve_seed(SEED)
        maps = np.empty((n_trials, idx.size, idx.size), np.float32)
        t0 = time.time()

        def submit(k):
            return [draws.submit(factory.draw, np.random.default_rng(
                _screen_seed(entropy, k, j))) for j in range(plan.z_m.size)]

        with ThreadPoolExecutor(plan.z_m.size) as draws:
            pending = submit(0)
            for k in range(n_trials):
                drawn, pending = pending, (submit(k + 1) if k + 1 < n_trials else [])
                screens = [factory.make_from_noise(plan.r0_m[j], drawn[j].result())
                           for j in range(plan.z_m.size)]
                F = split_step(F0, plan.z_m, screens, plan.z_total_m, boundary=mask)
                del screens, drawn
                I = xp.abs(F.field) ** 2
                B = xp.fft.irfft2(xp.fft.rfft2(I) * disc_ft, s=I.shape)
                maps[k] = xp.asnumpy(B[rows[:, None], rows[None, :]]) / p_ref
                if (k + 1) % 50 == 0:
                    print(f"  {k + 1}/{n_trials}, {time.time() - t0:.0f} s", flush=True)
        wall = time.time() - t0
    finally:
        set_fft_backend(previous)

    i0 = idx.size // 2
    if kind == "vacuum":
        X, Y = np.meshgrid(off_m, off_m)
        exact = bucket_loss_db(free_space_radius(WAIST, L, theta(div_urad), LAM),
                               np.hypot(X, Y), AP / 2)
        err = -10 * np.log10(maps[0]) - exact
        inside = np.hypot(X, Y) <= REACH * theta(div_urad) * L
        print(f"  vacuum map vs closed form: on axis {err[i0, i0]:+.3f} dB, "
              f"worst inside the reach {err[inside].min():+.3f} / "
              f"{err[inside].max():+.3f} dB (exact up to {exact[inside].max():.1f} dB)")
    else:
        n_gate = min(GATE_TRIALS, n_trials)
        res = propagate_turbulent_scenario(
            scn, geo, n_trials=n_gate, seed=SEED, grid=grid, plan=plan,
            L0_m=L0, fft_backend="cupy", absorber=absorber)
        for k, t in enumerate(res.trials):
            rel = maps[k, i0, i0] / t.collected_power - 1
            print(f"  gate trial {k}: map {maps[k, i0, i0]:.6e}, runner "
                  f"{t.collected_power:.6e}, rel {rel:+.1e}", flush=True)
            if abs(rel) > GATE_RTOL:
                raise SystemExit("IDENTITY GATE FAILED")
    os.makedirs(DATA, exist_ok=True)
    np.savez(path, maps=maps, off_m=off_m, div=div_urad, theta=theta(div_urad),
             side=grid.size_m, n=grid.n, dx=grid.pixel_m, wall_s=wall,
             absorber=np.array(absorber))
    print(f"  {n_trials} trials, {wall / n_trials:.2f} s/trial -> {path}", flush=True)


def jitter_read(maps, off_m, sigma_m, rng, n_draw=20):
    """The bucket of each trial at n_draw Gaussian offsets (bilinear map read).

    A draw outside the map takes the map edge: at 3 sigma that is 1 % of the
    draws for sigma = 0.25 theta_div, and 0 for the smaller sigma.
    """
    from scipy.interpolate import RegularGridInterpolator
    out = []
    for m in maps:
        f = RegularGridInterpolator((off_m, off_m), m)
        d = np.clip(rng.normal(0, sigma_m, (n_draw, 2)) if sigma_m else
                    np.zeros((1, 2)), off_m[0], off_m[-1])
        out.append(f(d))
    return np.concatenate(out)


def stats(p, B=1000):
    def f(x):
        return np.array([-10 * np.log10(x.mean()), x.var() / x.mean() ** 2,
                         -10 * np.log10(np.percentile(x, 50)),
                         -10 * np.log10(np.percentile(x, 1))])
    rng = np.random.default_rng(1)
    return f(p), np.array([f(p[rng.integers(0, p.size, p.size)])
                           for _ in range(B)]).std(axis=0)


def report():
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(2)
    cells = sorted((dict(np.load(f)) for f in glob.glob(os.path.join(DATA, "turb_*.npz"))),
                   key=lambda r: int(r["div"]))
    print("TURBULENT bucket loss, Cn2 5e-15, 10 km (value +- bootstrap SE; "
          "the jitter rows reuse each trial at 20 offsets, so the SE is a lower bound)")
    print(f"{'div':>4} {'N':>5} {'sigma/div':>9} {'vac mean':>8} {'mean dB':>13} "
          f"{'sigma2_P':>13} {'p50 dB':>13} {'p99 dB':>13}")
    res = {}
    for r in cells:
        d, th, maps, off = int(r["div"]), float(r["theta"]), r["maps"], r["off_m"]
        w = free_space_radius(WAIST, L, th, LAM)
        for k in JITTER:
            p = jitter_read(maps, off, k * th * L, rng)
            pv = 10 ** (-bucket_loss_db(w, np.hypot(*rng.normal(0, k * th * L, (2, 200000)))
                                        if k else 0.0, AP / 2) / 10)
            v, e = stats(p)
            res[(d, k)] = (v, e, -10 * np.log10(np.mean(pv)))
            print(f"{d:4d} {maps.shape[0]:5d} {k:9.2f} {res[(d, k)][2]:8.2f} "
                  + " ".join(f"{a:6.2f}+-{b:5.2f}" for a, b in zip(v, e)))
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.3))
    divs = sorted({d for d, _ in res})
    for k, c in zip(JITTER, ("C0", "C1", "C3")):
        for ax, j in zip(axs, (0, 1, 3)):
            v = np.array([res[(d, k)][0][j] for d in divs])
            e = np.array([res[(d, k)][1][j] for d in divs])
            ax.errorbar(divs, v, e, marker="o", capsize=3, color=c,
                        label=f"sigma = {k:g} theta_div")
        axs[0].plot(divs, [res[(d, k)][2] for d in divs], ls=":", color=c)
    for ax, t in zip(axs, ("Mean bucket loss [dB] (dotted: vacuum)",
                           "Scintillation index sigma2_P",
                           "p99 loss (1st percentile power) [dB]")):
        ax.set_xlabel("Tx half-angle divergence [urad]")
        ax.set_title(t)
        ax.grid(True, alpha=0.3)
    axs[0].legend(title="Tx jitter per axis")
    fig.suptitle("10 km, Cn2 5e-15, 9.08 mm waist, 50.8 mm bucket, turbulent split step")
    fig.tight_layout()
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=150)
    print(f"Figure: {FIG}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=("vacuum", "turb", "report"))
    ap.add_argument("--div", type=int, nargs="+", default=list(DIV_URAD))
    ap.add_argument("--trials", type=int, default=1000)
    a = ap.parse_args()
    if a.kind == "report":
        return report()
    for d in a.div:
        run_cell(a.kind, d, a.trials)


if __name__ == "__main__":
    main()
