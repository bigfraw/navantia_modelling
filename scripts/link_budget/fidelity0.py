"""Compare the fidelity-2 runs with the olb fidelity-0 terrestrial budget.

THE CHECK. For each circular case (the fidelity-0 truncation Term refuses a
45 deg aperture) at 10 km and 1 km, this script builds two fidelity-0 budgets
(`olb.links.terrestrial_budget(fidelity=0)`) and draws a Monte Carlo of each:

- BUCKET: the far terminal holds a plain `Aperture()`. The budget is the
  geometric spread, the launch truncation (Klein and Degnan,
  DOI 10.1364/AO.13.002134) and the Gaussian-beam scintillation fade (Dios
  on-axis index with weak aperture averaging). It is the analytic version of
  the fidelity-2 bucket loss.
- FIBRE: the far terminal holds the MMF at the design focal length. The
  budget then has the spot-in-core coupling and the tip-tilt walk-off fade IN
  PLACE OF the scintillation (olb does not count both), so it has no
  aperture fade.

Each statistic is from the power: mean = -10 log10 E[P], p99 = the 99th
percentile of the loss, as the fidelity-2 summary. The fidelity-2 values come
from `data/<cell>/reads.npz` (`plot_summary.bucket_stats`).

The fidelity-0 scintillation is a weak-fluctuation model. Its Rytov
variance is printed; past about 1 (10 km at all three Cn2) the model is out
of its range, and `Budget.check()` flags it.

Command:
    python scripts/link_budget/fidelity0.py
"""

import dataclasses
import json
import os
import warnings

import numpy as np

from olb.links.terrestrial import terrestrial_budget
from olb.terminal import Aperture, MMF
from olb.turbulence.andrews.scintillation import rytov_variance

from cases import (CASES, CN2, CORE_RADIUS_M, HERE, LAM, NA, build_scenario,
                   db, key)
from plot_summary import bucket_stats, load

N_MC = 200_000
PATHS = ((10e3, ""), (1e3, "_L1km"))


def with_detector(scn, det):
    return dataclasses.replace(scn, far=dataclasses.replace(scn.far,
                                                            detector=det))


def mc(budget, rng):
    """Mean (from the power) and p99 of the fidelity-0 total loss, dB."""
    loss = budget.monte_carlo(N_MC, rng=rng)["total_loss_samples"]
    return db(np.mean(10 ** (-loss / 10))), float(np.percentile(loss, 99))


def cell(name, cn2, path_m, rng):
    case = CASES[name]
    scn, geo = build_scenario(case, cn2, path_m)
    mmf = MMF(core_radius_m=CORE_RADIUS_M, numerical_aperture=NA,
              focal_length_m=case.f_read)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bucket = terrestrial_budget(with_detector(scn, Aperture()), geo)
        fibre = terrestrial_budget(with_detector(scn, mmf), geo)
        flags = [t.name for t in bucket.terms + fibre.terms
                 if not getattr(t.assumptions, "ok", True)]
    f0b, f0f = mc(bucket, rng), mc(fibre, rng)
    b2, c2 = bucket_stats(key(name, cn2, path_m))
    f2b = (b2["mean_db"][0], b2["p99_db"][0])
    f2f = (f2b[0] + c2["mean_db"][0], f2b[1] + c2["p99_db"][0])
    return {"rytov": float(rytov_variance(LAM, path_m, cn2)),
            "f0_bucket": f0b, "f2_bucket": f2b,
            "f0_fibre": f0f, "f2_fibre": f2f,
            "f0_coupling_mean": f0f[0] - f0b[0],
            "f2_coupling_mean": c2["mean_db"][0],
            "f0_terms": {t.name: float(np.mean(t.mean_db))
                         for t in fibre.terms},
            "f0_flags": sorted(set(flags))}


def main():
    rng = np.random.default_rng(20261026)
    out = {}
    print(f"{'cell':32s} {'Rytov':>6s} | bucket mean / p99: f0  f2 | "
          f"fibre mean / p99: f0  f2 | coupling mean f0 f2")
    for path_m, tag in PATHS:
        done = load("uncorrected", tag)
        for name, case in CASES.items():
            if case.tilt_deg is not None:
                continue
            for cn2 in CN2:
                k = key(name, cn2, path_m)
                if k not in done:
                    continue
                r = out[k] = cell(name, cn2, path_m, rng)
                print(f"{k:32s} {r['rytov']:6.2f} | "
                      f"{r['f0_bucket'][0]:5.1f} {r['f0_bucket'][1]:5.1f}  "
                      f"{r['f2_bucket'][0]:5.1f} {r['f2_bucket'][1]:5.1f} | "
                      f"{r['f0_fibre'][0]:5.1f} {r['f0_fibre'][1]:5.1f}  "
                      f"{r['f2_fibre'][0]:5.1f} {r['f2_fibre'][1]:5.1f} | "
                      f"{r['f0_coupling_mean']:5.2f} "
                      f"{r['f2_coupling_mean']:5.2f}  {r['f0_flags']}")
    with open(os.path.join(HERE, "results_fidelity0.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
