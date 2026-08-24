# Synthesis log

Each entry records one run of the `repo-change-synthesis` skill. The next run
starts from the last entry's `to` commit.

---

## 2026-08-24 — 121e719..9e51c8e

First synthesis. The range covers the whole history to date.

The jitter thread (spec, drive, jitter, the Tier 1 script, the tests) landed
and is already documented in CLAUDE.md, thus it is not re-synthesised here.

Two new signals reached the docs. First, a one-way bridge from the Tier 1
jitter to an MMF coupling loss now exists (`scripts/vibration_to_coupling.py`,
commit 170e918). It uses the `optical_link_budget` package. It has no
turbulence and no closed loop. It is a partial landing of thread 2, not the
closed-loop simulation. Second, the CG offset became a 3-vector, and each
gimbal axis now has its own perpendicular arm `r_perp` and its own inertia
(commit 9e51c8e). An offset along an axis gives zero torque on that axis. The
open-loop jitter of a uniform block is mass-independent, and it is a maximum
when `r_perp` equals the radius of gyration.

Direct edits: CLAUDE.md §1, §5, §6, §8. No mount input arrived. The Config A/B
fork did not move. The mass properties are still placeholders.
