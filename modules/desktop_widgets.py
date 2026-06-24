"""
Desktop widgets: weather, currency, quote of the day.
All with local fallback (no API keys needed).
"""

import json
import logging
import random
import urllib.request
import urllib.error
from datetime import datetime

logger = logging.getLogger("Astra.Widgets")

QUOTES_RU = [
    ("Единственный способ делать великие дела — любить то, что вы делаете.", "Стив Джобс"),
    ("Будь собой, остальные роли уже заняты.", "Оскар Уайльд"),
    ("Делай сегодня то, что другие не хотят, завтра будешь жить так, как другие не могут.", "неизв."),
    ("Знание — сила.", "Фрэнсис Бэкон"),
    ("Самая большая опасность в жизни — быть слишком осторожным.", "Альфред Адлер"),
    ("Всё гениальное просто.", "Леонардо да Винчи"),
    ("Никогда не сдавайся. Удача любит настойчивых.", "неизв."),
    ("Если проблему можно решить, не стоит о ней беспокоиться. Если её нельзя решить, беспокоиться бесполезно.", "Далай-лама"),
    ("Жизнь — это то, что происходит, пока ты строишь планы.", "Джон Леннон"),
    ("Вчера — это история, завтра — загадка, сегодня — подарок.", "неизв."),
]

CURRENCY_PAIRS = [
    ("USD/RUB", "доллар"),
    ("EUR/RUB", "евро"),
    ("CNY/RUB", "юань"),
]

_quote_cache = None
_weather_cache = None
_weather_time = 0
_currency_cache = None
_currency_time = 0

def get_random_quote():
    q, a = random.choice(QUOTES_RU)
    return f"«{q}» — {a}"

def get_weather(city="Москва"):
    global _weather_cache, _weather_time
    now = datetime.now().timestamp()
    if _weather_cache and now - _weather_time < 600:
        return _weather_cache
    try:
        url = f"https://wttr.in/{city}?format=%t+%C+%w"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        data = urllib.request.urlopen(req, timeout=5).read().decode("utf-8").strip()
        _weather_cache = data
        _weather_time = now
        return data
    except Exception as e:
        logger.debug("Weather fetch: %s", e)
        return f"{city}: данные недоступны"

def get_currency():
    global _currency_cache, _currency_time
    now = datetime.now().timestamp()
    if _currency_cache and now - _currency_time < 3600:
        return _currency_cache
    try:
        results = []
        for pair, name in CURRENCY_PAIRS:
            base, target = pair.split("/")
            url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base.lower()}.json"
            req = urllib.request.Request(url, headers={"User-Agent": "AstraAI/1.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=5).read())
            rate = data.get(base.lower(), {}).get(target.lower(), "—")
            results.append(f"{name}: {rate}")
        _currency_cache = " | ".join(results)
        _currency_time = now
        return _currency_cache
    except Exception as e:
        logger.debug("Currency fetch: %s", e)
        return "Курсы недоступны"
