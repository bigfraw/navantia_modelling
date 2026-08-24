"""The swept-sine ship qualification vibration standard.

This standard is a DISTURBANCE INPUT. It is not a jitter output. It gives the
base acceleration that the terminal receives. Calculate the result at each
frequency. The standard is a deterministic swept sine. It is NOT a random
vibration PSD. Do not use it as g^2/Hz statistics.

The profile applies to all three axes:
  - 2.0 Hz to 13.2 Hz : displacement control, +/-1 mm (zero to peak)
  - 13.2 Hz to 100 Hz : acceleration control, 7 m/s^2 (zero to peak)
  - the crossover is at 13.2 Hz. There a +/-1 mm sine gives approximately
    7 m/s^2.

The equation a = (2*pi*f)^2 * x gives one continuous acceleration curve. Below
13.2 Hz the input energy increases with f^2. Above 13.2 Hz the input energy is
constant. Thus the energy is concentrated in the UPPER band.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TWO_PI = 2.0 * np.pi

# --- The breakpoints of the standard --------------------------------------
F_LOW = 2.0        # Hz, the low limit of the qualification sweep
F_CROSS = 13.2     # Hz, the crossover from displacement to acceleration
F_HIGH = 100.0     # Hz, the high limit
DISP_AMP = 1.0e-3  # m,     zero-to-peak displacement (+/-1 mm) below crossover
ACCEL_AMP = 7.0    # m/s^2, zero-to-peak acceleration    above crossover

FREQ_BAND = (F_LOW, F_HIGH)


def acceleration(f):
    """Give the zero-to-peak base acceleration [m/s^2] at the frequency f [Hz].

    Below crossover the sweep uses displacement control. Thus
    a = (2*pi*f)^2 * x. Above crossover the sweep uses acceleration control at
    a constant value of 7 m/s^2.

    The parameter `f` is a scalar or an array. The result has the same shape.
    """
    f = np.asarray(f, dtype=float)
    return np.where(f < F_CROSS, (TWO_PI * f) ** 2 * DISP_AMP, ACCEL_AMP)


def displacement(f):
    """Give the zero-to-peak base displacement [m] at the frequency f [Hz].

    Below crossover this is the controlled value of +/-1 mm. Above crossover
    the constant acceleration sets the value: x = a / (2*pi*f)^2.
    """
    f = np.asarray(f, dtype=float)
    return np.where(f < F_CROSS, DISP_AMP, ACCEL_AMP / (TWO_PI * f) ** 2)


def in_band(f):
    """Give a boolean mask. It is true where `f` is in the band 2 Hz to 100 Hz."""
    f = np.asarray(f, dtype=float)
    return (f >= F_LOW) & (f <= F_HIGH)


@dataclass(frozen=True)
class VibrationSpec:
    """The qualification standard as an object.

    Use this class if the parameters must change. Examples are a different
    vessel class, or a tailored test level. The default values give the
    baseline swept-sine profile above."""

    f_low: float = F_LOW
    f_cross: float = F_CROSS
    f_high: float = F_HIGH
    disp_amp: float = DISP_AMP
    accel_amp: float = ACCEL_AMP

    def acceleration(self, f):
        f = np.asarray(f, dtype=float)
        return np.where(f < self.f_cross, (TWO_PI * f) ** 2 * self.disp_amp, self.accel_amp)

    def displacement(self, f):
        f = np.asarray(f, dtype=float)
        return np.where(f < self.f_cross, self.disp_amp, self.accel_amp / (TWO_PI * f) ** 2)
