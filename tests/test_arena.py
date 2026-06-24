import ctypes
import pytest
from modules.arena import StaticArena, ScratchpadArena, TensorView


class TestStaticArena:
    def test_init(self):
        a = StaticArena(1024)
        assert a.total == 1024
        assert a.used == 0

    def test_alloc(self):
        a = StaticArena(1024)
        off = a.alloc(64)
        assert off == 0
        assert a.used == 64

    def test_alloc_aligned(self):
        a = StaticArena(1024)
        off = a.alloc(1)
        assert off == 0
        assert a.used == 64

    def test_overflow(self):
        a = StaticArena(64)
        a.alloc(64)
        with pytest.raises(MemoryError):
            a.alloc(1)

    def test_buf_is_bytearray(self):
        a = StaticArena(128)
        assert isinstance(a.buf, bytearray)
        assert len(a.buf) == 128


class TestScratchpadArena:
    def test_init(self):
        a = ScratchpadArena(1024)
        assert a.total == 1024
        assert a.used == 0

    def test_alloc_and_reset(self):
        a = ScratchpadArena(1024)
        off = a.alloc(64)
        assert off == 0
        assert a.used == 64
        a.reset()
        assert a.used == 0

    def test_max_off_tracking(self):
        a = ScratchpadArena(1024)
        a.alloc(128)
        assert a.used == 128
        a.reset()
        a.alloc(64)
        assert a.used == 64
        a.reset()
        a.alloc(256)
        assert a.used == 256

    def test_overflow(self):
        a = ScratchpadArena(64)
        a.alloc(64)
        with pytest.raises(MemoryError):
            a.alloc(1)


class TestTensorView:
    def test_init(self):
        buf = bytearray(1024)
        tv = TensorView([2, 3], ctypes.c_int8, buf, 0)
        assert tv.shape == [2, 3]
        assert len(tv) == 6

    def test_get_set_item(self):
        buf = bytearray(1024)
        tv = TensorView([4], ctypes.c_int8, buf, 0)
        tv[0] = 42
        assert tv[0] == 42

    def test_at2d(self):
        buf = bytearray(1024)
        tv = TensorView([2, 3], ctypes.c_int8, buf, 0)
        tv[0] = 1
        tv[1] = 2
        tv[2] = 3
        tv[3] = 4
        tv[4] = 5
        tv[5] = 6
        assert tv.at2d(0, 0) == 1
        assert tv.at2d(0, 2) == 3
        assert tv.at2d(1, 0) == 4
        assert tv.at2d(1, 2) == 6

    def test_fill(self):
        buf = bytearray(1024)
        tv = TensorView([5], ctypes.c_int8, buf, 0)
        tv.fill(-1)
        for i in range(5):
            assert tv[i] == -1

    def test_offset(self):
        buf = bytearray(1024)
        tv = TensorView([3], ctypes.c_int8, buf, 64)
        tv[0] = 99
        assert tv[0] == 99
