"""Run the uncorrected 1000-trial cells and read every cell with one reader.

A cell is one case (cases.py) at one Cn2. A legacy cell opens the olb
campaign read-only. A new cell runs its trials into
`data/<case>_cn2<Cn2>/` (the campaign resumes, so a second call runs no
trial). Then `cases.read` reads each stored crop (through
`Campaign.map_trials`, on the CPU), so every cell takes the same fine-mask
bucket and the same MMF read. It writes `data/<cell>/reads.npz` and one entry
in `results_uncorrected.json`.

Run it on bigfraw from any folder, with the GPU venv:

    C:\\Users\\alexf\\olb-gpu-venv\\Scripts\\python.exe -u
        D:\\repos\\navantia_modelling\\scripts\\link_budget\\uncorrected.py
        --case b9_1in_ellipse --cn2 1e-15 5e-15 1e-14
"""

import argparse
import json
import os

import numpy as np

from olb.waveoptics.priority import boost_process_priority

from cases import (CASES, CN2, DATA, HERE, READ_COLS, key, campaign,
                   launch_fraction, read, stats)


class StoredRead:
    """`cases.read` of one stored trial (picklable for the process pool)."""

    def __init__(self, case):
        self.case = case

    def __call__(self, rec):
        return read(rec.field(), self.case, rec.context)


def cell(name, cn2, path_m, n, workers, fft_backend):
    camp = campaign(name, cn2, path_m, fft_backend)
    case = CASES[name]
    k = key(name, cn2, path_m)
    print(f"{k}: {camp.root_dir}\n  grid {camp.grid.n} px x "
          f"{camp.grid.size_m:.3f} m ({camp.grid.pixel_m * 1e3:.2f} mm), "
          f"{camp.plan.z_m.size} screens", flush=True)
    camp.run(n, workers=workers, progress=True)
    p = np.array([t.collected_power for t in camp.load(n, fields=False).trials])
    cols = dict(zip(READ_COLS, camp.map_trials(
        StoredRead(case), n_trials=n, workers=workers,
        screen_phase=False).T))
    lf = launch_fraction(case)
    os.makedirs(os.path.join(DATA, k), exist_ok=True)
    np.savez(os.path.join(DATA, k, "reads.npz"), collected=p,
             launch_fraction=lf, **cols)
    th = {s: np.hypot(cols[f"t{s}x"], cols[f"t{s}y"]) for s in "gz"}
    return {"n": int(p.size), "grid_px": camp.grid.n,
            "pixel_mm": camp.grid.pixel_m * 1e3,
            "screens": int(camp.plan.z_m.size), "root": camp.root_dir,
            **stats(lf * p * cols["ratio"],
                    {"no_tt": cols["eta"], "rx_tt": cols["eta_g"]}),
            **{f"theta_rms_urad_{s}": float(np.sqrt(np.mean(t ** 2)) * 1e6)
               for s, t in th.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", nargs="*", default=list(CASES),
                    choices=list(CASES))
    ap.add_argument("--cn2", type=float, nargs="*", default=CN2)
    ap.add_argument("--length-km", type=float, default=10.0)
    ap.add_argument("--trials", type=int, default=1000)
    ap.add_argument("--workers", default="8")
    ap.add_argument("--fft-backend", default="cupy")
    args = ap.parse_args()
    workers = args.workers if args.workers == "auto" else int(args.workers)

    boost_process_priority()
    path_m = args.length_km * 1e3
    out = os.path.join(HERE, "results_uncorrected" + ("" if path_m == 10e3
                       else f"_L{args.length_km:g}km") + ".json")
    results = json.load(open(out)) if os.path.exists(out) else {}
    for name in args.case:
        for cn2 in args.cn2:
            k = key(name, cn2, path_m)
            results[k] = cell(name, cn2, path_m, args.trials, workers,
                              args.fft_backend)
            print(json.dumps(results[k], indent=1), flush=True)
            with open(out, "w") as f:
                json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
