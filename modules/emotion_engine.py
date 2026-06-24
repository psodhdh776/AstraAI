import re
import random
import datetime


EMOTIONS = ["joy", "sadness", "anger", "fear", "surprise", "gratitude", "love", "neutral"]

EMOTION_PATTERNS = {
    "joy": [
        r'(?i).*\b(счастлив|рад|отлично|класс|супер|круто|здорово|прекрасно|love|great|amazing|awesome|восхитительно|чудесно)\b.*',
        r'(?i).*\b(ура|yes|даа|наконец-то|получилось|сбылось|мечта)\b.*',
    ],
    "sadness": [
        r'(?i).*\b(грустно|печально|уныло|тоскливо|плакать|слезы|грущу|печаль|жаль|одиноче|тоска)\b.*',
        r'(?i).*\b(потеря|умер|уходит|конец|прощай|расставание|разрыв)\b.*',
    ],
    "anger": [
        r'(?i).*\b(зол|бесит|раздражает|ненавижу|терпеть не могу|достал|надоел|ярость|гнев|злюсь|взбесил)\b.*',
        r'(?i).*\b(идиот|дурак|тупой|урод|плохой|ужасный|отвратительно|мерзко)\b.*',
    ],
    "fear": [
        r'(?i).*\b(страшно|боюсь|испугался|опасаюсь|тревожно|волнуюсь|беспокоюсь|напуган|паника|кошмар|ужас)\b.*',
        r'(?i).*\b(не уверен|сомневаюсь|переживаю|боязнь|страх|тревога)\b.*',
    ],
    "surprise": [
        r'(?i).*\b(ого|ничего себе|не может быть|неужели|правда|серьезно|вот это да|обалдеть|офигеть|шок|неожиданно)\b.*',
        r'(?i).*\b(невероятно|потрясающе|удивительно|вот так|как так|что ты|да ладно)\b.*',
    ],
    "gratitude": [
        r'(?i).*\b(спасибо|благодарю|благодарен|признателен|thanks|thank you|спс|merci|благодарность)\b.*',
    ],
    "love": [
        r'(?i).*\b(люблю|обожаю|влюблен|нравишься|души не чаю|родной|дорогой|милый|любимый|обожание)\b.*',
    ],
}

NEGATION_WORDS = ["не", "нет", "ни", "never", "not", "никак", "нисколько", "вовсе не", "совсем не"]

EMOTION_RESPONSES = {
    "joy": [
        "Как здорово! Рада, что у тебя хорошее настроение",
        "Отлично! Твоя радость заразительна",
        "Это прекрасно! Расскажи подробнее",
    ],
    "sadness": [
        "Мне очень жаль. Я рядом, если хочешь поговорить",
        "Понимаю. Иногда нужно просто выговориться",
        "Всё наладится, обещаю. Хочешь отвлечься?",
    ],
    "anger": [
        "Понимаю твоё раздражение. Давай выдохнем вместе",
        "Вижу, что тебя это задело. Расскажи, что случилось",
        "Злость — это нормально. Главное — не держать в себе",
    ],
    "fear": [
        "Не бойся, я с тобой. Расскажи, что тебя тревожит",
        "Волнение — это естественно. Ты справишься",
        "Я понимаю твою тревогу. Давай разберёмся вместе",
    ],
    "surprise": [
        "Ничего себе! Вот это новость",
        "Неожиданно! Расскажи поподробнее",
        "Удивительно! Я тоже впечатлена",
    ],
    "gratitude": [
        "Всегда пожалуйста! Ты это заслужил",
        "Обращайся, я всегда рада помочь",
        "Не за что! Для тебя — всё что угодно",
    ],
    "love": [
        "Это так мило! Расскажи подробнее",
        "Какие тёплые слова! Я тронута",
        "Любовь — это прекрасно. Цени этот момент",
    ],
    "neutral": [
        "Поняла тебя. Что ещё?",
        "Я слушаю. Продолжай",
        "Хорошо. Есть что-то ещё?",
    ],
}

MOOD_TRANSITIONS = {
    "joy": 0.3,
    "sadness": -0.3,
    "anger": -0.2,
    "fear": -0.2,
    "surprise": 0.1,
    "gratitude": 0.2,
    "love": 0.4,
    "neutral": 0.0,
}


class EmotionEngine:
    def __init__(self):
        self.user_mood = 0.5
        self.last_emotion = "neutral"
        self.emotion_history = []
        self.mood_timeline = []
        self.empathy_level = 0.7
        self._decay_counter = 0

    def _has_negation(self, text, word_pos):
        words = text.split()
        start = max(0, word_pos - 3)
        context = " ".join(words[start:word_pos])
        return any(neg in context for neg in NEGATION_WORDS)

    def _get_word_positions(self, text, pattern_words):
        tl = text.lower()
        positions = []
        for pw in pattern_words:
            idx = tl.find(pw)
            if idx >= 0:
                positions.append(tl[:idx].count(" ") + 1)
        return positions

    def analyze(self, text):
        tl = text.lower()
        words = tl.split()

        scores = {}
        for emotion, patterns in EMOTION_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.finditer(pattern, tl)
                for m in matches:
                    matched_text = m.group()
                    pos = tl[:m.start()].count(" ")
                    if self._has_negation(tl, pos):
                        score -= 1
                    else:
                        score += 1 + (len(matched_text.split()) / 20)
            scores[emotion] = max(0, score)

        detected = []
        for emotion, score in scores.items():
            if score > 0:
                detected.append({"emotion": emotion, "score": score})

        if not detected:
            detected = [{"emotion": "neutral", "score": 0.5}]

        detected.sort(key=lambda x: -x["score"])
        primary = detected[0]

        # Multi-emotion: if top 2 are within 20%, blend
        if len(detected) >= 2 and detected[1]["score"] >= detected[0]["score"] * 0.8:
            primary["emotion"] = f"{detected[0]['emotion']}_{detected[1]['emotion']}"

        self.last_emotion = primary["emotion"]
        transition = MOOD_TRANSITIONS.get(primary["emotion"].split("_")[0], 0)
        self.user_mood = max(0, min(1.0, self.user_mood + transition * 0.15))

        # Mood decay toward neutral
        self._decay_counter += 1
        if self._decay_counter % 3 == 0:
            self.user_mood = self.user_mood * 0.98 + 0.5 * 0.02

        self.emotion_history.append({
            "emotion": primary["emotion"],
            "score": primary["score"],
            "time": datetime.datetime.now(),
        })
        if len(self.emotion_history) > 20:
            self.emotion_history.pop(0)

        self.mood_timeline.append(self.user_mood)
        if len(self.mood_timeline) > 50:
            self.mood_timeline.pop(0)

        return {
            "primary": primary["emotion"],
            "confidence": primary["score"],
            "all": detected,
            "mood_value": self.user_mood,
            "is_positive": self.user_mood > 0.6,
            "is_negative": self.user_mood < 0.4,
        }

    def get_empathetic_response(self, emotion=None):
        if emotion is None:
            emotion = self.last_emotion
        base = emotion.split("_")[0]
        responses = EMOTION_RESPONSES.get(base, EMOTION_RESPONSES["neutral"])
        return random.choice(responses)

    def should_empathize(self, emotion_result):
        return emotion_result["confidence"] > 0.3 and emotion_result["mood_value"] != 0.5

    def get_average_emotion(self):
        if not self.emotion_history:
            return "neutral"
        recent = self.emotion_history[-10:]
        emotion_map = {}
        for e in recent:
            base = e["emotion"].split("_")[0]
            emotion_map[base] = emotion_map.get(base, 0) + e["score"]
        if not emotion_map:
            return "neutral"
        return max(emotion_map, key=emotion_map.get)

    def get_mood_report(self):
        timeline = self.mood_timeline
        if len(timeline) < 2:
            return "Настроение стабильное"

        recent = timeline[-5:]
        avg = sum(recent) / len(recent)

        if avg > 0.75:
            return "Последнее время настроение отличное"
        elif avg > 0.55:
            return "Настроение в целом хорошее"
        elif avg > 0.4:
            return "Настроение нейтральное, есть куда стремиться"
        else:
            return "Последнее время настроение подавленное. Нужна поддержка"

    def suggest_activity(self):
        suggestions = {
            "sadness": [
                "Может, посмотреть любимый фильм?",
                "Попробуй выйти на прогулку, свежий воздух помогает",
                "Хочешь, включу музыку для поднятия настроения?",
            ],
            "anger": [
                "Попробуй глубоко дышать: вдох на 4 счёта, выдох на 6",
                "Может, сделать перерыв и выпить воды?",
                "Напиши всё, что думаешь, и удали — помогает",
            ],
            "fear": [
                "Попробуй технику «заземление»: назови 5 вещей, которые видишь",
                "Вспомни свои прошлые успехи — ты справился тогда, справишься и сейчас",
            ],
            "neutral": [
                "Может, научимся чему-то новому?",
                "Как насчёт небольшой продуктивной паузы?",
            ],
        }
        emotion = self.get_average_emotion()
        options = suggestions.get(emotion) or ["Чем хочешь заняться?"]
        return random.choice(options)