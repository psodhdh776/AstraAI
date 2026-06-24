import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import re
import pytest


class TestIntentPatterns:
    @pytest.fixture
    def patterns(self):
        from intents import INTENT_PATTERNS
        return [(re.compile(p), name) for p, name in INTENT_PATTERNS]

    def _match(self, patterns, text):
        for pat, name in patterns:
            if pat.match(text):
                return name
        return None

    def test_greeting(self, patterns):
        assert self._match(patterns, "привет") == "greeting"
        assert self._match(patterns, "здравствуй") == "greeting"

    def test_farewell(self, patterns):
        assert self._match(patterns, "пока") == "farewell"
        assert self._match(patterns, "до свидания") == "farewell"

    def test_ask_name(self, patterns):
        assert self._match(patterns, "как тебя зовут") == "ask_name"
        assert self._match(patterns, "кто ты") == "ask_name"

    def test_introduce_name(self, patterns):
        assert self._match(patterns, "меня зовут Иван") == "introduce_name"
        assert self._match(patterns, "можешь звать Петр") == "introduce_name"

    def test_ask_state(self, patterns):
        assert self._match(patterns, "как дела") == "ask_state"
        assert self._match(patterns, "как ты") == "ask_state"

    def test_express_positive(self, patterns):
        assert self._match(patterns, "всё отлично") == "express_positive"
        assert self._match(patterns, "супер") == "express_positive"

    def test_express_negative(self, patterns):
        assert self._match(patterns, "мне грустно") == "express_negative"
        assert self._match(patterns, "я устал") == "express_negative"

    def test_thanks(self, patterns):
        assert self._match(patterns, "спасибо") == "thanks"
        assert self._match(patterns, "благодарю") == "thanks"

    def test_apology(self, patterns):
        assert self._match(patterns, "извини") == "apology"
        assert self._match(patterns, "прости") == "apology"

    def test_ask_capabilities(self, patterns):
        assert self._match(patterns, "что ты умеешь") == "ask_capabilities"

    def test_help(self, patterns):
        assert self._match(patterns, "как пользоваться") == "help"

    def test_ask_joke(self, patterns):
        assert self._match(patterns, "пошути") == "ask_joke"
        assert self._match(patterns, "анекдот") == "ask_joke"

    def test_ask_story(self, patterns):
        assert self._match(patterns, "расскажи историю") == "ask_story"

    def test_ask_advice(self, patterns):
        assert self._match(patterns, "посоветуй что делать") == "ask_advice"

    def test_ask_time(self, patterns):
        assert self._match(patterns, "сколько времени") == "ask_time"

    def test_ask_date(self, patterns):
        assert self._match(patterns, "какое сегодня число") == "ask_date"

    def test_ask_why(self, patterns):
        assert self._match(patterns, "почему небо голубое") == "ask_why"

    def test_topic_weather(self, patterns):
        assert self._match(patterns, "поговорим о погоде") == "topic_weather"

    def test_topic_programming(self, patterns):
        assert self._match(patterns, "я пишу на python") == "topic_programming"

    def test_topic_music(self, patterns):
        assert self._match(patterns, "слушаю музыку") == "topic_music"

    def test_topic_movies(self, patterns):
        assert self._match(patterns, "классный фильм") == "topic_movies"

    def test_topic_sport(self, patterns):
        assert self._match(patterns, "увлекаюсь спортом") == "topic_sport"

    def test_topic_food(self, patterns):
        assert self._match(patterns, "вкусная еда") == "topic_food"

    def test_short_agreement(self, patterns):
        assert self._match(patterns, "да") == "short_agreement"
        assert self._match(patterns, "ок") == "short_agreement"

    def test_ask_more(self, patterns):
        assert self._match(patterns, "ещё") == "ask_more"

    def test_no_match(self, patterns):
        assert self._match(patterns, "совершенно случайный набор слов") is None
