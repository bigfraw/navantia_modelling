"""Draw the two summary bar charts of the 10 km and 1 km MMF evaluation.

It reads the four results JSON files next to this script (copy them from
bigfraw) and writes, in `figures/`:

- `loss_summary.png`: the telescope-to-fibre loss of each case, no tip-tilt.
- `tx_tiptilt_summary.png`: the improvement that the transmit tip-tilt gives
  (the paired change, with the sign reversed so that a gain is up).
- `bucket_vs_fibre.png`: where the loss is. Top: the aperture (bucket) loss,
  telescope output to the power in the receive aperture. Bottom: the fibre
  coupling loss, the fibre loss less the bucket loss of the same statistic.
  It reads the per-trial `data/<cell>/reads.npz` (copy them from bigfraw).

Each case is one group, with one colour for each Cn2. The filled dot is the
mean and the open dot is the p99, each with +/- 1 bootstrap standard error
(the resample of the trials; paired for the tip-tilt change). The
`bucket_vs_fibre.png` figure also shows the p90 as an open diamond.

Command:
    python scripts/link_budget/plot_summary.py
"""

import json
import os

import matplotlib.pyplot as plt
import numpy as np

from cases import CASES, CN2, DATA, HERE, db, key

PATHS = ((10e3, "10 km", ""), (1e3, "1 km", "_L1km"))
LABELS = {"b9_1in_circle": "9.08 mm\n1 in circle",
          "b9_1in_ellipse": "9.08 mm\n1 in ellipse",
          "b18_1in_circle": "18.6 mm\n1 in circle",
          "b18_1in_ellipse": "18.6 mm\n1 in ellipse",
          "b18_2in_circle": "18.2 mm\n2 in circle",
          "b36_2in_circle": "36.3 mm\n2 in circle\n(benchmark)"}
# Cn2 is a magnitude, so one hue from light to dark (one sequential ramp).
SHADES = ("#86b6ef", "#2a78d6", "#104281")
INK, MUTED = "#0b0b0b", "#52514e"
WIDTH = 0.26                       # the spacing of the Cn2 within a group


def load(stem, tag):
    with open(os.path.join(HERE, f"results_{stem}{tag}.json")) as f:
        return json.load(f)


PENDING = {s: [np.nan, np.nan] for s in ("mean_db", "p90_db", "p99_db")}


def present(path_m, tag, done=None):
    """The cases with at least one Cn2 done at this path.

    A Cn2 that has not run yet draws no dot (PENDING); the 18.2 mm 2 in case
    ran at 10 km only.
    """
    done = load("uncorrected", tag) if done is None else done
    return [n for n in CASES if any(key(n, c, path_m) in done for c in CN2)]


def style(ax, title, ylabel, names):
    ax.set_title(title, color=INK, loc="left", fontsize=11)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.set_xticks(np.arange(len(names)), [LABELS[n] for n in names],
                  fontsize=8, color=MUTED)
    ax.tick_params(colors=MUTED, length=0)
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")


def offsets():
    return (np.arange(len(CN2)) - 1) * WIDTH


MARKS = {"mean_db": ("o", True, "mean"), "p90_db": ("D", False, "p90"),
         "p99_db": ("o", False, "p99")}


def dots(ax, x, stat, j, sign=1.0, names=("mean_db", "p99_db")):
    """Each statistic in `names` (see MARKS), each +/- 1 bootstrap SE."""
    for name in names:
        m, filled, lab = MARKS[name]
        face = SHADES[j] if filled else "white"
        v = sign * np.array([s[name][0] for s in stat])
        se = np.array([s[name][1] for s in stat])
        ax.errorbar(x, v, yerr=se, fmt=m, markersize=6 if m == "o" else 5,
                    markerfacecolor=face, markeredgecolor=SHADES[j],
                    markeredgewidth=1.6, ecolor=SHADES[j], elinewidth=1.2,
                    capsize=2.5, label=f"{lab}, Cn2 {CN2[j]:.0e} m^-2/3")


def group_lines(ax, names):
    for b in np.arange(len(names) - 1) + 0.5:
        ax.axvline(b, color="#ecebe7", linewidth=0.8)


def loss_figure():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), constrained_layout=True)
    for ax, (path_m, title, tag) in zip(axes, PATHS):
        u, names = load("uncorrected", tag), present(path_m, tag)
        for j, (cn2, dx) in enumerate(zip(CN2, offsets())):
            dots(ax, np.arange(len(names)) + dx,
                 [u[k]["no_tt"] if k in u else PENDING
                  for k in (key(n, cn2, path_m) for n in names)], j)
        group_lines(ax, names)
        style(ax, f"{title}: telescope-to-fibre loss, no tip-tilt",
              "Loss (dB), +/- 1 bootstrap SE", names)
    fig.legend(*axes[0].get_legend_handles_labels(), frameon=False,
               fontsize=8, ncol=6, loc="outside lower center")
    return fig


def tt_figure():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), sharey=True,
                             constrained_layout=True)
    for ax, (path_m, title, tag) in zip(axes, PATHS):
        t = load("tt", tag)
        names = present(path_m, tag, t)
        for j, (cn2, dx) in enumerate(zip(CN2, offsets())):
            dots(ax, np.arange(len(names)) + dx,
                 [t[k]["change_vs_none"]["tx"] if k in t else PENDING
                  for k in (key(n, cn2, path_m) for n in names)], j,
                 sign=-1.0)
        ax.axhline(0, color="#c3c2b7", linewidth=1)
        group_lines(ax, names)
        n = t[key(names[0], CN2[0], path_m)]["n"]
        style(ax, f"{title}: gain from transmit tip-tilt ({n} paired trials)",
              "Gain (dB), +/- 1 paired bootstrap SE", names)
    fig.legend(*axes[0].get_legend_handles_labels(), frameon=False,
               fontsize=8, ncol=6, loc="outside lower center")
    return fig


def bucket_stats(cell, B=2000, seed=1):
    """Bucket and coupling loss (mean, p90, p99), each [value, bootstrap SE].

    The coupling loss is fibre minus bucket on the SAME resample (paired).
    """
    r = np.load(os.path.join(DATA, cell, "reads.npz"))
    pb = r["launch_fraction"] * r["collected"] * r["ratio"]
    pf = pb * r["eta"]
    rng = np.random.default_rng(seed)
    idx = np.vstack([np.arange(pb.size),
                     rng.integers(0, pb.size, (B, pb.size))])

    def stats(p, i):
        return db(np.mean(p[i])), *np.percentile(db(p[i]), (90, 99))

    v = np.array([[*stats(pb, i), *stats(pf, i)] for i in idx])
    v = np.column_stack([v[:, :3], v[:, 3:] - v[:, :3]])

    def pair(c):
        return {n: [v[0, c + k], v[1:, c + k].std()]
                for k, n in enumerate(BUCKET_STATS)}
    return pair(0), pair(3)


BUCKET_STATS = ("mean_db", "p90_db", "p99_db")


def bucket_figure():
    fig, axes = plt.subplots(2, 2, figsize=(13, 9),
                             constrained_layout=True)
    for col, (path_m, title, tag) in enumerate(PATHS):
        names = present(path_m, tag)
        for j, (cn2, dx) in enumerate(zip(CN2, offsets())):
            st = [bucket_stats(k) if os.path.exists(
                      os.path.join(DATA, k, "reads.npz")) else (PENDING, PENDING)
                  for k in (key(n, cn2, path_m) for n in names)]
            x = np.arange(len(names)) + dx
            dots(axes[0, col], x, [s[0] for s in st], j, names=BUCKET_STATS)
            dots(axes[1, col], x, [s[1] for s in st], j, names=BUCKET_STATS)
        for row, what, ylab in (
                (0, "aperture (bucket) loss", "Loss (dB), +/- 1 bootstrap SE"),
                (1, "fibre coupling loss = fibre - bucket",
                 "Loss (dB), +/- 1 paired bootstrap SE")):
            ax = axes[row, col]
            group_lines(ax, names)
            style(ax, f"{title}: {what}", ylab, names)
        axes[1, col].axhline(0, color="#c3c2b7", linewidth=1)
    fig.legend(*axes[0, 0].get_legend_handles_labels(), frameon=False,
               fontsize=8, ncol=3, loc="outside lower center")
    return fig


if __name__ == "__main__":
    out = os.path.join(HERE, "figures")
    os.makedirs(out, exist_ok=True)
    for name, fig in (("loss_summary", loss_figure()),
                      ("tx_tiptilt_summary", tt_figure()),
                      ("bucket_vs_fibre", bucket_figure())):
        fig.savefig(os.path.join(out, f"{name}.png"), dpi=150,
                    facecolor="#fcfcfb")
        print(os.path.join(out, f"{name}.png"))
