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


def lever_arm(slew_deg, r_cg: float, phase_deg: float = 0.0):
    """Give the lever arm d [m] at the gimbal slew angle slew_deg [deg].

    The centre of gravity is at the radius r_cg from the gimbal axis. A slew
    turns the centre of gravity about that axis. The disturbance torque uses
    only the part of r_cg that is perpendicular to the base acceleration:

        d(phi) = r_cg * |cos(phi - phase)|

    `phase_deg` is the slew angle where d is at the maximum. It is a
    PLACEHOLDER. The build geometry of the centre of gravity gives the true
    value, and the concept gate sets that geometry. The default value of 0 deg
    puts the maximum at boresight.

    The moment of inertia I does not change with this slew. A rotation about
    an axis does not change the moment of inertia about that same axis.

    The parameter `slew_deg` is a scalar or an array. The result has the same
    shape.
    """
    slew = np.asarray(slew_deg, dtype=float)
    return r_cg * np.abs(np.cos(np.radians(slew - phase_deg)))


def disturbance_torque(f, mp: MassProperties):
    """Give the zero-to-peak disturbance torque [N m] at the frequency f [Hz].

    tau(f) = m * d * a(f). This is a rigid-mass idealisation. It does NOT
    include the internal flexure paths. Refer to the interface note, open
    scope.
    """
    f = np.asarray(f, dtype=float)
    return mp.mass * mp.lever_arm * spec.acceleration(f)
