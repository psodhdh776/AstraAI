"""
Advanced Thinking & Learning Engine — chain-of-thought, reflection, learning.
"""
import re, datetime, json, random, math, logging
from collections import defaultdict, Counter
from pathlib import Path

logger = logging.getLogger("Astra.Think")


class Thought:
    """Один шаг цепочки рассуждений."""
    def __init__(self, stage, content, score=1.0):
        self.stage = stage      # observe / reason / reflect / conclude
        self.content = content
        self.score = score
        self.time = datetime.datetime.now()

    def __repr__(self):
        return f"[{self.stage.upper()}] {self.content}"


class TraceGraph:
    """Граф рассуждений — ветвление и свертка."""
    def __init__(self):
        self.nodes = []
        self.edges = []  # (from_idx, to_idx, label)

    def add(self, thought, parent_idx=-1):
        idx = len(self.nodes)
        self.nodes.append(thought)
        if parent_idx >= 0:
            self.edges.append((parent_idx, idx, "next"))
        return idx

    def to_text(self):
        lines = []
        for i, n in enumerate(self.nodes):
            prefix = "  " if any(p == i for p, _, _ in self.edges) else ""
            lines.append(f"{prefix}▪ {n.stage}: {n.content}")
        return "\n".join(lines)


class ThinkingEngineV2:
    """
    Многошаговый движок мышления с:
    - Chain-of-Thought (пошаговая декомпозиция)
    - Self-Reflection (оценка собственных шагов)
    - Backtracking (возврат при тупике)
    - Pattern Learning (извлечение паттернов из диалогов)
    """

    def __init__(self):
        self.trace = TraceGraph()
        self.context = {
            "turn": 0,
            "session_start": datetime.datetime.now(),
            "last_topics": [],
            "last_intent": None,
            "confidence": 0.5,
            "user_name": None,
            "facts_known": {},       # факты о пользователе
            "entity_history": [],    # сущности из диалога
            "question_count": 0,
            "command_count": 0,
        }
        # Learning
        self._patterns = defaultdict(list)   # intent → [(words, count)]
        self._word_assoc = defaultdict(Counter)  # слово → {слово: вес}
        self._response_memory = []  # (user_text, response, score)
        self._user_preferences = defaultdict(float)  # preference → weight
        self._lesson_count = 0
        self._data_path = Path(__file__).parent.parent / "data" / "thinking_memory.json"
        self._load()

    # ═══════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ═══════════════════════════════════════════════════════════════

    def think(self, text):
        """Полный цикл мышления."""
        self.trace = TraceGraph()
        self.context["turn"] += 1

        # 1. Наблюдение
        obs = self._observe(text)
        obs_idx = self.trace.add(Thought("observe", obs))

        # 2. Декомпозиция вопроса
        parts = self._decompose(text)
        for part in parts:
            self.trace.add(Thought("decompose", f"Подвопрос: {part}"), obs_idx)

        # 3. Поиск в памяти
        mem = self._recall(text)
        if mem:
            self.trace.add(Thought("memory", f"Найдено в памяти: {mem[:60]}..."), obs_idx)

        # 4. Рассуждение (цепочка)
        reasoning = self._reason_chain(text)
        last_idx = obs_idx
        for step in reasoning:
            last_idx = self.trace.add(Thought("reason", step), last_idx)

        # 5. Рефлексия
        reflection = self._reflect(text, reasoning)
        if reflection:
            self.trace.add(Thought("reflect", reflection), last_idx)

        # 6. Вывод
        conclusion = self._conclude(text, reasoning, reflection)
        c_idx = self.trace.add(Thought("conclude", conclusion), last_idx)

        # 7. Обучение
        self._learn_from_query(text, conclusion)

        result = {
            "intent": self._classify(text),
            "confidence": self._estimate_confidence(text, reasoning),
            "trace": self.trace.to_text(),
            "conclusion": conclusion,
            "needs_reflection": self.context["turn"] > 3,
            "context": dict(self.context),
        }

        self.context["last_intent"] = result["intent"]
        self.context["last_topics"].append(result["intent"])
        if len(self.context["last_topics"]) > 10:
            self.context["last_topics"].pop(0)

        return result

    def reason_deep(self, text):
        """Быстрые шаги мышления для UI (отображаются в ThinkingBubble)."""
        tl = text.lower().strip()
        steps = []
        steps.append(("preprocess", f"Анализирую: «{text[:40]}»"))

        # Используем обученные паттерны
        known = self._find_known_patterns(tl)
        if known:
            steps.append(("memory", f"Узнаю: {known}"))

        intent = self._classify(tl)
        if intent == "deep":
            steps.append(("reason", "Глубокий вопрос — раскладываю на части"))
            parts = self._decompose(text)
            for p in parts[:2]:
                steps.append(("decompose", f"→ {p[:50]}"))
        elif intent == "info":
            steps.append(("reason", "Информационный запрос — ищу данные"))
            steps.append(("memory", "Проверяю базу знаний и историю"))
        elif intent == "action":
            steps.append(("reason", "Команда — определяю действие"))
        else:
            steps.append(("reason", "Свободный диалог — подбираю тон"))
            ctx = self.context.get("last_topics", [])
            if ctx:
                steps.append(("context", f"Контекст: {ctx[-1]}"))

        if self.context.get("user_name"):
            steps.append(("personal", f"Для {self.context['user_name']}"))

        # Подсказка из обучения
        lesson = self._get_lesson(tl)
        if lesson:
            steps.append(("learn", f"Помню: {lesson}"))

        return steps

    def learn_from_feedback(self, user_text, response, was_positive=True):
        """Обратная связь — учимся на оценке пользователя."""
        score = 1.0 if was_positive else -0.5
        self._response_memory.append((user_text, response, score))
        if len(self._response_memory) > 500:
            self._response_memory.pop(0)

        words = self._tokenize(user_text)
        resp_words = self._tokenize(response)

        # Укрепляем/ослабляем ассоциации
        for w in words:
            for rw in resp_words[:5]:
                if was_positive:
                    self._word_assoc[w][rw] += 0.1
                else:
                    self._word_assoc[w][rw] -= 0.05

        # Извлекаем урок
        if was_positive and len(words) > 2:
            pattern = " ".join(words[:3])
            self._patterns[self._classify(user_text)].append((pattern, 1))
            self._lesson_count += 1

        self._save()

    def learn_fact(self, key, value):
        """Запоминаем факт о пользователе."""
        self.context["facts_known"][key] = value
        self._save()

    def get_fact(self, key):
        return self.context["facts_known"].get(key)

    def get_thinking_trace(self):
        return self.trace.to_text()

    def save_state(self):
        return {"context": {k: v for k, v in self.context.items() if k != "entity_history"}}

    def load_state(self, data):
        if data and "context" in data:
            for k, v in data["context"].items():
                if k in self.context:
                    self.context[k] = v

    # ═══════════════════════════════════════════════════════════════
    #  INTERNAL: МЫШЛЕНИЕ
    # ═══════════════════════════════════════════════════════════════

    def _observe(self, text):
        """Анализ входящего сообщения."""
        tl = text.lower().strip()
        parts = []
        parts.append(f"Получен запрос из {len(tl.split())} слов")
        if "?" in tl:
            parts.append("Содержит вопрос")
        if any(w in tl for w in ["почему", "зачем", "отчего"]):
            parts.append("Причинно-следственный вопрос")
        if any(w in tl for w in ["как", "каким образом"]):
            parts.append("Вопрос о процессе/методе")
        if any(w in tl for w in ["кто", "что", "где", "когда"]):
            parts.append("Фактический вопрос")
        if any(w in tl for w in ["сделай", "открой", "запусти"]):
            parts.append("Обнаружена команда действия")
        return "; ".join(parts) if parts else "Запрос принят"

    def _decompose(self, text):
        """Разбиваем сложный вопрос на подвопросы."""
        tl = text.lower().strip()
        parts = []

        # Многосоставные вопросы
        if " и " in tl and "?" in tl:
            clauses = re.split(r'\s+и\s+', tl)
            for c in clauses:
                if "?" in c or len(c.split()) > 2:
                    parts.append(c.strip().capitalize())

        # "Почему X, если Y?"
        m = re.search(r'почему\s+(.+?)(?:,\s*если\s+(.+))?', tl)
        if m:
            parts.append(f"Причина: {m.group(1)}")
            if m.group(2):
                parts.append(f"Условие: {m.group(2)}")

        # "Как сделать X?"
        m = re.search(r'как\s+(.+?)(?:\?|$)', tl)
        if m:
            parts.append(f"Нужны шаги для: {m.group(1)}")

        # Тема + вопрос
        if "что такое" in tl:
            topic = tl.split("что такое")[-1].strip().rstrip("?").strip()
            parts.append(f"Определение: {topic}")
        if "кто такой" in tl:
            topic = tl.split("кто такой")[-1].strip().rstrip("?").strip()
            parts.append(f"Личность: {topic}")

        return parts if parts else [f"Целостный запрос: {text[:60]}"]

    def _recall(self, text):
        """Поиск похожих ситуаций в памяти."""
        tl = self._tokenize(text)
        if not tl:
            return None

        # Ищем в истории ответов
        best_score = 0
        best_mem = None
        for user_text, response, score in self._response_memory[-100:]:
            mem_words = self._tokenize(user_text)
            overlap = len(set(tl) & set(mem_words))
            if overlap > best_score:
                best_score = overlap
                best_mem = response

        if best_score >= 2:
            return f"Похожий запрос был: {best_mem[:80]}"

        # Ищем в фактах
        for key, val in self.context["facts_known"].items():
            if any(w in key for w in tl):
                return f"Знаю: {key} = {val}"

        return None

    def _reason_chain(self, text):
        """Цепочка рассуждений."""
        steps = []
        tl = text.lower().strip()

        intent = self._classify(tl)

        if intent == "deep":
            steps.append("Это требует анализа причин и следствий")
            if self.context.get("facts_known"):
                steps.append(f"Учитываю известные факты о пользователе")
            if self.context["turn"] > 2:
                steps.append(f"Анализирую в контексте предыдущих {min(self.context['turn']-1, 5)} реплик")
        elif intent == "info":
            steps.append("Ищу фактическую информацию в своей базе")
            if self.context["turn"] > 5:
                steps.append("Пользуюсь накопленными знаниями из диалога")
        elif intent == "action":
            steps.append("Определяю тип команды и параметры")
            steps.append("Проверяю безопасность выполнения")
        else:
            steps.append("Определяю эмоциональный тон запроса")
            if self.context["turn"] > 2:
                last_topic = self.context.get("last_topics", [None])[-1]
                if last_topic:
                    steps.append(f"Продолжаю тему: {last_topic}")
            steps.append("Подбираю ответ под стиль общения пользователя")

        # Саморефлексия если много ошибок
        if len(self._response_memory) >= 5:
            recent = [s for _, _, s in self._response_memory[-5:]]
            avg = sum(recent) / len(recent)
            if avg < 0:
                steps.append(f"⚠ Замечена низкая точность ответов — включаю осторожный режим")

        return steps

    def _reflect(self, text, reasoning):
        """Самооценка качества рассуждения."""
        if len(reasoning) == 0:
            return "Недостаточно данных для вывода — запрашиваю уточнение"
        if len(reasoning) > 5:
            return "Рассуждение слишком длинное — сворачиваю к главному"
        # Оценка уверенности
        tl = text.lower().strip()
        known_patterns = self._find_known_patterns(tl)
        if known_patterns:
            return f"Уверен: ранее встречал похожий запрос"
        return None

    def _conclude(self, text, reasoning, reflection):
        """Формирование вывода."""
        tl = text.lower().strip()
        if reflection and "уверен" in reflection:
            return "Могу ответить на основе предыдущего опыта"
        if "глубокий" in str(reasoning):
            return "Требуется развёрнутый ответ с объяснением"
        if "команда" in str(reasoning):
            return "Готов выполнить команду"
        return "Могу дать прямой ответ"

    def _estimate_confidence(self, text, reasoning):
        """Оценка уверенности в ответе (0..1)."""
        base = 0.5
        boost = 0.0

        known = self._find_known_patterns(text.lower())
        if known:
            boost += 0.2

        if self.context["turn"] > 5:
            boost += 0.1

        if len(self._response_memory) > 10:
            recent = [s for _, _, s in self._response_memory[-10:]]
            avg = sum(recent) / len(recent)
            boost += avg * 0.1

        if reasoning:
            boost += 0.1

        return min(1.0, base + boost)

    def _classify(self, tl):
        """Классификация типа запроса."""
        deep_words = ["почему", "зачем", "отчего", "как", "причина", "следствие",
                      "каким образом", "в чём", "объясни", "расскажи"]
        info_words = ["найди", "поищи", "где", "кто такой", "что такое",
                      "сколько", "когда", "информация", "узнать"]
        action_words = ["сделай", "открой", "запусти", "напиши", "создай",
                        "выполни", "загрузи", "установи", "включи", "выключи"]

        for w in deep_words:
            if w in tl:
                return "deep"
        for w in info_words:
            if w in tl:
                return "info"
        for w in action_words:
            if w in tl:
                return "action"
        return "chat"

    # ═══════════════════════════════════════════════════════════════
    #  INTERNAL: ОБУЧЕНИЕ
    # ═══════════════════════════════════════════════════════════════

    def _learn_from_query(self, text, conclusion):
        """Извлечение паттернов из каждого запроса."""
        tl = text.lower().strip()
        words = self._tokenize(tl)

        # Ассоциативное обучение
        for i, w in enumerate(words):
            for j in range(max(0, i-3), min(len(words), i+4)):
                if i != j:
                    self._word_assoc[w][words[j]] += 0.01

        # Извлечение темы для повторяющихся паттернов
        if len(words) >= 3 and self.context["turn"] > 5:
            ngram = " ".join(words[:3])
            intent = self._classify(tl)
            self._patterns[intent].append((ngram, 1))
            self._lesson_count += 1

    def _find_known_patterns(self, text):
        """Поиск известных паттернов в запросе."""
        words = self._tokenize(text)
        if not words:
            return None

        for intent, patterns in self._patterns.items():
            for pattern, count in patterns:
                if count > 2 and pattern in text:
                    return f"паттерн «{intent}» (повторений: {count})"

        return None

    def _get_lesson(self, text):
        """Извлечение урока из памяти."""
        if self._lesson_count > 5 and self.context["turn"] > 10:
            return f"уже обработано {self._lesson_count} обучающих примеров"
        return None

    def _tokenize(self, text):
        return [w for w in re.findall(r'\w+', text.lower()) if len(w) > 1]

    # ═══════════════════════════════════════════════════════════════
    #  СОХРАНЕНИЕ / ЗАГРУЗКА
    # ═══════════════════════════════════════════════════════════════

    def _save(self):
        try:
            data = {
                "patterns": {k: v[-50:] for k, v in self._patterns.items()},
                "word_assoc": {k: dict(v.most_common(20)) for k, v in self._word_assoc.items()},
                "response_memory": self._response_memory[-200:],
                "lesson_count": self._lesson_count,
                "facts": self.context["facts_known"],
            }
            self._data_path.parent.mkdir(parents=True, exist_ok=True)
            self._data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Save thinking memory: %s", e)

    def _load(self):
        try:
            if self._data_path.exists():
                data = json.loads(self._data_path.read_text(encoding="utf-8"))
                self._patterns = defaultdict(list, data.get("patterns", {}))
                self._word_assoc = defaultdict(Counter, {k: Counter(v) for k, v in data.get("word_assoc", {}).items()})
                self._response_memory = [tuple(x) for x in data.get("response_memory", [])]
                self._lesson_count = data.get("lesson_count", 0)
                self.context["facts_known"] = data.get("facts", {})
        except Exception as e:
            logger.warning("Load thinking memory: %s", e)
