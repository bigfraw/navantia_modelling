"""Draw the MMF encircled-energy physics as a figure.

Command:
    python scripts/mmf_encircled_energy_figure.py

The multimode fibre is a light bucket. The core is a hard disk of radius a. The
focal spot is a Gaussian of 1/e^2 intensity radius w_s. The coupled fraction eta
is the spot power inside the core. A received tilt moves the spot centre off the
core by an offset. Thus eta falls as the offset grows.

The coupled fraction is a non-central chi-square CDF. A Gaussian intensity is a
2-D Gaussian density. The spot offset is the non-centrality. The core radius is
the threshold. This script imports the olb function `_mmf_encircled_efficiency`,
so the curve uses the same model as the coupling bridge.

    eta(d) = F_chi2nc( (a/sigma)^2 ; k=2, lambda=(d/sigma)^2 ),   sigma = w_s/2

The figure has two parts:
  - The top row shows the spot (a glow) that walks across the core (a ring).
  - The bottom panel shows eta and the loss against the offset.

The top row uses a small core (5 spot radii), so the spot is visible. The real
coupling run uses 26.5 spot radii. Thus the real top is flatter and the real
cliff is sharper. This figure is a teaching aid. It uses no design values.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "D:/repos/optical_link_budget")
from olb.models.coupling.terrestrial import _mmf_encircled_efficiency  # noqa: E402

RATIO = 5.0             # core radius / spot radius, for the cartoons only
A = 1.0                 # core radius, normalised units
W_S = A / RATIO         # spot 1/e^2 intensity radius
SAMPLES = [0.0, 0.7, 1.0, 1.3]   # offset / a for the top-row panels


def eta(offset_over_a):
    """Give the coupled fraction at an offset. The offset is in core radii."""
    return _mmf_encircled_efficiency(np.asarray(offset_over_a, float) * A, W_S, A)


def make_figure(out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import Circle

    fig = plt.figure(figsize=(11, 8.6))
    gs = GridSpec(2, 4, height_ratios=[1.0, 1.3], hspace=0.45, wspace=0.16,
                  left=0.08, right=0.97, top=0.88, bottom=0.09)

    # --- top row: the spot walks across the core --------------------------
    lim = 1.7
    xx, yy = np.meshgrid(np.linspace(-lim, lim, 600), np.linspace(-lim, lim, 600))
    inside = (xx ** 2 + yy ** 2) <= A ** 2
    for i, off in enumerate(SAMPLES):
        ax = fig.add_subplot(gs[0, i])
        spot = np.exp(-2.0 * ((xx - off) ** 2 + yy ** 2) / W_S ** 2)
        # Dim the power that spills outside the core, so the loss is visible.
        shown = np.where(inside, spot, spot * 0.16)
        ax.imshow(shown ** 0.6, extent=[-lim, lim, -lim, lim], origin="lower",
                  cmap="inferno", vmin=0, vmax=1)
        ax.add_patch(Circle((0, 0), A, fill=False, ec="white", lw=2.0))
        ax.plot(off, 0, "+", color="cyan", ms=9, mew=1.6)
        ax.set_title(f"offset/a = {off:.2f}\n" + r"$\eta$ = " + f"{float(eta(off))*100:.1f}%",
                     fontsize=10)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        if i == 0:
            ax.set_ylabel("core = white ring\nspot = the glow", fontsize=8.5)

    # --- bottom: the curve ------------------------------------------------
    ax = fig.add_subplot(gs[1, :])
    o = np.linspace(0.0, 1.6, 1400)
    e = np.asarray(eta(o), float)
    loss = -10.0 * np.log10(np.clip(e, 1e-300, None))

    ax.plot(o, e * 100, color="#1f6feb", lw=2.5)
    ax.set_xlabel("spot offset / core radius   (offset / a)  =  how far the tilt walks the spot",
                  fontsize=11)
    ax.set_ylabel(r"coupled fraction  $\eta$  [%]", color="#1f6feb", fontsize=11)
    ax.tick_params(axis="y", labelcolor="#1f6feb")
    ax.set_xlim(0, 1.6); ax.set_ylim(0, 103); ax.grid(True, alpha=0.25)

    ax2 = ax.twinx()
    ax2.plot(o, loss, color="#d1242f", lw=2.0, ls="--")
    ax2.set_ylabel("walk-off loss [dB]", color="#d1242f", fontsize=11)
    ax2.tick_params(axis="y", labelcolor="#d1242f")
    ax2.set_ylim(0, 12)

    for off in SAMPLES:
        ax.axvline(off, color="0.6", lw=0.9, ls=":")
        ax.plot(off, float(eta(off)) * 100, "o", color="#1f6feb", ms=6)

    ax.annotate("FLAT TOP\nsmall spot roams deep inside the core:\n"
                r"non-centrality $\lambda=(d/\sigma)^2$ still far" + "\n"
                r"below the threshold $(a/\sigma)^2$",
                xy=(0.35, 100), xytext=(0.03, 55), fontsize=9.2,
                arrowprops=dict(arrowstyle="->", color="0.4"))
    ax.annotate("CLIFF\nspot centre on the rim (offset = a):\nhalf the power spills -> ~3 dB",
                xy=(1.0, float(eta(1.0)) * 100), xytext=(1.06, 74), fontsize=9.2, ha="left",
                arrowprops=dict(arrowstyle="->", color="0.4"))
    ax.axhline(50, color="#d1242f", lw=0.8, alpha=0.4)
    ax.text(0.02, 51.5, "50% = 3 dB", color="#d1242f", fontsize=8)
    ax.text(0.98, 6, "the real run:  core = 26.5 spot radii\n-> top even flatter, cliff even sharper",
            fontsize=8.5, style="italic", color="0.35")

    fig.suptitle(r"MMF encircled energy  =  non-central $\chi^2$ CDF sweeping past a fixed threshold"
                 "\n"
                 r"$\eta(d)=F_{\chi^2_{nc}}((a/\sigma)^2;\ k=2,\ \lambda=(d/\sigma)^2)$"
                 r"    with  $\sigma=w_s/2$    (cartoons: core = 5 spot radii, for visibility)",
                 fontsize=12, y=0.99)

    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"figure -> {out_path}")


def _selfcheck() -> None:
    """Check the two limits of the encircled-energy curve."""
    # On axis the spot is fully inside a big core, thus eta is ~1.
    assert float(eta(0.0)) > 0.999
    # The spot centre on the rim gives about half the power, thus eta is ~0.5.
    assert abs(float(eta(1.0)) - 0.5) < 0.05
    # A large offset walks the spot off the core, thus eta is ~0.
    assert float(eta(1.6)) < 1e-3


if __name__ == "__main__":
    _selfcheck()
    make_figure(Path(__file__).resolve().parents[1] / "mmf_encircled_energy.png")
