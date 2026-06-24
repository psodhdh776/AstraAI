import ctypes
from .arena import StaticArena, ScratchpadArena, TensorView
from .graph import Int8Graph


class AiEngine:
    def __init__(self, static_size=4*1024*1024, scratch_size=2*1024*1024, threaded=False):
        self._static = StaticArena(static_size)
        self._scratch = ScratchpadArena(scratch_size)
        self._graph = Int8Graph(self._static)
        self._threaded = threaded
        self._compiled = False
        self._input_scale = 0.04
        self._output_size = 3
        self._scratch_buf = None

    def build(self, layer_sizes=None, weights=None):
        if layer_sizes is None or len(layer_sizes) < 2:
            layer_sizes = [4, 8, 3]

        self._output_size = layer_sizes[-1]
        num_layers = len(layer_sizes) - 1

        if layer_sizes == [4, 8, 3] and weights is None:
            _p_w1 = [12, -30, 45, -5, 64, -12, 80, 0, -22, -40, 32, 18]
            _p_w2 = [10, -5, 3, -2, 8, -1, 4, 6, -3, 7, -4, -6,
                     2, -8, 5, -7, 1, -9, 9, -10, 11, 0, -11, 12]
            self._graph.register_weight("w1", [4, 8], _p_w1, 0.02)
            self._graph.register_weight("w2", [8, 3], _p_w2, 0.03)
            self._x_off = self._scratch.alloc(4 * ctypes.sizeof(ctypes.c_int8))
            self._h0_i32_off = self._scratch.alloc(8 * ctypes.sizeof(ctypes.c_int32))
            self._h0_off = self._scratch.alloc(8 * ctypes.sizeof(ctypes.c_int8))
            self._out_i32_off = self._scratch.alloc(3 * ctypes.sizeof(ctypes.c_int32))
            self._out_off = self._scratch.alloc(3 * ctypes.sizeof(ctypes.c_int8))
            self._scratch.reset()
            nodes = []
            nodes.append(("MatMul", ["x", "w1"], ["h0_i32", "h0"], {}))
            nodes.append(("MatMul", ["h0", "w2"], ["out_i32", "out_y"], {}))
            scratch_offsets = {
                "x": (self._x_off, [1, 4]),
                "h0": (self._h0_off, [1, 8]),
                "h0_i32": (self._h0_i32_off, [1, 8]),
                "out_i32": (self._out_i32_off, [1, 3]),
                "out_y": (self._out_off, [1, 3]),
            }
            self._graph.compile(nodes, scratch_offsets)
            self._compiled = True
            return

        for i in range(num_layers):
            in_d = layer_sizes[i]
            out_d = layer_sizes[i + 1]
            if weights and f"w{i+1}_data" in weights:
                wd = weights[f"w{i+1}_data"]
                ws = weights.get(f"w{i+1}_scale", 0.02)
            else:
                import random as _r
                _r.seed(42 + i)
                wd = [max(-128, min(127, round(_r.gauss(0, 16)))) for _ in range(in_d * out_d)]
                ws = 0.03
            self._graph.register_weight(f"w{i+1}", [in_d, out_d], wd, ws)

        nodes = []
        so = {"x": (0, [1, layer_sizes[0]])}
        for i in range(num_layers):
            w_name = f"w{i+1}"
            in_name = "x" if i == 0 else f"act{i-1}"
            acc_name = f"acc{i}"
            out_name = f"act{i}" if i < num_layers - 1 else "out_y"
            nodes.append(("MatMul", [in_name, w_name], [acc_name, out_name], {}))
            out_d = layer_sizes[i + 1]
            in_off, _ = so[in_name]
            acc_off = in_off + out_d * ctypes.sizeof(ctypes.c_int8) + 64
            out_off = acc_off + out_d * ctypes.sizeof(ctypes.c_int32) + 64
            for name, off in [(acc_name, acc_off), (out_name, out_off)]:
                if name not in so:
                    so[name] = (off, [1, out_d])
        self._graph.compile(nodes, so)
        self._compiled = True

    def predict(self, input_data, input_scale=None):
        if not self._compiled:
            self.build()
        if input_scale is None:
            input_scale = self._input_scale
        n = len(input_data)
        qi = [max(-128, min(127, round(v / input_scale))) for v in input_data]
        qiv = TensorView([1, n], ctypes.c_int8, self._scratch.buf, self._x_off)
        for i, v in enumerate(qi):
            qiv[i] = v
        self._scratch.reset()
        self._scratch_buf = self._scratch.buf
        self._graph.execute(self._scratch.buf)
        out_tv, _ = self._graph.get_output("out_y")
        if out_tv is None:
            out_tv = TensorView([1, self._output_size], ctypes.c_int8, self._scratch.buf, self._out_off)
        w_scales = []
        for w_name in ["w1", "w2"]:
            w = self._graph._weights.get(w_name)
            if w:
                w_scales.append(w[1])
        scale = self._input_scale
        for s in w_scales:
            scale *= s
        if scale == 0:
            scale = 0.5
        return [float(out_tv[i]) * scale for i in range(len(out_tv))]

    def get_logits(self, input_data, input_scale=None):
        result = self.predict(input_data, input_scale)
        while len(result) < self._output_size:
            result.append(0.0)
        return result[:self._output_size]

    @property
    def static_arena(self):
        return self._static

    @property
    def scratch_arena(self):
        return self._scratch


engine = AiEngine()
engine_threaded = AiEngine(static_size=4*1024*1024, scratch_size=2*1024*1024)

MemoryArena = StaticArena
