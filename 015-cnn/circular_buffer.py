from ucollections import deque


class CircularBuffer(object):
    """Very simple implementation of a circular buffer based on deque"""

    def __init__(self, max_size):
        self.data = deque((), max_size, True)
        self.max_size = max_size

    def __len__(self):
        return len(self.data)

    def append(self, item):
        try:
            self.data.append(item)
        except IndexError:
            # deque full, popping 1st item out
            self.data.popleft()
            self.data.append(item)

    def pop(self):
        return self.data.popleft()

    def clear(self):
        self.data = deque((), self.max_size, True)
