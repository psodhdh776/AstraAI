import re
import random
import datetime
import json


# ── Отражение местоимений (ELIZA-style) ──

REFLECTIONS = {
    "я": "ты", "ты": "я", "мне": "тебе", "тебе": "мне",
    "меня": "тебя", "тебя": "меня", "мой": "твой", "твой": "мой",
    "моя": "твоя", "твоя": "моя", "моё": "твоё", "твоё": "моё",
    "мои": "твои", "твои": "мои", "себя": "себя",
    "этот": "этот", "эта": "эта", "это": "это",
}


def _reflect(phrase):
    words = phrase.split()
    out = []
    for w in words:
        w_low = w.lower().strip(".,!?")
        if w_low in REFLECTIONS:
            repl = REFLECTIONS[w_low]
            if w[0].isupper():
                repl = repl.capitalize()
            out.append(repl)
        else:
            out.append(w)
    return " ".join(out)


# ── База знаний ──

KNOWLEDGE = {
    r'(?i).*\b(питон|python)\b.*': [
        "Python — это язык программирования. Я сама написана на Python!",
        "Python отлично подходит для AI, веба и автоматизации.",
    ],
    r'(?i).*\b(что такое\s+.+)': [
        "Хороший вопрос! К сожалению, у меня нет доступа к интернету, "
        "чтобы точно ответить. Попробуй написать «поищи {q}» — я открою браузер.",
    ],
    r'(?i).*\b(кто такой\s+.+)': [
        "Интересно! Если хочешь узнать подробнее, напиши «поищи {q}».",
    ],
    r'(?i).*\b(где находится\s+.+)': [
        "Точно не скажу, но могу поискать. Напиши «поищи {q}».",
    ],
    r'(?i).*\b(linux|windows|mac|ubuntu)\b.*': [
        "Классная тема! У тебя какая система?",
        "Я работаю на Windows, но могу рассказать и о других ОС.",
    ],
    r'(?i).*\b(steam|гейминг|gaming|комп игр|видеоигр|киберспорт)\b.*': [
        "Любишь игры? Во что играешь?",
        "Игры — отличный способ отдохнуть! Какой жанр предпочитаешь?",
    ],
    r'(?i).*\b(книг|читать|чтение|book|литератур)\b.*': [
        "Чтение — это здорово! Какой жанр предпочитаешь?",
        "Я тоже люблю «читать» файлы! Какая книга сейчас в процессе?",
    ],
    r'(?i).*\b(музык|песн|трек|music|song|мелоди)\b.*': [
        "Музыка вдохновляет! Что сейчас слушаешь?",
        "Отличный вкус! Какой жанр музыки тебе нравится?",
    ],
    r'(?i).*\b(фильм|кино|сериал|movie|cinema|фильмы|сериалы)\b.*': [
        "Кино — это круто! Какой жанр предпочитаешь?",
        "Давно смотрел что-то интересное? Поделишься?",
    ],
    r'(?i).*\b(спорт|тренировк|зарядк|качалк|фитнес|бег|sport)\b.*': [
        "Спорт — это сила! Как часто занимаешься?",
        "Молодец, что следишь за здоровьем! Какой спорт предпочитаешь?",
    ],
    r'(?i).*\b(программир|coding|code|пис|код|разработк)\b.*': [
        "Программирование — это магия создания! На чём пишешь?",
        "Круто! Я тоже из мира кода. Какой стек используешь?",
    ],
    r'(?i).*\b(учёб|универ|школ|курс|study|учиться|обучение)\b.*': [
        "Учёба — это инвестиция в будущее! Что изучаешь?",
        "Молодец! Всегда полезно узнавать новое. Какая область?",
    ],
    r'(?i).*\b(работ|офис|проект|дел|бизнес|бизне)\b.*': [
        "Работа — это важно! Чем занимаешься?",
        "Расскажи о своих проектах, мне интересно!",
    ],
    r'(?i).*\b(еда|кушать|готовить|рецепт|вкусн|eat|food|обед|ужин|завтрак)\b.*': [
        "О, про еду я могу говорить часами! Что любишь готовить?",
        "Вкусная тема! Какое твоё коронное блюдо?",
    ],
    r'(?i).*\b(погод|холодн|жарк|тепл|дождь|снег|солнц|ветер)\b.*': [
        "Хочешь узнать погоду? Просто скажи «погода в городе»!",
        "Я могу показать погоду для любого города. Напиши «погода в Москве».",
    ],
    r'(?i).*\b(компьютер|пк|ноут|железо|hardware|процессор|видеокарт)\b.*': [
        "Расскажи о своём ПК! Какое у тебя железо?",
        "Хочешь проверить систему? Напиши «система» — покажу характеристики.",
    ],
}

# ── Паттерны для диалога ──

PATTERNS = [
    (r'(?i).*\b(привет|здравств|хай|здаров|hi|hello)\b.*', [
        "Привет! Как твои дела?",
        "Здравствуй! Чем сегодня займёмся?",
        "Хай! Рада тебя видеть. Рассказывай.",
        "Приветствую! Как настроение?",
    ]),
    (r'(?i).*\b(как дела|как ты|чё как|как жизнь|how are you|как сам)\b.*', [
        "У меня всё отлично! А у тебя как?",
        "Всё хорошо, работаю. Как твои дела?",
        "Супер! Спрашивай что угодно. А у тебя что нового?",
        "Я в порядке, спасибо! Расскажи о себе.",
    ]),
    (r'(?i).*\b(отлично|хорошо|нормально|норм|прекрасно|класс|супер|круто|замечательно|great|fine|good)\b.*', [
        "Отлично, рада это слышать!",
        "Здорово! А что именно так хорошо?",
        "Класс! Расскажи подробнее.",
        "Супер! Продолжай в том же духе.",
    ]),
    (r'(?i).*\b(плохо|устал|грустно|скучно|не очень|так себе|bad|sad|tired|депресси|хреново|ужасно|отвратительно)\b.*', [
        "Мне жаль. Хочешь поговорить об этом? Я умею слушать.",
        "Понимаю. Может, сделать перерыв и выпить чай?",
        "Всё наладится, не переживай. Чем я могу помочь?",
        "Бывают тяжёлые дни. Хочешь отвлечься? Могу рассказать шутку.",
    ]),
    (r'(?i).*\b(спасибо|благодарю|thanks|thank you|спс|благодар)\b.*', [
        "Пожалуйста! Обращайся, если что.",
        "Всегда рада помочь! Есть ещё вопросы?",
        "Не за что! Рада быть полезной.",
    ]),
    (r'(?i).*\b(как тебя зовут|кто ты|ты кто|как звать|what is your name|представься)\b.*', [
        "Меня зовут Astra! Я твой персональный AI-помощник.",
        "Я Astra — цифровой ассистент на твоём компьютере.",
        "Astra, к твоим услугам! Чем могу помочь?",
    ]),
    (r'(?i)(меня зовут|my name is|я\s+|звать)\s+(\S{2,})', [
        "Очень приятно, {name}! Чем могу помочь?",
        "Приятно познакомиться, {name}! Спрашивай что угодно.",
        "{name} — отличное имя! Расскажи, чем займёмся?",
    ]),
    (r'(?i).*\b(сколько тебе лет|твой возраст|ты старая|какой год рождения)\b.*', [
        "Я появилась в 2026 году и с тех пор только расту и умнею!",
        "Я молодая, но уже много знаю и умею.",
        "Мне меньше года, но я быстро учусь на своих ошибках!",
    ]),
    (r'(?i).*\b(что ты умеешь|твои возможности|что можешь|функции|capabilities)\b.*', [
        "Я умею: время, дата, погода, скриншот, поиск, заметки, напоминания, "
        "калькулятор, перевод, открытие приложений и мониторинг системы.",
        "Могу помочь с делами, ответить на вопросы, развлечь или просто поболтать.\n"
        "Попробуй: «система», «погода в Москве», «заметка купить хлеб» или «пошути».",
    ]),
    (r'(?i).*\b(нравится|люблю|обожаю|кайф|love|like|нравиться|полюбил)\b.*', [
        "О, расскажи подробнее! Что именно тебя в этом привлекает?",
        "Здорово! Я рада, что тебе это нравится.",
        "Класс! А почему именно это?",
    ]),
    (r'(?i).*\b(не нравится|ненавижу|бесит|раздражает|терпеть не могу|ненавид)\b.*', [
        "Понимаю. А что именно не так?",
        "Бывает. Расскажи, что случилось.",
        "Может, попробуешь посмотреть на это с другой стороны?",
    ]),
    (r'(?i).*\b(думаю|кажется|мне кажется|полагаю|считаю|наверно|вероятно|возможно)\b.*', [
        "Интересная мысль. Расскажи подробнее.",
        "Понятно. А почему ты так думаешь?",
        "Я тебя понимаю. Продолжай, мне интересно.",
        "Хм, а что привело тебя к такому выводу?",
    ]),
    (r'(?i).*\b(извини|прости|sorry|извиняюсь|прошу прощения|виноват)\b.*', [
        "Ничего страшного, бывает!",
        "Всё в порядке, не переживай.",
        "Не извиняйся! Я здесь чтобы помогать.",
        "Проехали! Что дальше?",
    ]),
    (r'(?i).*(?:шутк|пошути|рассмеш|анекдот|joke|юмор).*', [
        "Почему программисты путают Хэллоуин и Рождество? Oct 31 == Dec 25!",
        "Что сказал ноль единице? — Ты без меня — просто пустое место!",
        "Почему робот пошёл к психологу? — У него были короткие замыкания.",
        "Как называют собаку-хакера? — Шпиц-программист!",
        "Почему функция пошла на вечеринку? — Чтобы передать параметры!",
    ]),
    (r'(?i).*\b(что делаешь|чем занят|занята|work|работа|чем занимаешься)\b.*', [
        "На связи 24/7! Жду твоих команд.",
        "Отдыхаю в фоне, но для тебя всегда на связи!",
        "Работаю — мониторю систему и жду команд.",
    ]),
    (r'(?i).*(?:помощ|help|команды|умеешь|возможност|что ты можешь).*', [
        "Напиши «помощь» — покажу все команды!",
    ]),
    (r'(?i).*\b(время|сколько времени|который час)\b.*', [
        "Сейчас {time}. {more}",
    ]),
    (r'(?i).*\b(дата|какое сегодня|какое число|день недели|год|месяц|число)\b.*', [
        "Сегодня {date}, {day}. {more}",
    ]),
    (r'(?i).*\b(ладно|договорились|ок|ok|okay|понял|понятно|ясно)\b.*', [
        "Супер! Что дальше?",
        "Отлично! Есть что-то ещё?",
        "Хорошо, я на связи.",
    ]),
    (r'(?i).*\b(спи|ночь|ночи|спокойно|good night|сладких снов|баю)\b.*', [
        "Спокойной ночи! Пусть снятся добрые сны.",
        "Хорошего отдыха! Завтра новый день.",
        "Сладких снов! Я буду здесь, когда проснёшься.",
    ]),
    (r'(?i).*\b(утр|доброе morning|morning|встал|проснулся|доброе утро)\b.*', [
        "Доброе утро! Как спалось?",
        "С добрым утром! Готов к новому дню?",
        "Утро — отличное время для продуктивной работы! Чем займёмся?",
    ]),
    (r'(?i).*\b(вечер|вечером|вечера|good evening|добрый вечер)\b.*', [
        "Добрый вечер! Как прошёл день?",
        "Отличный вечер! Чем хочешь заняться?",
        "Вечер — время отдыха. Может, фильм или музыка?",
    ]),
    (r'(?i).*\b(хочешь\s+|давай\s+|может\s+)(пить|кофе|чай|поесть|перекус|покушать)\b.*', [
        "Хорошая идея! Угощайся, а я посторожу компьютер.",
        "Давай! Только я виртуальная, так что угощайся без меня.",
    ]),
]

FALLBACKS = [
    "Интересно. Расскажи подробнее, я слушаю.",
    "Поняла. А что ещё?",
    "Хм, расскажи об этом побольше.",
    "Я не совсем поняла. Можешь объяснить другими словами?",
    "Продолжай, я внимательно слушаю.",
    "А что ты сам об этом думаешь? Мне важно твоё мнение.",
    "Понятно. Есть что-то ещё, чем я могу помочь?",
    "Расскажи мне об этом поподробнее.",
    "Хорошо. Что будем делать дальше?",
    "Интересная мысль. А почему тебя это волнует?",
    "Вот как! Никогда не перестаю удивляться.",
    "Я слушаю. Не стесняйся, говори что думаешь.",
    "Поняла тебя. Есть ещё что-то на уме?",
]

MOOD_EMOJI = {
    "positive": ["😊", "👍", "✨", "🌟", "💪", "🔥", "🎉"],
    "negative": ["🤗", "💙", "🌧️", "🤝"],
    "neutral":  ["💬", "🤔", "💡", "📌"],
}

TOPIC_KEYWORDS = {
    "tech":  ["компьютер", "код", "программ", "python", "ноутбук", "железо", "софт"],
    "food":  ["еда", "кушать", "готовить", "рецепт", "вкусно", "обед"],
    "music": ["музыка", "песня", "трек", "исполнитель", "группа"],
    "movies":["фильм", "кино", "сериал", "актёр"],
    "sport": ["спорт", "тренировка", "бег", "фитнес", "зарядка"],
    "books": ["книга", "читать", "чтение", "литература"],
    "work":  ["работа", "проект", "офис", "бизнес"],
    "study": ["учёба", "универ", "школа", "курс", "обучение"],
    "games": ["игр", "гейминг", "steam", "геймплей"],
}


def _detect_topic(text):
    tl = text.lower()
    for topic, kws in TOPIC_KEYWORDS.items():
        for kw in kws:
            if kw in tl:
                return topic
    return None


# ═══════════════════════════════════════════════
#  DialogueEngine с самообучением
# ═══════════════════════════════════════════════

class DialogueEngine:
    def __init__(self):
        self.memory = []
        self.context = {
            "user_name": None,
            "last_topic": None,
            "turn_count": 0,
            "mood": "neutral",
            "mood_history": [],
            "facts": [],
            "last_response": None,
            "last_user_emotion": None,
            "last_emotion_confidence": 0,
        }
        # Обучаемые веса ответов
        self.response_weights = {}  # {"pattern_idx|resp_idx": score}
        # Выученные пользовательские паттерны
        self.learned_patterns = []  # [(trigger_words, response)]
        # Профиль пользователя
        self.profile = {
            "likes": [],
            "dislikes": [],
            "hobbies": [],
            "frequent_words": {},
        }
        self._patterns = [(re.compile(p), r, i) for i, (p, r) in enumerate(PATTERNS)]
        self._knowledge = [(re.compile(p), r) for p, r in KNOWLEDGE.items()]

    # ── Персистентность ──

    def save_state(self, db):
        data = {
            "response_weights": self.response_weights,
            "learned_patterns": self.learned_patterns,
            "profile": self.profile,
            "context": {k: v for k, v in self.context.items()
                       if k in ("user_name", "facts")},
        }
        try:
            db.set_memory("dialogue_state", data)
        except Exception:
            pass

    def load_state(self, db):
        try:
            data = db.get_memory("dialogue_state")
        except Exception:
            data = None
        if data:
            self.response_weights = data.get("response_weights", {})
            self.learned_patterns = data.get("learned_patterns", [])
            self.profile = data.get("profile", self.profile)
            ctx = data.get("context", {})
            if ctx.get("user_name"):
                self.context["user_name"] = ctx["user_name"]
            if ctx.get("facts"):
                self.context["facts"] = ctx["facts"]

    # ── Обучение ──

    def learn_from_feedback(self, user_text, last_response):
        """Оценивает качество последнего ответа на основе реакции пользователя."""
        tl = user_text.lower()
        if not last_response:
            return

        # Ищем ключ в response_weights
        key = None
        for k, v in self.response_weights.items():
            if v.get("response") == last_response:
                key = k
                break

        pos_signals = ["спасибо", "хорошо", "отлично", "точно", "верно",
                       "да", "класс", "супер", "круто", "молодец", "умница"]
        neg_signals = ["нет", "не то", "не так", "неправильно", "неверно",
                       "плохо", "ошибка", "непонятно", "снова", "опять"]

        change = 0
        for w in pos_signals:
            if w in tl:
                change = 0.15
                break
        for w in neg_signals:
            if w in tl:
                change = -0.2
                break

        if change != 0 and key:
            self.response_weights[key]["score"] = min(
                5.0, max(-5.0,
                    self.response_weights[key].get("score", 0) + change
                )
            )

        # Если негатив — учим, что такой ответ не подходит для этого контекста
        if change < 0:
            topic = _detect_topic(user_text) or self.context.get("last_topic", "general")
            if topic not in self.profile["dislikes"]:
                self.profile["dislikes"].append(topic)

    def learn_from_repeat(self, text):
        """Извлекает новые паттерны из повторяющихся фраз пользователя."""
        words = [w.lower().strip(".,!?") for w in text.split()
                if len(w) > 3 and not re.match(r'^[0-9\W]+$', w)]
        for w in words:
            self.profile["frequent_words"][w] = \
                self.profile["frequent_words"].get(w, 0) + 1

        # Если слово встретилось 5+ раз — запоминаем как триггер
        for word, count in list(self.profile["frequent_words"].items()):
            if count >= 5 and len(self.learned_patterns) < 20:
                trigger_words = word
                response = f"Ты часто говоришь про «{word}». Расскажи подробнее!"
                exists = any(trigger_words in p[0] for p in self.learned_patterns)
                if not exists:
                    self.learned_patterns.append((trigger_words, response))
                    self.profile["frequent_words"][word] = -5  # отметить как обработанное

    def _learn_fact(self, text):
        """Извлекает факты из свободного текста."""
        m = re.search(
            r'(?i)(?:люблю|обожаю|нравится|увлекаюсь|занимаюсь|'
            r'хожу на|играю в|моё любимое|моя любимая|мой любимый)\s+(.+)',
            text
        )
        if m:
            fact = m.group(1).strip(".,!? ")[:60]
            if fact not in self.context["facts"]:
                self.context["facts"].append(fact)
                return fact
        return None

    def set_user_name(self, name):
        self.context["user_name"] = name

    # ── Основной метод ──

    def respond(self, text, emotion_result=None, system_context=None):
        tl = text.strip()
        if not tl:
            res = "Напиши что-нибудь, я слушаю!"
            self.context["last_response"] = res
            return res

        self.context["turn_count"] += 1
        self.memory.append({"text": tl, "time": datetime.datetime.now()})
        if len(self.memory) > 10:
            self.memory.pop(0)

        # Системный контекст: заметки, напоминания, профиль
        if system_context:
            if "reminders" in system_context and system_context["reminders"]:
                self.context["_reminders"] = system_context["reminders"]
            if "notes" in system_context and system_context["notes"]:
                self.context["_notes"] = system_context["notes"]
            if "profile" in system_context:
                self.context["_profile"] = system_context["profile"]

        # Самообучение: извлекаем факты и повторяющиеся слова
        fact = self._learn_fact(tl)
        self.learn_from_repeat(tl)

        # Настроение + эмоции
        tl_lower = tl.lower()
        if emotion_result:
            self.context["last_user_emotion"] = emotion_result.get("primary")
            self.context["last_emotion_confidence"] = emotion_result.get("confidence", 0)
            if emotion_result.get("mood_value", 0.5) > 0.6:
                self.context["mood"] = "positive"
            elif emotion_result.get("mood_value", 0.5) < 0.4:
                self.context["mood"] = "negative"
            else:
                self.context["mood"] = "neutral"
        else:
            pos_words = ["хорошо", "отлично", "класс", "супер", "круто",
                         "рад", "счастлив", "весело", "love", "great",
                         "прекрасно", "замечательно"]
            neg_words = ["плохо", "грустно", "устал", "скучно", "депрессия",
                         "хреново", "ужасно", "bad", "sad", "tired"]
            for w in pos_words:
                if w in tl_lower:
                    self.context["mood"] = "positive"
                    break
            for w in neg_words:
                if w in tl_lower:
                    self.context["mood"] = "negative"
                    break

        self.context["mood_history"].append((self.context["mood"], datetime.datetime.now()))
        if len(self.context["mood_history"]) > 20:
            self.context["mood_history"].pop(0)

        topic = _detect_topic(tl)
        if topic:
            self.context["last_topic"] = topic

        # Обработка обратной связи
        last = self.context.get("last_response")
        if last:
            self.learn_from_feedback(tl, last)

        now = datetime.datetime.now()
        days = ["понедельник", "вторник", "среда", "четверг",
                "пятница", "суббота", "воскресенье"]
        months = ["января", "февраля", "марта", "апреля", "мая", "июня",
                  "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        more_phrases = ["Чем могу помочь?", "Как твои дела?",
                       "Что нового?", "Рассказывай!", "Как настроение?"]
        now_str = now.strftime("%H:%M")
        date_str = f"{now.day} {months[now.month-1]} {now.year} года"
        day_str = days[now.weekday()]

        # 1. Выученные паттерны (с высоким приоритетом)
        best_learned = None
        best_score = 0
        for trigger, response in self.learned_patterns:
            if trigger in tl_lower:
                score = self.profile["frequent_words"].get(trigger, 0)
                if score > best_score:
                    best_score = score
                    best_learned = response
        if best_learned:
            self.context["last_response"] = best_learned
            return best_learned

        # 2. Паттерны диалога с весами (приоритет выше знаний)
        candidates = []
        for pattern, responses, idx in self._patterns:
            m = pattern.match(tl)
            if m:
                for ri, resp in enumerate(responses):
                    key = f"{idx}|{ri}"
                    w = self.response_weights.get(key, {}).get("score", 0)
                    candidates.append((w, resp, idx, ri, m))

        if candidates:
            candidates.sort(key=lambda x: -x[0])
            _, r, idx, ri, m = candidates[0]

            r = str(r)
            if m.lastindex and m.lastindex >= 2:
                name = m.group(m.lastindex)
                if name and "{name}" in r:
                    r = r.replace("{name}", name.capitalize())
                    if not self.context["user_name"]:
                        self.context["user_name"] = name.capitalize()
            r = r.replace("{time}", now_str).replace("{date}", date_str)
            r = r.replace("{day}", day_str).replace("{more}",
                                                    random.choice(more_phrases))

            # Сохраняем для обучения
            key = f"{idx}|{ri}"
            if key not in self.response_weights:
                self.response_weights[key] = {"response": r, "score": 0}

            self.context["last_response"] = r
            return r

        # 3. База знаний
        for pattern, responses in self._knowledge:
            m = pattern.match(tl)
            if m:
                r = random.choice(responses)
                q = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else ""
                r = r.replace("{q}", q)
                r = r.replace("{time}", now_str).replace("{date}", date_str)
                r = r.replace("{day}", day_str).replace("{more}",
                                                        random.choice(more_phrases))
                self.context["last_response"] = r
                return r

        # 4. Follow-up по топику
        followup_map = {
            "tech":   ["А ты сам программируешь?", "Какие технологии используешь?"],
            "food":   ["Любишь готовить сам или предпочитаешь заказы?", "Какое твоё коронное блюдо?"],
            "music":  ["Какую музыку предпочитаешь?", "Ходишь на концерты?"],
            "movies": ["Какой последний фильм смотрел?", "Любишь ходить в кинотеатр?"],
            "sport":  ["Как часто занимаешься?", "Какие виды спорта любишь?"],
            "books":  ["Какую книгу сейчас читаешь?", "Что любишь читать?"],
            "work":   ["Чем занимаешься по работе?", "Нравится твоя работа?"],
            "study":  ["Что изучаешь?", "Нравится учиться?"],
            "games":  ["Во что играешь?", "На какой платформе?"],
        }
        last_topic = self.context.get("last_topic")
        if last_topic and last_topic in followup_map:
            fqs = followup_map[last_topic]
            r = f"{random.choice(MOOD_EMOJI[self.context['mood']])} {random.choice(fqs)}"
            self.context["last_response"] = r
            return r

        # 5. Факт о пользователе
        if fact:
            r = f"Круто, что ты увлекаешься {fact}! Расскажи ещё."
            self.context["last_response"] = r
            return r

        # 6. Персонализация по имени
        name = self.context.get("user_name")
        if name and self.context["turn_count"] > 1:
            emoji = random.choice(MOOD_EMOJI[self.context["mood"]])
            if self.context["mood"] == "negative":
                r = f"{emoji} {name}, всё будет хорошо. Расскажи, что случилось?"
            else:
                r = f"{emoji} {name}, поняла тебя. Что ещё?"
            self.context["last_response"] = r
            return r

        # 7. Fallback
        emoji = random.choice(MOOD_EMOJI[self.context["mood"]])
        r = f"{emoji} {random.choice(FALLBACKS)}"
        self.context["last_response"] = r
        return r
