"""The Tier 1 bare-inertia jitter bound.

The mount is an open-loop stepper, not a servoed gimbal. There is no feedback
loop and no sensitivity function. This module models the payload as a PURE
INERTIA P = 1/(I s^2), which drops the passive detent stiffness. The residual
angle is the disturbance torque with two integrations against the inertia alone:

    theta(f) = tau(f) / (I * (2*pi*f)^2)
             = m * d * a(f) / (I * (2*pi*f)^2)

The accuracy flips sign at the detent resonance sqrt(k_detent/I), from the
interface note:
  - CONSERVATIVE above the detent resonance. There the inertia term dominates,
    and tau/I is a good, safe bound.
  - NON-CONSERVATIVE at and below the detent resonance. This bound drops
    k_detent, thus it misses the resonant peak and under-predicts the jitter.
    The resonance may sit inside the >13.2 Hz budget band, and it moves with the
    Config A/B mass decision. Only the Tier 2 measurement gives that peak.

Plant idealisation: tau/I is the k_detent -> 0 limit of the real plant
I s^2 + k_detent. The detent stiffness k_detent is the motor magnetic holding
spring. It is the PRIMARY passive rejection, not a small correction term. Below
the detent resonance the stiffness dominates and holds the residual small. Above
it the inertia term I*w^2 dominates and the bound is good again. The detent
torque and the Coulomb friction are non-linear at the small residual angles that
a fibre-coupling budget uses. Thus they ADD torque ripple and are a disturbance
source, not only a loss. Report this to the mount. The value of k_detent is a
mount input. It must be measured, because FLIR does not specify it.
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
    is constant, and the bare-inertia bound decreases as 1/f^2. Thus the maximum
    bare-inertia angle is at a low frequency. This is the shape of a pure
    inertia. The real plant is different. The passive detent stiffness holds the
    plateau smaller and adds a resonant peak at sqrt(k_detent/I). The Tier 2
    measurement gives the real shape.
    """
    return mp.mass * mp.lever_arm * spec.DISP_AMP / mp.inertia


def as_microrad(theta_rad):
    """Convert an angle from radians to microradians."""
    return np.asarray(theta_rad, dtype=float) * 1.0e6
