# simulate time
# it's controllable by code
_t = [0]

def ticks_ms():
    return _t[0]

def ticks_diff(a, b):
    return a - b

def sleep_ms(n):
    _t[0] += n
    
# there is no advance() in utime library
# just for simulate env
def advance(n):
    _t[0] += n