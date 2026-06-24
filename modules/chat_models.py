import math
import random
import os
import re
import numpy as np
from enum import Enum

from .engine import AiEngine, StaticArena, ScratchpadArena, TensorView
from .samplers import ExtremeSampler


# ============================================================================
# RUSSIAN_CHARS
# ============================================================================
RUSSIAN_CHARS = (
    " абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "0123456789"
    ".,!?-:;\"'() "
)


# ============================================================================
# KV Cache
# ============================================================================
class KVCache:
    def __init__(self):
        self.keys = []
        self.values = []
        self.seq_len = 0

    def append(self, new_k, new_v):
        self.keys.extend(new_k)
        self.values.extend(new_v)
        self.seq_len += 1

    def clear(self):
        self.keys.clear()
        self.values.clear()
        self.seq_len = 0


class PagedKVCache:
    def __init__(self, num_layers, block_size=64):
        self.block_size = block_size
        self.num_layers = num_layers
        self.blocks = [[] for _ in range(num_layers)]

    def append(self, layer, keys, values):
        blks = self.blocks[layer]
        if not blks or len(blks[-1][0]) >= self.block_size:
            blks.append(([], []))
        bk_keys, bk_vals = blks[-1]
        bk_keys.extend(keys)
        bk_vals.extend(values)

    def clear(self):
        for blk in self.blocks:
            blk.clear()

    @property
    def total_tokens(self):
        n = 0
        for blk in self.blocks:
            for k, _ in blk:
                n += len(k)
        return n


# ============================================================================
# GenerativeEngine — character-level INT8 bigram
# ============================================================================
class GenerativeEngine:
    def __init__(self, vocab=RUSSIAN_CHARS + "\n", corpus=None):
        self.vocab = vocab
        self.char_to_id = {c: i for i, c in enumerate(vocab)}
        self.id_to_char = {i: c for i, c in enumerate(vocab)}
        self.vocab_size = len(vocab)
        self.engine = AiEngine(static_size=2*1024*1024, scratch_size=512*1024)
        if corpus is not None:
            self.train(corpus)
        else:
            self._build_weights()

    def _bigram_matrix(self):
        _bigrams = {
            'а': 'лкнтрсмвзпшдбгхч', 'б': ' ыролуе', 'в': ' осеаыирнл',
            'г': ' орлауеи', 'д': ' еоаирну', 'е': ' рнлствмйжзч',
            'ё': ' тл', 'ж': ' еиано', 'з': ' наовдемкрл', 'и': ' снзквлмптр',
            'й': ' с', 'к': ' оаратливну', 'л': ' аоиеьюяй', 'м': ' оеиаун',
            'н': ' оеаиныут', 'о': ' встнрмгдп', 'п': ' ореалнуи',
            'р': ' аеоинсвзл', 'с': ' ткоаепнлм', 'т': ' оаевыргич',
            'у': ' тсбждпвчмн', 'ф': ' оиарабу', 'х': ' оарен',
            'ц': ' еиоявау', 'ч': ' еиатону', 'ш': ' иеаону',
            'щ': ' еиаоно', 'ъ': ' еяю', 'ы': ' е  мйлхсп',
            'ь': '   нсшмчетю', 'э': ' тлоэкм', 'ю': ' тдщмсвбр',
            'я': '   втзлспхнк', ' ': 'пвнскорздтбмгуачхищ',
        }
        mat = [0] * (self.vocab_size * self.vocab_size)
        base_boost = {'а': 4, 'е': 4, 'о': 4, 'и': 3, 'н': 3, 'т': 3, 'с': 2,
                      'р': 2, 'в': 2, 'л': 2, 'к': 2, 'м': 2, ' ': 3,
                      'п': 1, 'д': 1, 'б': 1, 'у': 1, 'я': 1, 'ь': 1, 'г': 1, 'ч': 1}

        for row in range(self.vocab_size):
            row_ch = self.id_to_char.get(row, ' ').lower()
            next_set = set(_bigrams.get(row_ch, ' '))
            for col in range(self.vocab_size):
                col_ch = self.id_to_char.get(col, ' ').lower()
                boost = base_boost.get(col_ch, 0) * 3
                if col_ch in next_set:
                    boost += 10
                if row_ch == col_ch and row_ch != ' ':
                    boost -= 5
                random.seed(row * self.vocab_size + col)
                val = boost + random.gauss(0, 1.5)
                mat[row * self.vocab_size + col] = max(-127, min(127, round(val)))
        return mat

    def _build_weights(self):
        w1 = self._bigram_matrix()
        self.engine._graph.register_weight("bigram", [self.vocab_size, self.vocab_size], w1, 0.03)
        nodes = [("MatMul", ["x", "bigram"], ["out_i32", "out_y"], {})]
        self.engine._graph.compile(nodes)
        self.engine._compiled = True
        self.engine._output_size = self.vocab_size

    def _char_to_vec(self, ch):
        tid = self.char_to_id.get(ch, self.char_to_id.get(' ', 0))
        vec = [0.0] * self.vocab_size
        vec[tid] = 1.0
        return vec

    def generate(self, prompt="", max_tokens=64, temperature=0.85, top_k=20, top_p=0.92):
        output = list(prompt)
        context = list(prompt) if prompt else [" "]

        for _ in range(max_tokens):
            last_char = context[-1] if context else " "
            inp = self._char_to_vec(last_char)
            logits = self.engine.get_logits(inp, input_scale=0.05)
            tid = ExtremeSampler.sample(logits, temperature=temperature, top_k=top_k, top_p=top_p)
            if tid < 0 or tid >= self.vocab_size:
                tid = 0
            next_char = self.id_to_char[tid]
            if next_char == "\n":
                break
            output.append(next_char)
            context.append(next_char)

        return "".join(output)

    def train(self, corpus=None, temperature=0.9):
        trainer = BigramTrainer(self.vocab)
        if corpus is None:
            _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
            _CORPUS_FILE = os.path.join(_THIS_DIR, "..", "corpus_ru.txt")
            if os.path.isfile(_CORPUS_FILE):
                with open(_CORPUS_FILE, "r", encoding="utf-8") as _f:
                    corpus = _f.read()
            else:
                corpus = "Привет как дела что нового"
        trainer.feed_corpus(corpus)
        weights = trainer.to_int8_weights(temperature)
        self.engine = AiEngine(static_size=2*1024*1024, scratch_size=512*1024)
        self.engine._graph.register_weight("bigram", [self.vocab_size, self.vocab_size], weights, 0.03)
        nodes = [("MatMul", ["x", "bigram"], ["out_i32", "out_y"], {})]
        self.engine._graph.compile(nodes)
        self.engine._compiled = True
        self.engine._output_size = self.vocab_size
        return trainer


# ============================================================================
# BigramTrainer
# ============================================================================
class BigramTrainer:
    def __init__(self, vocab=RUSSIAN_CHARS + "\n"):
        self.vocab = vocab
        self.char_to_id = {c: i for i, c in enumerate(vocab)}
        self.id_to_char = {i: c for i, c in enumerate(vocab)}
        self.vocab_size = len(vocab)
        self.counts = [[0] * self.vocab_size for _ in range(self.vocab_size)]
        self.total_bigrams = 0

    def feed(self, text):
        prev = None
        for ch in text:
            if ch not in self.char_to_id:
                ch = ' '
            cid = self.char_to_id[ch]
            if prev is not None:
                self.counts[prev][cid] += 1
                self.total_bigrams += 1
            prev = cid

    def feed_corpus(self, corpus):
        for line in corpus.strip().split('\n'):
            self.feed(line.strip() + "\n")

    def get_probs(self, temperature=1.0):
        probs = [[0.0] * self.vocab_size for _ in range(self.vocab_size)]
        for i in range(self.vocab_size):
            row_total = sum(self.counts[i])
            if row_total == 0:
                for j in range(self.vocab_size):
                    probs[i][j] = 1.0 / self.vocab_size
            else:
                for j in range(self.vocab_size):
                    raw = self.counts[i][j] / row_total
                    if temperature != 1.0 and raw > 0:
                        raw = raw ** (1.0 / temperature)
                    probs[i][j] = raw
            row_sum = sum(probs[i])
            if row_sum > 0:
                for j in range(self.vocab_size):
                    probs[i][j] /= row_sum
        return probs

    def to_int8_weights(self, temperature=1.0):
        max_weight = 127
        weights = [0] * (self.vocab_size * self.vocab_size)
        for i in range(self.vocab_size):
            row_total = sum(self.counts[i])
            if row_total == 0:
                for j in range(self.vocab_size):
                    weights[i * self.vocab_size + j] = 1
                continue
            max_cnt = max(self.counts[i]) if self.counts[i] else 1
            log_max = math.log(max_cnt + 1)
            if log_max < 0.001:
                log_max = 0.001
            for j in range(self.vocab_size):
                raw = math.log(self.counts[i][j] + 1)
                if temperature != 1.0:
                    raw = raw / temperature
                val = raw / log_max * max_weight
                weights[i * self.vocab_size + j] = max(-128, min(127, round(val)))
        return weights


# ============================================================================
# WordLevelEngine — word bigram from frequency file
# ============================================================================
def _load_word_vocab(path_or_n=1000):
    base = os.path.dirname(os.path.abspath(__file__))
    fpath = os.path.join(base, "..", "ru_50k.txt")
    if not os.path.isfile(fpath):
        raise FileNotFoundError(f"Frequency word list not found: {fpath}")
    words = []
    with open(fpath, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().rsplit(" ", 1)
            if len(parts) == 2:
                w = parts[0]
                if w and all("а" <= c.lower() <= "я" or c == "ё" for c in w):
                    words.append(w.lower())
                    if len(words) >= path_or_n:
                        break
    return words


class WordLevelEngine:
    BOS = "<BOS>"
    EOS = "<EOS>"
    UNK = "<UNK>"

    def __init__(self, num_words=1000):
        self.num_words = num_words
        self.vocab_size = num_words + 3
        self.word_list = []
        self.word_to_id = {}
        self.id_to_word = {}
        self._probs = None
        self._initialized = False

    def _init_vocab(self):
        if self.word_to_id:
            return
        word_list = _load_word_vocab(self.num_words)
        self.word_list = word_list
        self.word_to_id = {w: i for i, w in enumerate(word_list)}
        self.word_to_id[self.BOS] = self.num_words
        self.word_to_id[self.EOS] = self.num_words + 1
        self.word_to_id[self.UNK] = self.num_words + 2
        self.id_to_word = {v: k for k, v in self.word_to_id.items()}

    def train(self, corpus, temperature=0.9, laplace=0.1):
        self._init_vocab()
        tokens = self._tokenize(corpus)
        V = self.vocab_size
        counts = np.full((V, V), laplace, dtype=np.float64)

        prev = self.word_to_id[self.BOS]
        for tok in tokens:
            cur = self.word_to_id.get(tok, self.word_to_id[self.UNK])
            counts[prev, cur] += 1
            prev = cur
        counts[prev, self.word_to_id[self.EOS]] += 1

        row_totals = counts.sum(axis=1, keepdims=True)
        zero_rows = row_totals[:, 0] < 0.001
        self._probs_np = np.where(zero_rows[:, None], 1.0 / V, counts / row_totals)

        if temperature != 1.0:
            mask = self._probs_np > 0
            self._probs_np[mask] = self._probs_np[mask] ** (1.0 / temperature)

        row_sums = self._probs_np.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums < 0.001, 1.0, row_sums)
        self._probs_np /= row_sums

        self._probs = self._probs_np.tolist()
        self._initialized = True

    def _tokenize(self, text):
        words = re.findall(r"[а-яёА-ЯЁ]+", text)
        return [w.lower() for w in words if w]

    def _encode(self, word):
        return self.word_to_id.get(word.lower(), self.word_to_id[self.UNK])

    def _decode(self, token_id):
        return self.id_to_word.get(token_id, self.UNK)

    def generate(self, prompt="", max_tokens=30, temperature=1.0, top_k=10, top_p=0.9):
        if not self._initialized or self._probs is None:
            return prompt

        pn = self._probs_np if hasattr(self, '_probs_np') and self._probs_np is not None else None
        prompt_words = self._tokenize(prompt)
        if prompt_words:
            prev_id = self._encode(prompt_words[-1])
        else:
            prev_id = self.word_to_id[self.BOS]

        output_words = list(prompt_words)
        bos_id = self.word_to_id[self.BOS]
        eos_id = self.word_to_id[self.EOS]

        for _ in range(max_tokens):
            if pn is not None:
                logits = np.log(np.maximum(pn[prev_id], 1e-30))
            else:
                logits = [math.log(max(p, 1e-30)) for p in self._probs[prev_id]]
            logits[bos_id] = -1e9

            next_id = ExtremeSampler.sample(logits, temperature, top_k, top_p)

            if next_id == eos_id:
                break

            next_word = self._decode(next_id)
            if next_word == self.UNK:
                continue

            output_words.append(next_word)
            prev_id = next_id

        result = " ".join(output_words)
        return result

    def get_state(self):
        return {
            "vocab_size": self.vocab_size,
            "num_words": self.num_words,
            "initialized": self._initialized,
        }


# ============================================================================
# TrigramEngine — character-level, counts-based
# ============================================================================
class TrigramEngine:
    def __init__(self, corpus=None, vocab=RUSSIAN_CHARS + "\n"):
        self.vocab = vocab
        self.char_to_id = {c: i for i, c in enumerate(vocab)}
        self.id_to_char = {i: c for i, c in enumerate(vocab)}
        self.vocab_size = len(vocab)
        self.counts = {}
        self._probs = {}
        self._trained = False
        if corpus:
            self.train(corpus, temperature=0.9)

    def train(self, corpus, temperature=0.9, laplace=0.01):
        V = self.vocab_size
        ids = []
        for ch in corpus:
            if ch in self.char_to_id:
                ids.append(self.char_to_id[ch])
            else:
                ids.append(self.char_to_id.get(' ', 0))

        for i in range(len(ids) - 2):
            key = (ids[i], ids[i + 1])
            nxt = ids[i + 2]
            if key not in self.counts:
                self.counts[key] = [laplace] * V
            self.counts[key][nxt] += 1

        self._probs = {}
        for key, row in self.counts.items():
            total = sum(row)
            if total < 0.001:
                self._probs[key] = np.full(V, 1.0 / V, dtype=np.float64)
                continue
            probs = np.array(row, dtype=np.float64) / total
            if temperature != 1.0:
                mask = probs > 0
                probs[mask] = probs[mask] ** (1.0 / temperature)
            rs = probs.sum()
            if rs > 0:
                probs /= rs
            self._probs[key] = probs

        self._trained = True

    def _step(self, c1, c2, temperature=0.9, top_k=12, top_p=0.9):
        key = (c1, c2)
        if key in self._probs:
            logits = np.log(np.maximum(self._probs[key], 1e-30))
        else:
            logits = np.full(self.vocab_size, -30.0)

        next_id = ExtremeSampler.sample(logits, temperature, top_k, top_p)

        if next_id < 0 or next_id >= self.vocab_size:
            next_id = 0

        return self.id_to_char[next_id], next_id

    def generate(self, prompt="", max_tokens=64, temperature=0.9, top_k=12, top_p=0.9):
        if not self._trained:
            return prompt

        output = list(prompt)

        if len(output) >= 2:
            c1 = self.char_to_id.get(output[-2], self.char_to_id.get(' ', 0))
            c2 = self.char_to_id.get(output[-1], self.char_to_id.get(' ', 0))
        elif len(output) == 1:
            c1 = self.char_to_id.get(' ', 0)
            c2 = self.char_to_id.get(output[-1], self.char_to_id.get(' ', 0))
        else:
            c1 = self.char_to_id.get(' ', 0)
            c2 = self.char_to_id.get(' ', 0)

        for _ in range(max_tokens):
            next_char, next_id = self._step(c1, c2, temperature, top_k, top_p)
            output.append(next_char)
            c1, c2 = c2, next_id

        return "".join(output)


# ============================================================================
# CorpusWordEngine — word bigram from any text
# ============================================================================
class CorpusWordEngine:
    BOS = "<BOS>"
    EOS = "<EOS>"

    def __init__(self, corpus=None, min_freq=2):
        self.min_freq = min_freq
        self.word_list = []
        self.word_to_id = {}
        self.id_to_word = {}
        self._probs = None
        self._trained = False
        if corpus:
            self.train(corpus)

    def _build_vocab(self, tokens):
        from collections import Counter
        freq = Counter(tokens)
        vocab = [w for w, c in freq.items() if c >= self.min_freq]
        vocab.sort()
        self.word_list = vocab
        offset = 2
        self.word_to_id = {w: i for i, w in enumerate(vocab)}
        self.word_to_id[self.BOS] = len(vocab)
        self.word_to_id[self.EOS] = len(vocab) + 1
        self.id_to_word = {v: k for k, v in self.word_to_id.items()}
        self.vocab_size = len(vocab) + 2

    def train(self, corpus, temperature=0.9, laplace=0.01):
        tokens = self._tokenize(corpus)
        self._build_vocab(tokens)
        V = self.vocab_size
        counts = np.full((V, V), laplace, dtype=np.float64)

        prev = self.word_to_id[self.BOS]
        for tok in tokens:
            cur = self.word_to_id.get(tok, self.word_to_id[self.BOS])
            counts[prev, cur] += 1
            prev = cur
        counts[prev, self.word_to_id[self.EOS]] += 1

        row_totals = counts.sum(axis=1, keepdims=True)
        zero_rows = row_totals[:, 0] < 0.001
        self._probs_np = np.where(zero_rows[:, None], 1.0 / V, counts / row_totals)

        if temperature != 1.0:
            mask = self._probs_np > 0
            self._probs_np[mask] = self._probs_np[mask] ** (1.0 / temperature)

        row_sums = self._probs_np.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums < 0.001, 1.0, row_sums)
        self._probs_np /= row_sums

        self._probs = self._probs_np.tolist()
        self._trained = True

    def _tokenize(self, text):
        words = re.findall(r"[а-яёА-ЯЁ]+", text)
        return [w.lower() for w in words if w]

    def generate(self, prompt="", max_tokens=30, temperature=1.0, top_k=10, top_p=0.9):
        if not self._trained or self._probs is None:
            return prompt

        pn = self._probs_np if hasattr(self, '_probs_np') and self._probs_np is not None else None
        prompt_words = self._tokenize(prompt)
        if prompt_words:
            prev_id = self.word_to_id.get(prompt_words[-1], self.word_to_id[self.BOS])
        else:
            prev_id = self.word_to_id[self.BOS]

        output_words = list(prompt_words)
        bos_id = self.word_to_id[self.BOS]
        eos_id = self.word_to_id[self.EOS]

        for _ in range(max_tokens):
            if pn is not None:
                logits = np.log(np.maximum(pn[prev_id], 1e-30))
            else:
                logits = [math.log(max(p, 1e-30)) for p in self._probs[prev_id]]
            logits[bos_id] = -1e9

            next_id = ExtremeSampler.sample(logits, temperature, top_k, top_p)

            if next_id == eos_id:
                break
            if next_id == bos_id:
                continue

            next_word = self.id_to_word.get(next_id, "")
            if not next_word:
                continue

            output_words.append(next_word)
            prev_id = next_id

        return " ".join(output_words)

    def _step(self, prev_id, temperature=1.0, top_k=10, top_p=0.9):
        pn = self._probs_np if hasattr(self, '_probs_np') and self._probs_np is not None else None
        if pn is not None:
            logits = np.log(np.maximum(pn[prev_id], 1e-30))
        else:
            logits = [math.log(max(p, 1e-30)) for p in self._probs[prev_id]]
        logits[self.word_to_id[self.BOS]] = -1e9
        next_id = ExtremeSampler.sample(logits, temperature, top_k, top_p)
        next_word = self.id_to_word.get(next_id, "")
        return next_word, next_id


# ============================================================================
# Continuous Batch Scheduler
# ============================================================================
class RequestStatus(Enum):
    WAITING = 0
    RUNNING = 1
    FINISHED = 2


class Sequence:
    def __init__(self, sid, prompt="", max_tokens=48, temperature=0.9, top_k=15, top_p=0.88):
        self.id = sid
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        self.tokens = []
        self.text = ""
        self.status = RequestStatus.WAITING
        self.has_eos = False
        self.c1 = 0
        self.c2 = 0
        self.prev_id = 0

    @property
    def finished(self):
        return self.status == RequestStatus.FINISHED

    @property
    def done(self):
        return self.has_eos or len(self.tokens) >= self.max_tokens


class ContinuousBatchScheduler:
    def __init__(self, engine=None, max_batch_size=4):
        self.engine = engine or GenerativeEngine()
        self.max_batch_size = max_batch_size
        self._waiting = []
        self._active = []
        self._finished = []

    def submit(self, prompt="", max_tokens=48, temperature=0.9, top_k=15, top_p=0.88):
        sid = len(self._finished) + len(self._active) + len(self._waiting) + 1
        seq = Sequence(sid, prompt, max_tokens, temperature, top_k, top_p)
        self._waiting.append(seq)
        return seq

    def _is_word_engine(self):
        return hasattr(self.engine, 'word_to_id') and hasattr(self.engine, '_step')

    def step(self):
        is_word = self._is_word_engine()
        while len(self._active) < self.max_batch_size and self._waiting:
            seq = self._waiting.pop(0)
            seq.status = RequestStatus.RUNNING
            if seq.prompt:
                if is_word:
                    words = re.findall(r"[а-яёА-ЯЁ]+", seq.prompt.lower())
                    last = words[-1] if words else ""
                    seq.prev_id = self.engine.word_to_id.get(
                        last, self.engine.word_to_id.get(self.engine.BOS, 0)
                    )
                else:
                    text = seq.prompt
                    if len(text) >= 2:
                        seq.c1 = self.engine.char_to_id.get(text[-2], 0)
                        seq.c2 = self.engine.char_to_id.get(text[-1], 0)
                    elif len(text) == 1:
                        seq.c1 = self.engine.char_to_id.get(' ', 0)
                        seq.c2 = self.engine.char_to_id.get(text[-1], 0)
                    else:
                        seq.c1 = self.engine.char_to_id.get(' ', 0)
                        seq.c2 = self.engine.char_to_id.get(' ', 0)
                seq.text = seq.prompt
            self._active.append(seq)

        if not self._active:
            return

        surviving = []
        for seq in self._active:
            if is_word:
                next_word, nid = self.engine._step(
                    seq.prev_id,
                    temperature=seq.temperature,
                    top_k=seq.top_k, top_p=seq.top_p
                )
                seq.prev_id = nid
                tid = nid
                if next_word == self.engine.EOS:
                    seq.has_eos = True
                else:
                    sep = " " if seq.text and not seq.text.endswith(" ") else ""
                    seq.text += sep + next_word
            elif hasattr(self.engine, '_step'):
                next_char, tid = self.engine._step(
                    seq.c1, seq.c2,
                    temperature=seq.temperature,
                    top_k=seq.top_k, top_p=seq.top_p
                )
                seq.c1, seq.c2 = seq.c2, tid
                if next_char == "\n" or next_char == "\0":
                    seq.has_eos = True
                seq.text += next_char
            else:
                last_char = seq.text[-1] if seq.text else " "
                inp = self.engine._char_to_vec(last_char)
                logits = self.engine.engine.get_logits(inp, input_scale=0.05)
                tid = ExtremeSampler.sample(
                    logits, temperature=seq.temperature,
                    top_k=seq.top_k, top_p=seq.top_p
                )
                next_char = self.engine.id_to_char.get(tid, ' ')
                if next_char == "\n" or next_char == "\0":
                    seq.has_eos = True
                seq.text += next_char

            seq.tokens.append(tid)

            if seq.done:
                seq.status = RequestStatus.FINISHED
                self._finished.append(seq)
            else:
                surviving.append(seq)

        self._active = surviving

    def run(self, max_iterations=100):
        iterations = 0
        while self.has_work and iterations < max_iterations:
            self.step()
            iterations += 1
        return iterations

    @property
    def has_work(self):
        return bool(self._active) or bool(self._waiting)

    @property
    def finished(self):
        return self._finished

    def results(self):
        return [
            (s.id, s.prompt, s.text[len(s.prompt):])
            for s in self._finished
        ]
