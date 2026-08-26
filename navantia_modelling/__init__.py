"""navantia_modelling — convert a vibration environment into a pointing jitter.

This package is for the Phase 1 optical terminal (WBS 1.3). It implements the
chain from the vibration input to the angle fluctuation. The document
`vibration_jitter_interface_note.md` gives the derivation.

The mount is an open-loop stepper, not a servoed gimbal. The chain (pathway 3)
reacts against a passive plant:

    base acceleration a(f) -> disturbance torque tau = m*d*a(f)
                           -> reacts against the passive rotor-on-detent plant
                              P_dist = 1/(I*s^2 + k_detent)
                           -> the residual angle is the pointing jitter

This package implements Tier 1 (the bare-inertia bound) only. Tier 1 is the only
tier that optomechanics can calculate alone, because it needs only tau(f) and I.
We own these two quantities. Tier 2 is the mount direct torque->angle
measurement, which gives the true plant P_dist and the detent peak. It is an
extension point.
"""

from .spec import VibrationSpec, acceleration, displacement
from .drive import MassProperties, disturbance_torque, lever_arm
from .jitter import openloop_bound, displacement_band_bound

__all__ = [
    "VibrationSpec",
    "acceleration",
    "displacement",
    "MassProperties",
    "disturbance_torque",
    "lever_arm",
    "openloop_bound",
    "displacement_band_bound",
]
