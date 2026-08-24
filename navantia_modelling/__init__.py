"""navantia_modelling — convert a vibration environment into a pointing jitter.

This package is for the Phase 1 optical terminal (WBS 1.3). It implements the
chain from the vibration input to the angle fluctuation. The document
`vibration_jitter_interface_note.md` gives the derivation.

The chain (pathway 3, a servoed gimbal):

    base acceleration a(f) -> disturbance torque tau = m*d*a(f)
                           -> the loop rejects the in-band part (sensitivity S)
                           -> the residual angle is the pointing jitter

This package implements Tier 1 (the open-loop bound) only. Tier 1 is the only
tier that optomechanics can calculate alone, because it needs only tau(f) and
I. We own these two quantities. Tier 2 and Tier 3 need the loop shape or the
compensator C of the mount. They are extension points.
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
