import ctypes
import pytest
from modules.arena import StaticArena, TensorView
from modules.graph import Int8Graph


class TestInt8Graph:
    def test_init(self):
        s = StaticArena(4096)
        g = Int8Graph(s)
        assert not g._compiled

    def test_register_weight(self):
        s = StaticArena(4096)
        g = Int8Graph(s)
        tv = g.register_weight("w1", [2, 3], [1, 2, 3, 4, 5, 6], scale=0.5)
        assert isinstance(tv, TensorView)
        assert tv[0] == 1
        assert tv[5] == 6
        assert "w1" in g._weights

    def test_register_weight_infers_scale(self):
        s = StaticArena(4096)
        g = Int8Graph(s)
        tv = g.register_weight("w2", [2, 2], [0, 50, 100, 0])
        assert g._scales["w2"] > 0

    def test_compile_empty(self):
        s = StaticArena(4096)
        g = Int8Graph(s)
        g.compile([])
        assert g._compiled

    def test_execute_not_compiled(self):
        s = StaticArena(4096)
        g = Int8Graph(s)
        with pytest.raises(RuntimeError):
            g.execute(None)

    def test_compile_and_execute(self):
        s = StaticArena(8192)
        g = Int8Graph(s)
        g.register_weight("bigram", [3, 2], [1, 2, 3, 4, 5, 6], scale=0.5)
        nodes = [("MatMul", ["x", "bigram"], ["out_i32", "out_y"], {})]
        g.compile(nodes)
        assert g._compiled
        scratch = bytearray(4096)
        g.execute(scratch)

    def test_get_output_unknown(self):
        s = StaticArena(4096)
        g = Int8Graph(s)
        tv, scale = g.get_output("nonexistent")
        assert tv is None
        assert scale == 0

    def test_get_output_known(self):
        s = StaticArena(4096)
        g = Int8Graph(s)
        g.register_weight("w", [2, 2], [1, 2, 3, 4], scale=0.3)
        tv, scale = g.get_output("w")
        assert tv is not None
        assert scale == 0.3

    def test_calibrate(self):
        s = StaticArena(4096)
        g = Int8Graph(s)
        g.register_weight("w", [2, 2], [0, 50, 100, 0])
        g.calibrate()
        assert g._scales["w"] > 0
