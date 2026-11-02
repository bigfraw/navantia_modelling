"""Tip-tilt at both ends of the symmetric link: three passes on one atmosphere.

THE QUESTION. Each terminal has one fine-steering mirror. It removes the tilt
of the beam that it RECEIVES, and the same mirror steers its launch along the
reverse of that arrival direction. By reciprocity (Shapiro,
DOI 10.1364/JOSA.61.000492) the launch then retraces the path of the far
terminal's beam, which removes a part of the wander. How much of the fade
does that remove?

THE TRIAL. For trial k of a stored cell, this script builds the seeded screens
of the trial ONE time, then:

1. FORWARD: the near launch through the screens, to the far plane. This is
   the stored trial: its collected power must equal the stored value (the
   identity gate, on the first GATE_TRIALS trials).
2. REVERSE: the far launch (the same terminal) through the SAME screens in
   the reverse order, at the mirrored distances L - z_j, to the near plane.
   The near terminal senses the G-tilt of this beam over its own aperture.
3. CORRECTED: the near launch with the sensed tilt put on as a phase plane,
   exp(i SIGN k (theta_x x + theta_y y)), through the screens to the far
   plane. SIGN = -1 is the conjugate of the arriving tilt (the retrace).
   `--sign` is there for the sign gate: the right sign makes the far-end
   centroid wander smaller.

Each pass is read at its receive plane: the in-run collected power, the
`cases.read` columns (bucket ratio, MMF eta open and with a perfect receive
G-tilt, the G-tilt and Z-tilt angles), and the beam moments (the centroid and
the short-term radius inside 3 vacuum radii). So the four cases of the link
(no tip-tilt, receive only, transmit only, both) come from one trial, PAIRED.
The correction is PERFECT: no sensor noise, no servo lag, a snapshot.

Run it on bigfraw from any folder, with the GPU venv:

    C:\\Users\\alexf\\olb-gpu-venv\\Scripts\\python.exe -u
        D:\\repos\\navantia_modelling\\scripts\\link_budget\\tt_pass.py
        --case b36_2in_circle --cn2 1e-15 --trials 300
"""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from olb.waveoptics.field import Begin, Field, Power, field_dtype, to_host
from olb.waveoptics.priority import boost_process_priority
from olb.waveoptics.propagators import set_fft_backend
from olb.waveoptics.run import _clip
from olb.waveoptics.turbulence.run import (_resolve_seed, _screen_builder,
                                           _screen_seed, _start_field)
from olb.waveoptics.turbulence.sampling import PRESETS
from olb.waveoptics.turbulence.splitstep import (split_step,
                                                 super_gaussian_boundary)

from cases import (CASES, CN2, DATA, HERE, LAM, READ_COLS, campaign, db, key,
                   launch_fraction, read, stats, vacuum_radius)

ENDS = ("fwd", "rev", "cor")
END_COLS = ("collected",) + READ_COLS + ("cx", "cy", "w_st")
COLS = tuple(f"{e}_{c}" for e in ENDS for c in END_COLS)
GATE_TRIALS = 3
GATE_RTOL = 1e-4
SAVE_EVERY = 10


def crop(F, half):
    """The central (2 half + 1)^2 crop of F, as the stored patch holds it."""
    c = F.N // 2
    G = Begin((2 * half + 1) * F.dx, LAM, 2 * half + 1)
    G.field = F.field[c - half:c + half + 1, c - half:c + half + 1]
    return G


def moments(F, r_win):
    """The power centroid and the short-term 1/e^2 radius inside r_win.

    w_st = sqrt(2 <|r - c|^2>): a Gaussian exp(-2 r^2 / W^2) gives
    <r^2> = W^2 / 2 (Andrews and Phillips, Ch. 6, DOI 10.1117/3.626196).
    """
    Y, X = F.mgrid_cartesian
    w = np.abs(F.field).astype(np.float64) ** 2
    w[X ** 2 + Y ** 2 > r_win ** 2] = 0.0
    s = w.sum()
    cx, cy = (w * X).sum() / s, (w * Y).sum() / s
    return cx, cy, np.sqrt(2 * (w * ((X - cx) ** 2 + (Y - cy) ** 2)).sum() / s)


def tilted(F0, theta, sign):
    """F0 times the phase plane exp(i sign k theta . r)."""
    Y, X = F0.mgrid_cartesian
    k = 2 * np.pi / LAM
    F = Field.copy(F0)
    F.field = F0.field * np.exp(1j * sign * k * (theta[0] * X + theta[1] * Y)
                                ).astype(F0.field.dtype)
    return F


def run_cell(name, cn2, path_m, n, sign, fft_backend, tag, crop=None):
    case = CASES[name]
    camp = campaign(name, cn2, path_m, fft_backend, crop)
    stored = [t.collected_power
              for t in camp.load(GATE_TRIALS, fields=False).trials]
    cell = key(name, cn2, path_m, crop)
    os.makedirs(os.path.join(DATA, cell), exist_ok=True)
    out_path = os.path.join(DATA, cell, f"tt_pass{tag}.npz")
    rows = []
    if os.path.exists(out_path):
        old = np.load(out_path)
        if float(old["sign"]) != sign:
            raise SystemExit(f"{out_path} holds sign {old['sign']}, not {sign}")
        rows = list(old["rows"])
    grid, plan = camp.grid, camp.plan
    z = np.asarray(plan.z_m, dtype=float)
    z_rev = (plan.z_total_m - z)[::-1]
    # The mask of the campaign: the absorber it ran with (None = the record).
    band, strength = camp.absorber or (
        PRESETS[camp.preset].boundary_width_frac, 1.0)
    bmask = super_gaussian_boundary(grid.n, band, strength=strength)
    entropy = _resolve_seed(camp.seed)
    # A cropped grid cuts the window, so its beam moments are NOT valid.
    r_win = min(3 * vacuum_radius(case, path_m), (1 - band) * grid.size_m / 2)
    half = int(np.ceil(1.5 * case.aperture_m / 2 / grid.pixel_m))
    ctx = {}
    print(f"{cell}: {grid.n} px, {grid.pixel_m * 1e3:.2f} mm, "
          f"{z.size} screens, crop {2 * half + 1} px, sign {sign:+g}",
          flush=True)

    def read_end(F, p_ref):
        collected = Power(_clip(Field.copy(F), case.aperture_m, 0.0)) / p_ref
        return [collected, *read(crop(F, half), case, ctx),
                *moments(F, r_win)]

    previous = set_fft_backend(fft_backend)
    try:
        cdtype = field_dtype(camp.precision)
        build = _screen_builder(camp.screen_generator, grid, camp.L0_m,
                                camp.subharmonics, dtype=cdtype,
                                n_draw=grid.n)
        factory = build.factory           # the "olb" generator of the record
        F0 = _start_field(camp.scenario, grid, LAM, False, dtype=cdtype)
        p_ref = Power(F0)
        t0 = time.time()

        def submit(k):
            """Draw the host noise of trial k in threads (as the runner does).

            make_from_noise(r0, draw(rng)) equals make(r0, rng) bit for bit
            (olb.waveoptics.turbulence.screens), so the atmosphere is the same.
            """
            return [draws.submit(factory.draw, np.random.default_rng(
                _screen_seed(entropy, k, j))) for j in range(z.size)]

        def finish(k, fwd, rev, cor):
            fwd = fwd.result()
            rows.append(fwd + rev + cor.result())
            if k < GATE_TRIALS:
                rel = abs(fwd[0] / stored[k] - 1)
                print(f"  gate trial {k}: forward {fwd[0]:.6e}, stored "
                      f"{stored[k]:.6e}, rel {rel:.1e}", flush=True)
                if rel > GATE_RTOL:
                    raise SystemExit("IDENTITY GATE FAILED: the regenerated "
                                     "atmosphere is not the stored one.")
            if len(rows) % SAVE_EVERY == 0 or k == n - 1:
                np.savez(out_path, rows=np.array(rows), cols=np.array(COLS),
                         sign=sign)
                print(f"  {len(rows)}/{n} trials, {time.time() - t0:.0f} s",
                      flush=True)

        # THE PIPELINE. The noise of trial k+1 is drawn while the device runs
        # trial k, and the forward and corrected reads run in threads; only the
        # reverse read (it gives the tilt of the correction) waits.
        with ThreadPoolExecutor(z.size) as draws, \
                ThreadPoolExecutor(2) as reads:
            start, last = len(rows), None
            pending = submit(start) if start < n else []
            for k in range(start, n):
                drawn, pending = pending, submit(k + 1) if k + 1 < n else []
                screens = [factory.make_from_noise(plan.r0_m[j],
                                                   drawn[j].result())
                           for j in range(z.size)]
                del drawn
                F = to_host(split_step(F0, z, screens, plan.z_total_m,
                                       boundary=bmask))
                fwd = reads.submit(read_end, F, p_ref)
                if last:
                    finish(*last)
                F = to_host(split_step(F0, z_rev, screens[::-1],
                                       plan.z_total_m, boundary=bmask))
                rev = read_end(F, p_ref)
                theta = rev[1 + READ_COLS.index("tgx"):][:2]
                F = to_host(split_step(tilted(F0, theta, sign), z, screens,
                                       plan.z_total_m, boundary=bmask))
                del screens
                last = (k, fwd, rev, reads.submit(read_end, F, p_ref))
            if last:
                finish(*last)
    finally:
        set_fft_backend(previous)
    return np.array(rows)


def paired(pa, pb, B=2000, seed=1):
    """The change b - a of the mean, p95 and p99 loss (dB), paired bootstrap."""
    rng = np.random.default_rng(seed)
    idx = np.vstack([np.arange(pa.size), rng.integers(0, pa.size,
                                                      (B, pa.size))])
    la, lb = db(pa), db(pb)
    out = {}
    for name, fn in (("mean_db", lambda l, p, i: db(np.mean(p[i]))),
                     ("p95_db", lambda l, p, i: np.percentile(l[i], 95)),
                     ("p99_db", lambda l, p, i: np.percentile(l[i], 99))):
        d = np.array([fn(lb, pb, i) - fn(la, pa, i) for i in idx])
        out[name] = [float(d[0]), float(d[1:].std())]
    return out


def summary(rows, name):
    d = dict(zip(COLS, rows.T))
    lf = launch_fraction(CASES[name])
    p = {e: lf * d[f"{e}_collected"] * d[f"{e}_ratio"] for e in ("fwd", "cor")}
    cases = {"none": p["fwd"] * d["fwd_eta"], "rx": p["fwd"] * d["fwd_eta_g"],
             "tx": p["cor"] * d["cor_eta"], "both": p["cor"] * d["cor_eta_g"]}
    loss = stats(np.ones(rows.shape[0]), cases)
    del loss["bucket_mean_db"]          # p = 1 here, so it is not a bucket
    out = {"n": int(rows.shape[0]), **loss,
           "change_vs_none": {c: paired(cases["none"], cases[c])
                              for c in ("rx", "tx", "both")}}
    for e in ENDS:
        r = np.hypot(d[f"{e}_cx"], d[f"{e}_cy"])
        out[f"wander_rms_m_{e}"] = float(np.sqrt(np.mean(r ** 2)))
        out[f"w_st_mean_m_{e}"] = float(d[f"{e}_w_st"].mean())
        out[f"theta_rms_urad_{e}"] = float(np.sqrt(np.mean(
            d[f"{e}_tgx"] ** 2 + d[f"{e}_tgy"] ** 2)) * 1e6)
    for ax in "xy":
        tf, tn = d[f"fwd_tg{ax}"], d[f"rev_tg{ax}"]
        cf = d[f"fwd_c{ax}"]
        out[f"corr_{ax}"] = {
            "theta_near_far": float(np.corrcoef(tn, tf)[0, 1]),
            "theta_near_c_far": float(np.corrcoef(tn, cf)[0, 1]),
            "theta_far_c_far": float(np.corrcoef(tf, cf)[0, 1])}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", nargs="*", default=list(CASES),
                    choices=list(CASES))
    ap.add_argument("--cn2", type=float, nargs="*", default=CN2)
    ap.add_argument("--length-km", type=float, default=10.0)
    ap.add_argument("--trials", type=int, default=300)
    ap.add_argument("--sign", type=float, default=-1.0, choices=(-1.0, 1.0))
    ap.add_argument("--fft-backend", default="cupy")
    ap.add_argument("--crop", type=float, default=None,
                    help="side [m] of a cropped grid (see cases.campaign)")
    ap.add_argument("--tag", default="",
                    help="suffix of the npz and the result key (smoke runs)")
    args = ap.parse_args()

    boost_process_priority()
    path_m = args.length_km * 1e3
    out = os.path.join(HERE, "results_tt" + ("" if path_m == 10e3
                       else f"_L{args.length_km:g}km") + ".json")
    results = json.load(open(out)) if os.path.exists(out) else {}
    for name in args.case:
        for cn2 in args.cn2:
            rows = run_cell(name, cn2, path_m, args.trials, args.sign,
                            args.fft_backend, args.tag, args.crop)
            k = key(name, cn2, path_m, args.crop) + args.tag
            results[k] = summary(rows, name)
            s = results[k]
            print(f"  wander rms fwd {s['wander_rms_m_fwd']:.4f} m, corrected "
                  f"{s['wander_rms_m_cor']:.4f} m; change of mean / p99 (dB): "
                  + ", ".join(f"{c} {v['mean_db'][0]:+.2f} / {v['p99_db'][0]:+.2f}"
                              for c, v in s["change_vs_none"].items()),
                  flush=True)
            with open(out, "w") as f:
                json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
