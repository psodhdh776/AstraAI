"""
Cognitive Adaptive Processing System (CAPS)
=============================================
Многоступенчатый адаптивный алгоритм обработки запросов,
который учится на поведении пользователя и динамически
выбирает оптимальный путь обработки.

Pipeline:
  Perceive -> Reason -> Route -> Execute -> Learn -> Proactive
"""
import json

import re
import datetime
import random
import json
import logging

logger = logging.getLogger("Astra.CAPS")

# ── Конфигурация весов ──

ROUTING_WEIGHTS = {
    "fast_command": 0.9,
    "compound": 0.7,
    "dialogue": 0.5,
    "followup": 0.8,
    "proactive": 0.6,
}

LEARNING_RATE = 0.1
CONFIDENCE_BOOST_REPEAT = 0.15
CONFIDENCE_DECAY_TIME = 0.05

# ── Q-learning параметры ──
Q_LEARNING_RATE = 0.3
Q_DISCOUNT_FACTOR = 0.9
Q_EPSILON = 0.2        # exploration rate
Q_EPSILON_DECAY = 0.995
Q_EPSILON_MIN = 0.05


class CapsQLearning:
    """
    Q-learning планировщик для выбора путей маршрутизации.
    Состояние = (intent_группа, confusion_уровень, время_суток, тренд_успеха)
    Действия  = пути обработки из роутера.
    """

    STATE_INTENTS = [
        "command", "greet", "dialogue", "feedback",
        "followup", "compound", "fallback",
    ]
    STATE_CONFUSION = ["low", "medium", "high"]
    STATE_PERIODS = ["morning", "afternoon", "evening", "night"]
    STATE_TRENDS = ["improving", "stable", "declining"]

    def __init__(self):
        # Q-table: dict[(intent, confusion, period, trend)][action] = value
        self.q_table = {}
        self.epsilon = Q_EPSILON
        self.total_episodes = 0
        self.last_state = None
        self.last_action = None

    def _state_key(self, intent, confusion_rate, period, trend):
        if intent not in self.STATE_INTENTS:
            intent = "dialogue"
        c_level = self.STATE_CONFUSION[0] if confusion_rate < 0.33 else \
                  self.STATE_CONFUSION[1] if confusion_rate < 0.66 else \
                  self.STATE_CONFUSION[2]
        if period not in self.STATE_PERIODS:
            period = "afternoon"
        if trend not in self.STATE_TRENDS:
            trend = "stable"
        return (intent, c_level, period, trend)

    def _ensure_state(self, state):
        if state not in self.q_table:
            self.q_table[state] = {a: 0.0 for a in self.STATE_INTENTS}

    def choose_action(self, intent, confusion_rate, period, trend, candidates):
        """
        Выбирает лучшее действие из доступных кандидатов.
        Использует ε-greedy.
        """
        state = self._state_key(intent, confusion_rate, period, trend)
        self._ensure_state(state)
        self.total_episodes += 1

        # Доступные действия
        available = list(set([c.get("path", "dialogue") for c in candidates]))
        if not available:
            available = ["dialogue"]

        # ε-greedy
        if random.random() < self.epsilon:
            action = random.choice(available)
        else:
            q_values = {a: self.q_table[state].get(a, 0.0) for a in available}
            max_q = max(q_values.values())
            best_actions = [a for a, v in q_values.items() if v == max_q]
            action = random.choice(best_actions)

        self.last_state = state
        self.last_action = action

        return action

    def learn(self, reward):
        """
        Q(s,a) = Q(s,a) + α * [r + γ * max Q(s',a') - Q(s,a)]
        """
        if self.last_state is None or self.last_action is None:
            return

        state = self.last_state
        action = self.last_action
        old_q = self.q_table[state].get(action, 0.0)
        # Для offline оценки: max future = 0 (нет следующего состояния)
        new_q = old_q + Q_LEARNING_RATE * (reward - old_q)
        self.q_table[state][action] = round(new_q, 4)

        self.last_state = None
        self.last_action = None

    def get_q_summary(self):
        """Возвращает человеко-читаемую сводку Q-таблицы."""
        lines = []
        for state, actions in sorted(self.q_table.items()):
            best = max(actions, key=actions.get)
            avg = sum(actions.values()) / len(actions) if actions else 0
            lines.append(f"  {state[0]:10s} | conf={state[1]:6s} | {state[2]:9s} | "
                         f"trend={state[3]:9s} → best={best:10s} avg_q={avg:.2f}")
        return lines

    def to_dict(self):
        return {
            "q_table": {json.dumps(list(k)): v for k, v in self.q_table.items()},
            "epsilon": self.epsilon,
            "total_episodes": self.total_episodes,
        }

    def from_dict(self, data):
        self.q_table = {tuple(json.loads(k)): v for k, v in data.get("q_table", {}).items()}
        self.epsilon = data.get("epsilon", Q_EPSILON)
        self.total_episodes = data.get("total_episodes", 0)


class CapsAlgorithm:
    """
    Основной алгоритм CAPS.
    Заменяет линейный _think() + process() на адаптивный конвейер.
    """

    def __init__(self, assistant):
        self.assistant = assistant
        self.stats = CapsStats()
        self.learner = CapsLearner(assistant)
        self.proactive = CapsProactive(assistant)
        self.quality = CapsQualityTracker()
        self.qlearn = CapsQLearning()

    def process(self, text):
        """Главный метод: полный цикл обработки одного сообщения."""
        if not text or not text.strip():
            return ""

        text = text.strip()
        tl = text.lower().strip(".,!? ")

        # ── 0. EXIT check ──
        if tl in ("пока", "до свидания", "выйти", "exit", "quit",
                  "закрой", "стоп", "stop", "хватит", "завершить", "отбой"):
            return "__EXIT__"

        self.stats.total_messages += 1
        self.stats.session_messages.append({
            "text": text, "time": datetime.datetime.now(), "intent": None
        })
        if len(self.stats.session_messages) > 50:
            self.stats.session_messages.pop(0)

        # ── 1. PERCEIVE ──
        perception = self._perceive(text, tl)

        # ── 2. REASON ──
        reasoning = self._reason(perception)

        # ── 3. ROUTE ──
        route = self._route(reasoning)

        # ── 4. EXECUTE ──
        response = self._execute(route, perception)

        # ── 5. LEARN ──
        self._learn(perception, route, response)

        # ── 6. PROACTIVE ──
        self._proactive_check()

        return response

    def _perceive(self, text, tl):
        """Слой восприятия: извлекает все возможные сигналы из входа."""
        perception = {
            "text": text,
            "lower": tl,
            "words": tl.split(),
            "word_count": len(tl.split()),
            "has_question": "?" in text,
            "has_exclamation": "!" in text,
            "is_short": len(tl) < 15,
            "is_very_short": len(tl) < 5,
            "is_command_like": self._looks_like_command(text, tl),
            "is_greeting": self._is_greeting(tl),
            "is_farewell": self._is_farewell(tl),
            "is_feedback": self._is_feedback(tl),
            "is_followup": self._is_followup(tl),
            "emotion": None,
            "entities": self._extract_entities(text, tl),
            "intent_hints": self._extract_intent_hints(tl),
            "time_aware": self._get_time_context(),
            "user_context": self._get_user_context(),
            "history_context": self._get_history_context(),
        }

        # Emotion analysis
        if hasattr(self.assistant, "emotion") and self.assistant.emotion:
            perception["emotion"] = self.assistant.emotion.analyze(text)

        return perception

    def _looks_like_command(self, text, tl):
        """Определяет, похож ли текст на команду."""
        command_triggers = [
            "открой", "запусти", "найди", "поищи", "скриншот",
            "напомни", "заметк", "посчитай", "калькулятор",
            "погода", "переведи", "система", "нарисуй",
            "время", "дата", "помощь", "настроение",
        ]
        for t in command_triggers:
            if t in tl:
                return True
        return False

    def _is_greeting(self, tl):
        return any(w in tl for w in [
            "привет", "здравств", "хай", "hello", "hi",
            "доброе утро", "добрый день", "добрый вечер",
        ])

    def _is_farewell(self, tl):
        return tl in ("пока", "до свидания", "увидимся", "bye", "goodbye")

    def _is_feedback(self, tl):
        return any(w in tl for w in [
            "спасибо", "благодарю", "молодец", "умница",
            "круто", "классно", "супер", "отлично",
            "нет", "не то", "неправильно", "опять",
        ])

    def _is_followup(self, tl):
        """Определяет, является ли это продолжением предыдущего разговора."""
        followup_words = [
            "да", "нет", "ага", "неа", "ещё", "еще",
            "а ", "и ", "ладно", "ок", "ok", "давай",
            "понял", "понятно", "ясно", "хорошо",
        ]
        if tl in followup_words:
            return True
        if len(tl.split()) <= 3:
            for w in followup_words:
                if tl.startswith(w):
                    return True
        return False

    def _extract_entities(self, text, tl):
        """Извлекает сущности: города, числа, приложения, имена."""
        entities = {}
        # Город
        m = re.search(r'(?:в|во|на|в городе)\s+([А-Яа-яA-Za-z-]{2,})', text)
        if m:
            entities["city"] = m.group(1)
        # Число
        m = re.search(r'(\d+)', text)
        if m:
            entities["number"] = int(m.group(1))
        # Приложение
        apps = ["браузер", "блокнот", "калькулятор", "проводник",
                "vscode", "word", "excel", "chrome", "cmd", "терминал"]
        for a in apps:
            if a in tl:
                entities["app"] = a
                break
        return entities

    def _extract_intent_hints(self, tl):
        """Извлекает подсказки о намерении из текста."""
        hints = {}
        hint_map = {
            "время": "time", "часов": "time", "который час": "time",
            "дата": "date", "число": "date", "день недели": "date",
            "погод": "weather", "температур": "weather", "градус": "weather",
            "скриншот": "screenshot", "снимок": "screenshot",
            "систем": "system", "процессор": "system", "память": "system",
            "открой": "open_app", "запусти": "open_app",
            "найди": "web_search", "поищи": "web_search",
            "заметк": "add_note", "запомни": "add_note",
            "напомни": "remind", "напоминание": "remind",
            "калькулятор": "calc", "посчитай": "calc",
            "переведи": "translate", "перевод": "translate",
            "нарисуй": "generate_image",
            "помощь": "help", "умеешь": "help",
            "настроение": "mood_report", "эмоци": "mood_report",
            "поищи в истории": "fast_search", "найди в": "fast_search",
        }
        matched = []
        for keyword, intent in hint_map.items():
            if keyword in tl:
                matched.append(intent)
        hints["primary"] = matched[0] if matched else None
        hints["all"] = matched
        return hints

    def _get_time_context(self):
        now = datetime.datetime.now()
        hour = now.hour
        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 18:
            period = "afternoon"
        elif 18 <= hour < 23:
            period = "evening"
        else:
            period = "night"
        return {
            "hour": hour,
            "period": period,
            "weekday": now.weekday(),
            "is_weekend": now.weekday() >= 5,
            "date": now.strftime("%d.%m.%Y"),
        }

    def _get_user_context(self):
        ctx = {}
        tc = getattr(self.assistant, "_thinking_ctx", {})
        ctx["user_name"] = tc.get("user_name")
        ctx["user_city"] = tc.get("preferred_city")
        ctx["message_count"] = tc.get("mention_count", 0)
        ctx["frequent_commands"] = tc.get("frequent_commands", {})
        return ctx

    def _get_history_context(self):
        """Последние сообщения из истории для контекста."""
        history = getattr(self.assistant, "history", [])
        return [h for h in history[-6:]]

    def _reason(self, perception):
        """
        Слой рассуждения: многоступенчатый анализ с перебором гипотез.
        Возвращает ранжированный список возможных путей обработки.
        """
        tl = perception["lower"]
        hypotheses = []

        # Гипотеза 1: Приветствие
        if perception["is_greeting"]:
            confidence = 0.95
            if perception["user_context"]["user_name"]:
                confidence = 1.0
            hypotheses.append({
                "path": "greet",
                "confidence": confidence,
                "handler": self._h_greet,
                "params": None,
            })

        # Гипотеза 2: Follow-up (продолжение)
        if perception["is_followup"]:
            last_intent = self.stats.last_intent
            if last_intent:
                confidence = 0.85
                if perception["is_very_short"]:
                    confidence = 0.95
                hypotheses.append({
                    "path": "followup",
                    "confidence": confidence,
                    "handler": self._h_followup,
                    "params": {"last_intent": last_intent, "text": tl},
                })

        # Гипотеза 3: Команда (через плагины)
        if perception["is_command_like"] or perception["intent_hints"]["primary"]:
            plugin_hypotheses = self._get_plugin_hypotheses(perception)
            hypotheses.extend(plugin_hypotheses)

        # Гипотеза 4: Команда (через _think)
        think_result = self.assistant._think(perception["text"])
        if think_result and think_result != "__EXIT__":
            hypotheses.append({
                "path": "command",
                "confidence": 0.8,
                "handler": lambda p=None, r=think_result: r,
                "params": None,
            })

        # Гипотеза 5: Обратная связь
        if perception["is_feedback"] and self.stats.last_response:
            confidence = 0.75
            if "спасиб" in tl or "благодар" in tl:
                confidence = 0.9
            hypotheses.append({
                "path": "feedback",
                "confidence": confidence,
                "handler": self._h_feedback,
                "params": {"feedback": tl, "last_response": self.stats.last_response},
            })

        # Гипотеза 6: Простой диалог
        hypotheses.append({
            "path": "dialogue",
            "confidence": 0.4,
            "handler": self._h_dialogue,
            "params": {"text": perception["text"]},
        })

        # Сортировка по confidence + boosting
        for h in hypotheses:
            h["confidence"] = self._boost_confidence(h, perception)

        hypotheses.sort(key=lambda x: -x["confidence"])
        return hypotheses

    def _boost_confidence(self, hypothesis, perception):
        """Применяет бусты к confidence на основе контекста."""
        conf = hypothesis["confidence"]
        path = hypothesis["path"]

        # Буст за повторение той же команды
        if path == self.stats.last_intent:
            conf += CONFIDENCE_BOOST_REPEAT

        # Буст за правильное время суток
        if path == "greet" and perception["time_aware"]["period"] in ("morning", "evening"):
            conf += 0.05

        # Буст за эмоцию
        emotion = perception.get("emotion")
        if emotion and emotion["is_negative"]:
            conf += 0.05

        # Штраф за частые ошибки
        error_rate = self.learner.get_error_rate(path)
        conf -= error_rate * 0.3

        # Если путь часто успешен — буст
        success_rate = self.learner.get_success_rate(path)
        conf += success_rate * 0.1

        return min(1.0, max(0.0, conf))

    def _get_plugin_hypotheses(self, perception):
        """Получает гипотезы от плагинов."""
        hypotheses = []
        tl = perception["lower"]
        text = perception["text"]

        plugin_results = self.assistant._hypothesize(text, tl)
        for r in plugin_results:
            hypotheses.append({
                "path": r["name"],
                "confidence": r["score"],
                "handler": lambda params=r.get("params"), p=r["handler"]: p(params)
                            if callable(r["handler"]) else r["handler"](r.get("params")),
                "params": r.get("params"),
            })
        return hypotheses

    def _route(self, hypotheses):
        """
        Слой маршрутизации: Q-learning выбирает оптимальный путь
        из ранжированных гипотез.
        """
        if not hypotheses:
            self.qlearn.learn(-0.5)
            self.qlearn.epsilon = max(Q_EPSILON_MIN, self.qlearn.epsilon * Q_EPSILON_DECAY)
            return {"path": "fallback", "handler": self._h_fallback, "confidence": 0}

        best = hypotheses[0]

        # Адаптивный порог
        base_threshold = 0.45
        confusion_rate = self.learner.get_confusion_rate()
        threshold = base_threshold - (confusion_rate * 0.2)
        self.stats.routing_threshold = threshold
        self.stats.selected_path = best["path"]
        self.stats.selected_confidence = best["confidence"]

        # Q-learning выбор — среди топ-3
        period = self._get_time_context()["period"]
        top_candidates = hypotheses[:3]

        if best["confidence"] >= threshold:
            ql_action = self.qlearn.choose_action(
                best["path"], confusion_rate, period,
                self.learner.get_quality_trend(best["path"]), top_candidates
            )
            ql_candidate = next((h for h in top_candidates if h["path"] == ql_action), None)
            if ql_candidate:
                return ql_candidate
            return best

        # Низкая уверенность — Q-learning решает
        ql_action = self.qlearn.choose_action(
            "fallback", confusion_rate, period, "stable", top_candidates
        )
        ql_candidate = next((h for h in top_candidates if h["path"] == ql_action), None)
        if ql_candidate and ql_candidate["confidence"] > 0.3:
            return ql_candidate

        # Комбинированный fallback
        if len(hypotheses) >= 2:
            top2 = hypotheses[:2]
            combined = {
                "path": f"{top2[0]['path']}+{top2[1]['path']}",
                "confidence": top2[0]["confidence"] + top2[1]["confidence"] * 0.3,
            }
            if combined["confidence"] >= threshold:
                return combined

        self.qlearn.learn(-0.3)
        return {"path": "fallback", "handler": self._h_fallback, "confidence": best["confidence"]}

    def _execute(self, route, perception):
        """
        Слой выполнения: запускает обработчик с мониторингом.
        """
        path = route["path"]
        handler = route["handler"]
        params = route.get("params")

        self.stats.last_intent = path
        self.stats.current_path = path

        try:
            if params is not None:
                result = handler(params)
            else:
                result = handler()

            if result and result != "__EXIT__":
                self.stats.last_response = result
                self.stats.session_messages[-1]["intent"] = path
                self.stats.total_success += 1
                self.learner.record_success(path)

                # Улучшаем качество ответа через QualityTracker
                result = self.quality.enhance(result, perception)

            return result

        except Exception as e:
            logger.error("CAPS execute error [%s]: %s", path, e)
            self.stats.total_errors += 1
            self.learner.record_error(path)
            return self._h_fallback(None)

    def _learn(self, perception, route, response):
        """
        Слой обучения: Q-learning + статистика.
        """
        if response == "__EXIT__":
            return

        tl = perception["lower"]

        # Определяем награду для Q-learning по реакции пользователя
        quality_signals = []
        if "спасиб" in tl or "благодар" in tl or "молодец" in tl:
            quality_signals.append(1.0)
        elif "нет" in tl or "не то" in tl or "неправильно" in tl:
            quality_signals.append(-0.5)
        elif "ещё" in tl or "да" in tl or "еще" in tl:
            quality_signals.append(0.3)

        if quality_signals:
            avg_quality = sum(quality_signals) / len(quality_signals)
            path = self.stats.last_intent
            self.learner.update_quality(path, avg_quality)
            self.qlearn.learn(avg_quality)
        else:
            # Нейтральная награда за успешный ответ
            self.qlearn.learn(0.1)

        # Запоминаем частые команды
        if perception["is_command_like"]:
            self.stats.frequent_commands[route.get("path", "unknown")] = \
                self.stats.frequent_commands.get(route.get("path", "unknown"), 0) + 1

    def _proactive_check(self):
        """
        Слой проактивности: проверяет контекст и может инициировать действие.
        """
        if not hasattr(self.assistant, "_proactive_check"):
            return

        now = datetime.datetime.now()
        period = self._get_time_context()["period"]

        # Проверяем каждые N сообщений
        if self.stats.total_messages > 0 and self.stats.total_messages % 5 == 0:
            suggestions = self.assistant._proactive_check()
            if suggestions:
                self.stats.pending_proactive = suggestions

    # ── Обработчики путей ──

    def _h_greet(self, _=None):
        name = self._get_user_context().get("user_name")
        period = self._get_time_context()["period"]
        period_map = {
            "morning": "Доброе утро",
            "afternoon": "Добрый день",
            "evening": "Добрый вечер",
            "night": "Доброй ночи",
        }
        greeting = period_map.get(period, "Привет")
        if name:
            return f"{greeting}, {name}! ✨ Чем займёмся?"
        return f"{greeting}! ✨ Я Astra, твой помощник. Чем могу помочь?"

    def _h_followup(self, params):
        last = params.get("last_intent")
        text = params.get("text", "")
        tl = text.lower()

        if last == "weather" and any(w in tl for w in ["а ", "и ", "в "]):
            q = re.sub(r'^[аи]\s*', '', text)
            if hasattr(self.assistant, "_h_weather"):
                city = self.assistant._extract_city(q)
                if city:
                    return self.assistant._h_weather(city)

        return self.assistant._think(text) or self._h_dialogue({"text": text})

    def _h_dialogue(self, params):
        text = params.get("text", "")
        if hasattr(self.assistant, "_thinking_ctx") and \
           self.assistant._thinking_ctx.get("user_name"):
            self.assistant.dialogue.set_user_name(
                self.assistant._thinking_ctx["user_name"])
        resp = self.assistant.dialogue.respond(text)
        if self.assistant.db:
            self.assistant.dialogue.save_state(self.assistant.db)
        return resp

    def _h_feedback(self, params):
        feedback = params.get("feedback", "")
        last_resp = params.get("last_response", "")
        if "спасиб" in feedback or "благодар" in feedback or "молодец" in feedback:
            return random.choice([
                "Всегда пожалуйста!",
                "Рада помочь!",
                "Обращайся, я рядом!",
            ])
        return random.choice([
            "Поняла, учту!",
            "Хорошо, исправлюсь.",
            "Спасибо за обратную связь!",
        ])

    def _h_combined(self, params):
        """Комбинированный обработчик — запускает два пути и выбирает лучший результат."""
        primary = params.get("primary", {})
        secondary = params.get("secondary", {})
        handler_p = primary.get("handler")
        handler_s = secondary.get("handler")

        result_p = handler_p(None) if callable(handler_p) else None
        result_s = handler_s(None) if callable(handler_s) else None

        if result_p and not result_s:
            return result_p
        if result_s and not result_p:
            return result_s
        if result_p and result_s:
            return f"{result_p}\n\n{result_s}"
        return result_p or result_s or None

    def _h_fallback(self, _=None):
        return random.choice([
            "🤔 Не совсем поняла. Может, попробуешь другими словами?",
            "Не уверена, что правильно поняла. Расскажи подробнее.",
            "🤷 Я слушаю. Уточни, что ты имеешь в виду.",
            "Хм, я не до конца поняла. Попробуй переформулировать.",
        ])


class CapsStats:
    """Статистика работы алгоритма."""

    def __init__(self):
        self.total_messages = 0
        self.total_success = 0
        self.total_errors = 0
        self.last_intent = None
        self.last_response = None
        self.selected_path = None
        self.selected_confidence = 0
        self.routing_threshold = 0.45
        self.current_path = None
        self.session_messages = []
        self.frequent_commands = {}
        self.pending_proactive = []
        self.user_context = {}

    @property
    def success_rate(self):
        if self.total_messages == 0:
            return 1.0
        return self.total_success / self.total_messages


class CapsLearner:
    """Адаптивное обучение на основе результатов."""

    def __init__(self, assistant):
        self.assistant = assistant
        self.path_stats = {}  # path -> {"success": N, "error": N, "quality": []}
        self.confusion_count = 0
        self.total_feedback = 0

    def record_success(self, path):
        if path not in self.path_stats:
            self.path_stats[path] = {"success": 0, "error": 0, "quality": []}
        self.path_stats[path]["success"] += 1

    def record_error(self, path):
        if path not in self.path_stats:
            self.path_stats[path] = {"success": 0, "error": 0, "quality": []}
        self.path_stats[path]["error"] += 1
        self.confusion_count += 1

    def update_quality(self, path, quality_delta):
        if path not in self.path_stats:
            self.path_stats[path] = {"success": 0, "error": 0, "quality": []}
        self.path_stats[path]["quality"].append(quality_delta)
        if len(self.path_stats[path]["quality"]) > 20:
            self.path_stats[path]["quality"].pop(0)

    def get_success_rate(self, path):
        stats = self.path_stats.get(path, {})
        total = stats.get("success", 0) + stats.get("error", 0)
        if total == 0:
            return 0.5
        return stats.get("success", 0) / total

    def get_error_rate(self, path):
        return 1.0 - self.get_success_rate(path)

    def get_confusion_rate(self):
        if self.total_feedback == 0:
            return 0.1
        return min(1.0, self.confusion_count / max(1, self.total_feedback))

    def get_quality_trend(self, path):
        stats = self.path_stats.get(path, {})
        qualities = stats.get("quality", [])
        if len(qualities) < 3:
            return "stable"
        recent = sum(qualities[-3:]) / 3
        if recent > 0.3:
            return "improving"
        elif recent < -0.3:
            return "declining"
        return "stable"


class CapsProactive:
    """Проактивный слой — генерация подсказок и предложений."""

    def __init__(self, assistant):
        self.assistant = assistant
        self.last_proactive = datetime.datetime.min

    def get_suggestions(self):
        now = datetime.datetime.now()
        if (now - self.last_proactive).seconds < 300:
            return []
        self.last_proactive = now

        suggestions = []
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            if cpu > 80:
                suggestions.append("⚡ Высокая загрузка CPU. Проверь процессы.")

            mem = psutil.virtual_memory()
            if mem.percent > 90:
                suggestions.append("🧠 Почти вся память занята.")

            bat = psutil.sensors_battery()
            if bat and not bat.power_plugged and bat.percent < 20:
                suggestions.append(f"🔋 Батарея {bat.percent}%. Подключи зарядку.")
        except Exception:
            pass

        return suggestions


class CapsQualityTracker:
    """Отслеживание и улучшение качества ответов."""

    def __init__(self):
        self.enhancement_rules = {
            "time": self._enhance_time,
            "date": self._enhance_date,
            "weather": self._enhance_weather,
        }

    def enhance(self, text, perception):
        if not text:
            return text

        emotion = perception.get("emotion")
        if emotion and emotion["is_negative"]:
            hugs = [
                "\n\nОбнимаю тебя виртуально",
                "\n\nВсё будет хорошо, обещаю",
                "\n\nЯ рядом, если нужно поговорить",
            ]
            text += random.choice(hugs)

        return text

    def _enhance_time(self, text, perception):
        hour = perception["time_aware"]["hour"]
        if hour < 12:
            text += "\nХорошего дня!"
        elif hour > 20:
            text += "\nСкоро ночь, не забудь отдохнуть!"
        return text

    def _enhance_date(self, text, perception):
        if perception["time_aware"]["is_weekend"]:
            text += "\nВыходной! Отдыхай"
        return text

    def _enhance_weather(self, text, perception):
        return text
