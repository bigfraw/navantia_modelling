"""Tests that check the code and also record the expected physics."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navantia_modelling import (
    MassProperties,
    acceleration,
    displacement_band_bound,
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
