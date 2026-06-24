import math
import random
import pytest
import numpy as np
from modules.samplers import GenerativeOps, LlmSampler, ExtremeSampler


class TestGenerativeOps:
    def test_softmax_normalizes(self):
        logits = [2.0, 1.0, 0.0]
        GenerativeOps.softmax(logits)
        assert math.isclose(sum(logits), 1.0, rel_tol=1e-3)
        assert logits[0] > logits[1] > logits[2]

    def test_softmax_empty(self):
        GenerativeOps.softmax([])

    def test_softmax_single(self):
        logits = [5.0]
        GenerativeOps.softmax(logits)
        assert math.isclose(logits[0], 1.0)

    def test_argmax(self):
        probs = [0.1, 0.5, 0.3, 0.1]
        assert GenerativeOps.argmax(probs) == 1

    def test_argmax_first(self):
        probs = [0.9, 0.05, 0.05]
        assert GenerativeOps.argmax(probs) == 0

    def test_sample_temp_always_picks_highest(self):
        logits = [100.0, 0.0, 0.0]
        tid = GenerativeOps.sample_temp(logits, temp=0.1)
        assert tid == 0


class TestLlmSampler:
    def test_sample_default(self):
        logits = [5.0, 1.0, 0.0]
        tid = LlmSampler.sample(logits)
        assert 0 <= tid < 3

    def test_sample_with_temperature(self):
        logits = [10.0, 0.0, 0.0]
        tid = LlmSampler.sample(logits, temperature=0.01)
        assert tid == 0

    def test_sample_top_k(self):
        logits = [100.0, 0.0, 0.0, 0.0, 0.0]
        tid = LlmSampler.sample(logits, top_k=2)
        assert tid == 0

    def test_sample_top_p(self):
        logits = [100.0, 0.0, 0.0]
        tid = LlmSampler.sample(logits, top_p=0.5)
        assert tid == 0


class TestExtremeSampler:
    def test_sample_default(self):
        logits = np.array([5.0, 1.0, 0.0], dtype=np.float64)
        tid = ExtremeSampler.sample(logits)
        assert 0 <= tid < 3

    def test_sample_always_highest(self):
        logits = np.array([100.0, 0.0, 0.0], dtype=np.float64)
        tid = ExtremeSampler.sample(logits, temperature=0.01)
        assert tid == 0

    def test_sample_top_k(self):
        logits = np.array([100.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        tid = ExtremeSampler.sample(logits, top_k=2)
        assert tid == 0

    def test_sample_top_p(self):
        logits = np.array([100.0, 0.0, 0.0], dtype=np.float64)
        tid = ExtremeSampler.sample(logits, top_p=0.5)
        assert tid == 0

    def test_sample_list_input(self):
        logits = [5.0, 1.0, 0.0]
        tid = ExtremeSampler.sample(logits)
        assert 0 <= tid < 3
