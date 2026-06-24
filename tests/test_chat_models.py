import pytest
from modules.chat_models import (
    KVCache, PagedKVCache, BigramTrainer, RUSSIAN_CHARS,
    GenerativeEngine, TrigramEngine, CorpusWordEngine, ContinuousBatchScheduler
)


class TestKVCache:
    def test_init(self):
        c = KVCache()
        assert c.keys == []
        assert c.values == []
        assert c.seq_len == 0

    def test_append(self):
        c = KVCache()
        c.append([1, 2], [3, 4])
        assert c.keys == [1, 2]
        assert c.values == [3, 4]
        assert c.seq_len == 1

    def test_clear(self):
        c = KVCache()
        c.append([1], [2])
        c.clear()
        assert c.keys == []
        assert c.values == []
        assert c.seq_len == 0


class TestPagedKVCache:
    def test_init(self):
        c = PagedKVCache(2, block_size=4)
        assert c.num_layers == 2
        assert c.block_size == 4
        assert c.total_tokens == 0

    def test_append_and_total(self):
        c = PagedKVCache(1, block_size=4)
        c.append(0, [1, 2], [3, 4])
        assert c.total_tokens == 2
        c.append(0, [5], [6])
        assert c.total_tokens == 3

    def test_append_new_block(self):
        c = PagedKVCache(1, block_size=2)
        c.append(0, [1, 2], [3, 4])
        c.append(0, [5, 6], [7, 8])
        assert c.total_tokens == 4
        assert len(c.blocks[0]) == 2

    def test_clear(self):
        c = PagedKVCache(1)
        c.append(0, [1], [2])
        c.clear()
        assert c.total_tokens == 0


class TestBigramTrainer:
    def setup_method(self):
        self.t = BigramTrainer("абв")

    def test_init(self):
        assert self.t.vocab_size == 3
        assert self.t.total_bigrams == 0

    def test_feed(self):
        self.t.feed("аб")
        assert self.t.total_bigrams == 1
        a_id = self.t.char_to_id["а"]
        b_id = self.t.char_to_id["б"]
        assert self.t.counts[a_id][b_id] == 1

    def test_feed_corpus(self):
        t = BigramTrainer("абв\n")
        t.feed_corpus("аб")
        assert t.total_bigrams >= 1

    def test_get_probs(self):
        self.t.feed("аба")
        probs = self.t.get_probs()
        assert len(probs) == 3
        assert len(probs[0]) == 3
        for row in probs:
            assert abs(sum(row) - 1.0) < 1e-3

    def test_get_probs_with_temperature(self):
        self.t.feed("аба")
        probs = self.t.get_probs(temperature=2.0)
        for row in probs:
            assert abs(sum(row) - 1.0) < 1e-3

    def test_to_int8_weights(self):
        self.t.feed("аба")
        weights = self.t.to_int8_weights()
        assert len(weights) == 9
        for w in weights:
            assert -128 <= w <= 127

    def test_to_int8_weights_empty_row(self):
        weights = self.t.to_int8_weights()
        assert len(weights) == 9


class TestGenerativeEngine:
    def test_init(self):
        eng = GenerativeEngine(vocab="абв ")
        assert eng.vocab_size == 4
        assert eng.engine is not None


class TestTrigramEngine:
    def test_init_no_corpus(self):
        eng = TrigramEngine(vocab="абв ")
        assert not eng._trained

    def test_init_with_corpus(self):
        eng = TrigramEngine(corpus="аба бва абв", vocab="абв ")
        assert eng._trained

    def test_train_and_generate(self):
        eng = TrigramEngine(vocab="абвгдеёжзийклмнопрстуфхцчшщъыьэюя ")
        eng.train("привет как дела что нового", temperature=1.0)
        text = eng.generate("пр", max_tokens=10)
        assert len(text) > 0

    def test_generate_not_trained(self):
        eng = TrigramEngine(vocab="абв ")
        assert eng.generate("test") == "test"


class TestCorpusWordEngine:
    def test_init_no_corpus(self):
        eng = CorpusWordEngine()
        assert not eng._trained

    def test_train_and_generate(self):
        eng = CorpusWordEngine(min_freq=1)
        eng.train("привет как дела что нового", temperature=1.0)
        assert eng._trained
        text = eng.generate("привет", max_tokens=5, temperature=2.0)
        assert isinstance(text, str)

    def test_generate_not_trained(self):
        eng = CorpusWordEngine()
        assert eng.generate("hello") == "hello"

    def test_get_state(self):
        pass


class TestContinuousBatchScheduler:
    def test_init(self):
        sched = ContinuousBatchScheduler(engine=None, max_batch_size=2)
        assert sched.max_batch_size == 2
        assert not sched.has_work

    def test_submit(self):
        eng = TrigramEngine(corpus="аба бва", vocab="абв ")
        sched = ContinuousBatchScheduler(engine=eng, max_batch_size=2)
        seq = sched.submit("а", max_tokens=5)
        assert sched.has_work
        assert seq.status.value == 0

    def test_step(self):
        eng = TrigramEngine(corpus="аба бва абв", vocab="абв ")
        sched = ContinuousBatchScheduler(engine=eng, max_batch_size=2)
        sched.submit("а", max_tokens=3)
        sched.step()
        assert len(sched._active) == 1 or len(sched._finished) == 1

    def test_run(self):
        eng = TrigramEngine(corpus="аба бва абв ааа ббб ввв", vocab="абв ")
        sched = ContinuousBatchScheduler(engine=eng, max_batch_size=2)
        sched.submit("а", max_tokens=3)
        iters = sched.run(max_iterations=10)
        assert iters > 0

    def test_results(self):
        eng = TrigramEngine(corpus="аба бва", vocab="абв ")
        sched = ContinuousBatchScheduler(engine=eng, max_batch_size=2)
        sched.submit("а", max_tokens=3)
        sched.run(max_iterations=20)
        results = sched.results()
        assert len(results) > 0

    def test_finished_property(self):
        eng = TrigramEngine(corpus="аба бва", vocab="абв ")
        sched = ContinuousBatchScheduler(engine=eng, max_batch_size=2)
        sched.submit("а", max_tokens=3)
        sched.run(max_iterations=20)
        assert len(sched.finished) > 0
