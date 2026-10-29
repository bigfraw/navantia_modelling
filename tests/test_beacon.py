"""Tests of the beacon camera model."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import beacon_camera_snr as bc


def test_optimum_divergence_is_sqrt2_theta_e():
    # P ~ (1/theta^2) exp(-2 theta_e^2 / theta^2) has its maximum at
    # theta = sqrt(2) theta_e (docs/interfaces/beacon_divergence_spec_note.md).
    theta_e = 2e-3
    half = np.linspace(1e-3, 6e-3, 2001)
    for z in bc.RANGES_M:
        p = bc.required_ptx_dbm(-85.0, z, half, theta_e)
        assert abs(half[np.argmin(p)] / (np.sqrt(2) * theta_e) - 1) < 0.01


def test_mispoint_loss_at_optimum_is_4p3_db():
    assert abs(bc.mispoint_db(np.sqrt(2) * 1e-3, 1e-3) - 10 * np.log10(np.e)) < 1e-9
