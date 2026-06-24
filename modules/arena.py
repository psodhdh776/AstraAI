import ctypes


class StaticArena:
    def __init__(self, size_bytes=4*1024*1024):
        self._buf = bytearray(size_bytes)
        self._off = 0

    def alloc(self, nbytes):
        aligned = (nbytes + 63) & ~63
        if self._off + aligned > len(self._buf):
            raise MemoryError("StaticArena overflow")
        p = self._off
        self._off += aligned
        return p

    @property
    def buf(self): return self._buf

    @property
    def used(self): return self._off

    @property
    def total(self): return len(self._buf)


class ScratchpadArena:
    def __init__(self, size_bytes=2*1024*1024):
        self._buf = bytearray(size_bytes)
        self._off = 0
        self._max_off = 0

    def alloc(self, nbytes):
        aligned = (nbytes + 63) & ~63
        if self._off + aligned > len(self._buf):
            raise MemoryError("ScratchpadArena overflow")
        p = self._off
        self._off += aligned
        if self._off > self._max_off:
            self._max_off = self._off
        return p

    def reset(self):
        self._off = 0

    @property
    def buf(self): return self._buf

    @property
    def used(self): return self._off

    @property
    def total(self): return len(self._buf)


class TensorView:
    def __init__(self, shape, dtype, buf, offset):
        self.shape = shape
        self.dtype = dtype
        self._buf = buf
        self._offset = offset
        total = 1
        for s in shape:
            total *= s
        self._nbytes = total * ctypes.sizeof(dtype)

    @property
    def _arr(self):
        return (self.dtype * (self._nbytes // ctypes.sizeof(self.dtype))).from_buffer(
            self._buf, self._offset
        )

    def at2d(self, r, c):
        return self._arr[r * self.shape[1] + c]

    def fill(self, val):
        for i in range(len(self._arr)):
            self._arr[i] = val

    def __len__(self): return len(self._arr)
    def __getitem__(self, idx): return self._arr[idx]
    def __setitem__(self, idx, val): self._arr[idx] = val
