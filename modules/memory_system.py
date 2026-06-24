"""
Unified Memory System — short-term, long-term, semantic, episodic, procedural.
All persistent storage in data/memory/ directory.
"""
import json, datetime, re, threading, time, logging
from pathlib import Path
from collections import defaultdict, Counter
from typing import Optional, List, Dict, Any

logger = logging.getLogger("Astra.Memory")

MEMORY_DIR = Path(__file__).parent.parent / "data" / "memory"
LOCK = threading.Lock()


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _tokenize(text):
    return [w for w in re.findall(r'\w+', text.lower()) if len(w) > 1]


class MemoryStore:
    """Базовое хранилище с JSON-персистентностью."""
    def __init__(self, name: str):
        self.name = name
        self.path = MEMORY_DIR / f"{name}.json"
        self.data = {}
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
                logger.debug("Memory %s loaded (%d items)", self.name, len(self.data))
        except Exception as e:
            logger.warning("Load %s: %s", self.name, e)
            self.data = {}

    def save(self):
        with LOCK:
            try:
                MEMORY_DIR.mkdir(parents=True, exist_ok=True)
                self.path.write_text(
                    json.dumps(self.data, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
            except Exception as e:
                logger.warning("Save %s: %s", self.name, e)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        with LOCK:
            self.data[key] = value

    def delete(self, key):
        with LOCK:
            self.data.pop(key, None)

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()


class ShortTermMemory:
    """Краткосрочная память — текущая сессия (не сохраняется)."""
    def __init__(self, capacity=50):
        self.buffer = []
        self.capacity = capacity
        self.turn = 0
        self.session_start = _now()
        self.current_intent = None
        self.last_topic = None
        self.topic_history = []

    def add(self, role, text, intent=None, entities=None):
        self.turn += 1
        entry = {
            "turn": self.turn,
            "role": role,
            "text": text,
            "intent": intent or "unknown",
            "entities": entities or {},
            "time": _now(),
        }
        self.buffer.append(entry)
        self.current_intent = intent
        if intent and intent != "unknown":
            self.last_topic = intent
            self.topic_history.append(intent)
        if len(self.buffer) > self.capacity:
            self.buffer.pop(0)

    def recent(self, n=10):
        return self.buffer[-n:]

    def context_window(self, n=5):
        """Последние n реплик для контекста диалога."""
        return [(e["role"], e["text"]) for e in self.buffer[-n:]]

    def summary(self):
        return {
            "turns": self.turn,
            "session_start": self.session_start,
            "topics": self.topic_history[-10:],
            "last_intent": self.current_intent,
        }


class LongTermMemory(MemoryStore):
    """Долговременная память — факты, предпочтения, профиль пользователя."""
    def __init__(self):
        super().__init__("long_term")
        self._init_defaults()

    def _init_defaults(self):
        if "user_profile" not in self.data:
            self.data["user_profile"] = {
                "name": None, "city": None, "age": None,
                "likes": [], "dislikes": [], "hobbies": [],
                "first_seen": _now(), "last_seen": _now(),
                "total_sessions": 0, "total_messages": 0,
            }
        if "facts" not in self.data:
            self.data["facts"] = {}
        if "preferences" not in self.data:
            self.data["preferences"] = {}
        if "vocabulary" not in self.data:
            self.data["vocabulary"] = {}
        if "style_profile" not in self.data:
            self.data["style_profile"] = {
                "avg_length": 5.0, "emotion_level": 0.5,
                "curiosity": 0.5, "formality": 0.3,
            }

    @property
    def profile(self):
        return self.data["user_profile"]

    @property
    def facts(self):
        return self.data["facts"]

    def update_profile(self, key, value):
        if key in self.profile:
            self.profile[key] = value
            self.profile["last_seen"] = _now()
        self.data["facts"][key] = value
        self.save()

    def learn_fact(self, text):
        """Извлекает факты из текста."""
        tl = text.lower()
        learned = []
        # Имя
        m = re.search(r'(?:меня\s+зовут\s+|my\s+name\s+is\s+|(?:i|call)\s+me\s+)(\w+)', text, re.I)
        if m:
            name = m.group(1).capitalize()
            self.update_profile("name", name)
            learned.append(f"name={name}")
        # Город
        m = re.search(r'(?:я\s+(?:из|живу\s+в)\s+|i\s+(?:am\s+from|live\s+in)\s+)(\w+)', text, re.I)
        if m:
            city = m.group(1).capitalize()
            self.update_profile("city", city)
            learned.append(f"city={city}")
        # Возраст
        m = re.search(r'(?:мне\s+)(\d+)(?:\s+лет|\s+years?\s*old)', text, re.I)
        if m:
            age = int(m.group(1))
            self.update_profile("age", age)
            learned.append(f"age={age}")
        # Любит
        for pattern, key in [(r'(?:я\s+(?:люблю|обожаю|нравится)\s+)(.+)', "likes"),
                              (r'(?:i\s+(?:like|love|enjoy)\s+)(.+)', "likes")]:
            m = re.search(pattern, text, re.I)
            if m:
                topic = m.group(1).strip().rstrip(".!").strip().lower()
                if topic not in self.profile[key]:
                    self.profile[key].append(topic)
                    self.save()
                    learned.append(f"{key}={topic}")
        return learned if learned else None

    def update_style(self, text):
        """Анализ стиля общения."""
        words = _tokenize(text)
        sp = self.data["style_profile"]
        if words:
            sp["avg_length"] = round(sp["avg_length"] * 0.9 + len(words) * 0.1, 1)
        if "!" in text:
            sp["emotion_level"] = round(min(1.0, sp["emotion_level"] + 0.03), 2)
        if "?" in text:
            sp["curiosity"] = round(min(1.0, sp["curiosity"] + 0.03), 2)

    def get_summary(self):
        """Человеко-читаемая сводка."""
        p = self.profile
        parts = []
        if p.get("name"):
            parts.append(f"Имя: {p['name']}")
        if p.get("city"):
            parts.append(f"Город: {p['city']}")
        if p.get("age"):
            parts.append(f"Возраст: {p['age']}")
        if p.get("likes"):
            parts.append(f"Любит: {', '.join(p['likes'][-3:])}")
        parts.append(f"Сообщений: {p['total_messages']}")
        parts.append(f"Сессий: {p['total_sessions']}")
        return "; ".join(parts)


class EpisodicMemoryStore(MemoryStore):
    """Эпизодическая память — прошлые диалоги с суммаризацией."""
    def __init__(self):
        super().__init__("episodic")
        if "episodes" not in self.data:
            self.data["episodes"] = []
        if "summaries" not in self.data:
            self.data["summaries"] = []

    def add_episode(self, role, text, intent, importance=0.5):
        ep = {
            "role": role, "text": text, "intent": intent,
            "importance": importance, "time": _now(),
        }
        self.data["episodes"].append(ep)
        # Trim to keep top 500
        if len(self.data["episodes"]) > 500:
            self.data["episodes"].sort(key=lambda x: -x.get("importance", 0.5))
            self.data["episodes"] = self.data["episodes"][:500]
        # Periodic consolidation
        if len(self.data["episodes"]) % 50 == 0:
            self._consolidate()
        self.save()

    def _consolidate(self):
        """Создаёт краткие сводки по группам диалогов."""
        if not self.data["episodes"]:
            return
        # Группируем по интентам
        by_intent = defaultdict(list)
        for ep in self.data["episodes"][-200:]:
            by_intent[ep.get("intent", "unknown")].append(ep["text"])
        summaries = []
        for intent, texts in by_intent.items():
            if len(texts) >= 3:
                # Берём ключевые слова
                words = Counter(w for t in texts for w in _tokenize(t))
                top = [w for w, _ in words.most_common(5)]
                summaries.append({
                    "intent": intent,
                    "count": len(texts),
                    "keywords": top,
                    "last": _now(),
                })
        self.data["summaries"] = summaries[-30:]

    def recall(self, query, top_n=5):
        """Поиск похожих эпизодов."""
        q_words = set(_tokenize(query))
        if not q_words:
            return self.data["episodes"][-top_n:]
        scored = []
        for ep in self.data["episodes"]:
            ep_words = set(_tokenize(ep["text"]))
            overlap = len(q_words & ep_words)
            if overlap > 0:
                score = ep.get("importance", 0.5) + overlap * 0.1
                scored.append((score, ep))
        scored.sort(key=lambda x: -x[0])
        return [ep for _, ep in scored[:top_n]]


class SemanticMemory(MemoryStore):
    """Семантическая память — ассоциации между словами и понятиями."""
    def __init__(self):
        super().__init__("semantic")
        if "associations" not in self.data:
            self.data["associations"] = {}
        if "concepts" not in self.data:
            self.data["concepts"] = {}

    def learn_association(self, word1, word2, strength=0.1):
        """Укрепляет ассоциацию между двумя словами."""
        assoc = self.data["associations"]
        if word1 not in assoc:
            assoc[word1] = {}
        assoc[word1][word2] = min(1.0, assoc[word1].get(word2, 0) + strength)
        if word2 not in assoc:
            assoc[word2] = {}
        assoc[word2][word1] = min(1.0, assoc[word2].get(word1, 0) + strength)

    def get_associated(self, word, top_n=5):
        """Возвращает слова, ассоциированные с данным."""
        assoc = self.data["associations"].get(word, {})
        return sorted(assoc.items(), key=lambda x: -x[1])[:top_n]

    def learn_concept(self, name, attributes):
        """Запоминает понятие и его атрибуты."""
        self.data["concepts"][name.lower()] = {
            "attributes": attributes,
            "learned": _now(),
        }

    def get_concept(self, name):
        return self.data["concepts"].get(name.lower())


class ProceduralMemory(MemoryStore):
    """Процедурная память — как отвечать на разные типы запросов."""
    def __init__(self):
        super().__init__("procedural")
        if "response_patterns" not in self.data:
            self.data["response_patterns"] = {}
        if "success_rate" not in self.data:
            self.data["success_rate"] = {}

    def record_response(self, intent, response, was_successful):
        """Запоминает, какой ответ сработал для данного интента."""
        patterns = self.data["response_patterns"]
        if intent not in patterns:
            patterns[intent] = []
        patterns[intent].append({
            "response": response[:200],
            "success": was_successful,
            "time": _now(),
        })
        if len(patterns[intent]) > 20:
            patterns[intent] = patterns[intent][-20:]
        # Update success rate
        sr = self.data["success_rate"]
        sr[intent] = sr.get(intent, 0.5) * 0.9 + (0.1 if was_successful else -0.05)
        sr[intent] = max(0, min(1, sr[intent]))
        self.save()

    def get_best_response(self, intent):
        """Возвращает лучший ответ для интента."""
        patterns = self.data["response_patterns"].get(intent, [])
        successful = [p for p in patterns if p.get("success")]
        if successful:
            return successful[-1]["response"]
        return None


class MemorySystem:
    """
    Единая система памяти Astra AI.
    Объединяет все типы памяти в один интерфейс.
    """
    def __init__(self):
        self.short = ShortTermMemory()
        self.long = LongTermMemory()
        self.episodic = EpisodicMemoryStore()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        logger.info("MemorySystem: 5 модулей инициализированы")

    def observe(self, role, text, intent="unknown", entities=None):
        """Наблюдение за событием — запись во все виды памяти."""
        entities = entities or {}
        # Short-term
        self.short.add(role, text, intent, entities)
        # Long-term: стиль, факты
        self.long.update_style(text)
        self.long.profile["total_messages"] += 1
        facts = self.long.learn_fact(text)
        # Episodic
        importance = self._calc_importance(intent, entities)
        self.episodic.add_episode(role, text, intent, importance)
        # Semantic: ассоциации
        words = _tokenize(text)
        for i, w in enumerate(words):
            for j in range(max(0, i-2), min(len(words), i+3)):
                if i != j:
                    self.semantic.learn_association(w, words[j], 0.02)
        # Save periodically
        if self.short.turn % 10 == 0:
            self.long.save()
            self.episodic.save()

    def new_session(self):
        """Начало новой сессии."""
        self.short = ShortTermMemory()
        self.long.profile["total_sessions"] += 1
        self.long.profile["last_seen"] = _now()
        self.long.save()

    def recall(self, query, top_n=5):
        """Поиск по всей памяти."""
        return self.episodic.recall(query, top_n)

    def get_user_summary(self):
        """Сводка о пользователе."""
        return self.long.get_summary()

    def get_session_summary(self):
        """Сводка о текущей сессии."""
        s = self.short
        return {
            "turn": s.turn,
            "session_start": s.session_start,
            "topics": s.topic_history[-5:],
            "messages": len(s.buffer),
        }

    def get_memory_stats(self):
        """Статистика по всей памяти."""
        return {
            "short_term": len(self.short.buffer),
            "long_term_facts": len(self.long.facts),
            "long_term_vocab": len(self.long.data.get("vocabulary", {})),
            "episodic": len(self.episodic.data.get("episodes", [])),
            "episodic_summaries": len(self.episodic.data.get("summaries", [])),
            "semantic_associations": len(self.semantic.data.get("associations", {})),
            "procedural_patterns": len(self.procedural.data.get("response_patterns", {})),
            "total_messages": self.long.profile.get("total_messages", 0),
            "sessions": self.long.profile.get("total_sessions", 0),
            "user_name": self.long.profile.get("name"),
        }

    def _calc_importance(self, intent, entities):
        score = 0.4
        if intent in ("introduce_name", "express_love", "express_hate",
                       "ask_deep", "ask_dreams", "personal"):
            score += 0.3
        if entities:
            score += 0.1 * min(len(entities), 5)
        return min(1.0, score)

    def save_all(self):
        """Сохраняет все хранилища."""
        self.long.save()
        self.episodic.save()
        self.semantic.save()
        self.procedural.save()
