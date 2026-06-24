import ctypes
from .arena import StaticArena, TensorView
from .kernels import Int8Kernel, QuantizedOps


class Int8Graph:
    def __init__(self, static_arena: StaticArena):
        self._static = static_arena
        self._weights = {}
        self._scales = {}
        self._kernel = Int8Kernel()
        self._compiled = False
        self._activation_size = 0

    def register_weight(self, name: str, shape, data, scale=None):
        t = 1
        for s in shape:
            t *= s
        off = self._static.alloc(t * ctypes.sizeof(ctypes.c_int8))
        tv = TensorView(shape, ctypes.c_int8, self._static.buf, off)
        for i, v in enumerate(data):
            tv[i] = v
        final_scale = scale if scale is not None else QuantizedOps.calibrate_scale(tv)
        self._weights[name] = (tv, final_scale)
        self._scales[name] = final_scale
        return tv

    def compile(self, nodes_info: list, scratch_offsets: dict = None):
        if scratch_offsets is None:
            scratch_offsets = {}
        self._kernel = Int8Kernel()

        for op, ins, outs, meta in nodes_info:
            if op == "MatMul":
                w_name = ins[1]
                w_entry = self._weights.get(w_name)
                if w_entry is None:
                    continue
                w_tv, w_sc = w_entry
                A_name = ins[0]
                acc_name = outs[0]
                out_name = outs[1] if len(outs) >= 2 else acc_name
                N = w_tv.shape[1]

                a_off, a_shape = scratch_offsets.get(A_name, (0, (1, 4)))
                acc_off, _ = scratch_offsets.get(acc_name, (a_off + 64, (1, N)))
                out_off, _ = scratch_offsets.get(out_name, (acc_off + 64, (1, N)))

                def make_step(a_off, a_shape, w_tv, out_off, acc_off, N):
                    K = a_shape[1]
                    def step(sbuf):
                        A = TensorView(a_shape, ctypes.c_int8, sbuf, a_off)
                        C = TensorView([1, N], ctypes.c_int32, sbuf, acc_off)
                        c_ptr = [0] * N
                        for k in range(K):
                            av = int(A.at2d(0, k))
                            if av == 0:
                                continue
                            for j in range(N):
                                c_ptr[j] += av * int(w_tv.at2d(k, j))
                        for idx, val in enumerate(c_ptr):
                            C._arr[idx] = val
                        max_abs = 0
                        for idx in range(N):
                            v = int(C._arr[idx])
                            if v < 0:
                                v = 0
                            if v > max_abs:
                                max_abs = v
                        scale = 127.0 / max_abs if max_abs > 0 else 1.0
                        O = TensorView([1, N], ctypes.c_int8, sbuf, out_off)
                        for idx in range(N):
                            q = round(C._arr[idx] * scale)
                            O[idx] = max(-128, min(127, q))
                    return step

                self._kernel.add(make_step(a_off, a_shape, w_tv, out_off, acc_off, N))

        self._compiled = True

    def execute(self, scratch_buf):
        if not self._compiled:
            raise RuntimeError("Graph not compiled")
        self._kernel.execute(scratch_buf)

    def get_output(self, name):
        tv, scale = self._weights.get(name) if name in self._weights else (None, 0)
        return tv, scale

    def calibrate(self):
        for name, (tv, _) in self._weights.items():
            self._scales[name] = QuantizedOps.calibrate_scale(tv)
