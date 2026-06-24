"""
Semantic Engine v1 — семантический поиск, генерация текста,
самообучение и ассоциативный словарь.
Всё на чистом Python + numpy.
"""

import re
import math
import random
import json
import collections
from typing import List, Dict, Tuple, Optional

import numpy as np

from modules.utils import _tokenize, _TOKEN_PATTERN, _STOP_WORDS


class TfidfEngine:
    """
    Лёгкий TF-IDF для семантического поиска по библиотеке фраз.
    Использует numpy — без scikit-learn, без внешних ML-библиотек.
    """

    def __init__(self):
        self.documents: List[Dict] = []  # [{"text": ..., "label": ..., "meta": ...}]
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.vectors: np.ndarray = None  # (n_docs, n_vocab)
        self._built = False
        self._cache: Dict[str, List[Dict]] = {}
        self._cache_max = 50

    def add_document(self, text: str, label: str = "unknown", meta: dict = None):
        """Добавляет документ в корпус."""
        self.documents.append({
            "text": text,
            "label": label,
            "meta": meta or {},
        })
        self._built = False

    def add_patterns(self, patterns: List[Tuple[str, str]]):
        """Добавляет все regex-паттерны как документы (извлекает ключевые слова)."""
        for pattern, label in patterns:
            # Извлекаем русские слова из паттерна
            words = _TOKEN_PATTERN.findall(pattern)
            if words:
                example_text = " ".join(words)
                self.add_document(example_text, label)
        self._built = False

    def add_history(self, history: List[Dict], intent_key: str = "intent", text_key: str = "text"):
        """Добавляет историю диалогов для обучения."""
        for h in history:
            text = h.get(text_key, "")
            intent = h.get(intent_key, "unknown")
            if text and len(text) > 5:
                self.add_document(text, intent)

    def build(self):
        """Строит TF-IDF матрицу."""
        if self._built or not self.documents:
            return

        # Собираем словарь
        word_docs = collections.defaultdict(set)
        all_tokens = []
        for doc in self.documents:
            tokens = _tokenize(doc["text"])
            all_tokens.append(tokens)
            for w in set(tokens):
                word_docs[w].add(len(all_tokens) - 1)

        # Построение словаря
        self.vocab = {}
        for tokens in all_tokens:
            for w in tokens:
                if w not in self.vocab:
                    self.vocab[w] = len(self.vocab)

        if not self.vocab:
            self._built = True
            return

        n_docs = len(self.documents)
        n_vocab = len(self.vocab)

        # IDF
        self.idf = {}
        for w, widx in self.vocab.items():
            df = len(word_docs.get(w, set()))
            self.idf[w] = math.log((n_docs + 1) / (df + 1)) + 1.0

        # TF-IDF vectors
        self.vectors = np.zeros((n_docs, n_vocab), dtype=np.float32)
        for i, tokens in enumerate(all_tokens):
            tf = collections.Counter(tokens)
            for w, count in tf.items():
                if w in self.vocab:
                    self.vectors[i, self.vocab[w]] = (1 + math.log(count)) * self.idf.get(w, 1.0)

        # Normalize
        norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self.vectors = self.vectors / norms
        self._built = True

    def search(self, query: str, top_k: int = 5, threshold: float = 0.3) -> List[Dict]:
        """
        Ищет похожие документы по косинусной близости.
        Возвращает [{"text": ..., "label": ..., "score": ..., "meta": ...}]
        """
        cache_key = f"{query}|{top_k}|{threshold}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not self._built:
            self.build()
        if not self._built or self.vectors is None or self.vectors.shape[0] == 0:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # Query vector
        q_vec = np.zeros(len(self.vocab), dtype=np.float32)
        q_tf = collections.Counter(query_tokens)
        for w, count in q_tf.items():
            if w in self.vocab:
                q_vec[self.vocab[w]] = (1 + math.log(count)) * self.idf.get(w, 1.0)

        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_vec = q_vec / q_norm

        # Cosine similarity
        scores = self.vectors @ q_vec

        # Top-k
        top_idx = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_idx:
            score = float(scores[idx])
            if score < threshold:
                continue
            results.append({
                "text": self.documents[idx]["text"],
                "label": self.documents[idx]["label"],
                "score": round(score, 3),
                "meta": self.documents[idx]["meta"],
            })

        # Cache result
        if len(self._cache) >= self._cache_max:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = results

        return results

    def invalidate_cache(self):
        self._cache.clear()

    def best_intent(self, query: str, threshold: float = 0.35) -> Tuple[Optional[str], float]:
        """Возвращает (лучший интент, уверенность) или (None, 0)."""
        results = self.search(query, top_k=1, threshold=threshold)
        if results:
            return results[0]["label"], results[0]["score"]
        return None, 0.0

    def to_dict(self) -> dict:
        return {
            "documents": self.documents,
            "vocab": self.vocab,
            "idf": self.idf,
        }

    def from_dict(self, data: dict):
        self.documents = data.get("documents", [])
        self.vocab = data.get("vocab", {})
        self.idf = data.get("idf", {})
        self._built = False


# ══════════════════════════════════════════════════════════
#  2. MARKOV TEXT GENERATOR
# ══════════════════════════════════════════════════════════

class MarkovGenerator:
    """
    Генератор текста на цепях Маркова.
    Обучается на истории диалогов и генерирует новые фразы.
    """

    def __init__(self, order: int = 2):
        self.order = order
        self.chain: Dict[Tuple[str, ...], Dict[str, int]] = {}
        self.starters: List[Tuple[str, ...]] = []
        self.total_words = 0

    def train(self, texts: List[str]):
        """Обучает цепь Маркова на списке текстов."""
        for text in texts:
            words = _TOKEN_PATTERN.findall(text.lower())
            if len(words) < self.order + 1:
                continue

            # Starters (первые order слов)
            starter = tuple(words[:self.order])
            if len(set(starter)) > 0:
                self.starters.append(starter)

            # Transition chain
            for i in range(len(words) - self.order):
                state = tuple(words[i:i + self.order])
                next_word = words[i + self.order]
                if state not in self.chain:
                    self.chain[state] = {}
                self.chain[state][next_word] = self.chain[state].get(next_word, 0) + 1
                self.total_words += 1

    def train_from_history(self, history: List[Dict], text_key: str = "text"):
        """Обучается на истории диалогов."""
        texts = [h.get(text_key, "") for h in history if h.get(text_key)]
        self.train(texts)

    def generate(self, seed_words: List[str] = None, max_words: int = 25, temperature: float = 0.7) -> str:
        """Генерирует текст, начиная с seed_words (если есть).
        temperature: 0.0 = детерминированный, 0.7 = сбалансированный, >1.0 = хаотичный.
        """
        if not self.chain:
            return ""

        # Выбор начального состояния
        if seed_words:
            seed = [w.lower() for w in seed_words if len(w) > 2]
            # Ищем ближайшее состояние
            candidates = []
            for s in self.chain:
                matches = sum(1 for a, b in zip(seed[:self.order], s) if a == b)
                if matches > 0:
                    candidates.append((matches, random.random(), s))
            if candidates:
                candidates.sort(key=lambda x: (-x[0], x[1]))
                state = candidates[0][2]
            else:
                state = random.choice(self.starters) if self.starters else None
        else:
            state = random.choice(self.starters) if self.starters else None

        if not state:
            return ""

        # Генерация
        result = list(state)
        for _ in range(max_words - self.order):
            if state not in self.chain:
                break
            transitions = self.chain[state]
            if not transitions:
                break

            # Temperature-scaled softmax выбор
            words_list = list(transitions.keys())
            counts = np.array(list(transitions.values()), dtype=np.float64)

            if temperature <= 0:
                # Детерминированный: берём максимум
                next_word = words_list[np.argmax(counts)]
            else:
                # Softmax с температурой
                scaled = counts / temperature
                scaled -= scaled.max()  # численная стабильность
                exp_s = np.exp(scaled)
                probs = exp_s / exp_s.sum()
                next_word = np.random.choice(words_list, p=probs)

            if not next_word:
                break

            result.append(next_word)
            state = tuple(result[-self.order:])

        return " ".join(result)

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "chain": {str(k): v for k, v in self.chain.items()},
            "starters": [list(s) for s in self.starters],
            "total_words": self.total_words,
        }

    def from_dict(self, data: dict):
        import ast
        self.order = data.get("order", 2)
        self.chain = {ast.literal_eval(k): v for k, v in data.get("chain", {}).items()}
        self.starters = [tuple(s) for s in data.get("starters", [])]
        self.total_words = data.get("total_words", 0)


# ══════════════════════════════════════════════════════════
#  3. SELF-LEARNING v2
# ══════════════════════════════════════════════════════════

class SelfLearningV2:
    """
    Самообучение v2 — адаптация поведения на основе
    обратной связи пользователя.
    """

    def __init__(self):
        # Успешные паттерны: {pattern_text: intent}
        self.pattern_library: Dict[str, str] = {}
        # Счётчики: {intent: {template_index: success_count, fail_count}}
        self.template_scores: Dict[str, Dict[int, Dict[str, int]]] = {}
        # User-specific vocabulary
        self.user_words: Dict[str, int] = {}
        # Learned responses (user_message -> response)
        self.learned_responses: Dict[str, str] = {}
        # Confidence track
        self.intent_confidence: Dict[str, float] = {}

    def learn_pattern(self, user_text: str, intent: str, success: bool = True):
        """Запоминает новый паттерн из успешного диалога."""
        key = user_text.lower().strip()[:100]
        if success and key:
            self.pattern_library[key] = intent
            self.intent_confidence[intent] = self.intent_confidence.get(intent, 0.5) + 0.05
        elif not success and key in self.pattern_library:
            del self.pattern_library[key]

    def score_template(self, intent: str, template_idx: int, success: bool):
        """Отслеживает успешность конкретных шаблонов ответов."""
        if intent not in self.template_scores:
            self.template_scores[intent] = {}
        if template_idx not in self.template_scores[intent]:
            self.template_scores[intent][template_idx] = {"success": 0, "fail": 0}

        if success:
            self.template_scores[intent][template_idx]["success"] += 1
        else:
            self.template_scores[intent][template_idx]["fail"] += 1

    def best_template(self, intent: str) -> Optional[int]:
        """Возвращает индекс лучшего шаблона для интента."""
        scores = self.template_scores.get(intent, {})
        if not scores:
            return None
        best_idx = None
        best_rate = -1
        for idx, data in scores.items():
            total = data["success"] + data["fail"]
            if total > 0:
                rate = data["success"] / total
                if rate > best_rate:
                    best_rate = rate
                    best_idx = idx
        return best_idx

    def learn_response(self, user_message: str, response: str, success: bool):
        """Запоминает удачную пару вопрос-ответ."""
        key = user_message.lower().strip()[:80]
        if success and key:
            self.learned_responses[key] = response

    def find_learned_response(self, user_message: str) -> Optional[str]:
        """Ищет похожий запрос в выученных ответах."""
        key = user_message.lower().strip()[:80]
        exact = self.learned_responses.get(key)
        if exact:
            return exact
        # Частичное совпадение
        words = set(_tokenize(key))
        best_match = None
        best_score = 0
        for known, response in self.learned_responses.items():
            known_words = set(_tokenize(known))
            if not known_words or not words:
                continue
            overlap = len(words & known_words) / len(known_words)
            if overlap > 0.5 and overlap > best_score:
                best_score = overlap
                best_match = response
        return best_match

    def add_user_words(self, text: str):
        """Учит новые слова пользователя."""
        words = _TOKEN_PATTERN.findall(text.lower())
        for w in words:
            if w not in _STOP_WORDS:
                self.user_words[w] = self.user_words.get(w, 0) + 1

    def get_known_intents(self) -> List[str]:
        """Возвращает интенты, в которые уверен."""
        return [k for k, v in self.intent_confidence.items() if v > 0.7]

    def cleanup_old(self, max_patterns: int = 200, max_responses: int = 100):
        """Удаляет старые/редко используемые паттерны и ответы."""
        if len(self.pattern_library) > max_patterns:
            keys = list(self.pattern_library.keys())
            for k in keys[:-max_patterns]:
                del self.pattern_library[k]
        if len(self.learned_responses) > max_responses:
            keys = list(self.learned_responses.keys())
            for k in keys[:-max_responses]:
                del self.learned_responses[k]

    def to_dict(self) -> dict:
        return {
            "pattern_library": self.pattern_library,
            "template_scores": {k: {str(kk): vv for kk, vv in v.items()} for k, v in self.template_scores.items()},
            "user_words": dict(sorted(self.user_words.items(), key=lambda x: -x[1])[:200]),
            "learned_responses": dict(list(self.learned_responses.items())[:100]),
            "intent_confidence": self.intent_confidence,
        }

    def from_dict(self, data: dict):
        self.pattern_library = data.get("pattern_library", {})
        self.template_scores = {
            k: {int(kk): vv for kk, vv in v.items()}
            for k, v in data.get("template_scores", {}).items()
        }
        self.user_words = data.get("user_words", {})
        self.learned_responses = data.get("learned_responses", {})
        self.intent_confidence = data.get("intent_confidence", {})


# ══════════════════════════════════════════════════════════
#  4. WORD ASSOCIATOR
# ══════════════════════════════════════════════════════════

class WordAssociator:
    """
    Ассоциативный словарь — строит граф семантической близости
    на основе совместной встречаемости слов в историях.
    """

    def __init__(self, window: int = 5):
        self.window = window
        self.cooccurrence: Dict[str, Dict[str, int]] = {}
        self.word_freq: Dict[str, int] = {}
        self.total_docs = 0
        self._expand_cache: Dict[str, List[str]] = {}
        self._expand_cache_max = 100

    def train(self, texts: List[str]):
        """Обучает ассоциации на корпусе текстов."""
        for text in texts:
            words = _TOKEN_PATTERN.findall(text.lower())
            if len(words) < 2:
                continue
            self.total_docs += 1
            for w in words:
                self.word_freq[w] = self.word_freq.get(w, 0) + 1

            for i, w in enumerate(words):
                if w not in self.cooccurrence:
                    self.cooccurrence[w] = {}
                for j in range(max(0, i - self.window), min(len(words), i + self.window + 1)):
                    if i != j:
                        neighbor = words[j]
                        self.cooccurrence[w][neighbor] = self.cooccurrence[w].get(neighbor, 0) + 1

    def train_from_history(self, history: List[Dict], text_key: str = "text"):
        texts = [h.get(text_key, "") for h in history if h.get(text_key)]
        self.train(texts)

    def get_related(self, word: str, top_k: int = 5, threshold: int = 2) -> List[Tuple[str, int]]:
        """Возвращает связанные слова, отсортированные по силе связи."""
        wl = word.lower()
        related = self.cooccurrence.get(wl, {})
        if not related:
            return []
        sorted_words = sorted(related.items(), key=lambda x: -x[1])
        return [(w, c) for w, c in sorted_words[:top_k] if c >= threshold]

    def expand_query(self, text: str, top_k: int = 3) -> List[str]:
        """Расширяет запрос семантически близкими словами (с кэшированием)."""
        cache_key = f"{text}|{top_k}"
        cached = self._expand_cache.get(cache_key)
        if cached is not None:
            return cached

        words = _TOKEN_PATTERN.findall(text.lower())
        expanded = set(words)
        for w in words:
            related = self.get_related(w, top_k=top_k)
            for rw, _ in related:
                expanded.add(rw)

        result = list(expanded)
        if len(self._expand_cache) >= self._expand_cache_max:
            self._expand_cache.pop(next(iter(self._expand_cache)))
        self._expand_cache[cache_key] = result
        return result

    def similarity(self, word1: str, word2: str) -> float:
        """Косинусная близость двух слов по их коокуррентным векторам."""
        w1, w2 = word1.lower(), word2.lower()
        c1 = self.cooccurrence.get(w1, {})
        c2 = self.cooccurrence.get(w2, {})
        if not c1 or not c2:
            return 0.0
        all_keys = set(c1.keys()) | set(c2.keys())
        dot = sum(c1.get(k, 0) * c2.get(k, 0) for k in all_keys)
        n1 = math.sqrt(sum(v * v for v in c1.values()))
        n2 = math.sqrt(sum(v * v for v in c2.values()))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def to_dict(self) -> dict:
        return {
            "cooccurrence": {k: dict(v) for k, v in self.cooccurrence.items()},
            "word_freq": self.word_freq,
            "total_docs": self.total_docs,
        }

    def from_dict(self, data: dict):
        self.cooccurrence = {k: dict(v) for k, v in data.get("cooccurrence", {}).items()}
        self.word_freq = data.get("word_freq", {})
        self.total_docs = data.get("total_docs", 0)
