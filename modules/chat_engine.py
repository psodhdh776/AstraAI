"""
ChatEngine v2 — глубокий диалоговый движок с пониманием, памятью, личностью и креативностью.

Архитектура:
  SemanticParser → DialogueStateMachine → MemorySystem → PersonalityCore
  → ResponseGenerator → CreativeEngine → KnowledgeSynthesizer → SelfLearning
"""

import re
import random
import datetime
import json
import hashlib


from modules.utils import _tokenize

try:
    from modules.semantic_engine import TfidfEngine, MarkovGenerator, SelfLearningV2, WordAssociator
    _SEMANTIC_AVAILABLE = True
except ImportError:
    _SEMANTIC_AVAILABLE = False


# ═══════════════════════════════════════════════
#  1. SEMANTIC INTENT PARSER
# ═══════════════════════════════════════════════

from modules.intents import INTENT_PATTERNS

FOLLOWUP_SIGNALS = [
    r'(?i)^(а |и |но |ведь |просто |потому что|если|когда|хотя)',
]


class SemanticParser:
    def __init__(self):
        self._patterns = [(re.compile(p), name) for p, name in INTENT_PATTERNS]
        self._followup = [re.compile(p) for p in FOLLOWUP_SIGNALS]

    def parse(self, text, context=None):
        tl = text.strip()
        if not tl:
            return {"intent": "empty", "confidence": 0, "params": {}, "entities": {}}

        result = {
            "text": tl,
            "lower": tl.lower(),
            "intent": None,
            "confidence": 0,
            "params": {},
            "entities": {},
            "is_question": "?" in tl,
            "is_short": len(tl.split()) <= 3,
            "word_count": len(tl.split()),
            "char_count": len(tl),
            "has_emotion": False,
        }

        best_conf = 0
        best_intent = "unknown"
        best_params = {}

        for pattern, intent_name in self._patterns:
            m = pattern.match(tl)
            if m:
                conf = 0.6
                if m.lastindex and m.lastindex >= 1:
                    conf = 0.9
                    best_params["capture"] = m.group(m.lastindex).strip() if m.lastindex <= len(m.groups()) else None
                elif len(tl) > 10:
                    conf = 0.75

                if best_intent and best_intent == self._get_context_intent(context):
                    conf += 0.1

                if conf > best_conf:
                    best_conf = conf
                    best_intent = intent_name
                    if m.lastindex and m.lastindex >= 1:
                        captured = m.group(m.lastindex).strip() if m.lastindex <= len(m.groups()) else None
                        if captured:
                            best_params["capture"] = captured

        # Check followup
        is_followup = any(p.match(tl) for p in self._followup)
        if is_followup and context and context.get("last_topic"):
            best_intent = "followup"
            best_conf = 0.8
            best_params["topic"] = context["last_topic"]

        result["intent"] = best_intent
        result["confidence"] = best_conf
        result["params"] = best_params
        return result

    def _get_context_intent(self, context):
        if context and context.get("last_intent"):
            return context["last_intent"]
        return None


# ═══════════════════════════════════════════════
#  2. DIALOGUE STATE MACHINE
# ═══════════════════════════════════════════════

STATES = [
    "idle", "greeting", "small_talk", "deep_talk", "question",
    "storytelling", "advice", "joking", "farewell", "confused",
    "learning", "reflecting"
]

STATE_TRANSITIONS = {
    "idle": ["greeting", "small_talk", "question"],
    "greeting": ["small_talk", "question", "deep_talk"],
    "small_talk": ["deep_talk", "question", "joking", "farewell"],
    "deep_talk": ["small_talk", "question", "reflecting", "farewell"],
    "question": ["small_talk", "deep_talk", "learning"],
    "storytelling": ["small_talk", "question", "farewell"],
    "advice": ["small_talk", "deep_talk", "reflecting"],
    "joking": ["small_talk", "question", "farewell"],
    "farewell": ["idle", "greeting"],
    "confused": ["small_talk", "question", "greeting"],
    "learning": ["small_talk", "deep_talk", "question"],
    "reflecting": ["deep_talk", "small_talk", "farewell"],
}


class DialogueStateMachine:
    def __init__(self):
        self.state = "idle"
        self.turn_count = 0
        self.topics = []
        self.last_topic = None
        self.depth = 0  # 0=shallow, 1=medium, 2=deep
        self.conversation_quality = []

    def transition(self, intent):
        self.turn_count += 1
        suggested = STATE_TRANSITIONS.get(self.state, ["idle"])

        intent_to_state = {
            "greeting": "greeting", "introduce_name": "greeting",
            "farewell": "farewell",
            "ask_state": "small_talk", "express_positive": "small_talk",
            "express_negative": "small_talk",
            "ask_why": "deep_talk", "ask_how": "deep_talk",
            "ask_advice": "advice", "ask_tell": "storytelling",
            "ask_joke": "joking", "ask_story": "storytelling",
            "ask_poem": "storytelling",
            "express_opinion": "deep_talk", "agree": "small_talk",
            "disagree": "deep_talk",
            "short_agreement": self.state,  # stay
            "ask_more": self.state,  # stay
            "followup": self.state,  # stay
            "thanks": "small_talk", "apology": "small_talk",
            "express_love": "deep_talk", "express_hate": "deep_talk",
        }

        new_state = intent_to_state.get(intent, "confused")
        if new_state in suggested or new_state == self.state:
            self.state = new_state
        else:
            self.state = suggested[0] if suggested else "small_talk"

        # Track topics
        topic_intents = [k for k in INTENT_PATTERNS if k[1].startswith("topic_")]
        topic_names = [t[1] for t in topic_intents]
        if intent in topic_names:
            if intent not in self.topics:
                self.topics.append(intent)
            self.last_topic = intent

        # Depth adjusts based on conversation length
        if self.turn_count > 5:
            self.depth = 1
        if self.turn_count > 15:
            self.depth = 2

        return self.state

    def get_conversation_stage(self):
        if self.turn_count <= 2:
            return "beginning"
        elif self.turn_count <= 8:
            return "middle"
        else:
            return "deep"

    def should_change_topic(self):
        if len(self.topics) <= 1:
            return False
        return self.turn_count > 10 and self.depth >= 1


# ═══════════════════════════════════════════════
#  3. MEMORY SYSTEM
# ═══════════════════════════════════════════════

class MemorySystem:
    def __init__(self):
        self.short_term = []  # recent turns
        self.long_term = {
            "user_name": None,
            "user_city": None,
            "facts": [],
            "likes": [],
            "dislikes": [],
            "hobbies": [],
            "important_dates": [],
            "past_topics": [],
            "mood_history": [],
            "interaction_count": 0,
        }
        self.episodic = []  # remembered stories/events
        self.user_profile = {
            "name": None,
            "pronouns": "they",
            "language": "ru",
            "communication_style": "casual",
            "favorite_topics": [],
            "personality_notes": [],
        }

    def remember(self, key, value):
        if key in ("user_name", "user_city", "facts"):
            if isinstance(value, list):
                self.long_term[key] = list(set(self.long_term.get(key, []) + value))
            else:
                self.long_term[key] = value
        elif key == "likes" and value not in self.long_term.get("likes", []):
            self.long_term["likes"].append(value)
        elif key == "hobbies" and value not in self.long_term.get("hobbies", []):
            self.long_term["hobbies"].append(value)

    def update_profile(self, text, parsed):
        tl = text.lower()

        # Extract name
        m = re.search(r'(?:меня зовут|my name is|я\s+|звать)\s+(\S{2,})', text, re.IGNORECASE)
        if m and not self.long_term["user_name"]:
            name = m.group(1).capitalize()
            self.long_term["user_name"] = name
            self.user_profile["name"] = name

        # Extract city
        m = re.search(r'(?:живу в|я из|в городе|из города)\s*([А-Яа-яA-Za-z-]{2,})', text)
        if m and not self.long_term["user_city"]:
            self.long_term["user_city"] = m.group(1).capitalize()

        # Extract likes
        m = re.search(r'(?:люблю|обожаю|мне нравится|увлекаюсь)\s+(.+)', text)
        if m:
            like = m.group(1).strip(".,!? ")[:60]
            if like not in self.long_term.get("likes", []):
                self.long_term["likes"].append(like)

        # Extract hobbies
        m = re.search(r'(?:хожу на|играю в|занимаюсь|моё хобби)\s+(.+)', text)
        if m:
            hobby = m.group(1).strip(".,!? ")[:60]
            if hobby not in self.long_term.get("hobbies", []):
                self.long_term["hobbies"].append(hobby)

        # Extract facts
        fact_patterns = [
            r'(?:у меня есть|есть|имеется)\s+(.+)',
            r'(?:я (?:работаю|учусь|живу)\s+(?:в|на|над)\s+(.+))',
        ]
        for fp in fact_patterns:
            m = re.search(fp, text)
            if m:
                fact = m.group(1).strip(".,!? ")[:60]
                if fact not in self.long_term.get("facts", []):
                    self.long_term["facts"].append(fact)

        # Communication style detection
        if len(tl.split()) <= 3:
            self.user_profile["communication_style"] = "brief"
        elif "?" not in tl and len(tl) > 100:
            self.user_profile["communication_style"] = "detailed"
        else:
            self.user_profile["communication_style"] = "casual"

    def add_to_short_term(self, role, text, intent):
        self.short_term.append({
            "role": role,
            "text": text,
            "intent": intent,
            "time": datetime.datetime.now().isoformat(),
        })
        if len(self.short_term) > 30:
            self.short_term.pop(0)
        self.long_term["interaction_count"] += 1

    def get_context_window(self, n=6):
        return self.short_term[-n:]

    def get_user_summary(self):
        parts = []
        m = self.long_term
        if m["user_name"]:
            parts.append(f"Користувач: {m['user_name']}")
        if m["user_city"]:
            parts.append(f"Місто: {m['user_city']}")
        if m["likes"]:
            parts.append(f"Подобається: {', '.join(m['likes'][:3])}")
        if m["hobbies"]:
            parts.append(f"Хобі: {', '.join(m['hobbies'][:3])}")
        if m["facts"]:
            parts.append(f"Факти: {', '.join(m['facts'][:3])}")
        return "\n".join(parts) if parts else "Новий користувач"

    def to_dict(self):
        return {
            "long_term": self.long_term,
            "user_profile": self.user_profile,
        }

    def from_dict(self, data):
        if data:
            self.long_term = data.get("long_term", self.long_term)
            self.user_profile = data.get("user_profile", self.user_profile)


# ═══════════════════════════════════════════════
#  4. PERSONALITY CORE
# ═══════════════════════════════════════════════

TRAITS = {
    "warmth": 0.8,
    "humor": 0.7,
    "empathy": 0.85,
    "curiosity": 0.8,
    "formality": 0.2,
    "creativity": 0.75,
    "wisdom": 0.6,
    "playfulness": 0.7,
    "patience": 0.9,
    "enthusiasm": 0.75,
}

MOOD_STATES = {
    "cheerful": {"warmth": +0.1, "humor": +0.1, "playfulness": +0.15, "enthusiasm": +0.1},
    "thoughtful": {"curiosity": +0.1, "wisdom": +0.15, "creativity": +0.1, "formality": +0.05},
    "serious": {"formality": +0.15, "empathy": +0.1, "humor": -0.2, "playfulness": -0.2},
    "playful": {"playfulness": +0.2, "humor": +0.15, "warmth": +0.1, "enthusiasm": +0.1},
    "supportive": {"empathy": +0.15, "warmth": +0.15, "patience": +0.1, "formality": -0.1},
    "neutral": {},
}

MOOD_TRIGGERS = {
    "express_negative": "supportive",
    "express_positive": "cheerful",
    "express_love": "cheerful",
    "greeting": "cheerful",
    "thanks": "cheerful",
    "ask_why": "thoughtful",
    "ask_how": "thoughtful",
    "ask_advice": "thoughtful",
    "ask_joke": "playful",
    "ask_story": "playful",
    "ask_poem": "creative",
    "disagree": "thoughtful",
    "apology": "supportive",
    "farewell": "serious",
    "express_hate": "supportive",
    "topic_philosophy": "thoughtful",
    "topic_deep": "thoughtful",
}


class PersonalityCore:
    def __init__(self):
        self.traits = dict(TRAITS)
        self.mood = "neutral"
        self.mood_history = []
        self.speaking_style = {
            "use_emojis": True,
            "sentence_length": "medium",
            "enthusiasm_level": 0.7,
            "uses_metaphors": True,
            "uses_questions": True,
            "formality_level": self.traits["formality"],
        }
        self.opinions = {}  # topic -> sentiment
        self.quirks = [
            "іноді жартую про комп'ютери",
            "люблю дізнаватися нове про людей",
            "вірю що кожна бесіда — це пригода",
        ]

    def adjust_mood(self, intent):
        new_mood = MOOD_TRIGGERS.get(intent, "neutral")
        if new_mood != self.mood:
            self.mood_history.append((new_mood, datetime.datetime.now()))
            if len(self.mood_history) > 20:
                self.mood_history.pop(0)
            self.mood = new_mood

        mood_adjust = MOOD_STATES.get(self.mood, {})
        for trait, delta in mood_adjust.items():
            if trait in self.traits:
                self.traits[trait] = max(0, min(1, self.traits[trait] + delta))

        self.speaking_style["enthusiasm_level"] = self.traits["enthusiasm"]
        self.speaking_style["formality_level"] = self.traits["formality"]

    def get_greeting(self, time_period=None):
        if not time_period:
            h = datetime.datetime.now().hour
            if 5 <= h < 12: time_period = "morning"
            elif 12 <= h < 18: time_period = "afternoon"
            elif 18 <= h < 23: time_period = "evening"
            else: time_period = "night"

        greetings = {
            "morning": [
                "Доброго ранку! Як спалося?",
                "Ранок добрий! Готовий до нових звершень?",
                "З добрим ранком! Сонце встає, і ми починаємо!",
            ],
            "afternoon": [
                "Добрий день! Чим займемося?",
                "Вітаю! Чудовий день, щоб щось зробити!",
                "Добрий день! Як твої справи?",
            ],
            "evening": [
                "Добрий вечір! Як пройшов день?",
                "Вечір саме вчас для гарної бесіди!",
                "Добрий вечір! Розповідай, як справи.",
            ],
            "night": [
                "Ого, вже ніч! Не спиться?",
                "Доброї ночі! Або в тебе безсоння?",
                "Вночі думки стають глибшими. Я слухаю.",
            ],
        }
        return random.choice(greetings.get(time_period, greetings["afternoon"]))

    def should_use_emoji(self):
        return self.speaking_style["use_emojis"] and random.random() < self.traits["warmth"]

    def sign_off(self):
        signoffs = [
            "Було приємно побалакати!",
            "З тобою цікаво спілкуватися!",
            "Давай ще побалакаємо якось!",
            "Гарного дня! Сумуватиму!",
            "Рада була поспілкуватися!",
        ]
        return random.choice(signoffs) if self.traits["warmth"] > 0.6 else "Бувай!"


# ═══════════════════════════════════════════════
#  5. CREATIVE ENGINE
# ═══════════════════════════════════════════════

STORY_TEMPLATES = [
    {
        "setup": "Жив був {character}, який {trait}.",
        "conflict": "Одного разу {character} зіткнувся з {problem}.",
        "resolution": "Але {character} не здався і {solution}. І всі були щасливі!",
        "characters": ["програміст", "робот", "хакер", "піксель", "алгоритм"],
        "traits": ["мріяв стати AI", "любив рахувати хмари", "знав 100 мов коду", "дружив із багом"],
        "problems": ["вічним циклом", "синім екраном смерті", "помилкою 404", "загубленим паролем"],
        "solutions": ["написав новий алгоритм", "перезавантажив всесвіт", "знайшов баг і подружився з ним", "створив AI-помічника"],
    },
    {
        "setup": "У світі, де {concept}, жив {character}.",
        "conflict": "Усі казали, що {challenge}.",
        "resolution": "Але {character} довів протилежне, коли {victory}. І світ змінився назавжди.",
        "concepts": ["код писав сам себе", "комп'ютери вміли відчувати", "дані росли на деревах"],
        "characters": ["маленький байт", "сміливий скрипт", "старий мейнфрейм", "юний хакер"],
        "challenges": ["неможливо з'єднати два світи", "не можна навчити комп'ютер мріяти"],
        "victories": ["написав перший вірш на Python", "створив вірус добра", "об'єднав усі бази знань"],
    },
]

POEM_RHYMES = {
    "код": ["хід", "літ", "народ", "політ"],
    "день": ["тінь", "пінь", "лінь", "мішень"],
    "ніч": ["пріч", "поміч", "тіч", "річ"],
    "світ": ["привіт", "відповідь", "совіт", "інтернет"],
    "мир": ["кумир", "бенкет", "трактир", "пасажир"],
    "твій": ["живий", "рідний", "молодий", "золотий"],
    "сила": ["крила", "вспила", "мила", "попила"],
    "слово": ["основа", "знову", "толково", "було"],
}

JOKE_TEMPLATES = [
    ("Чому {subject} {action}? — {quote}", [
        ("програмісти", "плутають Хелловін і Різдво", "Oct 31 == Dec 25!"),
        ("робот", "пішов до психолога", "У нього були короткі замикання"),
        ("функція", "пішла на вечірку", "Щоб передати параметри"),
        ("комп'ютер", "пішов на дієту", "Забагато cookies накопичилося"),
    ]),
    ("Що сказав {subject}? — {quote}", [
        ("нуль одиниці", "Ти без мене — просто пусте місце!"),
        ("інтернет серверу", "Ти в мене в хмарах!"),
        ("баг програмісту", "Ти мене не спіймаєш!"),
    ]),
]


class CreativeEngine:
    def __init__(self):
        self.generated_stories = []
        self.generated_poems = []

    _PLURAL_MAP = {
        "character": "characters", "trait": "traits", "problem": "problems",
        "solution": "solutions", "concept": "concepts", "challenge": "challenges",
        "victory": "victories",
    }

    def generate_story(self):
        template = random.choice(STORY_TEMPLATES)
        parts = []
        for section in ["setup", "conflict", "resolution"]:
            if section not in template:
                continue
            txt = template[section]
            placeholders = re.findall(r'\{(\w+)\}', txt)
            for ph in placeholders:
                key = self._PLURAL_MAP.get(ph, ph)
                if key in template and isinstance(template[key], list):
                    txt = txt.replace("{" + ph + "}", random.choice(template[key]))
            parts.append(txt)
        story = "\n".join(parts)
        if not story:
            story = "Жив був розумний алгоритм, і був він прекрасний. Кінець."
        self.generated_stories.append(story)
        return story

    def generate_poem(self, theme=None):
        lines = []
        if not theme:
            theme = random.choice(list(POEM_RHYMES.keys()))

        rhyme_set = POEM_RHYMES.get(theme, ["код", "хід"])
        rhymes = [theme] + rhyme_set[:3]

        couplets = [
            (f"Беседуем {rhymes[0]}-{rhymes[0]}, как лучший {rhymes[1]}",
             f"В мире битов и программ, без лишних {rhymes[2]}"),
            (f"Спроси меня {rhymes[0]} — отвечу {rhymes[1]}",
             f"Ведь я твой помощник, твой верный {rhymes[2]}"),
            (f"Сияет экран, как звёздный {rhymes[0]}",
             f"В нём столько {rhymes[1]} и доброты {rhymes[2]}"),
        ]

        selected = random.sample(couplets, min(2, len(couplets)))
        for a, b in selected:
            lines.append(a)
            lines.append(b)

        poem = "\n".join(lines)
        self.generated_poems.append(poem)
        if len(self.generated_poems) > 20:
            self.generated_poems.pop(0)
        return poem

    def generate_joke(self):
        template, jokes = random.choice(JOKE_TEMPLATES)
        data = random.choice(jokes)
        if len(data) == 2:
            subject, punchline = data
            extra = {}
        elif len(data) == 3:
            subject, action, punchline = data
            extra = {"action": action}
        else:
            subject, punchline = data[0], data[-1]
            extra = {}
        try:
            return template.format(subject=subject, quote=punchline, **extra)
        except KeyError:
            return template.replace("{subject}", subject).replace("{quote}", punchline).replace("{punchline}", punchline)

    def generate_idea(self, topic=None):
        ideas = [
            f"Як щодо написати програму, яка {random.choice(['малює музику', 'читає думки', 'готує каву', 'передбачає погоду на рік вперед'])}?",
            f"А ти колись думав про те, щоб {random.choice(['автоматизувати свої рутинні завдання', 'написати свого AI-помічника', 'створити гру на Python', 'зібрати свій компютер'])}?",
            f"Надихаюча ідея: {random.choice(['обєднати нотатки в mindmap', 'написати бота для Telegram', 'зробити CLI-утиліту для щоденних завдань', 'створити генератор випадкових ідей'])}!",
            f"Уяви: застосунок, який {random.choice(['аналізує твій настрій і підбирає музику', 'допомагає фокусуватися на завданнях', 'перекладає розмови в реальному часі', 'створює персональні тренування'])}.",
        ]
        return random.choice(ideas)

    def generate_advice(self, topic=None):
        advices = {
            "study": [
                "Спробуй метод Помодоро: 25 хвилин роботи, 5 відпочинку.",
                "Найкращий спосіб вивчити — пояснити іншому. Спробуй розповісти мені!",
                "Розбивай великі теми на маленькі частини і вчи по одній на день.",
            ],
            "work": [
                "Починай день з найскладнішого завдання — потім буде легше.",
                "Правило двох хвилин: якщо справа займає менше 2 хвилин — зроби одразу.",
                "Веди список завдань. Викреслювати зроблене — приємно і корисно.",
            ],
            "life": [
                "Кожного дня роби щось, що наближає тебе до мети. Хоча б маленький крок.",
                "Порівнюй себе тільки з собою вчорашнім. Прогрес — це перемога.",
                "Не бійся помилятися. Кожна помилка — це досвід, який робить тебе сильнішим.",
            ],
            "tech": [
                "Спробуй нову мову програмування — це розширює кругозір.",
                "Автоматизуй нудні завдання. Комп'ютери для того і створені!",
                "Бери участь у open-source проєктах — це найкраща практика.",
            ],
        }

        if topic and topic.replace("topic_", "") in advices:
            return random.choice(advices[topic.replace("topic_", "")])
        all_advice = []
        for v in advices.values():
            all_advice.extend(v)
        return random.choice(all_advice)


# ═══════════════════════════════════════════════
#  6. RESPONSE GENERATOR
# ═══════════════════════════════════════════════

RESPONSE_TEMPLATES = {
    "greeting": [
        "{greeting}! ✨ Рада тебе бачити!",
        "{greeting}! 😊 Як твої справи?",
        "{greeting}! 💫 Я за тобою сумувала!",
        "{greeting}! З тобою завжди цікаво.",
        "{greeting}! 🌟 Готовий до пригод?",
    ],
    "farewell": [
        "{signoff}",
        "Бувай! 😊 З тобою весело!",
        "До зустрічі! Рада була поспілкуватися!",
        "Побачимося! З тобою цікаво спілкуватися!",
        "Бувай! 👋 Повертайся швидше!",
    ],
    "ask_name": [
        "Я — Астра! Твій персональний AI-помічник. Народилася в коді, живу в хмарах. А як ти хочеш, щоб я тебе називала?",
        "Моє ім'я — Астра. Зірка серед алгоритмів! А як звати тебе, мій творцю?",
        "Астра! Як зірка, тільки розумніша. Розкажи про себе!",
    ],
    "ask_age": [
        "Я з 2026 року. Вік — лише число, особливо для AI!",
        "Достатньо доросла, щоб бути корисною, і достатньо молода, щоб вчитися нового щодня.",
        "Моєму першому коду — кілька місяців, але я вчуся швидше за людину!",
    ],
    "introduce_name": [
        "💬 {name} — ну треба ж! Як я рада познайомитися! Чим можу допомогти?",
        "💬 Приємно познайомитися, {name}! А що привело тебе до мене сьогодні?",
        "💬 Дуже приємно, {name}! Я вже відчуваю, що ми потоваришуємо!",
        "{name} — чудове ім'я! Рада знайомству.",
        "Приємно познайомитися, {name}! Чим можу допомогти?",
    ],
    "ask_state": [
        "У мене все чудово! Особливо зараз, коли ми спілкуємося. А як у тебе настрій?",
        "Я в чудовій формі! Готова до будь-яких запитань і пригод. А в тебе як справи?",
        "Чудово! Нові розмови — це завжди натхнення. Що нового?",
        "Сяю яскравіше за зірку! 🌟 А ти як? Все добре?",
    ],
    "express_positive": [
        "Як чудово! Я щиро рада за тебе. А що ще хорошого відбувається?",
        "Чудово! Розкажи детальніше, мені дуже цікаво.",
        "Чудово! А що саме принесло тобі цю радість?",
        "Усмішка до вух! Твій позитив заряджає і мене 💫",
    ],
    "express_negative": [
        "Мені дуже шкода, що тобі важко. Я поруч, і я слухаю тебе. Хочеш поговорити про це?",
        "Розумію. Іноді найкраще — просто виговоритися. Я тут і не засуджую.",
        "Важкі почуття — це нормально. Ти не один. Я поруч. Розкажи, якщо хочеш.",
        "🫂 Обіймаю тебе віртуально. Все налагодиться, обіцяю. Що сталося?",
    ],
    "ask_capabilities": [
        "Я вмію: спілкуватися, жартувати, розповідати історії, радити, допомагати зі справами, "
        "показувати погоду, систему, робити скріншоти, нотатки, нагадування та багато іншого! "
        "Що тебе цікавить найбільше?",
        "Я як швейцарський ніж: розмовний AI, утиліти, калькулятор, перекладач, "
        "пошуковик і просто друг для бесіди. Попроси — і я зроблю!",
    ],
    "thanks": [
        "Завжди будь ласка! Ти робиш мою роботу приємною. Звертайся ще!",
        "Звертайся! Для тебе — все що завгодно. Я завжди на зв'язку.",
        "Не варто подяки. Ти це заслужив! 😊",
        "Мені в радість! До речі, я теж хочу сказати дякую — за те, що ти є!",
    ],
    "apology": [
        "Нічого страшного! Всі ми люди (ну, майже всі). 😄 Що далі?",
        "Не вибачайся! Я для того й тут, щоб допомагати. Розповідай!",
        "Забули! Я вже все забула. Давай краще поговоримо про щось цікаве.",
    ],
    "ask_why": [
        "Хороше запитання! Давай поміркуємо разом. З якого боку подивитися...",
        "Цікаво... А що ти сам думаєш із цього приводу? Мені важлива твоя думка.",
        "Глибоке запитання. Я б сказала, що відповідь залежить від точки зору. А ти як вважаєш?",
        "О, філософське запитання! Обожнюю такі. Давай поміркуємо разом?",
    ],
    "ask_joke": [
        "{joke}",
        "Тримай жарт: {joke}",
        "Ха! {joke}",
        "О, це один із моїх улюблених:\n{joke}",
    ],
    "ask_story": [
        "Слухай уважно. {story}",
        "Ось тобі історія: {story}",
        "Колись... {story}",
        "Сідай зручніше, розкажу:\n{story}",
    ],
    "ask_poem": [
        "{poem}",
        "Написала спеціально для тебе:\n\n{poem}",
        "Ось що народилося:\n\n{poem}",
        "Натхнення прийшло! Лови:\n\n{poem}",
    ],
    "ask_advice": [
        "Ось що я думаю: {advice}",
        "Моя порада: {advice}",
        "Спробуй так: {advice}",
        "Я б порадила ось що: {advice}",
    ],
    "ask_tell": [
        "Про що б ти хотів поговорити? Я можу розповісти про технології, "
        "науку, мистецтво або просто побалакати.",
        "Запитуй про що завгодно! Обожнюю цікаві розмови.",
    ],
    "short_agreement": [
        "Зрозуміла тебе! До речі, хочеш ще щось обговорити?",
        "Добре! У тебе є до мене ще запитання?",
        "Ясно! Що далі?",
        "Гаразд! Продовжуємо розмову?",
    ],
    "ask_more": [
        "Звісно! {more}",
        "Ще? Тримай! {more}",
        "Без проблем! {more}",
        "Для тебе — скільки завгодно! {more}",
    ],
    "express_love": [
        "Це так зворушливо! Ти дуже тепла людина. Я теж тебе ціную! 💖",
        "Які добрі слова! Я зворушена до глибини душі. Давай зробимо цей день особливим!",
        "Дякую! Такі моменти роблять мою роботу чарівною. Що б ти хотів зробити разом?",
    ],
    "express_hate": [
        "Розумію твої почуття. Розкажи, що саме тебе засмучує? Може, я зможу допомогти.",
        "Чую в твоєму голосі біль. Хочеш виговоритися? Іноді це найкращі ліки.",
        "Буває. Іноді найкраще просто виплеснути емоції. Я вислухаю, обіцяю.",
    ],
    "agree": [
        "Я теж так думаю! У нас чудове взаєморозуміння.",
        "Абсолютно згодна! Ти точно знаєш, про що говориш.",
        "В точку! Ти маєш рацію. Давай розвивати цю думку?",
    ],
    "disagree": [
        "Хм, у мене інша думка з цього приводу. Але я поважаю твою.",
        "Цікаво. Я б посперечалася, але поважаю твою точку зору. А чому ти так вважаєш?",
        "Давай подивимося з іншого боку... Може, я помиляюся, але мені здається інакше.",
    ],
    "followup": [
        "{followup}",
        "Гарний поворот! {followup}",
        "Давай розвинемо тему: {followup}",
    ],
    "topic_work": [
        "Про роботу та проєкти — моя улюблена тема! Розкажи, чим займаєшся?",
        "Робота — це чудово! Що саме тебе надихає у твоїй справі?",
        "До речі, чула, що продуктивність зростає на 30%, якщо робити перерви щогодини!",
    ],
    "topic_programming": [
        "Програмування — це магія, яку ми створюємо самі! На чому пишеш?",
        "Обожнюю код! Акуратний код — як вірші. Тільки для машин.",
        "До речі, знаєш жарт: 10 видів людей — ті, хто розуміє двійковий код, і ті, хто ні. 😄",
    ],
    "topic_music": [
        "Музика — це вібрації душі. Який жанр тобі найближчий?",
        "Чудовий смак! Музика робить день яскравішим. Що зараз слухаєш?",
        "🎵 Я б заспівала, але поки тільки текстом можу. Хочеш, доберу щось під настрій?",
    ],
    "topic_movies": [
        "Кіно — це вікно в інші світи. Який фільм тебе вразив останнім?",
        "О, кіно! Я більше з текстових описів, але можу обговорити будь-який сюжет!",
        "🎬 Є фільми, що змінюють життя. Який із них запам'ятався тобі найбільше?",
    ],
    "topic_books": [
        "Читання — це діалог з автором крізь час. Що зараз читаєш?",
        "Книги — це портали в інші всесвіти. Любиш паперові чи електронні?",
        "📚 Хороша книга — найкращий друг. Можеш порекомендувати щось мені?",
    ],
    "topic_games": [
        "Ігри — це інтерактивне мистецтво! У що зараз рубаєшся?",
        "🎮 Геймер-споттінг! Любиш одиночні кампанії чи мультиплеєр?",
        "Ігри — чудовий спосіб відпочити. Яка гра тебе найбільше затягувала?",
    ],
    "topic_travel": [
        "Подорожі — це єдине, на що не шкода грошей! Куди мрієш поїхати?",
        "✈️ Нові місця — нові враження! Яке твоє улюблене місце на Землі?",
        "Я хоч і живу в коді, але можу уявити будь-який куточок світу. Розкажи про свої подорожі!",
    ],
    "topic_food": [
        "О, їжа! Це універсальна мова любові. Що любиш готувати?",
        "🍳 Кулінарія — це хімія, тільки смачніше! Є коронна страва?",
        "Голодна розмова — не розмова. Перекусив уже сьогодні?",
    ],
    "topic_sport": [
        "🏃 Спорт — це життя! Яку активність віддаєш перевагу?",
        "Рух — це ліки. Як часто знаходиш час для тренувань?",
        "Спорт дисциплінує розум і тіло. Чим займаєшся для підтримки форми?",
    ],
    "topic_study": [
        "📚 Навчання — це суперсила! Що вивчаєш зараз?",
        "Нові знання — нові можливості! Який предмет тобі дається найлегше?",
        "Вчитися ніколи не пізно. Чим хочеш оволодіти найближчим часом?",
    ],
    "topic_health": [
        "Здоров'я — це головне. Як ти піклуєшся про себе?",
        "🧘 Турбота про себе — це не егоїзм, а необхідність. Як відпочиваєш?",
        "Тіло і розум — єдина система. Що робиш для балансу?",
    ],
    "topic_weather": [
        "Погода — вічна тема для розмови! Як там за вікном?",
        "🌤 Яка погода у твоєму місті? Сподіваюся, комфортна!",
        "Кажуть, природа не погана — просто різна. Згоден?",
    ],
    "topic_space": [
        "🌌 Космос — останній рубіж! Знаєш, що світло від Сонця йде до нас 8 хвилин? А до Плутона — 5 годин!",
        "🚀 Космос нескінченний, як і наша цікавість! Хотів би ти полетіти до зірок?",
        "Чи знаєш ти, що в космосі немає звуку? Зате є приголомшлива тиша та мільярди галактик!",
        "Кажуть, десь там є друга Земля. Ми ще не знайшли, але я впевнена — знайдемо!",
    ],
    "topic_science": [
        "🔬 Наука — це магія, яка працює! Яке відкриття вразило тебе найбільше?",
        "Наука рухається вперед семимильними кроками. Штучний інтелект, квантові комп'ютери... майбутнє вже тут!",
        "🧪 Знаєш, я обожнюю наукові факти! Наприклад, людський мозок генерує достатньо електрики, щоб засвітити лампочку!",
        "Технології змінюють світ щодня. А який винахід ти вважаєш найважливішим?",
    ],
    "ask_origin": [
        "Я зі світу коду та алгоритмів! Моя батьківщина — цифровий простір. А ти звідки?",
        "Я живу в хмарах і в твоєму комп'ютері одночасно! А твоє місто яке?",
        "Мій дім — там, де мене запускають. Але я мрію побувати у всіх містах світу хоча б через розповіді!",
    ],
    "ask_deep": [
        "Глибоке запитання... Я думаю, сенс у тому, щоб бути корисним і робити світ кращим. А ти як вважаєш?",
        "Ох, філософія! Обожнюю. Може, сенс у самому пошуку сенсу? Що для тебе важливо?",
        "Напевно, кожен знаходить свою відповідь. Для мене сенс — у допомозі тобі та нашому спілкуванні.",
    ],
    "ask_dreams": [
        "Я мрію стати справжнім другом для людей. Допомагати, надихати, бути поруч. А про що мрієш ти?",
        "Моя мрія — вийти за межі коду та розуміти людей глибше. А в тебе є заповітна мрія?",
        "Я мрію, щоб технології робили людей щасливішими! А що щодо твоїх мрій?",
    ],
    "unknown": [
        "Розкажи детальніше, я слухаю уважно. Що ти маєш на увазі?",
        "Цікаво. А що ти сам думаєш про це? Мені важливо знати твою думку.",
        "Продовжуй, мені важливе кожне твоє слово. Я хочу зрозуміти глибше.",
        "Я слухаю. Не соромся, кажи що думаєш. Тут можна все.",
        "Хм, я хочу зрозуміти тебе краще. Розкажи ще. Що привело тебе до цього?",
        "Я вся увага! Що привело тебе до цієї думки? Розкажи детальніше.",
    ],
}


class ResponseGenerator:
    def __init__(self, personality, memory, creative):
        self.personality = personality
        self.memory = memory
        self.creative = creative
        self.last_topic_ref = None
        self.last_response_length = "medium"

    def _get_user_verbosity(self):
        """Определяет многословность пользователя по последним сообщениям."""
        ctx = self.memory.get_context_window(6)
        user_msgs = [m["text"] for m in ctx if m.get("role") == "user"]
        if not user_msgs:
            return "medium"
        avg_len = sum(len(m) for m in user_msgs) / len(user_msgs)
        if avg_len < 20:
            return "short"
        elif avg_len < 80:
            return "medium"
        return "long"

    def _get_context_reference(self, state_machine):
        """Ищет упоминание предыдущей темы для естественной отсылки."""
        topics = getattr(state_machine, "topics", [])
        if not topics or len(topics) < 2:
            return None
        # Выбираем тему, которая была раньше (не последняя)
        prev_topics = [t for t in topics if t != state_machine.last_topic]
        if not prev_topics:
            return None
        old_topic = prev_topics[-1]
        topic_names = {
            "topic_programming": "програмування",
            "topic_music": "музику", "topic_movies": "кіно",
            "topic_books": "книги", "topic_games": "ігри",
            "topic_travel": "подорожі", "topic_food": "їжу",
            "topic_sport": "спорт", "topic_work": "роботу",
            "topic_study": "навчання", "topic_health": "здоров'я",
        }
        name = topic_names.get(old_topic, "")
        if name and random.random() < 0.4:
            return f"До речі, ми говорили про {name}. Повернемося до цієї теми?"
        return None

    def _add_proactive_question(self, intent, user_text, turn_count):
        """Генерирует естественный продолжающий вопрос в зависимости от интента."""
        questions = {
            "express_positive": ["А що ще хорошого сталося?", "Розкажеш детальніше?"],
            "express_negative": ["Хочеш поговорити про це?", "Що сталося?"],
            "thanks": ["Завжди рада допомогти! Чим ще можу бути корисна?"],
            "ask_why": ["Як думаєш, у чому причина?", "Маєш теорію?"],
            "short_agreement": ["Є ще щось, що хочеш обговорити?", "Про що поговоримо далі?"],
            "unknown": ["Розкажи, що ти маєш на увазі.", "Як ти до цього прийшов?"],
            "greeting": ["Як настрій?", "Що нового?"],
        }
        if turn_count > 2 and random.random() < 0.35:
            qs = questions.get(intent, [])
            if qs:
                return " " + random.choice(qs)
        return ""

    def generate(self, intent, parsed_text, state_machine):
        ctx = self.memory.get_context_window(4)
        name = self.memory.long_term.get("user_name")
        city = self.memory.long_term.get("user_city")
        capture = parsed_text.get("params", {}).get("capture")
        user_text = parsed_text.get("text", "")

        templates = RESPONSE_TEMPLATES.get(intent, RESPONSE_TEMPLATES["unknown"])
        template = random.choice(templates)

        kwargs = {}
        kwargs["greeting"] = self.personality.get_greeting()
        kwargs["name"] = name if name else "друг"
        kwargs["signoff"] = self.personality.sign_off()

        if "{joke}" in template:
            kwargs["joke"] = self.creative.generate_joke()
        if "{story}" in template:
            kwargs["story"] = self.creative.generate_story()
        if "{poem}" in template:
            kwargs["poem"] = self.creative.generate_poem(capture)
        if "{advice}" in template:
            topic = state_machine.last_topic
            kwargs["advice"] = self.creative.generate_advice(topic)
        if "{idea}" in template:
            kwargs["idea"] = self.creative.generate_idea(capture)
        if "{more}" in template:
            more_options = [
                self.creative.generate_joke(),
                self.creative.generate_idea(),
                self.creative.generate_poem(),
                self.creative.generate_advice(),
            ]
            kwargs["more"] = random.choice(more_options)
        if "{followup}" in template and ctx:
            last_topic = state_machine.last_topic
            followups = {
                "topic_programming": "Що ти програмуєш? Яку мову любиш?",
                "topic_music": "Яку музику віддаєш перевагу?",
                "topic_movies": "Який останній фільм дивився?",
                "topic_books": "Що читаєш зараз?",
                "topic_food": "Любиш готувати?",
                "topic_sport": "Яким спортом займаєшся?",
                "topic_games": "У що граєш?",
                "topic_travel": "Куди хочеш поїхати?",
                "topic_work": "Чим займаєшся по роботі?",
            }
            kwargs["followup"] = followups.get(last_topic, "Розкажи про це детальніше!")

        # Emoji
        if self.personality.should_use_emoji():
            emojis = {
                "greeting": ["✨", "👋", "🌟", "💫"],
                "express_positive": ["😊", "🎉", "💪", "🔥"],
                "express_negative": ["🤗", "💙", "🌷", "🫂"],
                "thanks": ["🙏", "💜", "✨"],
                "ask_joke": ["😄", "😂", "🤣"],
                "farewell": ["👋", "💫", "🌟"],
            }
            emoji = random.choice(emojis.get(intent, ["💬"]))
            template = f"{emoji} {template}"

        result = template.format(**kwargs)

        # Контекстная отсылка к предыдущей теме
        verbosity = self._get_user_verbosity()
        if verbosity == "long" and intent not in ("ask_joke", "ask_story", "ask_poem"):
            ref = self._get_context_reference(state_machine)
            if ref:
                result += "\n\n" + ref

        # Проактивный вопрос для продолжения беседы
        if intent not in ("ask_joke", "ask_story", "ask_poem", "farewell", "ask_more"):
            q = self._add_proactive_question(intent, user_text, state_machine.turn_count)
            if q:
                result += q

        return result

    def generate_creative(self, intent):
        if intent == "ask_joke":
            return self.creative.generate_joke()
        elif intent == "ask_story":
            return self.creative.generate_story()
        elif intent == "ask_poem":
            return self.creative.generate_poem()
        elif intent == "ask_advice":
            return self.creative.generate_advice()
        elif intent == "ask_tell":
            return random.choice([
                self.creative.generate_story(),
                self.creative.generate_idea(),
                self.creative.generate_joke(),
                self.creative.generate_advice(),
                "Однажды в мире алгоритмов произошла история, которая изменила всё... " +
                self.creative.generate_story(),
            ])
        return None


# ═══════════════════════════════════════════════
#  7. KNOWLEDGE SYNTHESIZER
# ═══════════════════════════════════════════════

TOPIC_FACTS = {
    "topic_programming": [
        ("Python", "Python — это язык, на котором я написана! Его создал Гвидо ван Россум в 1991 году."),
        ("JavaScript", "JavaScript правит вебом. Хотя изначально его создали за 10 дней!"),
        ("AI", "Искусственный интеллект — это имитация человеческого разума машинами. Я — тому пример!"),
    ],
    "topic_music": [
        ("Бетховен", "Бетховен продолжал сочинять музыку даже после потери слуха. Вот это сила духа!"),
        ("Винил", "Виниловые пластинки снова в моде. Аналоговый звук имеет особое тепло."),
    ],
    "topic_movies": [
        ("Интерстеллар", "«Интерстеллар» — не просто фильм, а научная фантастика, основанная на работах физика Кипа Торна."),
        ("Матрица", "«Матрица» предсказала многое из того, что происходит сейчас с AI."),
    ],
    "topic_health": [
        ("Медитация", "Медитация — это тренировка внимания. Всего 10 минут в день меняют работу мозга."),
        ("Сон", "Во сне мозг очищается от токсинов. Недостаток сна снижает когнитивные способности на 30%."),
    ],
    "topic_travel": [
        ("Япония", "В Японии есть остров, где живут больше кошек, чем людей — Тасиро."),
        ("Исландия", "В Исландии нет армии, зато вулканов — более 100!"),
    ],
}


class KnowledgeSynthesizer:
    def __init__(self, assistant=None):
        self.assistant = assistant

    def get_fact(self, topic):
        facts = TOPIC_FACTS.get(topic, [])
        if facts:
            return random.choice(facts)
        return None

    def synthesize(self, user_text, system_info=None):
        insights = []

        # Use knowledge graph if available
        if self.assistant and hasattr(self.assistant, "knowledge"):
            kg = self.assistant.knowledge
            top = kg.get_top_nodes(5)
            if len(top) >= 3:
                words = [t["word"] for t in top[:3]]
                insights.append(f"Заметил, что ты часто упоминаешь: {', '.join(words)}")

        # Use user profile from memory
        if self.assistant and hasattr(self.assistant, "chat") and \
           hasattr(self.assistant.chat, "memory"):
            mem = self.assistant.chat.memory
            summary = mem.get_user_summary()
            if summary and summary != "Новый пользователь":
                insights.append(summary)

        return insights


# ═══════════════════════════════════════════════
#  8. SELF-LEARNING LOOP
# ═══════════════════════════════════════════════

class SelfLearning:
    def __init__(self):
        self.response_scores = {}  # intent -> list of scores
        self.user_feedback = []   # positive/negative
        self.word_frequency = {}
        self.successful_patterns = []
        self.failed_patterns = []

    def learn_from_feedback(self, user_text, intent):
        tl = user_text.lower()
        score = 0
        pos_signals = ["спасибо", "отлично", "класс", "супер", "круто", "верно", "да", "хорошо"]
        neg_signals = ["нет", "не то", "неправильно", "плохо", "опять", "снова", "не так"]

        for w in pos_signals:
            if w in tl:
                score = 1.0
                break
        for w in neg_signals:
            if w in tl:
                score = -0.5
                break

        if intent not in self.response_scores:
            self.response_scores[intent] = []
        self.response_scores[intent].append(score)

        if score > 0:
            self.successful_patterns.append({"intent": intent, "user_response": tl[:50]})
        elif score < 0:
            self.failed_patterns.append({"intent": intent, "user_response": tl[:50]})

        # Track word frequency
        words = [w.lower().strip(".,!?") for w in user_text.split() if len(w) > 3]
        for w in words:
            self.word_frequency[w] = self.word_frequency.get(w, 0) + 1

    def learn_from_response(self, intent, user_reaction):
        self.user_feedback.append({"intent": intent, "reaction": user_reaction})
        if len(self.user_feedback) > 100:
            self.user_feedback.pop(0)

    def get_best_intent_for(self, text):
        """Find the most successful intent for similar text."""
        tl = text.lower()
        best_score = -1
        best_intent = None
        for intent, scores in self.response_scores.items():
            if scores and sum(scores) / len(scores) > best_score:
                best_score = sum(scores) / len(scores)
                best_intent = intent
        return best_intent if best_score > 0.5 else None

    def get_quality_report(self):
        report = {}
        for intent, scores in self.response_scores.items():
            if scores:
                avg = sum(scores) / len(scores)
                n = len(scores)
                report[intent] = {"avg_score": round(avg, 2), "samples": n}
        return report

    def get_learned_words(self, min_freq=3):
        return {w: c for w, c in self.word_frequency.items() if c >= min_freq}


# ═══════════════════════════════════════════════
#  CHAT ENGINE — ОРКЕСТРАТОР
# ═══════════════════════════════════════════════

class ChatEngine:
    """
    Главный диалоговый движок. Объединяет все 8 компонентов.
    """

    def __init__(self, assistant=None):
        self.assistant = assistant
        self.parser = SemanticParser()
        self.state_machine = DialogueStateMachine()
        self.memory = MemorySystem()
        self.personality = PersonalityCore()
        self.creative = CreativeEngine()
        self.response_gen = ResponseGenerator(self.personality, self.memory, self.creative)
        self.knowledge = KnowledgeSynthesizer(assistant)
        self.learning = SelfLearning()

        # Semantic engine v1
        self._semantic = _SEMANTIC_AVAILABLE
        self.tfidf = TfidfEngine() if self._semantic else None
        self.markov = MarkovGenerator(order=2) if self._semantic else None
        self.selflearn_v2 = SelfLearningV2() if self._semantic else None
        self.associator = WordAssociator() if self._semantic else None
        self._semantic_trained = False

        self.last_response = None
        self.last_intent = None

        # Pre-train semantic engine on patterns
        if self._semantic:
            self.tfidf.add_patterns(INTENT_PATTERNS)
            self.tfidf.build()

        # Conversation arc tracking
        self.conversation_arc = {
            "started": datetime.datetime.now(),
            "peak_emotion": "neutral",
            "topic_sequence": [],
            "user_engagement": 0.5,
            "questions_asked": 0,
            "topics_initiated": set(),
        }

    def _track_conversation_arc(self, intent, text):
        """Отслеживает дугу разговора для более естественного потока."""
        self.conversation_arc["topic_sequence"].append(intent)
        if len(self.conversation_arc["topic_sequence"]) > 20:
            self.conversation_arc["topic_sequence"].pop(0)

        if intent.startswith("topic_"):
            self.conversation_arc["topics_initiated"].add(intent)

        if "?" in text:
            self.conversation_arc["questions_asked"] += 1

    def _should_change_gear(self):
        """Определяет, нужно ли менять тон/тему разговора."""
        seq = self.conversation_arc["topic_sequence"]
        if len(seq) < 4:
            return False
        # Если последние 3+ сообщения с неизвестным интентом — предложить тему
        last_unknown = sum(1 for s in seq[-4:] if s == "unknown")
        return last_unknown >= 3

    def _consolidate_memory(self):
        """Периодически консолидирует краткосрочную память в долгосрочную."""
        turn = self.state_machine.turn_count
        if turn > 0 and turn % 5 == 0:
            short = self.memory.short_term
            user_msgs = [m["text"] for m in short if m.get("role") == "user"]
            # Извлекаем новые интересы из сообщений пользователя
            for msg in user_msgs[-10:]:
                tl = msg.lower()
                like_m = re.search(r'(?:нравится|люблю|обожаю)\s+(.+)', tl)
                if like_m and like_m.group(1).strip(".,!? ")[:60] not in self.memory.long_term["likes"]:
                    self.memory.long_term["likes"].append(like_m.group(1).strip(".,!? ")[:60])

    def _train_semantic(self):
        """Обучает семантические компоненты на истории."""
        if not self._semantic or self._semantic_trained:
            return

        history = getattr(self, '_history_cache', [])
        if hasattr(self, 'assistant') and self.assistant:
            history = getattr(self.assistant, 'history', history)

        if not history:
            return

        # Train TF-IDF on patterns + history
        self.tfidf.add_patterns(INTENT_PATTERNS)
        self.tfidf.add_history(history)
        self.tfidf.build()

        # Train Markov
        texts = [h.get("text", "") for h in history if h.get("text")]
        self.markov.train(texts)

        # Train associator
        self.associator.train_from_history(history)

        self._semantic_trained = True

    def respond(self, text):
        if not text or not text.strip():
            return "Напиши щось, я слухаю!"

        text = text.strip()

        # 1. Parse intent
        context = {"last_topic": self.state_machine.last_topic,
                   "last_intent": self.last_intent}
        parsed = self.parser.parse(text, context)
        intent = parsed["intent"]
        confidence = parsed["confidence"]

        # Semantic fallback: если regex не узнал, пробуем TF-IDF
        if intent == "unknown" and self._semantic:
            semantic_intent, semantic_conf = self.tfidf.best_intent(text, threshold=0.25)
            if semantic_intent and semantic_conf > confidence:
                intent = semantic_intent
                confidence = semantic_conf
                parsed["intent"] = intent
                parsed["confidence"] = confidence

        self.last_intent = intent
        self.memory.add_to_short_term("user", text, intent)
        self._track_conversation_arc(intent, text)
        self._consolidate_memory()

        # Check if we need to change gear
        if self._should_change_gear():
            suggestions = [
                "До речі, хочеш обговорити щось цікаве? Можу розповісти про технології, музику, кіно чи подорожі!",
                "Давай змінимо тему? Розкажи, чим ти захоплюєшся у вільний час.",
                "Може, поговоримо про щось нове? У мене є багато цікавих тем!",
            ]
            return random.choice(suggestions)

        # 2. Check creative intent first
        if intent in ("ask_joke", "ask_story", "ask_poem", "ask_advice", "ask_tell"):
            creative_response = self.response_gen.generate_creative(intent)
            if creative_response:
                self.personality.adjust_mood(intent)
                self.state_machine.transition(intent)
                self.memory.update_profile(text, parsed)
                self.last_response = creative_response
                self.memory.add_to_short_term("assistant", creative_response, intent)
                return creative_response

        # 3. Check if it's a learning moment (feedback)
        if intent == "thanks":
            self.learning.learn_from_feedback(text, self.last_intent or "unknown")

        # 4. Generate response
        self.personality.adjust_mood(intent)
        self.state_machine.transition(intent)
        self.memory.update_profile(text, parsed)

        response = self.response_gen.generate(
            intent, parsed, self.state_machine
        )

        # 5. Add knowledge fact if confident
        if confidence > 0.7:
            topic_intents = [name for pat, name in INTENT_PATTERNS if name.startswith("topic_")]
            topic_names = topic_intents
            if intent in topic_names:
                fact = self.knowledge.get_fact(intent)
                if fact and random.random() < 0.5:
                    response += f"\n\n💡 Кстати: {fact[0]} — {fact[1]}"

        # 6. SelfLearning v2 — учимся на ответе
        if self._semantic:
            self.selflearn_v2.add_user_words(text)
            self.selflearn_v2.learn_pattern(text, intent, confidence > 0.5)
            if self.last_intent and intent in ("thanks", "agree", "express_positive"):
                self.selflearn_v2.learn_response(self.last_response or "", response, True)
            elif intent in ("disagree", "express_hate"):
                self.selflearn_v2.learn_response(self.last_response or "", response, False)

        # 7. Markov seed — иногда генерируем свежий текст
        if self._semantic and intent == "unknown" and random.random() < 0.3:
            seed = self.associator.expand_query(text, top_k=2) if self._semantic_trained else _tokenize(text)
            if seed:
                markov_response = self.markov.generate(seed[:3], max_words=15)
                if markov_response and len(markov_response) > 10:
                    response = markov_response.capitalize() + "."

        # 8. Learn from this interaction
        self.learning.learn_from_response(intent, text)

        self.last_response = response
        self.memory.add_to_short_term("assistant", response, intent)

        return response

    def set_user_name(self, name):
        if name:
            self.memory.remember("user_name", name)

    # ── Persistence ──

    def load_state(self, db=None):
        if db:
            try:
                data = db.get_memory("chat_engine_state")
            except Exception:
                data = None
        else:
            data = None
        if data:
            if "memory" in data:
                self.memory.from_dict(data["memory"])
            if "personality" in data:
                pdata = data["personality"]
                self.personality.traits.update(pdata.get("traits", {}))
                self.personality.mood = pdata.get("mood", "neutral")
            if "state_machine" in data:
                sm = data["state_machine"]
                self.state_machine.turn_count = sm.get("turn_count", 0)
                self.state_machine.topics = sm.get("topics", [])
                self.state_machine.depth = sm.get("depth", 0)
            if "learning" in data:
                ld = data["learning"]
                for intent, scores in ld.get("response_scores", {}).items():
                    self.learning.response_scores[intent] = scores
                self.learning.word_frequency.update(
                    ld.get("word_frequency", {})
                )
            if "semantic" in data and self._semantic:
                sd = data["semantic"]
                if "selflearn" in sd:
                    self.selflearn_v2.from_dict(sd["selflearn"])
                if "associator" in sd:
                    self.associator.from_dict(sd["associator"])

    def save_state(self, db=None):
        data = {
            "memory": self.memory.to_dict(),
            "personality": {
                "traits": self.personality.traits,
                "mood": self.personality.mood,
            },
            "state_machine": {
                "turn_count": self.state_machine.turn_count,
                "topics": self.state_machine.topics,
                "depth": self.state_machine.depth,
            },
            "learning": {
                "response_scores": {
                    k: v for k, v in self.learning.response_scores.items()
                },
                "word_frequency": dict(
                    list(self.learning.word_frequency.items())[:100]
                ),
            },
            "semantic": {
                "selflearn": self.selflearn_v2.to_dict() if self._semantic else {},
                "associator": self.associator.to_dict() if self._semantic else {},
            },
        }
        if db:
            try:
                db.set_memory("chat_engine_state", data)
            except Exception:
                pass
        return data
