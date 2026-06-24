import ctypes
import math
import pytest
from modules.arena import StaticArena, TensorView
from modules.kernels import Int8Kernel, QuantizedOps


class TestInt8Kernel:
    def test_add_and_execute(self):
        calls = []
        k = Int8Kernel()
        k.add(lambda buf: calls.append("a"))
        k.add(lambda buf: calls.append("b"))
        k.execute(None)
        assert calls == ["a", "b"]

    def test_empty_execute(self):
        k = Int8Kernel()
        k.execute(None)


class TestQuantizedOps:
    def test_calibrate_scale_zero(self):
        buf = bytearray(1024)
        tv = TensorView([4], ctypes.c_int8, buf, 0)
        tv.fill(0)
        assert QuantizedOps.calibrate_scale(tv) == 1.0

    def test_calibrate_scale_positive(self):
        buf = bytearray(1024)
        tv = TensorView([3], ctypes.c_int8, buf, 0)
        tv[0] = 0
        tv[1] = 50
        tv[2] = 100
        scale = QuantizedOps.calibrate_scale(tv)
        assert math.isclose(scale, 127.0 / 100, rel_tol=1e-3)

    def test_calibrate_scale_negative(self):
        buf = bytearray(1024)
        tv = TensorView([2], ctypes.c_int8, buf, 0)
        tv[0] = -80
        tv[1] = 10
        scale = QuantizedOps.calibrate_scale(tv)
        assert math.isclose(scale, 127.0 / 80, rel_tol=1e-3)

    def test_requantize_relu(self):
        inp = [10, -5, 20, 0]
        out = [0] * 4
        QuantizedOps.requantize_relu(inp, 1.0, out)
        assert out == [10, 0, 20, 0]

    def test_requantize_linear(self):
        inp = [10, -6, 20]
        out = [0] * 3
        QuantizedOps.requantize_linear(inp, 0.5, out)
        assert out == [5, -3, 10]

    def test_dynamic_requantize_relu(self):
        inp = [-10, 50, -30, 100]
        out = [0] * 4
        scale = QuantizedOps.dynamic_requantize_relu(inp, out)
        assert inp == [0, 50, 0, 100]
        assert out[0] == 0
        assert out[3] == 127
        assert 0 < scale <= 127.0 / 100

    def test_dynamic_requantize_relu_with_scale_ref(self):
        inp = [10, 20, 30]
        out = [0] * 3
        scale_ref = [0.0]
        QuantizedOps.dynamic_requantize_relu(inp, out, scale_ref)
        assert scale_ref[0] > 0

    def test_matmul_int8_tiled(self):
        s = StaticArena(4096)
        buf = s.buf
        A = TensorView([2, 3], ctypes.c_int8, buf, s.alloc(6))
        B = TensorView([3, 2], ctypes.c_int8, buf, s.alloc(6))
        C = TensorView([2, 2], ctypes.c_int32, buf, s.alloc(16))
        A_data = [1, 2, 3, 4, 5, 6]
        B_data = [1, 0, 0, 1, 1, 0]
        for i, v in enumerate(A_data):
            A[i] = v
        for i, v in enumerate(B_data):
            B[i] = v
        QuantizedOps.matmul_int8_tiled(A, B, C)
        assert C[0] == 1*1 + 2*0 + 3*1
        assert C[1] == 1*0 + 2*1 + 3*0
        assert C[2] == 4*1 + 5*0 + 6*1
        assert C[3] == 4*0 + 5*1 + 6*0
