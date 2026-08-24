"""The Tier 1 open-loop jitter bound.

This module models the payload as a pure inertia P = 1/(I s^2), and the loop
does nothing (the sensitivity S is 1). The residual angle is the disturbance
torque with two integrations against the inertia alone:

    theta(f) = tau(f) / (I * (2*pi*f)^2)
             = m * d * a(f) / (I * (2*pi*f)^2)

The accuracy, from the interface note:
  - EXACT above the loop bandwidth. There S is 1, and the largest jitter
    occurs there.
  - CONSERVATIVE below the bandwidth. There the true loop cancels the larger
    part of tau.
  - TOO SMALL in the narrow waterbed band immediately above crossover. There
    the true sensitivity is more than 1. Only Tier 2 and Tier 3 give that peak.

Plant idealisation: tau/I is the limit of the correct open-loop plant
I s^2 + c s + k, when c and k decrease to zero. The terms c and k are the
bearing friction, the back-EMF damping, and the detent stiffness or cable
stiffness. These terms increase as k, c*w, and I*w^2. In the high band the
inertia term is much larger, and the high band sets the budget. Thus it is
conservative to remove c and k there. There is one exception. The detent
torque and the Coulomb friction are non-linear. They can ADD torque ripple at
small residual angles. Report this to the mount for a calculation. The terms c
and k are in the hardware of the mount, thus the values are mount inputs.
"""
from __future__ import annotations

import numpy as np

from . import spec
from .drive import MassProperties, disturbance_torque


def openloop_bound(f, mp: MassProperties):
    """Give the Tier 1 open-loop angular jitter bound at the frequency f [Hz].

    The result is in rad, zero to peak. theta(f) = tau(f) / (I * (2*pi*f)^2).
    """
    f = np.asarray(f, dtype=float)
    tau = disturbance_torque(f, mp)
    return tau / (mp.inertia * (spec.TWO_PI * f) ** 2)


def displacement_band_bound(mp: MassProperties) -> float:
    """Give the Tier 1 bound in the displacement-control band [rad].

    Below crossover a(f) = (2*pi*f)^2 * x0. Thus the term (2*pi*f)^2 cancels,
    and the bound DOES NOT CHANGE WITH FREQUENCY:

        theta = m * d * x0 / I

    This is a constant plateau from 2 Hz to 13.2 Hz. Above crossover the torque
    is constant, and the bound decreases as 1/f^2. Thus the maximum open-loop
    angle is at a low frequency. This is the OPEN-loop peak. The closed-loop
    maximum stays at a high frequency, because the loop decreases this
    low-frequency plateau but does not change the high band.
    """
    return mp.mass * mp.lever_arm * spec.DISP_AMP / mp.inertia


def as_microrad(theta_rad):
    """Convert an angle from radians to microradians."""
    return np.asarray(theta_rad, dtype=float) * 1.0e6
