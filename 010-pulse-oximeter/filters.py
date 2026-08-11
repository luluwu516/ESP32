from math import pi, exp


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
