# Cycle detection for periodic biosignals.
#
# A filter maps one sample to one sample. The classes here do not: they track
# where you are inside a cycle and how long the last few cycles took. That is
# why they live apart from filters.py.
#
# Nothing here is specific to a heartbeat. The period window is a constructor
# argument, so the same code serves a pulse, a breath, or an R-wave.


from utime import ticks_ms, ticks_diff

class AC_extractor(object):
    """Peak-to-peak amplitude of the last cycle, plus the cycle phase.

    Feed it a signal with the baseline already removed, so it swings either
    side of zero. Two outputs:
        .ac              peak-to-peak of the most recent accepted cycle
        .is_down_period  True while the signal is below the baseline

    is_down_period turning False to True is the downward zero crossing, one
    per cycle. Rate_calculator times those edges.
    """

    def __init__(self, min_period_ms=270, max_period_ms=2000):
        self.min_period_ms = min_period_ms
        self.max_period_ms = max_period_ms

        # 0 doubles as "not set yet". Safe only because max_ac is assigned
        # from strictly positive values and min_ac from strictly negative
        # ones, so neither can legitimately be 0. Keep that property.
        self.max_ac = 0
        self.min_ac = 0

        self.ac = 0

        self.cycle_time_mark = ticks_ms()
        self.get_time_mark = ticks_ms()

        self.is_down_period = False

    def update(self, value_nodc):
        if value_nodc > 0:
            if self.max_ac != 0 and self.min_ac != 0:
                self.is_down_period = False
                time_intval = ticks_diff(ticks_ms(), self.cycle_time_mark)
                if self.max_period_ms > time_intval > self.min_period_ms:
                    self.ac = self.max_ac - self.min_ac
                    self.get_time_mark = ticks_ms()
                self.max_ac = 0
                self.min_ac = 0

                self.cycle_time_mark = ticks_ms()
            else:
                if value_nodc > self.max_ac:
                    self.max_ac = value_nodc
        elif value_nodc < 0 and self.max_ac != 0:
            self.is_down_period = True
            if value_nodc < self.min_ac:
                self.min_ac = value_nodc

    def reset_ac(self):
        self.ac = 0


class Rate_calculator(object):
    """
    Cycles per minute, averaged over the last target_n_cycles intervals.

    Named for the rate, not the heart: fed a breath phase it reports breaths
    per minute with no change.
    """

    def __init__(self, target_n_cycles=5, min_period_ms=270, max_period_ms=2000):
        self.target_n_cycles = target_n_cycles
        self.min_period_ms = min_period_ms
        self.max_period_ms = max_period_ms

        self.n_cycles = 0
        self.rate = 0.0
        self.total_intval = 0

        # None, not ticks_ms(). Timestamping at construction makes the first
        # interval run from power-on to the first cycle instead of between
        # two cycles, and that gap gets averaged in as though it were real.
        # Measured on the 75 bpm synthetic signal, it reported 84.3 bpm.
        self.cycle_time_mark = None

        self.is_cycling = False

    def update(self, is_cycling):
        if self.is_cycling == False and is_cycling == True:
            now = ticks_ms()

            if self.cycle_time_mark is None:
                self.cycle_time_mark = now
            else:
                intval = ticks_diff(now, self.cycle_time_mark)
                self.cycle_time_mark = now

                if self.max_period_ms > intval > self.min_period_ms:
                    self.n_cycles += 1
                    self.total_intval += intval
                    if self.n_cycles == self.target_n_cycles:
                        self.rate = self.target_n_cycles / (
                            self.total_intval / 1000 / 60
                        )
                        self.total_intval = 0
                        self.n_cycles = 0
                else:
                    self.total_intval = 0
                    self.n_cycles = 0

        self.is_cycling = is_cycling

    def get_rate(self):
        return self.rate
