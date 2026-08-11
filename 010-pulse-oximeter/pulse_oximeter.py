from max30102 import MAX30102
from utime import ticks_ms, ticks_diff
from filters import IIR_filter
from detectors import AC_extractor, Rate_calculator


class Pulse_oximeter(object):
    def __init__(self, sensor):
        sensor.set_led_mode(2)
        self.sensor = sensor

        self.raw_ir = 0
        self.raw_red = 0

        self.spo2 = 0
        self.heart_rate = 0

        self.is_beating = False
        self.is_available = False

        self.ac_extractor_ir = AC_extractor()
        self.ac_extractor_red = AC_extractor()

        # self.dc_remover_ir = IIR_filter(0.99)
        # self.dc_remover_red = IIR_filter(0.99)
        self.dc_remover_ir = IIR_filter(0.95)  # adjust to 0.95
        self.dc_remover_red = IIR_filter(0.95)

        self.hr_calculator = Rate_calculator()

    def update(self):
        # self.spo2 = 0  # bug!
        self.sensor.check()
        if self.sensor.available():
            self.is_available = True
            self.raw_ir = self.sensor.pop_ir_from_storage()
            self.raw_red = self.sensor.pop_red_from_storage()

            ir_dc = self.dc_remover_ir.step(self.raw_ir)  # get the dc
            red_dc = self.dc_remover_red.step(self.raw_red)

            ir_nodc = self.raw_ir - ir_dc  # remove the dc
            red_nodc = self.raw_red - red_dc

            self.ac_extractor_ir.update(ir_nodc)
            self.ac_extractor_red.update(red_nodc)

            ir_ac = self.ac_extractor_ir.ac
            red_ac = self.ac_extractor_red.ac

            time_mark_ir = self.ac_extractor_ir.get_time_mark
            time_mark_red = self.ac_extractor_red.get_time_mark

            # self.is_beating = self.ac_extractor_red.is_down_period
            self.is_beating = self.ac_extractor_ir.is_down_period  # change to ir

            self.hr_calculator.update(self.is_beating)
            self.heart_rate = self.hr_calculator.get_rate()

            ir_red_intval = abs(ticks_diff(time_mark_ir, time_mark_red))
            if ir_ac > 0 and red_ac > 0:
                if ir_red_intval < 100:
                    ratio = (red_ac / red_dc) / (ir_ac / ir_dc)
                    self.spo2 = -45.060 * ratio**2 + 30.354 * ratio + 94.845

                self.ac_extractor_ir.reset_ac()
                self.ac_extractor_red.reset_ac()
        else:
            self.is_available = False

    def available(self):
        return self.is_available

    def get_spo2(self):
        return self.spo2

    def get_raw_ir(self):
        return self.raw_ir

    def get_raw_red(self):
        return self.raw_red

    def get_heart_rate(self):
        return self.heart_rate
