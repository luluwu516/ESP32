from collections import deque as _deque

# simulate MicroPython (add flags variable)
def deque(iterable, maxlen, flags=0):
    return _deque(iterable, maxlen)