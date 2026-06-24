from .arena import TensorView


class Int8Kernel:
    def __init__(self):
        self.steps = []

    def add(self, fn):
        self.steps.append(fn)

    def execute(self, scratch_buf):
        for fn in self.steps:
            fn(scratch_buf)


class QuantizedOps:

    @staticmethod
    def calibrate_scale(tv: TensorView) -> float:
        max_abs = 0
        for i in range(len(tv)):
            v = abs(int(tv[i]))
            if v > max_abs:
                max_abs = v
        return 127.0 / max_abs if max_abs > 0 else 1.0

    @staticmethod
    def matmul_int8_tiled(A, B, C, tile_m=4, tile_k=4, tile_n=4):
        M, K, N = A.shape[0], A.shape[1], B.shape[1]
        C_acc = [0] * (M * N)

        for i0 in range(0, M, tile_m):
            imax = min(i0 + tile_m, M)
            for k0 in range(0, K, tile_k):
                kmax = min(k0 + tile_k, K)
                for j0 in range(0, N, tile_n):
                    jmax = min(j0 + tile_n, N)
                    for i in range(i0, imax):
                        row_off = i * N
                        for k in range(k0, kmax):
                            av = int(A.at2d(i, k))
                            if av == 0:
                                continue
                            b_row_off = k * N
                            for j in range(j0, jmax):
                                C_acc[row_off + j] += av * int(B._arr[b_row_off + j])

        for idx, val in enumerate(C_acc):
            C._arr[idx] = val

    @staticmethod
    def requantize_relu(inp, scale, out):
        for i in range(len(inp)):
            v = float(inp[i]) * scale
            if v < 0:
                v = 0.0
            q = round(v)
            out[i] = max(-128, min(127, q))

    @staticmethod
    def requantize_linear(inp, scale, out):
        for i in range(len(inp)):
            v = float(inp[i]) * scale
            q = round(v)
            out[i] = max(-128, min(127, q))

    @staticmethod
    def dynamic_requantize_relu(inp, out, out_scale_ref=None):
        max_abs = 0
        for i in range(len(inp)):
            v = int(inp[i])
            if v < 0:
                v = 0
            inp[i] = v
            if v > max_abs:
                max_abs = v
        scale = 127.0 / max_abs if max_abs > 0 else 1.0
        for i in range(len(inp)):
            q = round(inp[i] * scale)
            out[i] = max(-128, min(127, q))
        if out_scale_ref is not None:
            out_scale_ref[0] = scale
        return scale
