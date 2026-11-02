# Interface Note — Maritime Optical Turbulence Characterisation

**WBS:** 1.3.2 (Optomechanics & Atmospherics) → 1.5.3 (Atmospheric propagation) interface
**Author:** Optomechanics & Atmospherics (WBS 1.3 lead)
**Status:** Research note. It records the maritime turbulence facts for the coupling simulation. It supplies inputs for the split-step backend in CLAUDE.md §6. It is not an interface agreement with the mount.

---

## 0. Purpose of this note

This note answers one question. How does near-surface maritime optical
turbulence behave, and how does it differ from the standard von Kármán model?

The context is the horizontal ship-to-ship link. The link runs 1 km to 5 km.
The receive aperture is about 25 mm. The wavelength is 1550 nm. The beam skims
the air-sea interface. The atmospheric angle-of-arrival movement is the second
part of the pointing budget. The vibration jitter is the first part. See
CLAUDE.md §6.

A deep-research run produced the facts below. The run fetched 19 sources. It
extracted 49 claims. It verified 25 claims with a three-vote adversarial check.
It confirmed 25 claims. It refuted none. Each fact below gives its confidence
and its primary source.

---

## 1. The primary principle

**Maritime turbulence keeps a Kolmogorov −5/3 inertial subrange.** It is not a
different physics. The standard isotropic von Kármán spectrum is still a poor
fit near the sea surface. There are three reasons. The method to get the
turbulence strength over water is also different from the method over land.

The three differences are:

1. Humidity is a first-order driver of `Cn²`. Over land it is negligible.
2. The marine spectrum is non-Kolmogorov and anisotropic in the FSOC
   literature. The power-law exponent is variable, not the fixed 11/3.
3. The strength `Cn²` comes from bulk meteorology, not from the spectrum. The
   accuracy depends strongly on atmospheric stability.

---

## 2. How the turbulence is characterised and measured

`Cn²` is the refractive-index structure constant. It is the primary metric for
maritime optical turbulence. It sets the received-power fluctuation, the beam
spread, and the beam wander.

Over the sea, engineers estimate `Cn²` from bulk meteorology. They do not need
a direct optical instrument. The inputs are the mean wind, the air-sea
temperature difference, and the humidity. The models are Monin-Obukhov
similarity models. The Navy models are NSLOT and NAVSLaM. Field campaigns
validated the estimates:

- a 7 km infrared scintillation path over San Diego Bay (EOPACE 1998);
- a 7.2 km path with a flux buoy (SPIE 6303, 2006);
- a large-aperture scintillometer with in-situ data (JOSA A 2024).

*[high confidence; 6 merged claims, all 3-0]*

Sources:
- Frederickson et al. "Estimating the Refractive Index Structure Parameter
  (C_n^2) over the Ocean Using Bulk Methods." Journal of Applied Meteorology,
  39(10):1770-1783, 2000.
  https://journals.ametsoc.org/view/journals/apme/39/10/1520-0450-39.10.1770.xml
- Frederickson et al. "Measurements and modeling of optical turbulence in a
  maritime environment." Proc. SPIE 6303, 630307, 2006. DOI 10.1117/12.683017.
  https://www.spiedigitallibrary.org/conference-proceedings-of-spie/6303/1/Measurements-and-modeling-of-optical-turbulence-in-a-maritime-environment/10.1117/12.683017.short
- Burkhardt et al. Journal of the Optical Society of America A, 41(6):B65,
  2024. PubMed 38856411. https://pubmed.ncbi.nlm.nih.gov/38856411/ This dataset
  ran nearly four years. It is the most comprehensive near-surface dataset to
  date. (Confirm the title and author list at the source.)

**The bulk-model accuracy depends on the atmospheric stability.** The agreement
is good in unstable conditions. Unstable conditions are typically warm water or
daytime. The agreement degrades near neutral. The agreement is poor in stable
conditions. In stable air the turbulence is intermittent and non-stationary,
because mesoscale motions drive it. Thus the Monin-Obukhov similarity theory
loses validity. The structure functions that build on it lose validity too.
*[medium confidence; this was the only split vote in the run, 2-1. The dissent
was about the extension from similarity theory to structure functions, and
about an imprecise "stable = nighttime" gloss that does not hold over water.]*

Source: South China Sea micro-thermometer study. Remote Sensing, 15(3):631,
2023. DOI 10.3390/rs15030631. https://doi.org/10.3390/rs15030631 (Confirm the
author list at the DOI. The research run did not capture it.)

---

## 3. Typical quantitative values

The near-surface `Cn²` spans about 1e-16 to 1e-13 m^(−2/3). It has a clear
diurnal cycle. The land-derived Wyngaard 1973 relation over-predicts `Cn²` near
the sea surface. The error is worst in weak turbulence. Thus a sea-specific
parameterisation is necessary. A sea-tuned model raised the correlation by 0.05
to 0.27. It cut the RMSE by 0.04 to 0.56 against Wyngaard. *[high confidence,
both sub-claims 3-0]*

Source: South China Sea micro-thermometer study (about 2 m height). Remote
Sensing, 15(3):631, 2023. DOI 10.3390/rs15030631. https://doi.org/10.3390/rs15030631

Corroborating source (the sea-specific parameterisation): Frederickson et al.
"Improving bulk C_n^2 models for over-ocean applications through new
determinations of the dimensionless temperature structure parameter." 2007.
https://www.researchgate.net/publication/252203593

**Caveat for the budget.** These magnitudes come from one regional dataset (the
South China Sea). The exact 2 m height and the diurnal polarity are not fully
confirmed for the open ocean. The values at other locations may differ.

**Open input — inner scale and outer scale.** No source in this set gave a
maritime inner scale `l0` or outer scale `L0` magnitude near the sea surface.
The literature confirms that `l0` is an influential parameter in the
scintillation models. It supplies no over-sea number. Treat `l0` and `L0` as
open inputs. This is the same rule that the repository uses for `k_detent`. See
CLAUDE.md §3. Do not invent a value.

---

## 4. How it differs from standard von Kármán

### 4.1 Humidity is a first-order contributor to `Cn²`

Over the marine boundary layer, the refractive-index fluctuation variance
decomposes into three terms:

- a temperature spectrum;
- a humidity spectrum;
- a temperature-humidity cross-spectrum (the cospectrum).

Over land the humidity term is a negligible correction. Over the sea it is not.
The humidity correlation term ranges from about +17% (cold air over warm ocean)
to a dominant cancelling −268% (dry air over the Salton Sea) of the total
refractive-index variance. Each of the three terms keeps a −5/3 inertial
subrange. *[high confidence, both 3-0]*

Source: Friehe et al. "Effects of temperature and humidity fluctuations on the
optical refractive index in the marine boundary layer." Journal of the Optical
Society of America, 65(12):1502-1511, 1975.
https://www.researchgate.net/publication/231222215 (Confirm the full author
list at the source. The research run confirmed the journal, volume, page, and
year.)

The physics inherits the Kolmogorov and Obukhov-Corrsin scaling. The difference
is in the sources that feed the fluctuation. The difference is not in the
spectral slope of the inertial range.

### 4.2 Non-Kolmogorov power law and finite scales

The maritime FSOC scintillation work replaces the von Kármán spectrum. It uses
a generalized spectrum with a variable power-law exponent. The exponent is not
the fixed 11/3. The generalized form uses exponents from 3 to 5. The value 11/3
is a special case. It keeps finite inner and outer scales. It reduces to the
classical non-Kolmogorov spectrum as `l0 → 0` and `L0 → ∞`. Both `l0` and the
exponent affect the scintillation index. *[high confidence, 3-0]*

Sources:
- Cui et al. "Scintillation and aperture averaging for Gaussian beams through
  non-Kolmogorov maritime atmospheric turbulence channels." Applied Optics,
  2015. PubMed 26699050. https://pubmed.ncbi.nlm.nih.gov/26699050/
- Xue et al. "Generalized modified atmospheric spectral model for optical wave
  propagating through non-Kolmogorov turbulence." Journal of the Optical
  Society of America A, 28(5):912, 2011.
  https://opg.optica.org/josaa/abstract.cfm?uri=josaa-28-5-912 This is the
  general non-Kolmogorov framework. It is not maritime-specific.

### 4.3 Anisotropy breaks the circular symmetry

The generalized anisotropic spectra add eddy asymmetry in the transverse plane.
They use two direction-dependent anisotropy factors. Thus they remove the
circular-symmetry assumption of the standard von Kármán model. The power-law
exponents run from 3 to 4. *[high confidence, 3-0]*

For a Gaussian-Schell-model beam, the anisotropic marine turbulence shifts the
scintillation index by direction. The on-axis index is higher over the sea than
over land. The off-axis index is lower. More anisotropy lowers the on-axis
index and raises the off-axis index. *[medium confidence; single paper, single
beam model. Do not generalize this to a coherent Gaussian beam.]*

Sources:
- "Generalized anisotropic turbulence spectra and applications in the optical
  waves' propagation through anisotropic turbulence." Optics Express,
  23(23):30088, 2015.
  https://opg.optica.org/oe/abstract.cfm?uri=oe-23-23-30088 (Toselli / Andrews
  / Phillips lineage.)
- "Influence of moderate-to-strong anisotropic non-Kolmogorov turbulence on
  intensity fluctuations of a Gaussian-Schell model beam in marine
  atmosphere." Chinese Physics B, 27(5):054203, 2018.
  https://cpb.iphy.ac.cn/article/2018/1940/cpb_27_5_054203.html
  (Gaussian-Schell partially coherent beam only.)

---

## 5. What this means for our link

Longer wavelength and larger aperture both reduce scintillation. The
weak-turbulence variance scales as about λ^(−7/6). The receiver aperture
averages the fluctuation. Thus 1550 nm helps against 780 nm to 850 nm. But a
25 mm aperture at 1 km to 5 km is near or below the transverse coherence scale.
Thus the aperture-averaging gain is modest. It reduces the scintillation. It
does not remove it. *[high confidence, 3-0]*

Source: Cui et al. "Scintillation and aperture averaging for Gaussian beams
through non-Kolmogorov maritime atmospheric turbulence channels." Applied
Optics, 2015. PubMed 26699050. https://pubmed.ncbi.nlm.nih.gov/26699050/

The facts map onto the repository architecture in CLAUDE.md §6:

- The non-Kolmogorov and anisotropic result means the split-step phase-screen
  backend must not fix an isotropic von Kármán screen. Make the power-law
  exponent and the two anisotropy factors parameters. Do this the same way that
  the beacon wavelength is a parameter.
- The humidity three-term `Cn²` result means a bulk-meteorology front end sets
  the turbulence strength from a sea state. Do not pick a `Cn²` directly.
- The stability dependence is the maritime analogue of a placeholder range. The
  worst case is stable, intermittent air. This is where the standard models
  fail. Give it its own flag.

---

## 6. Open questions

These questions the research run did not close. The last one feeds the pointing
budget directly.

1. What are the maritime `l0` and `L0` magnitudes near the surface, and how do
   they scale with height and fetch? The run confirmed that `l0` matters. It
   found no over-sea number.
2. Does the sea-versus-land and on-axis-versus-off-axis anisotropy behaviour
   hold for a coherent Gaussian beam, not only a Gaussian-Schell beam? What
   power-law exponent is representative over the sea?
3. How do `Cn²`, the anisotropy, and the humidity contribution vary with height
   in the first few metres above the water, and with fetch?
4. At 1550 nm, with a 25 mm aperture, over 1 km to 5 km, what is the residual
   scintillation index and the angle-of-arrival (beam-wander) variance after
   aperture averaging? How does this magnitude compare with the vibration
   jitter budget in the coupling model?
