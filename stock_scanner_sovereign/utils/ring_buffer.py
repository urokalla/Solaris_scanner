import numpy as np
class RingBuffer:
    def __init__(self, capacity=1250, columns=5):
        self.cap, self.cols, self.idx, self.full = capacity, columns, 0, False
        self.data = np.zeros((capacity, columns), dtype=np.float64)
    def append(self, row):
        self.data[self.idx] = row
        self.idx = (self.idx + 1) % self.cap
        if self.idx == 0: self.full = True
    def extend(self, arr):
        sz = len(arr)
        if sz == 0: return
        if sz >= self.cap:
            self.data[:] = arr[-self.cap:]; self.idx, self.full = 0, True
        else:
            end = self.idx + sz
            if end <= self.cap:
                self.data[self.idx:end] = arr; self.idx = end % self.cap
                if end == self.cap: self.full = True
            else:
                p1 = self.cap - self.idx; self.data[self.idx:] = arr[:p1]; self.data[:sz - p1] = arr[p1:]
                self.idx, self.full = sz - p1, True
    def get_ordered_view(self): return self.data[:self.idx] if not self.full else np.roll(self.data, -self.idx, axis=0)
    def clear(self): self.idx, self.full = 0, False
    def is_empty(self) -> bool:
        """True when no rows have been appended (prefer over len() for older code paths)."""
        return not self.full and self.idx == 0
    def __len__(self): return self.cap if self.full else self.idx
