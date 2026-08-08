"""
Capture 1 - poor finger contact

Recorded from the ESP32 hardware on 2026-07-31. Sample rate 50 Hz (400 Hz
internal, 8 samples averaged by the chip). Each entry is (ir, red), both
already shifted right by 3 by fifo_bytes_to_int(). 120 samples = 2.4 s.

Measured characteristics, de-trended with alpha=0.99 rather than raw
peak-to-peak - the raw figure is dominated by baseline drift and badly
overstates the pulse. These are residual amplitudes, not pulse amplitudes;
see the periodicity note below before treating either as a heartbeat:
    IR   residual  54.8 counts, DC 16227, 0.338 % of DC
    RED  residual  61.6 counts, DC 13515, 0.456 % of DC

Periodicity, from the autocorrelation of each de-trended channel over
lag 15-69 (200 down to 43 bpm):
    IR   lag=39 -> 77 bpm, r=0.21. Weak, but the period is where a
         resting heart rate belongs. Under a 0.5-5 Hz band-pass it
         sharpens to lag=40 at r=0.38.
    RED  lag=15 -> 200 bpm, r=0.47. The high r is misleading: lag 15 is
         the bottom of the search range, so the true peak may lie outside
         it, and 200 bpm is not a resting rate in any case. The band-pass
         drops it to r=0.20 while leaving the lag pinned to the boundary.
         There is no heartbeat in this channel, only contact noise.

Read the two together and the red channel is the louder of the two while
carrying no pulse at all. Red sits on a lower DC (13515 against 16227),
so an equal absolute disturbance is a larger fraction of its baseline.
Taking the amplitudes at face value gives R = 1.350 and SpO2 = 53.7 %,
which the same finger contradicts minutes later at 99 %. An implausible
SpO2 is the cheapest signal that a measurement is noise.

The channels are not swapped here. All three captures put field 0 near
16300 and field 1 near 13800, a ratio of 1.18-1.20 that never inverts,
and 880 nm infrared loses less in tissue than 660 nm red at the same
25.4 mA drive, so the larger of the two is infrared. The red/IR swap in
the driver was already fixed before any of these captures were recorded.

Use: the hardest sample. The one-pole DC follower fails on it at both
alpha=0.99 and alpha=0.95, producing no reading at all, so it is the
reference case for judging whether a band-pass filter actually helps.
"""

DATA = [
    (16271, 13581),
    (16259, 13575),
    (16251, 13570),
    (16247, 13566),
    (16247, 13562),
    (16246, 13558),
    (16244, 13555),
    (16243, 13555),
    (16244, 13556),
    (16245, 13555),
    (16245, 13552),
    (16244, 13549),
    (16243, 13547),
    (16241, 13546),
    (16241, 13547),
    (16242, 13547),
    (16244, 13546),
    (16247, 13547),
    (16252, 13553),
    (16255, 13558),
    (16255, 13558),
    (16253, 13554),
    (16251, 13551),
    (16252, 13549),
    (16251, 13548),
    (16248, 13545),
    (16246, 13543),
    (16245, 13541),
    (16244, 13540),
    (16243, 13539),
    (16241, 13535),
    (16239, 13533),
    (16240, 13534),
    (16242, 13537),
    (16243, 13537),
    (16243, 13535),
    (16243, 13532),
    (16242, 13531),
    (16241, 13527),
    (16237, 13522),
    (16230, 13518),
    (16221, 13514),
    (16215, 13512),
    (16215, 13512),
    (16217, 13512),
    (16219, 13513),
    (16221, 13513),
    (16221, 13514),
    (16222, 13513),
    (16222, 13513),
    (16221, 13512),
    (16222, 13511),
    (16222, 13512),
    (16221, 13513),
    (16222, 13515),
    (16224, 13515),
    (16225, 13514),
    (16227, 13513),
    (16229, 13513),
    (16230, 13514),
    (16231, 13514),
    (16230, 13513),
    (16229, 13511),
    (16229, 13510),
    (16228, 13507),
    (16228, 13505),
    (16227, 13505),
    (16226, 13506),
    (16224, 13504),
    (16224, 13504),
    (16224, 13505),
    (16224, 13504),
    (16224, 13503),
    (16224, 13501),
    (16223, 13501),
    (16222, 13501),
    (16222, 13501),
    (16223, 13503),
    (16223, 13503),
    (16218, 13500),
    (16209, 13493),
    (16200, 13488),
    (16194, 13486),
    (16193, 13487),
    (16195, 13487),
    (16195, 13487),
    (16197, 13489),
    (16198, 13490),
    (16200, 13489),
    (16201, 13490),
    (16204, 13492),
    (16206, 13492),
    (16206, 13490),
    (16206, 13490),
    (16205, 13489),
    (16205, 13489),
    (16207, 13488),
    (16210, 13487),
    (16210, 13488),
    (16210, 13487),
    (16211, 13487),
    (16211, 13485),
    (16211, 13485),
    (16211, 13485),
    (16212, 13487),
    (16215, 13492),
    (16217, 13494),
    (16218, 13495),
    (16220, 13496),
    (16220, 13494),
    (16221, 13494),
    (16220, 13490),
    (16221, 13488),
    (16219, 13486),
    (16219, 13485),
    (16220, 13485),
    (16220, 13485),
    (16221, 13485),
    (16221, 13482),
    (16220, 13482),
]
