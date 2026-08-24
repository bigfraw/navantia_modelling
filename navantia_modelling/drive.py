"""The disturbance drive: the part of the interface that optomechanics owns.

This module converts the base acceleration of the standard into a disturbance
TORQUE about the gimbal axis. It uses the mass properties of the terminal:

    tau(f) = m * d * a(f)

where:
    m = the payload mass
    d = the lever arm from the centre of gravity to the axis. It changes with
        the state in the pointing envelope.
    a = the base acceleration from `spec`

This module owns m, d, and I as a RANGE, not as one value. The Config A/B
division and the open baseboard envelope make the mass properties a range. The
range stays open until the concept gate closes. All values here are
provisional.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import spec


@dataclass(frozen=True)
class MassProperties:
    """The mass properties of the terminal about the applicable gimbal axis.

    The value `lever_arm` changes with the state. A slew turns the payload in
    relation to its axes. Thus d changes in the pointing envelope. Use the
    maximum value, or calculate several points in the envelope. The ship
    attitude does NOT change d, because the rigid mass turns as one body. Only
    a gimbal slew moves the centre of gravity in relation to the axis.
    """

    mass: float        # kg
    lever_arm: float   # m,      the distance d from the centre of gravity to the axis
    inertia: float     # kg m^2, the moment of inertia about the axis

    def gravity_holding_torque(self, g: float = 9.81) -> float:
        """Give the static m*g*d holding torque [N m].

        Use this torque for MOTOR SIZING and for the droop load. It is NOT a
        jitter source. It is in this module only to keep it separate from the
        torque that the vibration causes."""
        return self.mass * g * self.lever_arm


def disturbance_torque(f, mp: MassProperties):
    """Give the zero-to-peak disturbance torque [N m] at the frequency f [Hz].

    tau(f) = m * d * a(f). This is a rigid-mass idealisation. It does NOT
    include the internal flexure paths. Refer to the interface note, open
    scope.
    """
    f = np.asarray(f, dtype=float)
    return mp.mass * mp.lever_arm * spec.acceleration(f)
