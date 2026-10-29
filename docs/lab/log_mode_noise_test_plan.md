# Test Plan — WiDy SenS 320V-ST Log-Mode Noise

**Purpose:** Measure the log-mode values that the datasheet does not give. The
values replace the PLACEHOLDERS in `scripts/beacon_camera_snr.py`.
**Status:** Plan. Created 2026-10-21.

| Result | Script parameter |
|---|---|
| temporal code noise [LSB rms] | `LOG_NOISE_LSB` |
| residual FPN after the NUC [LSB rms], against the sensor temperature | `LOG_FPN_LSB` |
| floor current [e-/s], against the sensor temperature | the log floor (now `DARK_E_S`) |
| response slope [LSB/decade] | `LOG_LSB_DECADE` (datasheet: 600) |
| conversion gain [e-/LSB], CTIA high gain | a check of `QE` and `DARK_REF_E_S` |
| detection contrast threshold | a check of `log_required_rate` |

---

## 1. Equipment

- the camera, the USB3 cable, and an external supply for the TEC
- the 1550 nm LED and its current driver
- a diffuser: a PTFE sheet, an opal glass, or printer paper
- ND filters, enough for 3 to 4 decades
- a calibrated InGaAs power meter (1550 nm)
- a tape measure, and a rail or a bench for the distance steps
- a dark enclosure or a dark room
- the 140 mm receive lens, the 10 nm filter, and the 1550 nm laser with a
  fibre collimator (Section 4 only)

## 2. Camera settings for all tests

1. Record RAW 14-bit data (.PTW or the SDK). Do not record AVI or JPEG.
2. Set the histogram stretch, the gamma, and the contrast enhancement to off.
3. Record the state of the factory NUC and the bad pixel correction. Do each
   test with the NUC on. Do Test B one time with the NUC off.
4. Record the sensor temperature from the camera readout for each recording.
5. After each change of the TEC setpoint, wait 10 minutes before you record.
6. Name each file with the mode, the setpoint, the level, and the exposure.
   Example: `log_T25_d050cm_ND2_I100mA_t1ms.ptw`.

## 3. Bench tests (indoors, controlled light)

### Test A — Dark frames against the sensor temperature

1. Put the lens cap on. Set the log mode, with a 1 ms exposure.
2. Record 1000 frames at each TEC setpoint: 15, 25, 35, 45, 48 C.
3. Repeat at 25 C in CTIA high gain, for the dark current in e-/s.

The TEC heats as well as it cools. Thus you can sweep the sensor temperature
with the housing at the room temperature.

### Test B — Response curve (flat field)

Set-up: LED → diffuser → free space (0.2 m to 2 m) → camera, with no lens.
Remove the 10 nm filter. You need only the relative level here.

1. Set the TEC to 25 C and the log mode, with a 1 ms exposure.
2. Step the level in steps of approximately 3 dB from dark to the top of the
   range (more than 6 decades). Use these three controls:
   - the distance: the level changes as 1/d^2 (keep d much larger than the diffuser)
   - the ND filters
   - the LED current (measure each step with the power meter)
3. Record 200 frames at each level.
4. At each level, put the power meter head at the sensor plane. Record the
   power. Record it again behind the 10 nm filter at 3 levels or more, for the
   absolute scale.
5. Repeat 5 levels with the NUC off.
6. Repeat 5 levels at 45 C.
7. Move the camera by 2 mm to 3 mm at one level. Record 200 frames. This
   separates the illumination pattern from the pixel pattern.

### Test C — Exposure time

At 3 levels from Test B, record 200 frames at 100 us, 1 ms, and 10 ms (the
log-mode maximum).

### Test D — Photon transfer curve (CTIA high gain)

Use the Test B set-up. Record pairs of frames at 10 levels, from dark to near
the full well (17 ke-). This gives the conversion gain in e-/LSB.

## 4. Outdoor test (the end-to-end check)

Set-up: the laser through a fibre collimator, with a known divergence, at a
measured range. The camera has the 140 mm lens and the 10 nm filter, in the
log mode.

1. Apply the laser safety controls for the range before you start.
2. Measure the laser power before the ND filters.
3. Step the power down (ND filters) until the spot is no longer visible
   against the adjacent pixels. Record 500 frames at each step.
4. At each step, record 500 frames with the laser blocked. These give the
   background and the on-minus-off difference.
5. Record the sky in the background: clear sky, sunlit cloud, or overcast.
   Also record the sun direction, the time, the range, and the weather.
6. Do the test again under different sky conditions on different days.

## 5. Analysis

| Quantity | Calculation |
|---|---|
| temporal noise | the std over frames of each pixel, then the mean over pixels |
| FPN | the spatial std of the frame mean, after you subtract a 15x15 median-filtered copy; remove sigma_t^2 / N |
| slope and floor | fit `code = s log10(1 + I / I_floor) + c0` to the mean code against the level |
| noise against level | the temporal noise at each level of Test B (the model assumes it is constant) |
| drift | the std of the difference of consecutive frames, divided by sqrt(2); the per-pixel PSD over frames |
| conversion gain | the slope of the variance against the mean of the frame-pair differences (Test D) |
| contrast threshold | the smallest spot that gives dcode >= 10 sigma; compare with `log_required_rate` |
| background rate | the background code around the spot, converted with the Test B fit |

## 6. Limits of this plan

- The LED illumination is not perfectly flat. The median subtraction and the
  2 mm camera move remove the slow pattern. They do not remove a pattern at
  the pixel scale from a dirty diffuser.
- The housing stays at the room temperature. Thus the plan does not test the
  TEC capacity at a hot housing. The datasheet value (15 C) stays in the model.
- The outdoor background is not controlled. Measure it from each frame. Do not
  assume it.
