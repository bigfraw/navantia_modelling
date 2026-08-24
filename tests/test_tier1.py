"""Tests that check the code and also record the expected physics."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navantia_modelling import (
    MassProperties,
    acceleration,
    displacement_band_bound,
    lever_arm,
    openloop_bound,
    spec,
)

MP = MassProperties(mass=8.0, lever_arm=0.05, inertia=0.08)


def test_crossover_acceleration_is_about_7():
    # A displacement of +/-1 mm at 13.2 Hz gives approximately 7 m/s^2.
    # This is the crossover condition of the standard.
    a = float(acceleration(spec.F_CROSS - 1e-6))  # just below the displacement band limit
    assert abs(a - 7.0) < 0.2


def test_bound_is_flat_in_displacement_band():
    # Below crossover the term (2 pi f)^2 cancels. Thus the bound is a
    # plateau, and it does not change with frequency.
    f = np.array([2.0, 5.0, 10.0, 13.0])
    theta = openloop_bound(f, MP)
    assert np.allclose(theta, theta[0], rtol=1e-9)
    assert np.isclose(theta[0], displacement_band_bound(MP), rtol=1e-9)


def test_bound_rolls_off_as_inverse_f_squared_above_crossover():
    # Above crossover the torque is constant. Thus theta decreases as 1/f^2.
    # If the frequency increases by a factor of 2, the angle decreases by 4.
    a = float(openloop_bound(20.0, MP))
    b = float(openloop_bound(40.0, MP))
    assert np.isclose(a / b, 4.0, rtol=1e-6)


def test_lever_arm_geometry():
    # The lever arm is at the maximum at the phase angle, and it is zero at
    # 90 deg from the phase angle. There the CG is in line with the base
    # acceleration, thus it gives no torque about the axis.
    assert np.isclose(lever_arm(0.0, 0.05, phase_deg=0.0), 0.05)
    assert np.isclose(lever_arm(90.0, 0.05, phase_deg=0.0), 0.0, atol=1e-17)
    # A slew of +/-30 deg from the maximum gives cos(30) = 0.866 of r_cg.
    assert np.isclose(lever_arm([-30.0, 30.0], 0.05, 0.0), 0.05 * np.cos(np.pi / 6)).all()


def test_bound_is_linear_in_lever_arm():
    # The bound scales with d. Thus the slew envelope is a simple band.
    single = openloop_bound(20.0, MassProperties(mass=8.0, lever_arm=0.05, inertia=0.08))
    double = openloop_bound(20.0, MassProperties(mass=8.0, lever_arm=0.10, inertia=0.08))
    assert np.isclose(double / single, 2.0, rtol=1e-12)


def test_plateau_matches_closed_form():
    assert np.isclose(
        displacement_band_bound(MP),
        MP.mass * MP.lever_arm * spec.DISP_AMP / MP.inertia,
        rtol=1e-12,
    )


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
