import math
import random
import numpy as np


class GenerativeOps:
    @staticmethod
    def softmax(logits):
        if not logits:
            return
        max_l = max(logits)
        for i in range(len(logits)):
            logits[i] = math.exp(logits[i] - max_l)
        s = sum(logits)
        for i in range(len(logits)):
            logits[i] /= s

    @staticmethod
    def argmax(probs):
        return max(range(len(probs)), key=lambda i: probs[i])

    @staticmethod
    def sample_temp(logits, temp):
        scaled = [x / temp for x in logits]
        GenerativeOps.softmax(scaled)
        r = random.random()
        cumulative = 0.0
        for i, p in enumerate(scaled):
            cumulative += p
            if r < cumulative:
                return i
        return len(scaled) - 1


class LlmSampler:
    @staticmethod
    def sample(logits, temperature=1.0, top_k=0, top_p=0.0):
        probs = list(logits)

        if temperature > 0:
            probs = [x / temperature for x in probs]

        max_l = max(probs)
        for i in range(len(probs)):
            probs[i] = math.exp(probs[i] - max_l)
        s = sum(probs)
        for i in range(len(probs)):
            probs[i] /= s

        tokens = list(enumerate(probs))
        tokens.sort(key=lambda x: x[1], reverse=True)

        if top_k > 0 and top_k < len(tokens):
            tokens = tokens[:top_k]

        if 0.0 < top_p < 1.0:
            cumulative = 0.0
            cutoff = len(tokens)
            for i, (_, p) in enumerate(tokens):
                cumulative += p
                if cumulative >= top_p:
                    cutoff = i + 1
                    break
            tokens = tokens[:cutoff]

        new_sum = sum(p for _, p in tokens)
        if new_sum > 0:
            tokens = [(tid, p / new_sum) for tid, p in tokens]

        r = random.random()
        cur = 0.0
        for tid, p in tokens:
            cur += p
            if r <= cur:
                return tid
        return tokens[0][0]


class ExtremeSampler:
    @staticmethod
    def sample(logits, temperature=1.0, top_k=10, top_p=0.92):
        logits = np.asarray(logits, dtype=np.float64)
        V = logits.shape[0]

        if temperature > 0:
            logits = logits / temperature

        max_l = np.max(logits)
        exp_l = np.exp(logits - max_l)
        sum_exp = np.sum(exp_l)
        probs = exp_l / sum_exp

        if 0 < top_k < V:
            idx = np.argpartition(probs, -top_k)[-top_k:]
            pk = probs[idx]
            order = np.argsort(pk)[::-1]
            idx = idx[order]
            pk = pk[order]
        else:
            idx = np.arange(V)
            pk = probs

        if 0.0 < top_p < 1.0:
            cum = np.cumsum(pk)
            cutoff = int(np.searchsorted(cum, top_p)) + 1
            idx = idx[:cutoff]
            pk = pk[:cutoff]
            pk = pk / np.sum(pk)

        r = random.random()
        cum = np.cumsum(pk)
        return idx[int(np.searchsorted(cum, r))]
