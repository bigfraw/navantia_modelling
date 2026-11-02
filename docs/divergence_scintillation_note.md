# Divergence, jitter and scintillation at 10 km

Date: 2026-10-28. Script: `scripts/divergence_jitter_sweep.py`. Figure:
`figures/divergence_jitter_sweep.png`.

## Case

- Path 10 km, 1550 nm, Cn2 5e-15, 50.8 mm bucket.
- Tx waist radius 9.08 mm. Divergence 54 to 300 urad. The 54 urad case is the
  diffraction limit λ/(π·w0) = 54.3 urad. The Rayleigh range is 167 m.
- Pointing jitter: Gaussian on each axis, sigma = 0, 0.1 and 0.25 times the
  divergence.
- 1000 turbulent trials for each divergence. Each trial gives 20 jitter draws.
- All divergences use the same seed, thus the same atmospheres (paired trials).

## Result (bucket loss in dB)

| Div (urad) | sigma/theta | Vacuum mean | Mean | sigma2_P | p50 | p99 |
|---|---|---|---|---|---|---|
| 54 | 0 | 23.6 | 24.6±0.2 | 1.70±0.21 | 26.7 | 36.4±0.4 |
| 54 | 0.1 | 23.8 | 24.7 | 1.37±0.04 | 26.7 | 36.4 |
| 54 | 0.25 | 24.6 | 25.4 | 1.53±0.05 | 27.7 | 38.0 |
| 75 | 0 | 26.5 | 27.1±0.2 | 1.58±0.14 | 29.3 | 38.5±0.3 |
| 75 | 0.1 | 26.6 | 27.3 | 1.33±0.03 | 29.3 | 38.6 |
| 75 | 0.25 | 27.4 | 27.9 | 1.46±0.04 | 30.1 | 39.8 |
| 100 | 0 | 29.0 | 29.2±0.2 | 1.71±0.27 | 31.4 | 41.5±0.3 |
| 100 | 0.1 | 29.1 | 29.5 | 1.41±0.05 | 31.5 | 41.0 |
| 100 | 0.25 | 29.9 | 30.2 | 1.47±0.04 | 32.4 | 42.0 |
| 150 | 0 | 32.5 | 32.8±0.2 | 1.45±0.13 | 35.1 | 44.0±0.3 |
| 150 | 0.1 | 32.6 | 32.9 | 1.31±0.03 | 34.9 | 43.8 |
| 150 | 0.25 | 33.4 | 33.7 | 1.37±0.03 | 35.8 | 45.1 |
| 200 | 0 | 35.0 | 35.3±0.2 | 1.27±0.10 | 37.3 | 46.5±0.3 |
| 200 | 0.1 | 35.1 | 35.2 | 1.35±0.04 | 37.2 | 46.1 |
| 200 | 0.25 | 35.9 | 36.0 | 1.37±0.04 | 38.1 | 47.4 |
| 300 | 0 | 38.5 | 38.8±0.2 | 1.42±0.15 | 40.9 | 50.5±0.4 |
| 300 | 0.1 | 38.6 | 38.7 | 1.35±0.05 | 40.8 | 49.4 |
| 300 | 0.25 | 39.4 | 39.5 | 1.44±0.06 | 41.6 | 50.9 |

The ± values on the jitter rows are a lower bound, because each trial gives 20
correlated draws. The runtime was 0.4 s/trial at 54 urad (n = 2048) and
13.4 s/trial at 300 urad (n = 5888).

## Findings

1. **The scintillation does not decrease with divergence.** sigma2_P stays at
   1.3 to 1.7 from 54 to 300 urad. Thus the fade margin (mean to p99) stays at
   11 to 12 dB.
2. **Reason 1: the path is in saturation.** The Rytov variance is
   sigma_R² = 1.23·Cn2·k^(7/6)·L^(11/6) ≈ 6.8. In saturation, r0 and the
   scattering disc L/(k·r0) set the scintillation. These are turbulence
   quantities, not beam quantities.
3. **Reason 2: each beam is in its far field.** The Fresnel parameter is
   Λ0 = 2L/(k·w0²) ≈ 60, thus the link is 60 Rayleigh ranges long. At the
   receiver, Θ and Λ are near zero, which is the spherical-wave limit. A larger
   divergence moves the beam further into that limit. This also applies in weak
   turbulence.
4. **Divergence changes the mean, not the fades.** See the next section.
5. **The jitter cost is small in turbulence.** Jitter of 0.25·theta adds about
   0.7 to 0.9 dB to the mean and 0.4 to 1.6 dB to the p99. In vacuum, the same
   jitter adds 5 dB to the p99. The scintillation fades already set the tail.

## Turbulence spread of the mean

Turbulence adds a spread angle of approximately λ/(π·ρ0) ≈ 20 to 30 urad
(spherical-wave ρ0 ≈ 26 mm). This angle adds in quadrature to the beam
divergence. The 9.08 mm waist is smaller than ρ0, thus diffraction sets the
footprint. The long-term spread is W_LT² = W²·(1 + 1.33·sigma_R²·Λ^(5/6)), with
Λ = 2L/(k·W²) at the receiver.

| Div (urad) | Λ | Predicted excess (dB) | Sweep excess (dB) |
|---|---|---|---|
| 54 | 0.017 | 1.1 | 0.95±0.2 |
| 75 | 0.009 | 0.8 | 0.6±0.2 |
| 100 | 0.005 | 0.45 | 0.2±0.2 |
| 150 | 0.002 | 0.24 | 0.3±0.2 |
| 200 | 0.001 | 0.14 | 0.4±0.2 |
| 300 | 0.0005 | 0.06 | 0.3±0.2 |

The theory and the sweep agree at 54 to 150 urad. At 200 and 300 urad the sweep
is 1 to 2 SE above the theory. The paired trials share their error, thus the
rows are not independent.

## Off-axis scintillation

The off-axis scintillation index is larger than the on-axis index, because the
beam has an intensity gradient. The radial term scales as (r/W)². Thus jitter
must increase sigma2_P.

- **The sigma = 0 rows are not a good reference.** Each sigma = 0 row reads only
  the on-axis point of 1000 atmospheres. All divergences share these
  atmospheres. Thus a few bright on-axis trials raise sigma2_P in all rows
  together (1.70 ± 0.21 at 54 urad). The jitter rows read 20 points in each
  trial, so their estimate is more stable.
- **Compare sigma = 0.1 against sigma = 0.25.** sigma2_P increases in all six
  divergences, by 0.02 to 0.16. The increase is larger at small divergence
  (0.06 to 0.16 at 54 to 100 urad) than at large divergence (0.02 to 0.09 at
  150 to 300 urad). This agrees with the off-axis argument.
- **The increase is smaller than weak theory.** The weak-theory radial term is
  approximately 4.4·sigma_R²·Λ^(5/6)·<r²/W²> ≈ 0.13 at 54 urad. Saturation
  decreases it: the beam breaks into speckle, and the long-term footprint W_LT
  sets the mean profile.

Thus jitter increases the scintillation a little, as expected. It does not
decrease it.

## Beam size for a near-field beam

The beam leaves the spherical-wave limit when Λ0 ≲ 1. At 10 km and 1550 nm:

- Transition (Λ0 = 1): w0 = √(2L/k) ≈ 70 mm radius (140 mm 1/e² diameter).
- Plane-wave behaviour (Λ0 ≈ 0.1): w0 ≈ 0.2 m radius.
- Our waist (9.08 mm) gives Λ0 ≈ 60. The radius is approximately 8 times too
  small.

This size is not realistic for the terminal. It also does not remove the
scintillation:

- The spherical-wave r0 on this path is approximately 54 mm. A 140 mm beam
  spans 2 to 3 r0, thus the turbulence spreads the beam far beyond its
  diffraction footprint.
- At sigma_R² ≈ 6.8, the on-axis index goes to the saturated value for all wave
  types.
- The gain is power, not fade margin. The diffraction divergence is
  approximately 7 urad. The mean loss decreases by approximately 15 dB, but
  the pointing must then hold to a few urad.

## Open checks

- Calculate sigma2_I against the offset r/W from the stored maps, without the
  jitter average. This gives the off-axis profile directly.
- Do a short run at Cn2 ≈ 1e-16 (sigma_R² ≈ 0.14). The far-field argument
  predicts that sigma2_P stays flat with divergence there too.
