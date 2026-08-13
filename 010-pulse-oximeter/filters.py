"""
Robert Bristow-Johnson (RBJ) audio cookbook: https://www.w3.org/TR/2021/NOTE-audio-eq-cookbook-20210608/
"""

from math import pi, exp, sin, cos


class IIR_filter(object):
    def __init__(self, alpha):
        self.old_value = None
        self.alpha = alpha

    @classmethod
    def from_cutoff(cls, fs, fc):
        """Alternative constructor: IIR_filter.from_cutoff(50, 0.41) == alpha 0.95."""
        return cls(exp(-2.0 * pi * fc / fs))

    def step(self, value):
        if self.old_value is None:
            self.old_value = value
            return value

        self.old_value = self.alpha * self.old_value + (1 - self.alpha) * value
        return self.old_value


class Biquad(object):
    """Second order section, Direct Form II Transposed.

    Coefficients follow the RBJ audio cookbook. Build one with low_pass()
    or high_pass(), not by hand.

    Rolls off at 12 dB/octave against the 6 dB of IIR_filter. With a 0.5 Hz
    corner a one-pole still passes about half of a 0.25 Hz baseline drift;
    this passes a quarter of it.

    Numerical limit: as fc/fs shrinks, a2 approaches 1 and single precision
    (what ESP32 MicroPython uses) starts to lose it. Keep fc/fs above about
    0.001. At 50 Hz a 0.5 Hz corner gives 0.010, which is comfortable.
    """

    def __init__(self, b0, b1, b2, a1, a2):
        self.b0, self.b1, self.b2 = b0, b1, b2
        self.a1, self.a2 = a1, a2
        self.s1 = self.s2 = 0.0
        self.primed = False

    @staticmethod
    def _shared(fs, fc, q):
        w0 = 2.0 * pi * fc / fs
        cw, sw = cos(w0), sin(w0)
        return cw, sw / (2.0 * q)

    @classmethod
    def low_pass(cls, fs, fc, q=0.7071):
        cw, alpha = cls._shared(fs, fc, q)
        a0 = 1.0 + alpha
        return cls(
            (1.0 - cw) / 2.0 / a0,
            (1.0 - cw) / a0,
            (1.0 - cw) / 2.0 / a0,
            (-2.0 * cw) / a0,
            (1.0 - alpha) / a0,
        )

    @classmethod
    def high_pass(cls, fs, fc, q=0.7071):
        cw, alpha = cls._shared(fs, fc, q)
        a0 = 1.0 + alpha
        return cls(
            (1.0 + cw) / 2.0 / a0,
            -(1.0 + cw) / a0,
            (1.0 + cw) / 2.0 / a0,
            (-2.0 * cw) / a0,
            (1.0 - alpha) / a0,
        )

    def _prime(self, x):
        """Load the state so a constant input x is already in steady state.

        Same idea as seeding IIR_filter with its first sample, but it matters
        more here. From zero state a 16000 count input makes the filter ring
        for seconds, which is the 12 second warm-up all over again.
        """
        y = x * (self.b0 + self.b1 + self.b2) / (1.0 + self.a1 + self.a2)
        self.s2 = self.b2 * x - self.a2 * y
        self.s1 = self.b1 * x - self.a1 * y + self.s2
        self.primed = True

    def step(self, x):
        if not self.primed:
            self._prime(x)
        y = self.b0 * x + self.s1
        self.s1 = self.b1 * x - self.a1 * y + self.s2
        self.s2 = self.b2 * x - self.a2 * y
        return y


class BandPass(object):
    """High-pass then low-pass in series.

    Not the cookbook band-pass biquad. That one is built around a centre
    frequency and a Q, which suits a narrow band. A pulse band of 0.5 to
    5 Hz spans more than three octaves, and one section stretched that wide
    peaks instead of staying flat. Two sections give a flat passband and a
    clean skirt on each side.
    """

    def __init__(self, fs, f_low, f_high):
        self.hp = Biquad.high_pass(fs, f_low)
        self.lp = Biquad.low_pass(fs, f_high)

    def step(self, x):
        return self.lp.step(self.hp.step(x))


class Channel(object):
    """One sensor channel: band-passed AC plus a slow DC estimate.

    step() returns (ac, dc). They are used differently: ac feeds beat
    detection and the waveform, dc is the denominator of the perfusion
    index. The DC tracker stays a one-pole on purpose, because a baseline
    estimate wants a gentle follower rather than a sharp skirt.
    """

    def __init__(self, fs, f_low, f_high, dc_cutoff=None):
        self.ac_filter = BandPass(fs, f_low, f_high)
        self.dc_filter = IIR_filter.from_cutoff(fs, dc_cutoff if dc_cutoff else f_low)

    def step(self, x):
        return self.ac_filter.step(x), self.dc_filter.step(x)


class AGC(object):
    """Automatic gain control for a zero-centred AC signal.

    A band-pass has a gain of about 1: it removes what is not the pulse but
    never makes the pulse larger. This does make it larger, by dividing out
    a running estimate of the current amplitude. A weak pulse and a strong
    one then reach the same height on screen.

    Attack faster than release, but not instant. An instant attack sets the
    envelope to the sample that caused it, so the output lands on exactly
    target and the systolic peak comes out as a flat plateau. Measured on
    replayed captures it flattened 20 to 36 samples, 0.4 to 0.7 s, which
    destroys the peak the ECG comparison needs a landmark from. At
    attack_hz=0.5 the plateau is 4 samples, and the band-passed waveform's
    own peak is 4 samples wide, so nothing is being flattened at all.

    The slower attack costs nothing measurable: normalisation stays within
    1.13x across captures spanning 6.3x in perfusion, recovery after the
    pulse suddenly weakens is 1.0 s against 1.6 s for the instant version,
    and the usable range of beat thresholds is wider.

    Two things it costs, both worth knowing before using it for anything
    but a display:

      - Amplitude information is gone. Measured on the recorded captures,
        perfusion ranging 0.195 % to 1.228 %, a 6.3x spread, comes out
        within 1.3x after this. You can no longer judge contact quality by
        how tall the trace is, and it must never feed a perfusion or SpO2
        calculation.

      - With no finger on the sensor the envelope collapses and noise gets
        the full gain. That is what floor is for: it caps the gain at
        target/floor. At floor=16 the weakest real capture still reaches
        183 out of a 200 target, while a 2 count noise signal only reaches
        about 25.
    """

    def __init__(self, fs, target=100.0, attack_hz=0.5, release_hz=0.15, floor=16.0):
        # attack_hz is half the pulse fundamental, so its 0.32 s time
        # constant cannot follow an 80 ms upstroke and the peak survives.
        self.attack = exp(-2.0 * pi * attack_hz / fs)
        self.release = exp(-2.0 * pi * release_hz / fs)
        self.target = target
        self.floor = floor
        self.env = None

    def step(self, ac):
        a = ac if ac >= 0 else -ac

        if self.env is None:
            self.env = a
        elif a > self.env:
            self.env = self.env * self.attack + a * (1.0 - self.attack)
        else:
            self.env = self.env * self.release + a * (1.0 - self.release)

        e = self.env if self.env > self.floor else self.floor
        return ac * self.target / e
