"""Off-device test harness for the MAX30102 pulse oximeter.

The firmware runs on an ESP32 under MicroPython, but the source is standard
Python plus a handful of device-only modules. Replacing those modules with the
fakes in stubs/ lets the exact same source run here, so a 30-second experiment
finishes in about a second instead of requiring a finger on the sensor.

Three layers, each cutting the signal chain at a different point and replacing
everything upstream with something whose behaviour is controlled:

    chip  ->  I2C bus  ->  max30102.py  ->  pulse_oximeter.py  ->  output
                  ^                              ^
                  |                              |
        test_driver() cuts here      test_algorithm() / test_trace() cut here

Why layer it: an end-to-end failure only says "something is broken". A layered
failure shows which half. If test_driver() fails while test_algorithm() passes,
the issue is in register/FIFO/byte handling; the reverse points to filtering and
the SpO2 math. If both pass, the code is fine, and the problem lies in signal
quality or the device environment.

Layers 1 and 2 have a correct answer designed into them, so they assert - a
regression stops the run instead of quietly printing a wrong number. Layer 3
replays real captures whose true SpO2 is unknown, so it only reports. It is a
comparison tool, not a pass/fail check.

Run from any working directory:  python3 sim.py
"""

import os, sys

# Resolve paths from __file__ rather than the working directory, so the harness
# behaves the same whether it is run from the project root or from inside sim/.
PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PATH, "stubs"))
sys.path.insert(0, os.path.dirname(PATH))
# Insertion order matters: the project directory ends up ahead of stubs/, so the
# real modules (circular_buffer, max30102, pulse_oximeter) win, and only the
# device-only ones (utime, machine, ...) fall through to the fakes.

import math
import utime
from utime import ticks_ms, advance
from pulse_oximeter import Pulse_oximeter

# --- Layer 1 expectations ---------------------------------------------------
# The synthetic waveform below is built with a known perfusion ratio, so the
# correct output is known before the test runs. That is what separates a test
# from an observation.
#     R    = (90/9000) / (180/12000) = 0.6667
#     SpO2 = -45.060*R^2 + 30.354*R + 94.845 = 95.05 %
#     1.25 Hz * 60 = 75 bpm
EXPECTED_SPO2 = 95.05
EXPECTED_HR = 75.0
SPO2_TOLERANCE = 0.5  # observed error is ~0.09, from int() rounding the samples
HR_TOLERANCE = 1.0

# --- Layer 2 probe values ---------------------------------------------------
# Deliberately far apart: after fifo_bytes_to_int() shifts right by 3 they read
# as 582 and 5497, so a swapped channel is obvious at a glance. Two similar
# values (like the ~16000 and ~13800 seen on real hardware) would hide the swap.
RED = 0x001234  # -> 582 after the >>3 pulse-width shift
IR = 0x00ABCD  # -> 5497


class FakeSensor(object):
    """Layer 1 stand-in for MAX30102: emits a synthetic PPG waveform.

    Pulse_oximeter only ever calls five methods on its sensor, so five is all
    this needs - the other 51 methods of the real driver are irrelevant to the
    algorithm. A fake implements the contract with its caller, not the thing it
    replaces.
    """

    def __init__(self):
        self.next_at = 0
        self.ready = False
        self.red = 0
        self.ir = 0

    def set_led_mode(self, m):
        pass

    def check(self):
        now = ticks_ms()
        # One new sample every 20 ms = 50 Hz, matching 400 Hz / 8 averaged.
        if now >= self.next_at:
            self.ir = int(12000 + 180 * math.sin(2 * math.pi * 1.25 * now / 1000))
            self.red = int(9000 + 90 * math.sin(2 * math.pi * 1.25 * now / 1000))
            self.next_at = now + 20
            self.ready = True

        else:
            self.ready = False

        return self.ready

    def available(self):
        return 1 if self.ready else 0

    def pop_ir_from_storage(self):
        return self.ir

    def pop_red_from_storage(self):
        return self.red


class FakeI2C(object):
    """Layer 2 stand-in for the I2C bus, so the real driver can be exercised.

    The driver's whole contract with the bus is three methods. Register writes
    are remembered; the reads the driver depends on are answered explicitly.
    """

    def __init__(self):
        self.reg = {0xFF: 0x15}  # PART_ID, or check_part_id() rejects the device
        self.pending = None

    def scan(self):
        return [0x57]

    def writeto(self, addr, buf):
        # One byte selects the register to read next; two bytes write a value.
        if len(buf) == 1:
            self.pending = buf[0]

        else:
            self.reg[buf[0]] = buf[1]
            self.pending = None

    def readfrom(self, addr, n):
        r = self.pending
        if r == 0x04:  # FIFO_WRITE_PTR
            return bytes([1])  # pretend one sample is waiting...
        if r == 0x06:  # FIFO_READ_PTR
            return bytes([0])  # ...or check() sees an empty FIFO and returns early
        if r == 0x09:  # MODE_CONFIG
            # soft_reset() spins until the RESET bit clears, so clear it here or
            # setup_sensor() never returns.
            v = self.reg.get(r, 0) & ~0x40
            self.reg[r] = v
            return bytes([v])
        if r == 0x07:  # FIFO_DATA
            # SpO2 mode packs LED1 (RED) first, then LED2 (IR), 3 bytes each.
            return RED.to_bytes(3, "big") + IR.to_bytes(3, "big")

        # Fallback: without this, unhandled registers return None and the
        # driver's ord() call raises TypeError.
        return bytes([self.reg.get(r, 0)] * n)


class Replay(object):
    """Layer 3 stand-in: feeds samples captured from the real device.

    Same interface as FakeSensor, but the data is recorded rather than
    generated, which is what makes it useful for comparing parameter or
    algorithm choices against a fixed, repeatable signal.
    """

    def __init__(self, data):
        self.data = data
        self.i = 0
        self.next_at = 0
        self.ready = False
        self.cur = None

    def set_led_mode(self, m):
        pass

    def check(self):
        now = ticks_ms()
        if now >= self.next_at and self.i < len(self.data):
            self.cur = self.data[self.i]
            self.i += 1
            self.next_at = now + 20
            self.ready = True
        else:
            self.ready = False

        return self.ready

    def available(self):
        return 1 if self.ready else 0

    def pop_ir_from_storage(self):
        return self.cur[0]

    def pop_red_from_storage(self):
        return self.cur[1]


def test_algorithm():
    """Layer 1: pulse_oximeter.py alone, driven by a synthetic waveform."""
    # Every test resets the clock. AC_extractor and HR_calculator record
    # ticks_ms() at construction, so a non-zero start would shift the first
    # interval measurement.
    utime._t[0] = 0
    sensor = FakeSensor()
    pox = Pulse_oximeter(sensor)

    first = None
    n_update = 0
    n_nonzero = 0

    while ticks_ms() < 30000:  # simulate 30s
        pox.update()
        n_update += 1

        if pox.get_spo2() != 0:
            n_nonzero += 1
            if first is None:
                first = ticks_ms()
        advance(1)  # 1 ms per loop -> ~1000 updates/s, close to the real device

    spo2 = pox.get_spo2()
    hr = pox.get_heart_rate()

    # These two are worth printing even on a pass. A low non-zero ratio is what
    # exposed the "spo2 reset on every update" bug (0.08 %), and a late first
    # reading is what exposed the 12-second DC filter warm-up.
    print("Updates       : %d" % n_update)
    print("Non-zero      : %.1f %%" % (100.0 * n_nonzero / n_update))
    print("First reading : %s ms" % first)
    print("SpO2          : %.2f %%   (expected %.2f)" % (spo2, EXPECTED_SPO2))
    print("HR            : %.1f bpm  (expected %.1f)" % (hr, EXPECTED_HR))

    # Let a failed assert propagate. Catching it here would print the message
    # and carry on, which is no better than eyeballing the numbers.
    assert abs(spo2 - EXPECTED_SPO2) < SPO2_TOLERANCE, (
        "SpO2 should be %.2f +/- %.2f, got %.2f - suspect the DC removal, the "
        "AC extractor, or the ratio formula" % (EXPECTED_SPO2, SPO2_TOLERANCE, spo2)
    )
    assert abs(hr - EXPECTED_HR) < HR_TOLERANCE, (
        "HR should be %.1f +/- %.1f, got %.1f - suspect beat detection or "
        "target_n_beats" % (EXPECTED_HR, HR_TOLERANCE, hr)
    )

    print("PASS")
    print()


def test_driver():
    """Layer 2: max30102.py alone, driven by a fake I2C bus."""
    from max30102 import MAX30102

    s = MAX30102(i2c=FakeI2C())
    s.setup_sensor()
    # Start from a known-empty state: the reset sequence may have left samples
    # in the buffers.
    s.sense.ir.clear()
    s.sense.red.clear()
    s.check()

    # pop() consumes the value, so read each once and reuse for print + assert.
    got_ir = s.sense.ir.pop()
    got_red = s.sense.red.pop()

    print("sense.ir      : %-6d (expected %d)" % (got_ir, IR >> 3))
    print("sense.red     : %-6d (expected %d)" % (got_red, RED >> 3))

    # This is the probe that caught the swapped red/IR channels. It also catches
    # a "fix" that swaps the buffer names AND the byte offsets, which cancel out
    # and leave the mapping unchanged.
    assert got_ir == IR >> 3, (
        "IR channel holds %d but should hold %d - red/IR are swapped in "
        "check(), or the byte slice is wrong" % (got_ir, IR >> 3)
    )
    assert got_red == RED >> 3, (
        "RED channel holds %d but should hold %d - red/IR are swapped in "
        "check(), or the byte slice is wrong" % (got_red, RED >> 3)
    )

    print("PASS")
    print()


def test_trace():
    """Layer 3: replay captures recorded from the real device.

    No assert on the SpO2 value itself - the true reading for a real finger is
    unknown, so there is nothing to compare against. The only check is a
    plausibility band, which catches gross breakage (0 %, negative, above 100 %)
    without pretending to verify accuracy.

    trace1 currently yields nothing, and that is expected: its perfusion is
    0.34 % and the baseline drift outruns the one-pole DC follower, so the AC
    extractor never sees a zero crossing. It is the reference case for the
    band-pass filter - once that lands, trace1 should start producing a value.
    """
    import trace1, trace2, trace3

    for name, mod in (
        ("trace1 (bad contact) ", trace1),
        ("trace2 (good contact)", trace2),
        ("trace3               ", trace3),
    ):

        utime._t[0] = 0
        sensor = Replay(mod.DATA)
        pox = Pulse_oximeter(sensor)

        while sensor.i < len(mod.DATA):
            pox.update()
            advance(1)

        spo2 = pox.get_spo2()
        print("%s -> %s" % (name, ("%.2f %%" % spo2) if spo2 else "N/A"))

        if spo2:
            assert 85.0 < spo2 < 100.0, (
                "%s produced %.2f %%, outside any plausible range - that is a "
                "broken algorithm, not an imprecise one" % (name.strip(), spo2)
            )

    print()


def main():
    print("----- Layer 1: algorithm (pulse_oximeter.py) -----")
    test_algorithm()

    print("----- Layer 2: driver (max30102.py) -----")
    test_driver()

    print("----- Layer 3: recorded captures -----")
    test_trace()

    print("===== All checks passed =====")


if __name__ == "__main__":
    main()
