"""
Multidimensional Fractal Processing Engine (MFPE) — уникальный метод обработки данных.
Основан на принципах фрактальной самоподобности, квантовой суперпозиции
и голографической ассоциативной памяти.

Ключевые концепции:
  1. Фрактальная декомпозиция — паттерны повторяются на всех масштабах
  2. Голографическая проекция — данные проецируются в N-мерное пространство
  3. Квантовая суперпозиция — множество гипотез существуют одновременно
  4. Резонансное схлопывание — выбор гипотезы через интерференцию паттернов
  5. Фазовая память — информация хранится в фазовых переходах между состояниями
"""
import re, math, random, datetime, json, hashlib, threading, time, logging
from collections import defaultdict, Counter
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

logger = logging.getLogger("Astra.MFPE")

DATA_PATH = Path(__file__).parent.parent / "data" / "fractal_engine.json"


# ── Утилиты ──
def _tokenize(text):
    return [w for w in re.findall(r'\w+', text.lower()) if len(w) > 1]


def _ngrams(tokens, n=3):
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _hash_fingerprint(text):
    """Голографический отпечаток текста."""
    h = hashlib.sha256(text.encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF  # нормализация 0..1


def _cosine_sim(a, b):
    """Косинусная близость между векторами."""
    if not a or not b:
        return 0
    a_v, b_v = list(a.values()), list(b.values())
    dot = sum(a_v[i] * b_v[i] for i in range(min(len(a_v), len(b_v))))
    na = math.sqrt(sum(v * v for v in a_v))
    nb = math.sqrt(sum(v * v for v in b_v))
    return dot / (na * nb + 1e-10)


# ═══════════════════════════════════════════════════════════════
#  1. ФРАКТАЛЬНАЯ ДЕКОМПОЗИЦИЯ
# ═══════════════════════════════════════════════════════════════

class FractalDecomposer:
    """
    Разбивает данные на самоподобные фрактальные уровни.
    Каждый уровень отражает структуру вышестоящего.
    """

    LEVEL_NAMES = ["character", "word", "phrase", "sentence", "paragraph", "dialogue"]

    @staticmethod
    def decompose(text):
        """Декомпозиция текста на 6 фрактальных уровней."""
        levels = {}
        tl = text.lower().strip()

        # Level 0: символы (частотность)
        chars = Counter(c for c in tl if c.isalpha())
        levels["character"] = {
            "entropy": FractalDecomposer._entropy(chars.values()),
            "unique_ratio": len(chars) / max(1, len(tl)),
            "top": [c for c, _ in chars.most_common(5)],
        }

        # Level 1: слова
        words = _tokenize(tl)
        word_freq = Counter(words)
        levels["word"] = {
            "count": len(words),
            "unique": len(word_freq),
            "richness": len(word_freq) / max(1, len(words)),
            "top": [w for w, _ in word_freq.most_common(5)],
            "avg_len": sum(len(w) for w in words) / max(1, len(words)),
        }

        # Level 2: фразы (биграммы)
        bigrams = _ngrams(words, 2)
        levels["phrase"] = {
            "count": len(bigrams),
            "unique": len(set(bigrams)),
            "top": [b for b, _ in Counter(bigrams).most_common(5)],
        }

        # Level 3: предложения
        sentences = [s.strip() for s in re.split(r'[.!?]+', tl) if s.strip()]
        sent_lens = [len(s.split()) for s in sentences]
        levels["sentence"] = {
            "count": len(sentences),
            "avg_len": sum(sent_lens) / max(1, len(sent_lens)),
            "variability": max(sent_lens) - min(sent_lens) if sent_lens else 0,
        }

        # Level 4: абзацы (по смыслу)
        topics = FractalDecomposer._extract_topics(tl)
        levels["paragraph"] = {
            "count": len(topics),
            "topics": topics,
        }

        # Level 5: диалог (интенты)
        intents = FractalDecomposer._detect_intent_shifts(tl)
        levels["dialogue"] = {
            "intent": intents.get("primary", "chat"),
            "confidence": intents.get("confidence", 0.5),
            "type": intents.get("type", "statement"),
        }

        # Фрактальная подпись: хеш от всех уровней
        signature = hashlib.md5(
            json.dumps(levels, sort_keys=True).encode()
        ).hexdigest()

        return {
            "levels": levels,
            "signature": signature,
            "depth": max(1, len(set(words)) / max(1, len(words))) * 6,
        }

    @staticmethod
    def _entropy(values):
        total = sum(values)
        if not total:
            return 0
        return -sum(v / total * math.log2(v / total) for v in values if v > 0)

    @staticmethod
    def _extract_topics(text):
        """Извлекает темы из текста."""
        topics = []
        # Ключевые слова тем
        topic_keywords = {
            "tech": ["компьютер", "программа", "код", "алгоритм", "данные"],
            "science": ["наука", "физика", "математика", "биология", "химия"],
            "art": ["музыка", "кино", "книга", "рисовать", "творчество"],
            "life": ["работа", "дом", "семья", "друг", "еда"],
            "emotion": ["люблю", "грустно", "радость", "страх", "надежда"],
        }
        tl = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(k in tl for k in keywords):
                topics.append(topic)
        return topics[:3] if topics else ["general"]

    @staticmethod
    def _detect_intent_shifts(text):
        """Определяет интенты и их смену."""
        tl = text.lower()
        result = {"primary": "chat", "confidence": 0.5, "type": "statement"}

        if "?" in tl:
            result["type"] = "question"
            result["confidence"] = 0.7
            if any(w in tl for w in ["почему", "зачем", "как"]):
                result["primary"] = "deep"
                result["confidence"] = 0.85
            elif any(w in tl for w in ["где", "когда", "кто", "что"]):
                result["primary"] = "info"
                result["confidence"] = 0.8
        elif any(w in tl for w in ["сделай", "открой", "запусти"]):
            result["primary"] = "action"
            result["type"] = "command"
            result["confidence"] = 0.9
        elif any(w in tl for w in ["привет", "здравствуй"]):
            result["primary"] = "greeting"
            result["type"] = "social"
            result["confidence"] = 0.95

        return result


# ═══════════════════════════════════════════════════════════════
#  2. ГОЛОГРАФИЧЕСКАЯ ПРОЕКЦИЯ
# ═══════════════════════════════════════════════════════════════

class HolographicProjector:
    """
    Проецирует данные в N-мерное голографическое пространство.
    Каждый текст — это интерференционная картина.
    """

    DIMENSIONS = ["semantic", "emotional", "temporal", "structural", "associative"]

    def __init__(self):
        self._phase_space = defaultdict(lambda: defaultdict(float))
        self._interference_patterns = {}

    def project(self, text, fractal_profile=None):
        """Проецирует текст в 5-мерное пространство."""
        if not fractal_profile:
            fractal_profile = FractalDecomposer.decompose(text)

        tl = text.lower().strip()
        words = _tokenize(tl)

        # Semantic dimension — смысловая проекция
        sem = self._project_semantic(words, fractal_profile)

        # Emotional dimension — эмоциональная проекция
        emo = self._project_emotional(tl)

        # Temporal dimension — временная проекция
        tmp = self._project_temporal(fractal_profile)

        # Structural dimension — структурная проекция
        stc = self._project_structural(fractal_profile)

        # Associative dimension — ассоциативная проекция
        asc = self._project_associative(words)

        hologram = {
            "semantic": sem,
            "emotional": emo,
            "temporal": tmp,
            "structural": stc,
            "associative": asc,
            "phase": self._calculate_phase(sem, emo, tmp, stc, asc),
            "magnitude": self._calculate_magnitude(sem, emo, tmp, stc, asc),
        }

        # Сохраняем интерференционную картину
        sig = fractal_profile.get("signature", hashlib.md5(text.encode()).hexdigest())
        self._interference_patterns[sig] = hologram

        return hologram

    def _project_semantic(self, words, fp):
        """Семантическая проекция: интенты, темы, ключевые слова."""
        levels = fp["levels"]
        return {
            "word_richness": levels["word"]["richness"],
            "unique_words": levels["word"]["unique"],
            "topics": levels["paragraph"]["topics"],
            "intent": levels["dialogue"]["intent"],
            "depth": fp["depth"],
        }

    def _project_emotional(self, text):
        """Эмоциональная проекция: позитив/негатив, интенсивность."""
        tl = text.lower()
        pos = sum(tl.count(w) for w in ["спасиб", "хорош", "отличн", "прекрасн",
                                          "люблю", "рад", "классн", "супер"])
        neg = sum(tl.count(w) for w in ["плох", "ужасн", "груст", "негатив",
                                          "зл", "ненавиж", "гадк"])
        return {
            "valence": (pos - neg) / max(1, pos + neg),  # -1..1
            "intensity": min(1.0, (pos + neg) / 5),
            "exclamation": tl.count("!"),
            "question": tl.count("?"),
            "caps_ratio": sum(1 for c in text if c.isupper()) / max(1, len(text)),
        }

    def _project_temporal(self, fp):
        """Временная проекция: плотность, ритм."""
        levels = fp["levels"]
        return {
            "sentence_rhythm": levels["sentence"]["variability"],
            "avg_sentence_len": levels["sentence"]["avg_len"],
            "phrase_density": levels["phrase"]["count"] / max(1, levels["word"]["count"]),
        }

    def _project_structural(self, fp):
        """Структурная проекция: сложность, организация."""
        levels = fp["levels"]
        return {
            "char_entropy": levels["character"]["entropy"],
            "unique_ratio": levels["character"]["unique_ratio"],
            "depth": fp["depth"],
            "complexity": len(fp["signature"]) / 10,
        }

    def _project_associative(self, words):
        """Ассоциативная проекция: связи с известными паттернами."""
        associations = {}
        for i, w in enumerate(words):
            # Ассоциации из фазового пространства
            if w in self._phase_space:
                for assoc, strength in self._phase_space[w].items():
                    if assoc not in associations or strength > associations[assoc]:
                        associations[assoc] = strength
        return {
            "assoc_count": len(associations),
            "max_strength": max(associations.values()) if associations else 0,
        }

    def _calculate_phase(self, *dims):
        """Фаза голограммы — суммарный угол в N-мерном пространстве."""
        values = []
        for d in dims:
            if isinstance(d, dict):
                values.extend(v for v in d.values() if isinstance(v, (int, float)))
        if not values:
            return 0
        return math.atan2(sum(values), len(values))

    def _calculate_magnitude(self, *dims):
        """Амплитуда голограммы — энергия проекции."""
        energy = 0
        for d in dims:
            if isinstance(d, dict):
                energy += sum(v * v for v in d.values() if isinstance(v, (int, float)))
        return math.sqrt(energy)

    def learn_association(self, word1, word2, strength=0.1):
        """Формирует ассоциацию в фазовом пространстве."""
        self._phase_space[word1][word2] += strength
        self._phase_space[word2][word1] += strength

    def get_associations(self, word, top_n=5):
        """Возвращает ассоциации для слова."""
        assoc = dict(self._phase_space.get(word, {}))
        return sorted(assoc.items(), key=lambda x: -x[1])[:top_n]

    def compare(self, holo1, holo2):
        """Сравнивает две голограммы — квантовая интерференция."""
        phase_diff = abs(holo1["phase"] - holo2["phase"])
        mag_ratio = holo1["magnitude"] / max(0.001, holo2["magnitude"])
        interference = math.cos(phase_diff) * min(mag_ratio, 1 / max(0.001, mag_ratio))
        return max(0, interference)


# ═══════════════════════════════════════════════════════════════
#  3. КВАНТОВАЯ СУПЕРПОЗИЦИЯ
# ═══════════════════════════════════════════════════════════════

class QuantumSuperposition:
    """
    Множество гипотез существуют в суперпозиции до момента "схлопывания".
    Каждая гипотеза — это возможный путь обработки данных.
    """

    def __init__(self):
        self._hypotheses = []

    def add_hypothesis(self, name, data, amplitude=1.0):
        """Добавляет гипотезу с квантовой амплитудой."""
        self._hypotheses.append({
            "name": name,
            "data": data,
            "amplitude": amplitude,
            "phase": random.uniform(0, 2 * math.pi),
        })

    def collapse(self, observation=None):
        """Схлопывание суперпозиции — выбор гипотезы."""
        if not self._hypotheses:
            return None

        if observation:
            # Наблюдение влияет на вероятности
            for h in self._hypotheses:
                obs_match = self._match_observation(h["data"], observation)
                h["amplitude"] *= (0.5 + obs_match * 0.5)

        # Born rule: вероятность = |амплитуда|²
        total_prob = sum(h["amplitude"] ** 2 for h in self._hypotheses)
        if total_prob == 0:
            return random.choice(self._hypotheses)

        r = random.random() * total_prob
        cumulative = 0
        for h in self._hypotheses:
            cumulative += h["amplitude"] ** 2
            if r <= cumulative:
                return h

        return self._hypotheses[-1]

    def get_probabilities(self):
        """Возвращает распределение вероятностей."""
        total = sum(h["amplitude"] ** 2 for h in self._hypotheses) or 1
        return [{"name": h["name"], "prob": h["amplitude"] ** 2 / total,
                 "amplitude": h["amplitude"]} for h in self._hypotheses]

    def interfere(self, other):
        """Интерференция двух суперпозиций."""
        result = QuantumSuperposition()
        for h1 in self._hypotheses:
            for h2 in other._hypotheses:
                new_name = f"{h1['name']}+{h2['name']}"
                phase_diff = h1["phase"] - h2["phase"]
                interference = math.cos(phase_diff)
                new_amplitude = (h1["amplitude"] + h2["amplitude"]) / 2 * interference
                if new_amplitude > 0.1:
                    new_data = {**h1["data"], **h2["data"]}
                    result.add_hypothesis(new_name, new_data, new_amplitude)
        return result

    def _match_observation(self, data, observation):
        """Насколько гипотеза соответствует наблюдению."""
        if not data or not observation:
            return 0.5
        keys = set(data.keys()) & set(observation.keys())
        if not keys:
            return 0.5
        matches = sum(1 for k in keys if data.get(k) == observation.get(k))
        return matches / len(keys) if keys else 0.5

    def __len__(self):
        return len(self._hypotheses)


# ═══════════════════════════════════════════════════════════════
#  4. РЕЗОНАНСНОЕ СХЛОПЫВАНИЕ
# ═══════════════════════════════════════════════════════════════

class ResonanceCollapser:
    """
    Аналог квантового измерения — схлопывает суперпозицию
    через резонанс с известными паттернами.
    """

    def __init__(self):
        self._resonators = {}  # имя → {частота, паттерны}

    def add_resonator(self, name, frequency=1.0, patterns=None):
        """Добавляет резонатор (известный паттерн)."""
        self._resonators[name] = {
            "frequency": frequency,
            "patterns": patterns or [],
            "resonance": 0.0,
        }

    def resonate(self, hologram, text):
        """Вычисляет резонанс с каждым известным паттерном."""
        if not self._resonators:
            return "default", 0

        tl = text.lower().strip()
        best_name = "default"
        best_resonance = 0

        for name, res in self._resonators.items():
            resonance = 0
            freq = res["frequency"]

            # Паттерн-матчинг
            for pattern in res["patterns"]:
                if isinstance(pattern, str):
                    if pattern in tl:
                        resonance += freq * 0.3
                elif callable(pattern):
                    resonance += pattern(tl, hologram) * freq

            # Фазовая синхронизация с голограммой
            if hologram:
                h_phase = hologram.get("phase", 0)
                phase_match = abs(math.sin(h_phase - freq))
                resonance += phase_match * 0.2

            # Нормализация
            resonance = min(1.0, resonance)

            if resonance > best_resonance:
                best_resonance = resonance
                best_name = name

            res["resonance"] = resonance

        return best_name, best_resonance


# ═══════════════════════════════════════════════════════════════
#  5. ФАЗОВАЯ ПАМЯТЬ
# ═══════════════════════════════════════════════════════════════

class PhaseMemory:
    """
    Память, организованная через фазовые переходы.
    Информация кодируется не в точках, а в переходах между состояниями.
    """

    def __init__(self):
        self._states = []          # последовательность состояний
        self._transitions = Counter()  # (state_from, state_to) → count
        self._phase_map = {}        # state → фазовая координата

    def record(self, state, value=None):
        """Записывает фазовый переход."""
        if self._states:
            prev = self._states[-1]
            self._transitions[(prev, state)] += 1
        self._states.append(state)

        # Фазовая координата
        coord = _hash_fingerprint(str(state) + str(value or ""))
        self._phase_map[state] = coord

    def predict_next(self, n=3):
        """Предсказывает следующие состояния на основе фазовых переходов."""
        if not self._states:
            return []
        current = self._states[-1]
        candidates = []
        for (f, t), count in self._transitions.items():
            if f == current:
                candidates.append((t, count))
        candidates.sort(key=lambda x: -x[1])
        return candidates[:n]

    def get_phase_transition(self, state):
        """Возвращает фазовую траекторию состояния."""
        return self._phase_map.get(state, 0)

    def similarity(self, state1, state2):
        """Фазовая близость между состояниями."""
        p1 = self._phase_map.get(state1, 0)
        p2 = self._phase_map.get(state2, 0)
        return abs(p1 - p2)

    def get_entropy(self):
        """Энтропия фазовой памяти — мера хаотичности."""
        if not self._transitions:
            return 0
        total = sum(self._transitions.values())
        return -sum(c / total * math.log2(c / total) for c in self._transitions.values())

    def to_dict(self):
        return {
            "states": self._states[-100:],
            "transitions": [(f"{f}->{t}", c) for (f, t), c in self._transitions.most_common(50)],
            "entropy": self.get_entropy(),
        }


# ═══════════════════════════════════════════════════════════════
#  6. ГЛАВНЫЙ ДВИЖОК MFPE
# ═══════════════════════════════════════════════════════════════

class FractalProcessor:
    """
    Multidimensional Fractal Processing Engine.
    Главный класс — объединяет все 5 компонентов.
    """

    def __init__(self):
        self.decomposer = FractalDecomposer()
        self.projector = HolographicProjector()
        self.superposition = QuantumSuperposition()
        self.collapser = ResonanceCollapser()
        self.phase_memory = PhaseMemory()

        # Инициализация резонаторов
        self._init_resonators()

        # Хранилище голограмм
        self._holo_cache = {}
        self._insights = []

        # Загрузка
        self._load()

    def _init_resonators(self):
        """Инициализация резонаторов для разных типов запросов."""
        self.collapser.add_resonator("greeting", 1.0, [
            "привет", "здравствуй", "хай", "hello", "hi", "добрый",
        ])
        self.collapser.add_resonator("question", 0.85, [
            "?", "почему", "зачем", "как", "что", "кто", "где",
        ])
        self.collapser.add_resonator("command", 0.95, [
            "сделай", "открой", "запусти", "напиши", "включи",
        ])
        self.collapser.add_resonator("emotional", 0.7, [
            "груст", "рад", "люблю", "ненавиж", "страш",
        ])
        self.collapser.add_resonator("deep", 0.75, [
            lambda t, h: 0.8 if t.count(" ") > 8 and "?" in t else 0,
        ])

    def process(self, text):
        """Полный цикл обработки данных через MFPE."""
        start = time.time()

        # 1. Фрактальная декомпозиция
        fractal = self.decomposer.decompose(text)
        self.phase_memory.record("decompose", fractal["depth"])

        # 2. Голографическая проекция
        hologram = self.projector.project(text, fractal)
        self._holo_cache[fractal["signature"]] = hologram
        self.phase_memory.record("project", hologram["phase"])

        # 3. Квантовая суперпозиция гипотез
        self.superposition = QuantumSuperposition()
        intent = fractal["levels"]["dialogue"]["intent"]
        for engine in ["chat", "semantic", "creative", "command"]:
            h_data = {
                "engine": engine,
                "intent": intent,
                "complexity": fractal["depth"],
                "emotional": hologram["emotional"]["valence"],
            }
            self.superposition.add_hypothesis(engine, h_data, amplitude=random.uniform(0.5, 1.0))

        # 4. Резонансное схлопывание
        best_resonator, resonance_strength = self.collapser.resonate(hologram, text)
        self.phase_memory.record("resonate", resonance_strength)

        # Наблюдение для схлопывания
        observation = {"intent": intent, "resonator": best_resonator}
        chosen = self.superposition.collapse(observation)

        # 5. Фазовый результат
        engine = chosen["name"] if chosen else "chat"
        confidence = resonance_strength * (chosen["amplitude"] if chosen else 0.5)

        self.phase_memory.record("result", confidence)

        # Формируем инсайты
        self._generate_insights(text, fractal, hologram, engine, confidence)

        elapsed = time.time() - start
        logger.debug("MFPE: %.3fs | resonance=%.2f | engine=%s | depth=%.1f",
                     elapsed, resonance_strength, engine, fractal["depth"])

        return {
            "engine": engine,
            "confidence": min(1.0, confidence),
            "resonance": resonance_strength,
            "fractal_depth": fractal["depth"],
            "hologram": hologram,
            "phase": hologram["phase"],
            "magnitude": hologram["magnitude"],
            "quantum_hypotheses": self.superposition.get_probabilities(),
            "insights": self._insights[-5:] if self._insights else [],
            "signature": fractal["signature"],
            "time": elapsed,
        }

    def _generate_insights(self, text, fractal, hologram, engine, confidence):
        """Генерирует инсайты из фрактальной обработки."""
        insight = {}
        levels = fractal["levels"]

        # Инсайт о стиле
        word_richness = levels["word"]["richness"]
        if word_richness > 0.8:
            insight["style"] = "богатый словарный запас"
        elif word_richness < 0.3:
            insight["style"] = "лаконичный стиль"

        # Инсайт об эмоциях
        if hologram["emotional"]["valence"] > 0.3:
            insight["mood"] = "позитивный настрой"
        elif hologram["emotional"]["valence"] < -0.3:
            insight["mood"] = "негативная окраска"

        # Инсайт о сложности
        if fractal["depth"] > 4:
            insight["complexity"] = "сложный запрос — требуется глубокий анализ"

        # Инсайт о квантовом выборе
        if confidence > 0.8:
            insight["certainty"] = f"высокая уверенность: {engine}"

        if insight:
            insight["time"] = datetime.datetime.now().isoformat()
            self._insights.append(insight)
            if len(self._insights) > 100:
                self._insights = self._insights[-100:]

    def learn(self, text, response, success=True):
        """Обучение на результате обработки."""
        fractal = self.decomposer.decompose(text)
        hologram = self.projector.project(text, fractal)

        # Ассоциативное обучение
        words = _tokenize(text)
        for i, w in enumerate(words):
            for j in range(max(0, i-2), min(len(words), i+3)):
                if i != j:
                    strength = 0.05 if success else -0.02
                    self.projector.learn_association(w, words[j], strength)

        # Фазовая память
        state = fractal["levels"]["dialogue"]["intent"]
        self.phase_memory.record(f"learn_{state}_{'ok' if success else 'fail'}")

        # Сохраняем
        self._save()

    def get_insights(self, n=10):
        """Последние инсайты."""
        return self._insights[-n:]

    def get_stats(self):
        """Статистика движка."""
        return {
            "holograms": len(self._holo_cache),
            "phase_states": len(self._phase_map()),
            "phase_entropy": self.phase_memory.get_entropy(),
            "resonators": list(self.collapser._resonators.keys()),
            "insights": len(self._insights),
        }

    def _phase_map(self):
        m = {}
        s = self.phase_memory
        for st in set(s._states):
            m[st] = s.get_phase_transition(st)
        return m

    def _save(self):
        """Сохраняет состояние (фазовая память, ассоциации)."""
        try:
            DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "phase_memory": self.phase_memory.to_dict(),
                "insights": self._insights[-50:],
            }
            DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("MFPE save: %s", e)

    def _load(self):
        """Загружает сохранённое состояние."""
        try:
            if DATA_PATH.exists():
                data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
                pm = data.get("phase_memory", {})
                if pm.get("states"):
                    for s in pm["states"]:
                        self.phase_memory.record(s)
                self._insights = data.get("insights", [])
        except Exception as e:
            logger.warning("MFPE load: %s", e)


# ═══════════════════════════════════════════════════════════════
#  ДЕМОНСТРАЦИЯ
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    fp = FractalProcessor()
    tests = [
        "привет, как дела?",
        "почему небо голубое? объясни подробно, мне очень интересно",
        "открой браузер и найди информацию о космосе",
        "мне грустно сегодня, расскажи что-нибудь весёлое",
        "сколько будет 25 умножить на 4?",
    ]
    for t in tests:
        result = fp.process(t)
        print(f"\n{'='*60}")
        print(f"ВХОД: {t}")
        print(f"ВЫХОД: engine={result['engine']}, "
              f"conf={result['confidence']:.2f}, "
              f"resonance={result['resonance']:.2f}, "
              f"depth={result['fractal_depth']:.1f}")
        print(f"ФАЗА: {result['phase']:.3f}, МАГНИТУДА: {result['magnitude']:.3f}")
        print(f"КВАНТОВЫЕ ГИПОТЕЗЫ:")
        for h in result['quantum_hypotheses']:
            print(f"  {h['name']}: {h['prob']:.2f} (ampl={h['amplitude']:.2f})")
        if result['insights']:
            for ins in result['insights']:
                for k, v in ins.items():
                    if k != 'time':
                        print(f"  ИНСАЙТ: {v}")
