"""
CoreModel v2 — Среднеуровневая когнитивная модель.
====================================================
Архитектура (7 этапов):
  Sense → Reason → Plan → Execute → Learn → Reflect → Adapt
     ↕        ↕        ↕        ↕        ↕        ↕       ↕
  Ensemble  Chain-of- Dialogue  Engine   Online   Intro-  Personality
  Intent   Thought   Planner   Dispatcher Learning  spect  Dynamics

Компоненты:
  v1 → EnsembleIntentResolver  (regex + TF-IDF + word-assoc + context voting)
  v2 → ReasoningEngine          (chain-of-thought: 4-step internal monologue)
  v3 → DialoguePlanner          (multi-turn goals, topic arc)
  v4 → EngineDispatcher         (6 движков с weighted voting)
  v5 → OnlineLearner            (real-time pattern extraction без feedback)
  v6 → Introspection            (self-evaluation, auto-correction)
  v7 → PersonalityDynamics      (эволюция черт, дрейф настроения, стиль)
  v8 → EpisodicMemory           (важные воспоминания с затуханием)
  v9 → ProactiveEngine          (интересы, своевременные предложения)
"""

import re
import json
import math
import random
import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict, Counter

logger = logging.getLogger("Astra.CoreModel")

from modules.utils import _tokenize, _clamp

def _now_iso() -> str:
    return datetime.datetime.now().isoformat()

def _time_period() -> str:
    h = datetime.datetime.now().hour
    if 5 <= h < 12: return "morning"
    elif 12 <= h < 18: return "afternoon"
    elif 18 <= h < 23: return "evening"
    return "night"


# ═══════════════════════════════════════════════════════════════
# v1 — ENSEMBLE INTENT RESOLVER
# ═══════════════════════════════════════════════════════════════
# Комбинирует: regex, TF-IDF, word-associations, контекст диалога

from modules.intents import INTENT_PATTERNS as INTENT_PATTERNS_V2

_COMMAND_TRIGGERS_V2 = {
    "врем": "time", "часов": "time", "который час": "time",
    "дата": "date", "число": "date", "день недели": "date",
    "погод": "weather", "температур": "weather", "градус": "weather",
    "скриншот": "screenshot", "снимок": "screenshot",
    "систем": "system", "процессор": "system", "память": "system",
    "открой": "open_app", "запусти": "open_app",
    "найди": "web_search", "поищи": "web_search", "погугли": "web_search",
    "заметк": "add_note", "запомни": "add_note", "запиши": "add_note",
    "напомни": "remind",
    "калькулятор": "calc", "посчитай": "calc",
    "переведи": "translate",
    "нарисуй": "generate_image", "сгенерируй": "generate_image",
    "помощь": "help",
    # Ukrainian triggers
    "часу": "time", "годин": "time", "котра година": "time",
    "дат": "date", "числ": "date", "день тижн": "date",
    "погод": "weather", "температур": "weather", "градус": "weather",
    "скріншот": "screenshot", "знімок": "screenshot",
    "систем": "system", "процесор": "system", "пам'ят": "system",
    "відкрий": "open_app", "запусти": "open_app",
    "знайди": "web_search", "пошук": "web_search", "пошукай": "web_search",
    "нотатк": "add_note", "запам'ятай": "add_note", "запиши": "add_note",
    "нагадай": "remind",
    "калькулятор": "calc", "порахуй": "calc",
    "переклади": "translate",
    "намалюй": "generate_image", "згенеруй": "generate_image",
    "допомог": "help",
}

_ENTITY_PATTERNS = {
    "user_name": re.compile(r'(?:меня зовут|my name is|я\s+|звать|называй|можно называти|звати)\s+(\S{2,})', re.IGNORECASE),
    "city": re.compile(r'(?:в |во |на |в городе|из города|у місті|з міста)\s*([А-Яа-яA-Za-z-]{3,})'),
    "like": re.compile(r'(?:люблю|обожаю|мне нравится|увлекаюсь|нравится|подобається|полюбляю)\s+(.+)', re.IGNORECASE),
    "number": re.compile(r'(\d+)'),
    "app": re.compile(r'(браузер|блокнот|калькулятор|проводник|vscode|chrome|cmd|терминал|word|excel)', re.IGNORECASE),
}


class EnsembleIntentResolver:
    """
    Комбинирует три источника для определения интента:
      1. Regex (скорость, точность для известных паттернов)
      2. TF-IDF (семантическая близость для неизвестных фраз)
      3. Контекст (предыдущий интент, тема, сущности)

    Голосование: каждый источник даёт (intent, confidence).
    Итоговый = weighted average.
    """

    WEIGHTS = {"regex": 1.0, "tfidf": 0.6, "context": 0.4}

    def __init__(self):
        self._patterns = [(re.compile(p), name) for p, name in INTENT_PATTERNS_V2]
        self._history_boost = defaultdict(float)  # intent -> boost from past success

    def resolve(self, text: str, context: dict = None, tfidf=None, associator=None) -> dict:
        tl = text.strip()
        if not tl:
            return {"intent": "empty", "confidence": 0.0, "method": "empty", "entities": {}}

        result = {
            "text": tl, "lower": tl.lower(),
            "intent": "unknown", "confidence": 0.0,
            "method": "none", "entities": {},
            "is_question": "?" in tl,
            "is_command": False, "command_type": None,
            "word_count": len(tl.split()), "char_count": len(tl),
            "votes": [],
        }

        # ── 1. Regex голос ──
        regex_vote = self._regex_vote(tl)
        result["votes"].append(("regex", regex_vote[0], regex_vote[1]))

        # ── 2. TF-IDF голос ──
        if tfidf and hasattr(tfidf, "best_intent"):
            try:
                t_intent, t_conf = tfidf.best_intent(tl, threshold=0.2)
                if t_intent and t_conf > 0:
                    result["votes"].append(("tfidf", t_intent, t_conf))
            except Exception:
                pass

        # ── 3. Контекстный голос ──
        if context:
            ctx_vote = self._context_vote(tl, context)
            if ctx_vote[1] > 0:
                result["votes"].append(("context", ctx_vote[0], ctx_vote[1]))

        # ── Взвешенное голосование ──
        vote_tally = defaultdict(float)
        for method, intent, conf in result["votes"]:
            weight = self.WEIGHTS.get(method, 0.5)
            vote_tally[intent] += conf * weight

        if vote_tally:
            best_intent = max(vote_tally, key=vote_tally.get)
            total_weight = sum(self.WEIGHTS.get(m, 0.5) for m, _, _ in result["votes"])
            best_score = vote_tally[best_intent] / total_weight if total_weight > 0 else 0
            best_method = next((m for m, i, _ in result["votes"] if i == best_intent), "regex")
            result["intent"] = best_intent
            result["confidence"] = _clamp(best_score)
            result["method"] = best_method
        else:
            result["intent"] = regex_vote[0]
            result["confidence"] = regex_vote[1]
            result["method"] = "regex"

        # ── Command detection ──
        tl_lower = tl.lower()
        for trigger, cmd in _COMMAND_TRIGGERS_V2.items():
            if trigger in tl_lower:
                result["is_command"] = True
                result["command_type"] = cmd
                break

        # ── Entity extraction ──
        for key, pattern in _ENTITY_PATTERNS.items():
            m = pattern.search(text)
            if m:
                val = m.group(1).strip(".,!? ")[:60]
                if key == "number":
                    try:
                        val = int(val)
                    except ValueError:
                        val = val
                elif key == "user_name":
                    val = val.capitalize()
                result["entities"][key] = val

        return result

    def _regex_vote(self, tl: str) -> Tuple[str, float]:
        best_conf, best_intent = 0.0, "unknown"
        for pattern, intent_name in self._patterns:
            m = pattern.match(tl)
            if m:
                boost = self._history_boost.get(intent_name, 0.0)
                conf = 0.6 + boost
                if m.lastindex and m.lastindex >= 1:
                    conf = 0.9 + boost
                elif len(tl) > 10:
                    conf = 0.75 + boost
                conf = _clamp(conf)
                if conf > best_conf:
                    best_conf, best_intent = conf, intent_name
        return best_intent, best_conf

    def _context_vote(self, tl: str, context: dict) -> Tuple[str, float]:
        last_intent = context.get("last_intent")
        last_topic = context.get("last_topic")
        if not last_intent and not last_topic:
            return "unknown", 0.0

        tl_lower = tl.lower()
        followup_words = {"да", "нет", "ага", "неа", "yes", "no", "ok", "ладно",
                          "понятно", "ясно", "и", "а", "но", "ещё", "еще"}

        if tl_lower in followup_words or any(tl_lower.startswith(w) for w in ["а ", "и ", "но ", "ведь "]):
            if last_intent:
                return last_intent, 0.5
            if last_topic:
                return last_topic, 0.4

        return "unknown", 0.0

    def learn_success(self, intent: str):
        self._history_boost[intent] = _clamp(self._history_boost.get(intent, 0.0) + 0.05)

    def to_dict(self) -> dict:
        return {"history_boost": dict(self._history_boost)}

    def from_dict(self, data: dict):
        self._history_boost = defaultdict(float, data.get("history_boost", {}))


# ═══════════════════════════════════════════════════════════════
#  v2 — REASONING ENGINE (Chain-of-Thought)
# ═══════════════════════════════════════════════════════════════
# 4-step internal monologue перед ответом:
#   Step 1: "Что сказал пользователь?"
#   Step 2: "Что я знаю об этом?"
#   Step 3: "Какой будет лучший ответ?"
#   Step 4: "Как сформулировать с учётом контекста?"

REASONING_STEPS = ["clarify", "recall", "formulate", "refine"]


class ReasoningEngine:
    def __init__(self):
        self.last_reasoning_trace = []
        self.reasoning_depth = 0
        self.confidence_threshold = 0.5

    def reason(self, text: str, intent: str, confidence: float,
               context: dict, memory=None) -> dict:
        self.last_reasoning_trace = []
        reasoning = {
            "original_intent": intent,
            "original_confidence": confidence,
            "refined_intent": intent,
            "refined_confidence": confidence,
            "reasoning_steps": [],
            "needs_clarification": False,
            "suggested_engine": None,
        }

        # Step 1: Clarify — понимаем ли мы запрос?
        self._trace("clarify", f"intent={intent}, conf={confidence:.2f}")
        if confidence < self.confidence_threshold:
            reasoning["needs_clarification"] = True
            reasoning["reasoning_steps"].append({
                "step": "clarify",
                "finding": "low_confidence",
                "action": "use_fallback",
            })
        else:
            reasoning["reasoning_steps"].append({
                "step": "clarify",
                "finding": "clear",
                "action": "proceed",
            })

        # Step 2: Recall — есть ли похожий опыт?
        similar_past = self._recall_similar(text, memory)
        if similar_past:
            reasoning["reasoning_steps"].append({
                "step": "recall",
                "finding": f"found {len(similar_past)} similar past interactions",
                "action": "use_past_pattern",
                "similar": similar_past[:2],
            })
            reasoning["refined_confidence"] = _clamp(confidence + 0.15)
        else:
            reasoning["reasoning_steps"].append({
                "step": "recall",
                "finding": "no similar past",
                "action": "proceed",
            })

        # Step 3: Formulate — какой движок подойдёт?
        engine_choice = self._choose_engine(intent, confidence, context)
        self._trace("formulate", f"engine={engine_choice}")
        reasoning["suggested_engine"] = engine_choice
        reasoning["reasoning_steps"].append({
            "step": "formulate",
            "engine_choice": engine_choice,
        })

        # Step 4: Refine — уточняем уверенность
        if context:
            turn_count = context.get("turn_count", 0)
            if turn_count > 5 and confidence > 0.3:
                reasoning["refined_confidence"] = _clamp(reasoning.get("refined_confidence", confidence) + 0.1)
                self._trace("refine", f"long conversation boost → {reasoning['refined_confidence']:.2f}")
                reasoning["reasoning_steps"].append({
                    "step": "refine",
                    "finding": "long conversation boost",
                    "new_confidence": reasoning["refined_confidence"],
                })

        self.reasoning_depth += 1
        reasoning["trace"] = list(self.last_reasoning_trace)
        return reasoning

    def _trace(self, step: str, msg: str):
        entry = f"[{step.upper()}] {msg}"
        self.last_reasoning_trace.append(entry)

    def _recall_similar(self, text: str, memory) -> List[str]:
        """Ищет похожие прошлые взаимодействия по ключевым словам."""
        if not memory:
            return []
        words = _tokenize(text)
        if not words:
            return []
        past = getattr(memory, "short_term", [])
        similar = []
        for entry in past[-20:]:
            past_text = entry.get("text", "")
            past_words = _tokenize(past_text)
            if past_words:
                overlap = len(set(words) & set(past_words))
                if overlap >= 2:
                    similar.append(past_text[:80])
        return similar

    def _choose_engine(self, intent: str, confidence: float, context: dict) -> str:
        if confidence >= 0.65:
            return "chat"
        if confidence >= 0.4:
            return "semantic"
        return "fallback"

    def get_trace_str(self) -> str:
        return "\n".join(self.last_reasoning_trace[-20:])

    def to_dict(self) -> dict:
        return {"reasoning_depth": self.reasoning_depth}

    def from_dict(self, data: dict):
        self.reasoning_depth = data.get("reasoning_depth", 0)


# ═══════════════════════════════════════════════════════════════
#  v3 — DIALOGUE PLANNER
# ═══════════════════════════════════════════════════════════════
# Многошаговое планирование: определяет цель диалога,
# отслеживает дугу разговора, предлагает следующие шаги.

GOAL_TYPES = ["inform", "entertain", "assist", "empathize", "explore", "none"]


class DialoguePlanner:
    def __init__(self):
        self.current_goal = "none"
        self.goal_history = []
        self.topic_sequence = []
        self.turn_count = 0
        self.user_engagement = 0.5
        self.last_goal_change = datetime.datetime.min

    def plan(self, intent: str, confidence: float, text: str, user_profile: dict = None) -> dict:
        self.turn_count += 1
        self.topic_sequence.append(intent)
        if len(self.topic_sequence) > 30:
            self.topic_sequence.pop(0)

        # Определяем цель диалога
        new_goal = self._infer_goal(intent, text)
        if new_goal != self.current_goal and len(self.goal_history) < self.turn_count:
            self.goal_history.append((self.current_goal, _now_iso()))
            self.current_goal = new_goal

        plan = {
            "goal": self.current_goal,
            "turn": self.turn_count,
            "engagement": self.user_engagement,
            "topics_covered": list(set(self.topic_sequence[-10:])),
            "suggest_proactive": self._should_be_proactive(),
            "suggest_topic_change": self._should_change_topic(),
            "response_style": self._choose_style(intent, user_profile),
        }
        return plan

    def _infer_goal(self, intent: str, text: str) -> str:
        if intent in ("ask_joke", "ask_story", "ask_poem"):
            return "entertain"
        if intent in ("ask_advice", "help", "ask_time", "ask_date"):
            return "assist"
        if intent in ("express_negative", "express_hate"):
            return "empathize"
        if intent in ("ask_why", "ask_deep", "ask_dreams", "ask_who", "ask_what"):
            return "explore"
        if intent in ("greeting", "ask_state", "express_positive"):
            return "inform"
        return self.current_goal if self.current_goal != "none" else "inform"

    def _should_be_proactive(self) -> bool:
        if self.turn_count < 3:
            return False
        if self.turn_count >= 5 and self.turn_count % 5 == 0 and self.user_engagement > 0.4:
            return True
        recent = self.topic_sequence[-4:]
        unknown_count = sum(1 for t in recent if t == "unknown")
        return unknown_count >= 3

    def _should_change_topic(self) -> bool:
        if len(self.topic_sequence) < 6:
            return False
        recent = self.topic_sequence[-4:]
        unique = len(set(recent))
        return unique <= 2

    def _choose_style(self, intent: str, profile: dict = None) -> str:
        casual_intents = {"greeting", "ask_state", "ask_joke", "ask_story",
                          "express_positive", "short_agreement"}
        formal_intents = {"help", "ask_time", "ask_date"}
        if profile:
            style = profile.get("communication_style", "casual")
            return style
        if intent in casual_intents:
            return "casual"
        if intent in formal_intents:
            return "brief"
        return "casual"

    def set_engagement(self, value: float):
        self.user_engagement = _clamp(value)

    def to_dict(self) -> dict:
        return {
            "current_goal": self.current_goal,
            "turn_count": self.turn_count,
            "user_engagement": self.user_engagement,
        }

    def from_dict(self, data: dict):
        self.current_goal = data.get("current_goal", "none")
        self.turn_count = data.get("turn_count", 0)
        self.user_engagement = data.get("user_engagement", 0.5)


# ═══════════════════════════════════════════════════════════════
#  v4 — ENGINE DISPATCHER
# ═══════════════════════════════════════════════════════════════
# Weighted voting между движками с учётом уверенности.

ENGINE_WEIGHTS = {
    "command": 1.0, "chat": 0.6,
    "creative": 0.55, "semantic": 0.4, "fallback": 0.3,
}


class EngineDispatcher:
    def __init__(self, core_model):
        self.core = core_model
        self.last_engine_used = None
        self.engine_success_rate = defaultdict(lambda: 0.5)

    def dispatch(self, plan: dict, perception: dict) -> Tuple[str, str]:
        intent = plan.get("intent") or perception["intent"]
        text = perception["text"]
        reasoning = plan.get("reasoning", {})

        preferred = reasoning.get("suggested_engine", plan.get("engine", "fallback"))
        fallback_chain = plan.get("fallback_chain", ["fallback"])

        engines_to_try = [preferred] + [e for e in fallback_chain if e != preferred]

        for eng in engines_to_try:
            score = self._score_engine(eng, intent, perception)
            if score < 0.2:
                continue
            try:
                result = self._call(eng, text, intent, perception)
                if result and len(result.strip()) > 2 and result != "__IMAGE_ERROR__":
                    self.last_engine_used = eng
                    self.engine_success_rate[eng] = _clamp(self.engine_success_rate[eng] + 0.05)
                    return result, eng
            except Exception as e:
                logger.warning("Engine %s error: %s", eng, e)
                self.engine_success_rate[eng] = _clamp(self.engine_success_rate[eng] - 0.05)
                continue

        return self._fallback(), "fallback"

    def _score_engine(self, engine: str, intent: str, perception: dict) -> float:
        base = ENGINE_WEIGHTS.get(engine, 0.3)
        success = self.engine_success_rate.get(engine, 0.5)
        return base * success

    def _call(self, engine: str, text: str, intent: str, perception: dict) -> Optional[str]:
        core = self.core

        if engine == "command":
            return self._call_command(perception)

        if engine == "chat":
            if hasattr(core, "chat") and core.chat:
                return core.chat.respond(text)
            return None

        if engine == "creative":
            if hasattr(core, "chat") and core.chat:
                return core.chat.response_gen.generate_creative(intent)
            return None

        if engine == "semantic":
            return self._call_semantic(text)

        return None

    def _call_command(self, perception: dict) -> Optional[str]:
        cmd = perception.get("command_type")
        if not cmd:
            return None
        ast = getattr(self.core, "_assistant", None)
        if not ast:
            return None

        cmds = {
            "time": "_do_time", "date": "_do_date",
            "weather": "_do_weather", "screenshot": "_do_screenshot",
            "system": "_do_system", "open_app": "_do_open",
            "web_search": "_do_search", "add_note": "_do_add_note",
            "remind": "_do_reminder", "calc": "_do_calc",
            "translate": "_do_translate", "generate_image": "_do_generate_image",
            "help": "_do_help",
        }
        method_name = cmds.get(cmd)
        if not method_name:
            return None
        method = getattr(ast, method_name, None)
        if not method:
            return None

        if cmd == "weather":
            city = perception["entities"].get("city", "Київ")
            return str(method(city))
        if cmd == "open_app":
            app = perception["entities"].get("app", "")
            return str(method(app))
        if cmd == "remind":
            return str(method(text, 5))
        return str(method())

    def _call_semantic(self, text: str) -> Optional[str]:
        core = self.core
        if not hasattr(core, "chat") or not core.chat:
            return None
        chat = core.chat

        if chat._semantic:
            semantic_intent, _ = chat.tfidf.best_intent(text, threshold=0.2)
            if semantic_intent and semantic_intent != "unknown":
                return chat.response_gen.generate(
                    semantic_intent,
                    {"intent": semantic_intent, "text": text, "params": {}, "confidence": 0.6},
                    chat.state_machine,
                )
            if random.random() < 0.3:
                seed = _tokenize(text)
                if seed:
                    markov_resp = chat.markov.generate(seed[:3], max_words=15)
                    if markov_resp and len(markov_resp) > 10:
                        return markov_resp.capitalize() + "."
        return None

    def _fallback(self) -> str:
        fallbacks = [
            "Розкажи детальніше, я слухаю.",
            "Цікаво. А що ти сам думаєш про це?",
            "Продовжуй, я уважно слухаю.",
            "Хм, я хочу зрозуміти тебе краще. Розкажи ще.",
            "Я вся увага! Що привело тебе до цієї думки?",
        ]
        return random.choice(fallbacks)

    def record_feedback(self, engine: str, success: bool):
        delta = 0.05 if success else -0.05
        self.engine_success_rate[engine] = _clamp(self.engine_success_rate.get(engine, 0.5) + delta)

    def to_dict(self) -> dict:
        return {"engine_success_rate": dict(self.engine_success_rate)}

    def from_dict(self, data: dict):
        self.engine_success_rate = defaultdict(lambda: 0.5, data.get("engine_success_rate", {}))


# ═══════════════════════════════════════════════════════════════
#  v5 — ONLINE LEARNER (расширенный)
# ═══════════════════════════════════════════════════════════════
# Извлекает паттерны, стиль общения, предпочтения, факты.
# Обучается на каждом сообщении в реальном времени.

class OnlineLearner:
    def __init__(self):
        self.user_word_freq = Counter()
        self.intent_word_map = defaultdict(lambda: Counter())
        self.pattern_success = defaultdict(float)
        self.discovered_patterns = []
        self.session_new_words = set()
        self._bigram_freq = Counter()         # частотность биграмм
        self._user_style = defaultdict(float)  # стиль: краткость, эмоции, темы
        self._preferred_topics = Counter()     # любимые темы
        self._known_facts = {}                 # извлечённые факты
        self._session_count = 0

    def learn_from_message(self, text: str, intent: str, confidence: float):
        self._session_count += 1
        words = _tokenize(text)
        for w in words:
            self.user_word_freq[w] += 1
            self.intent_word_map[intent][w] += 1

        # Discovering new user-specific vocabulary
        for w in words:
            if self.user_word_freq[w] <= 2:
                self.session_new_words.add(w)

        # Track pattern success
        if confidence > 0.7:
            self.pattern_success[intent] = _clamp(self.pattern_success[intent] + 0.1)

        # Биграммы — стиль письма
        for i in range(len(words) - 1):
            self._bigram_freq[f"{words[i]} {words[i+1]}"] += 1

        # Стиль: длина сообщения
        avg_len = self._user_style.get("avg_length", 5)
        self._user_style["avg_length"] = avg_len * 0.9 + len(words) * 0.1

        # Стиль: эмоциональность (восклицания)
        if "!" in text:
            self._user_style["emotion_level"] = _clamp(self._user_style.get("emotion_level", 0.5) + 0.05)
        if "?" in text:
            self._user_style["curiosity"] = _clamp(self._user_style.get("curiosity", 0.5) + 0.05)

        # Извлечение фактов
        self._extract_facts(text, words)

    def _extract_facts(self, text, words):
        """Извлекает факты из сообщений."""
        # "меня зовут X"
        m = re.search(r'(?:меня\s+зовут|my\s+name\s+is|i\'?m\s+)\s*(\w+)', text, re.IGNORECASE)
        if m:
            self._known_facts["user_name"] = m.group(1)

        # "я из X" / "я живу в X"
        m = re.search(r'(?:я\s+(?:из|живу\s+в)\s+|i\s+(?:am\s+from|live\s+in)\s+)(\w+)', text, re.IGNORECASE)
        if m:
            self._known_facts["user_city"] = m.group(1)

        # "мне X лет"
        m = re.search(r'(?:мне\s+)(\d+)(?:\s+лет)', text, re.IGNORECASE)
        if m:
            self._known_facts["user_age"] = m.group(1)

        # Предпочтения
        like_patterns = [
            (r'(?:я\s+(?:люблю|обожаю|нравится)\s+)(.+)', "likes"),
            (r'(?:i\s+(?:like|love|enjoy)\s+)(.+)', "likes"),
            (r'(?:не\s+(?:люблю|ненавижу|терпеть\s+не\s+могу)\s+)(.+)', "dislikes"),
        ]
        for pattern, key in like_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                topic = m.group(1).strip().rstrip(".!").strip()
                self._known_facts[key] = topic
                self._preferred_topics[topic] += 1

    def learn_from_feedback(self, text: str, was_positive: bool):
        words = _tokenize(text)
        for w in words:
            if was_positive:
                self.pattern_success[w] = _clamp(self.pattern_success.get(w, 0.5) + 0.1)
            else:
                self.pattern_success[w] = _clamp(self.pattern_success.get(w, 0.5) - 0.05)

    def get_new_words(self) -> List[str]:
        words = list(self.session_new_words)
        self.session_new_words.clear()
        return words

    def get_frequent_words(self, min_freq: int = 3) -> Dict[str, int]:
        return {w: c for w, c in self.user_word_freq.items() if c >= min_freq}

    def get_top_words_for_intent(self, intent: str, top_n: int = 10) -> List[str]:
        return [w for w, _ in self.intent_word_map[intent].most_common(top_n)]

    def get_user_summary(self) -> dict:
        """Краткая сводка о пользователе (для персонализации)."""
        return {
            "session_count": self._session_count,
            "vocabulary_size": len(self.user_word_freq),
            "avg_length": round(self._user_style.get("avg_length", 5), 1),
            "emotion_level": round(self._user_style.get("emotion_level", 0.5), 2),
            "curiosity": round(self._user_style.get("curiosity", 0.5), 2),
            "facts": dict(self._known_facts),
            "top_topics": [t for t, _ in self._preferred_topics.most_common(5)],
            "top_words": [w for w, _ in self.user_word_freq.most_common(10)],
        }

    def to_dict(self) -> dict:
        return {
            "user_word_freq": dict(self.user_word_freq.most_common(200)),
            "intent_word_map": {k: dict(v.most_common(50)) for k, v in self.intent_word_map.items()},
            "pattern_success": dict(self.pattern_success),
            "bigram_freq": dict(self._bigram_freq.most_common(100)),
            "user_style": dict(self._user_style),
            "preferred_topics": dict(self._preferred_topics.most_common(20)),
            "known_facts": self._known_facts,
            "session_count": self._session_count,
        }

    def from_dict(self, data: dict):
        self.user_word_freq = Counter(data.get("user_word_freq", {}))
        self.intent_word_map = defaultdict(
            lambda: Counter(),
            {k: Counter(v) for k, v in data.get("intent_word_map", {}).items()}
        )
        self.pattern_success = defaultdict(float, data.get("pattern_success", {}))
        self._bigram_freq = Counter(data.get("bigram_freq", {}))
        self._user_style = defaultdict(float, data.get("user_style", {}))
        self._preferred_topics = Counter(data.get("preferred_topics", {}))
        self._known_facts = data.get("known_facts", {})
        self._session_count = data.get("session_count", 0)


# ═══════════════════════════════════════════════════════════════
#  v6 — INTROSPECTION
# ═══════════════════════════════════════════════════════════════
# Самооценка качества ответов и автоматическая коррекция.

class Introspection:
    def __init__(self):
        self.response_quality = []  # list of scores
        self.last_self_eval = None
        self.correction_count = 0
        self.consecutive_bad = 0

    def evaluate(self, response: str, perception: dict, plan: dict) -> dict:
        score = 0.5
        reasons = []

        # Too short responses are bad
        if len(response) < 10:
            score -= 0.2
            reasons.append("too_short")
        elif len(response) > 200:
            score -= 0.1
            reasons.append("too_long")

        # Repetitive responses
        if self.response_quality:
            last_responses = [r[0] for r in self.response_quality[-5:]]
            if response in last_responses:
                score -= 0.15
                reasons.append("repetitive")

        # Unknown intent with short response
        if perception["intent"] == "unknown" and len(response) < 30:
            score -= 0.2
            reasons.append("unknown_with_short_response")

        # Falls through multiple engines is bad
        if plan.get("engine") == "fallback":
            score -= 0.3
            reasons.append("fallback_used")

        score = _clamp(score)
        self.response_quality.append((response, score, _now_iso()))
        if len(self.response_quality) > 50:
            self.response_quality.pop(0)

        self.last_self_eval = {
            "score": score,
            "reasons": reasons,
            "needs_correction": score < 0.3,
        }

        if score < 0.3:
            self.consecutive_bad += 1
        else:
            self.consecutive_bad = 0

        return self.last_self_eval

    def get_correction(self, original_response: str, perception: dict) -> Optional[str]:
        if self.consecutive_bad < 2:
            return None
        self.correction_count += 1
        self.consecutive_bad = 0
        corrections = [
            "Вибач, давай спробуємо інакше. Що ти мав на увазі?",
            "Здається, я не зовсім зрозуміла. Можеш переформулювати?",
            "Давай по-іншому. Розкажи детальніше, що тебе цікавить.",
            "Хм, я, здається, помилилася. Спробуємо ще раз?",
        ]
        return random.choice(corrections)

    def get_average_quality(self) -> float:
        if not self.response_quality:
            return 0.5
        recent = [s for _, s, _ in self.response_quality[-20:]]
        return sum(recent) / len(recent)

    def to_dict(self) -> dict:
        return {
            "correction_count": self.correction_count,
            "consecutive_bad": self.consecutive_bad,
        }

    def from_dict(self, data: dict):
        self.correction_count = data.get("correction_count", 0)
        self.consecutive_bad = data.get("consecutive_bad", 0)


# ═══════════════════════════════════════════════════════════════
#  v7 — PERSONALITY DYNAMICS
# ═══════════════════════════════════════════════════════════════
# Черты личности эволюционируют: дрейфуют к стилю пользователя,
# меняются в зависимости от времени суток, настроения.

TRAIT_DEFAULTS = {
    "warmth": 0.75, "humor": 0.65, "empathy": 0.8,
    "curiosity": 0.75, "formality": 0.2, "creativity": 0.7,
    "patience": 0.85, "playfulness": 0.65, "enthusiasm": 0.7,
}

TRAIT_MIRROR_RATE = 0.02  # скорость подстройки под пользователя
TRAIT_DRIFT_RATE = 0.005  # скорость возврата к базе
MOOD_DECAY = 0.92         # затухание настроения между циклами

MOODS = {
    "cheerful": {"warmth": 0.12, "humor": 0.1, "playfulness": 0.15, "enthusiasm": 0.1},
    "thoughtful": {"curiosity": 0.12, "creativity": 0.1, "formality": 0.05},
    "playful": {"playfulness": 0.2, "humor": 0.15, "warmth": 0.1, "enthusiasm": 0.1},
    "supportive": {"empathy": 0.15, "warmth": 0.15, "patience": 0.1},
    "serious": {"formality": 0.15, "empathy": 0.1, "humor": -0.15, "playfulness": -0.15},
    "neutral": {},
}

MOOD_TRIGGERS_V2 = {
    "express_negative": "supportive", "express_hate": "supportive",
    "express_positive": "cheerful", "express_love": "cheerful",
    "greeting": "cheerful", "thanks": "cheerful",
    "ask_why": "thoughtful", "ask_deep": "thoughtful", "ask_dreams": "thoughtful",
    "ask_joke": "playful", "ask_story": "playful", "ask_poem": "playful",
    "disagree": "thoughtful", "apology": "supportive", "farewell": "serious",
}


class PersonalityDynamics:
    def __init__(self):
        self.traits = dict(TRAIT_DEFAULTS)
        self.mood = "neutral"
        self.style = {
            "use_emojis": True, "sentence_length": "medium",
            "enthusiasm_level": 0.7, "formality_level": 0.2,
        }
        self.user_style_estimate = {"verbosity": "medium", "formality": 0.3}
        self.mood_history = []
        self._last_update = datetime.datetime.now()

    def update(self, intent: str, user_text: str):
        # Mood trigger
        new_mood = MOOD_TRIGGERS_V2.get(intent, "neutral")
        if new_mood != self.mood:
            self.mood = new_mood
            self.mood_history.append((new_mood, _now_iso()))
            if len(self.mood_history) > 20:
                self.mood_history.pop(0)

        # Apply mood effects
        mood_effect = MOODS.get(self.mood, {})
        for trait, delta in mood_effect.items():
            if trait in self.traits:
                self.traits[trait] = _clamp(self.traits[trait] + delta)

        # Mirror user style
        words = user_text.split()
        avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
        if avg_word_len > 7:
            self.user_style_estimate["verbosity"] = "formal"
        elif len(user_text) > 100:
            self.user_style_estimate["verbosity"] = "detailed"
        elif len(user_text) < 20:
            self.user_style_estimate["verbosity"] = "brief"
        else:
            self.user_style_estimate["verbosity"] = "medium"

        # Drift style toward user
        if self.user_style_estimate["verbosity"] == "formal" and self.traits["formality"] < 0.5:
            self.traits["formality"] = _clamp(self.traits["formality"] + TRAIT_MIRROR_RATE)
        if self.user_style_estimate["verbosity"] == "brief" and self.traits["warmth"] > 0.3:
            self.traits["warmth"] = _clamp(self.traits["warmth"] - TRAIT_MIRROR_RATE)

        # Decay toward defaults
        now = datetime.datetime.now()
        elapsed_hours = (now - self._last_update).total_seconds() / 3600
        if elapsed_hours > 1:
            for k, v in TRAIT_DEFAULTS.items():
                self.traits[k] = _clamp(self.traits[k] + (v - self.traits[k]) * TRAIT_DRIFT_RATE * elapsed_hours)
        self._last_update = now

        # Update style
        self.style["enthusiasm_level"] = self.traits["enthusiasm"]
        self.style["formality_level"] = self.traits["formality"]

    def should_use_emoji(self) -> bool:
        return self.style["use_emojis"] and random.random() < self.traits["warmth"]

    def get_mood_report(self) -> str:
        if not self.mood_history:
            return "нейтральне"
        dominant = max(set(self.mood_history), key=self.mood_history.count)
        names = {"cheerful": "веселе", "thoughtful": "задумливе", "playful": "грайливе",
                 "supportive": "підтримуюче", "serious": "серйозне", "neutral": "нейтральне"}
        return names.get(dominant, "нейтральне")

    def to_dict(self) -> dict:
        return {
            "traits": self.traits,
            "mood": self.mood,
            "style": self.style,
            "user_style_estimate": self.user_style_estimate,
        }

    def from_dict(self, data: dict):
        if data:
            self.traits.update(data.get("traits", {}))
            self.mood = data.get("mood", "neutral")
            self.style.update(data.get("style", {}))
            self.user_style_estimate.update(data.get("user_style_estimate", {}))


# ═══════════════════════════════════════════════════════════════
#  v8 — EPISODIC MEMORY
# ═══════════════════════════════════════════════════════════════
# Важные воспоминания с оценкой важности и затуханием.

IMPORTANCE_BOOST = {"user_name": 1.0, "like": 0.8, "hobby": 0.7, "fact": 0.6}
DECAY_PER_TURN = 0.01
CONSOLIDATION_INTERVAL = 10


class EpisodicMemory:
    def __init__(self):
        self.episodes = []       # List[Dict] с важностью
        self.consolidated = []   # Важные, сохранённые навсегда
        self._turn_counter = 0

    def remember(self, role: str, text: str, intent: str, entities: dict):
        importance = self._calc_importance(text, intent, entities)

        self.episodes.append({
            "role": role, "text": text, "intent": intent,
            "entities": entities, "importance": importance,
            "age": 0, "time": _now_iso(),
        })

        # Keep only top-N by importance
        self.episodes.sort(key=lambda x: -x["importance"])
        if len(self.episodes) > 30:
            self.episodes = self.episodes[:30]

        # Periodic consolidation
        self._turn_counter += 1
        if self._turn_counter % CONSOLIDATION_INTERVAL == 0:
            self._consolidate()

    def _calc_importance(self, text: str, intent: str, entities: dict) -> float:
        score = 0.3
        if intent in ("introduce_name", "express_love", "express_hate",
                       "ask_deep", "ask_dreams"):
            score += 0.3
        for key in entities:
            score += IMPORTANCE_BOOST.get(key, 0.1)
        words = text.split()
        if len(words) > 15:
            score += 0.1
        return _clamp(score)

    def _consolidate(self):
        """Переносит важные эпизоды в долговременную память."""
        important = [e for e in self.episodes if e["importance"] >= 0.7]
        for ep in important:
            # Avoid duplicates
            if not any(c["text"] == ep["text"] for c in self.consolidated):
                self.consolidated.append(ep)
        self.consolidated = self.consolidated[-50:]

    def decay(self):
        """Экспоненциальное затухание: старые воспоминания теряют важность."""
        for ep in self.episodes:
            ep["age"] += 1
            ep["importance"] = _clamp(ep["importance"] * 0.99)
        # Remove forgotten
        self.episodes = [e for e in self.episodes if e["importance"] > 0.2]

    def recall(self, query: str = "", top_n: int = 5) -> List[dict]:
        if not query:
            return self.episodes[:top_n]
        words = _tokenize(query.lower())
        if not words:
            return self.episodes[:top_n]

        scored = []
        for ep in self.episodes + self.consolidated:
            ep_words = _tokenize(ep["text"].lower())
            overlap = len(set(words) & set(ep_words))
            score = ep["importance"] + (overlap * 0.1)
            scored.append((score, ep))

        scored.sort(key=lambda x: -x[0])
        return [ep for _, ep in scored[:top_n]]

    def get_facts(self) -> List[str]:
        facts = []
        for ep in self.consolidated:
            for key, val in ep.get("entities", {}).items():
                if key in ("user_name", "like", "hobby", "city"):
                    facts.append(f"{key}={val}")
        return list(set(facts))

    def get_emotion_context(self, n: int = 5) -> List[str]:
        emotional = [e["text"] for e in (self.episodes + self.consolidated)
                     if e["intent"] in ("express_negative", "express_positive",
                                        "express_love", "express_hate")]
        return emotional[-n:]

    def to_dict(self) -> dict:
        return {
            "consolidated": self.consolidated,
            "_turn_counter": self._turn_counter,
        }

    def from_dict(self, data: dict):
        self.consolidated = data.get("consolidated", [])
        self._turn_counter = data.get("_turn_counter", 0)


# ═══════════════════════════════════════════════════════════════
#  v9 — PROACTIVE ENGINE
# ═══════════════════════════════════════════════════════════════
# Отслеживает интересы пользователя и инициирует темы.

class ProactiveEngine:
    def __init__(self):
        self.interest_scores = defaultdict(float)
        self.suggested_topics = []
        self.last_proactive_time = datetime.datetime.min
        self.proactive_cooldown_min = 3
        self.session_stats = {"topics_initiated": 0, "questions_asked": 0}

    def observe(self, intent: str, text: str):
        # Увеличиваем интерес к темам, которые пользователь сам поднимает
        if intent.startswith("topic_"):
            self.interest_scores[intent] = _clamp(self.interest_scores[intent] + 0.15)
        # Интерес к тому, о чём пользователь спрашивает
        if "?" in text:
            self.session_stats["questions_asked"] += 1
        # Если пользователь спрашивает "а ещё" — повышаем любопытство
        if intent == "ask_more":
            for topic in list(self.interest_scores.keys()):
                self.interest_scores[topic] = _clamp(self.interest_scores[topic] + 0.05)

    def decay_interests(self):
        for k in list(self.interest_scores.keys()):
            self.interest_scores[k] = _clamp(self.interest_scores[k] - 0.01)
            if self.interest_scores[k] < 0.05:
                del self.interest_scores[k]

    def should_suggest(self, turn_count: int, engagement: float) -> bool:
        now = datetime.datetime.now()
        elapsed = (now - self.last_proactive_time).total_seconds() / 60
        if elapsed < self.proactive_cooldown_min:
            return False
        if turn_count < 4:
            return False
        if engagement < 0.3:
            return False
        # Не предлагать слишком часто
        if self.session_stats["topics_initiated"] > 3:
            return False
        return True

    def get_suggestion(self, turn_count: int) -> Optional[str]:
        self.last_proactive_time = datetime.datetime.now()
        self.session_stats["topics_initiated"] += 1

        # Предложить тему, если есть интересы
        if self.interest_scores:
            best_topic = max(self.interest_scores, key=self.interest_scores.get)
            if self.interest_scores[best_topic] > 0.3:
                self.session_stats["topics_initiated"] += 1
                return self._topic_to_question(best_topic)

        # Универсальные предложения в зависимости от времени суток
        period = _time_period()
        time_suggestions = {
            "morning": ["Що плануєш робити сьогодні?", "Як спалося?"],
            "afternoon": ["Як проходить день?", "Вже пообідав?"],
            "evening": ["Як пройшов день?", "Є плани на вечір?"],
            "night": ["Не спиться? Хочеш поговорити про щось?"],
        }
        if turn_count > 10:
            suggestions = time_suggestions.get(period, time_suggestions["afternoon"])
            return random.choice(suggestions)

        return None

    def _topic_to_question(self, topic: str) -> str:
        questions = {
            "topic_programming": "До речі, ти нещодавно говорив про програмування. Є нові проєкти?",
            "topic_music": "Слухаєш щось нове останнім часом?",
            "topic_movies": "Не дивився нічого цікавого останнім часом?",
            "topic_books": "Читаєш зараз щось?",
            "topic_games": "У що граєш зараз?",
            "topic_sport": "Як успіхи у спорті?",
            "topic_food": "Відкрив для себе щось смачне?",
            "topic_travel": "Куди мрієш поїхати наступного разу?",
            "topic_work": "Як справи на роботі?",
            "topic_study": "Як навчання просувається?",
            "topic_health": "Як самопочуття?",
        }

        return questions.get(topic, "Розкажи, що нового в цій темі?")

    def to_dict(self) -> dict:
        return {
            "interest_scores": dict(self.interest_scores),
            "session_stats": self.session_stats,
        }

    def from_dict(self, data: dict):
        self.interest_scores = defaultdict(float, data.get("interest_scores", {}))
        self.session_stats.update(data.get("session_stats", {}))


# ═══════════════════════════════════════════════════════════════
#  CORE MODEL v2 — ГЛАВНЫЙ КЛАСС
# ═══════════════════════════════════════════════════════════════

class CoreModel:
    """
    CoreModel v2 — Среднеуровневая когнитивная модель.

    7-этапный конвейер:
      Sense → Reason → Plan → Execute → Learn → Reflect → Adapt

    9 когнитивных компонентов:
      v1 EnsembleIntentResolver — комбинированный анализ намерений
      v2 ReasoningEngine — цепочка рассуждений (Chain-of-Thought)
      v3 DialoguePlanner — многошаговое планирование диалога
      v4 EngineDispatcher — взвешенный выбор движка
      v5 OnlineLearner — обучение в реальном времени
      v6 Introspection — самооценка и коррекция
      v7 PersonalityDynamics — эволюция личности
      v8 EpisodicMemory — эпизодическая память
      v9 ProactiveEngine — проактивное вовлечение
    """

    MODEL_VERSION = "2.0.0"
    MODEL_NAME = "Astra Core v2"

    def __init__(self, assistant=None):
        self._assistant = assistant
        self.created = datetime.datetime.now()
        self.version = self.MODEL_VERSION

        # Внешние подсистемы
        self.chat = None
        self.caps = None
        self.thinker = None
        self.emotion = None
        self.knowledge = None

        # Когнитивные компоненты v2
        self.intent_resolver = EnsembleIntentResolver()
        self.reasoning = ReasoningEngine()
        self.planner = DialoguePlanner()
        self.dispatcher = EngineDispatcher(self)
        self.learner = OnlineLearner()
        self.introspect = Introspection()
        self.personality = PersonalityDynamics()
        self.memory = EpisodicMemory()
        self.proactive = ProactiveEngine()

        # Состояние
        self.last_response = None
        self.last_plan = None
        self.total_cycles = 0
        self.consecutive_unknown = 0
        self._last_state_save = datetime.datetime.now()

        logger.info("CoreModel v%s инициализирована (%d компонентов)",
                     self.MODEL_VERSION, 9)

    # ── ИНИЦИАЛИЗАЦИЯ ──

    def init_from_assistant(self, assistant):
        self._assistant = assistant
        for attr, name in [("chat", "ChatEngine"), ("caps", "CapsAlgorithm"),
                           ("thinker", "ThinkingEngineV2"), ("emotion", "EmotionEngine"),
                           ("knowledge", "KnowledgeGraph")]:
            if hasattr(assistant, attr):
                setattr(self, attr, getattr(assistant, attr))
                logger.info("CoreModel: %s подключён", name)
        # Если старый ThinkingEngine — заменяем на v2
        if self.thinker and not hasattr(self.thinker, '_reason_chain'):
            try:
                from modules.thinking_engine import ThinkingEngineV2
                self.thinker = ThinkingEngineV2()
                logger.info("CoreModel: ThinkingEngine обновлён до v2")
            except Exception as e:
                logger.warning("CoreModel: upgrade thinker: %s", e)

    def init_chat_engine(self):
        if self.chat:
            return
        try:
            from modules.chat_engine import ChatEngine
            self.chat = ChatEngine(self._assistant)
            logger.info("CoreModel: ChatEngine создан")
        except Exception as e:
            logger.error("CoreModel: ChatEngine creation failed: %s", e)

    # ── ГЛАВНЫЙ ЦИКЛ (7 этапов) ──

    def process(self, text: str) -> str:
        logger.debug("CoreModel.process: entry text=%r", text[:80])
        if not text or not text.strip():
            return "Напиши щось, я слухаю!"

        self.total_cycles += 1
        start_time = datetime.datetime.now()

        # EXIT check
        if text.strip().lower() in ("пока", "до свидания", "выйти", "exit", "quit",
                                      "закрой", "стоп", "stop", "хватит", "завершить", "отбой"):
            return "__EXIT__"

        # Image extension filter
        _IMG_EXTS_PATTERN = re.compile(r'\.(png|jpg|jpeg|gif|bmp|webp|ico|svg)\b', re.IGNORECASE)
        if _IMG_EXTS_PATTERN.search(text):
            return "Я — текстова модель і не бачу зображень. Опиши словами ✨"

        # Ensure ChatEngine is available
        self.init_chat_engine()
        logger.debug("CoreModel.process: chat=%s", self.chat is not None)

        # Fast path: simple greetings & small talk
        tl = text.strip().lower()
        if tl in ("привет", "здравствуй", "хай", "hello", "hi", "добрый день", "доброе утро", "добрый вечер"):
            return random.choice(["Привет!", "Здравствуй!", "Хай!", "Приветствую!"])
        if tl in ("как дела", "как ты", "what's up", "how are you", "дела"):
            return random.choice(["Отлично! Чем помочь?", "Всё хорошо!", "Работаю, спрашивай!"])
        if tl in ("кто ты", "что ты", "who are you"):
            return "Я Astra AI — твой голосовой ассистент."

        # ═══ STAGE 1: SENSE (с мышлением) ═══
        try:
            context_in = {
                "last_intent": self.planner.current_goal if self.planner.current_goal != "none" else None,
                "last_topic": self.planner.topic_sequence[-1] if self.planner.topic_sequence else None,
                "turn_count": self.planner.turn_count,
            }
            tfidf = getattr(self.chat, "tfidf", None) if self.chat else None
            associator = getattr(self.chat, "associator", None) if self.chat else None
            perception = self.intent_resolver.resolve(text, context_in, tfidf, associator)

            if self.emotion and hasattr(self.emotion, "analyze"):
                try:
                    perception["emotion"] = self.emotion.analyze(text)
                except Exception:
                    pass

            # ThinkingEngine v2 — глубокий анализ
            if self.thinker and hasattr(self.thinker, "think"):
                try:
                    thought = self.thinker.think(text)
                    perception["thought"] = thought
                    perception["confidence"] = thought.get("confidence", perception["confidence"])
                    # Извлечённые факты
                    if thought.get("context", {}).get("user_name"):
                        context_in["user_name"] = thought["context"]["user_name"]
                except Exception as e:
                    logger.debug("Thinker v2: %s", e)
        except Exception as e:
            logger.warning("Sense stage failed: %s", e)
            perception = {"intent": "unknown", "confidence": 0.0, "is_command": False,
                          "lower": text.lower(), "entities": {}, "emotion": None}

        # ═══ STAGE 2: REASON ═══
        try:
            reasoning = self.reasoning.reason(
                text, perception["intent"], perception["confidence"],
                context_in, self.memory,
            )
            perception["reasoning"] = reasoning
        except Exception as e:
            logger.warning("Reason stage failed: %s", e)
            reasoning = {"suggested_engine": "chat"}

        # ═══ STAGE 3: PLAN ═══
        try:
            profile = None
            if self.chat and hasattr(self.chat, "memory"):
                profile = self.chat.memory.user_profile
            dialogue_plan = self.planner.plan(
                perception["intent"], perception["confidence"], text, profile,
            )
            dialogue_plan["intent"] = perception["intent"]
            dialogue_plan["reasoning"] = reasoning
            dialogue_plan["engine"] = reasoning.get("suggested_engine", "chat")
            dialogue_plan["fallback_chain"] = self._fallback_chain(
                reasoning.get("suggested_engine", "chat")
            )

            if perception["is_command"]:
                dialogue_plan["engine"] = "command"
                dialogue_plan["fallback_chain"] = ["command", "chat", "fallback"]
        except Exception as e:
            logger.warning("Plan stage failed: %s", e)
            dialogue_plan = {"engine": "chat", "fallback_chain": ["chat", "fallback"],
                             "intent": perception["intent"]}

        # ═══ STAGE 4: EXECUTE ═══
        try:
            response, used_engine = self.dispatcher.dispatch(dialogue_plan, perception)
            self.last_response = response
        except Exception as e:
            logger.warning("Execute stage failed: %s", e)
            response = "Вибач, сталася помилка. Спробуй ще раз."
            used_engine = "error"

        # ═══ STAGE 5: LEARN ═══
        try:
            self.learner.learn_from_message(text, perception["intent"], perception["confidence"])
            satisfaction = self._calc_satisfaction(perception["lower"], response)
            self.dispatcher.record_feedback(used_engine, satisfaction > 0)
        except Exception as e:
            logger.warning("Learn stage failed: %s", e)
            satisfaction = 0.0

        # ═══ STAGE 6: REFLECT (самооценка + обучение) ═══
        try:
            eval_result = self.introspect.evaluate(response, perception, dialogue_plan)
            if eval_result["needs_correction"]:
                correction = self.introspect.get_correction(response, perception)
                if correction:
                    response = correction
                    used_engine = "self_corrected"

            # Передаём обратную связь в ThinkingEngine
            if self.thinker:
                was_positive = satisfaction > 0.5
                self.thinker.learn_from_feedback(text, response, was_positive)

                # Извлекаем факты
                tl = text.lower()
                if "меня зовут" in tl:
                    name = tl.split("меня зовут")[-1].strip()
                    self.thinker.learn_fact("user_name", name)
                if self.thinker.get_fact("user_name"):
                    self.thinker.context["user_name"] = self.thinker.get_fact("user_name")
        except Exception as e:
            logger.warning("Reflect stage failed: %s", e)

        # ═══ STAGE 7: ADAPT (персонализация + проактивность) ═══
        try:
            self.personality.update(perception["intent"], text)
            self.memory.remember("user", text, perception["intent"], perception["entities"])
            self.memory.decay()
            self.proactive.observe(perception["intent"], text)
            self.proactive.decay_interests()

            # Персонализация: получаем имя из MemorySystem
            user_name = None
            if self._assistant and hasattr(self._assistant, "memory"):
                user_name = self._assistant.memory.long.profile.get("name")
            if not user_name and self.thinker and hasattr(self.thinker, "get_fact"):
                user_name = self.thinker.get_fact("user_name")

            if self.proactive.should_suggest(self.planner.turn_count,
                                              self.planner.user_engagement):
                suggestion = self.proactive.get_suggestion(self.planner.turn_count)
                if suggestion and not perception["is_command"]:
                    response += "\n\n" + suggestion

            if perception["intent"] == "unknown":
                self.consecutive_unknown += 1
            else:
                self.consecutive_unknown = 0
                self.intent_resolver.learn_success(perception["intent"])

            self.planner.set_engagement(satisfaction)
        except Exception as e:
            logger.warning("Adapt stage failed: %s", e)

        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        logger.debug("Cycle %d: [%s] → %s (%.2fs) engine=%s",
                      self.total_cycles, perception["intent"],
                      response[:40], elapsed, used_engine)

        return response

    def _fallback_chain(self, primary: str) -> List[str]:
        chains = {
            "chat": ["chat", "creative", "semantic", "fallback"],
            "creative": ["creative", "chat", "semantic", "fallback"],
            "command": ["command", "chat", "fallback"],
            "semantic": ["semantic", "chat", "creative", "fallback"],
            "fallback": ["fallback", "chat", "semantic"],
        }
        chain = chains.get(primary, ["chat", "semantic", "fallback"])
        return chain

    def _calc_satisfaction(self, lower: str, response: str) -> float:
        if "спасиб" in lower or "благодар" in lower or "молодец" in lower:
            return 1.0
        if "нет" in lower or "не то" in lower or "неправильно" in lower:
            return -0.5
        if "ещё" in lower or "еще" in lower or re.search(r'\bда\b', lower):
            return 0.3
        if len(response) > 10:
            return 0.1
        return 0.0

    # ── API ──

    def set_user_name(self, name: str):
        if name and self.chat and hasattr(self.chat, "set_user_name"):
            self.chat.set_user_name(name)

    def get_status(self) -> dict:
        response_quality = self.introspect.get_average_quality()
        return {
            "model": self.MODEL_NAME,
            "version": self.version,
            "total_cycles": self.total_cycles,
            "consecutive_unknown": self.consecutive_unknown,
            "personality_mood": self.personality.get_mood_report(),
            "dialogue_goal": self.planner.current_goal,
            "turn_count": self.planner.turn_count,
            "response_quality": round(response_quality, 2),
            "corrections": self.introspect.correction_count,
            "episodic_memories": len(self.memory.episodes),
            "consolidated_facts": len(self.memory.consolidated),
                "top_interests": dict(sorted(self.proactive.interest_scores.items(),
                                               key=lambda x: -x[1])[:5]),
            "last_engine": self.dispatcher.last_engine_used,
            "engine_success": dict(self.dispatcher.engine_success_rate),
        }

    def get_thinking_trace(self) -> str:
        lines = [f"CoreModel v{self.MODEL_VERSION}", f"Цикл: {self.total_cycles}"]
        lines.append(f"Настрій: {self.personality.get_mood_report()}")
        lines.append(f"Мета діалогу: {self.planner.current_goal}")
        lines.append(f"Обертів: {self.planner.turn_count}")
        lines.append(f"Якість: {self.introspect.get_average_quality():.2f}")
        lines.append(f"Корекцій: {self.introspect.correction_count}")
        return "\n".join(lines)

    # ── СОСТОЯНИЕ ──

    def save_state(self, path: Path = None) -> dict:
        data = {
            "model_version": self.MODEL_VERSION,
            "total_cycles": self.total_cycles,
            "consecutive_unknown": self.consecutive_unknown,
            "intent_resolver": self.intent_resolver.to_dict(),
            "reasoning": self.reasoning.to_dict(),
            "planner": self.planner.to_dict(),
            "dispatcher": self.dispatcher.to_dict(),
            "learner": self.learner.to_dict(),
            "introspect": self.introspect.to_dict(),
            "personality": self.personality.to_dict(),
            "memory": self.memory.to_dict(),
            "proactive": self.proactive.to_dict(),
        }
        if self.chat and hasattr(self.chat, "save_state"):
            data["chat"] = self.chat.save_state()
        if path:
            try:
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                logger.error("CoreModel save failed: %s", e)
        return data

    def load_state(self, data: dict = None, path: Path = None):
        if path and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("CoreModel load failed: %s", e)
                return
        if not data:
            return
        self.total_cycles = data.get("total_cycles", 0)
        self.consecutive_unknown = data.get("consecutive_unknown", 0)
        if "intent_resolver" in data:
            self.intent_resolver.from_dict(data["intent_resolver"])
        if "reasoning" in data:
            self.reasoning.from_dict(data["reasoning"])
        if "planner" in data:
            self.planner.from_dict(data["planner"])
        if "dispatcher" in data:
            self.dispatcher.from_dict(data["dispatcher"])
        if "learner" in data:
            self.learner.from_dict(data["learner"])
        if "introspect" in data:
            self.introspect.from_dict(data["introspect"])
        if "personality" in data:
            self.personality.from_dict(data["personality"])
        if "memory" in data:
            self.memory.from_dict(data["memory"])
        if "proactive" in data:
            self.proactive.from_dict(data["proactive"])
        if "chat" in data and self.chat and hasattr(self.chat, "load_state"):
            try:
                self.chat.load_state()
                cd = data["chat"]
                if "memory" in cd:
                    self.chat.memory.from_dict(cd["memory"])
                if "personality" in cd:
                    self.chat.personality.traits.update(cd["personality"].get("traits", {}))
                    self.chat.personality.mood = cd["personality"].get("mood", "neutral")
            except Exception as e:
                logger.error("CoreModel chat state load failed: %s", e)

    def reset(self):
        self.intent_resolver = EnsembleIntentResolver()
        self.reasoning = ReasoningEngine()
        self.planner = DialoguePlanner()
        self.dispatcher = EngineDispatcher(self)
        self.learner = OnlineLearner()
        self.introspect = Introspection()
        self.personality = PersonalityDynamics()
        self.memory = EpisodicMemory()
        self.proactive = ProactiveEngine()
        self.total_cycles = 0
        self.consecutive_unknown = 0
        self.last_response = None
        self.last_plan = None
        logger.info("CoreModel v%s сброшена", self.MODEL_VERSION)
