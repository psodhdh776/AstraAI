"""Built-in plugins wrapping existing Assistant command handlers."""

import datetime
import webbrowser
import subprocess
import re
import random
from pathlib import Path

from modules.plugin_base import Plugin


# ---------- helpers ----------

def _extract_after(text, triggers):
    tl = text.lower()
    for t in triggers:
        idx = tl.find(t)
        if idx >= 0:
            after = text[idx + len(t):].strip().lstrip(" ,.!?")
            if after and len(after) > 1:
                return after
    return None


def _extract_weather_city(text, tl):
    words = text.split()
    for i, w in enumerate(words):
        if w.lower() in ("в", "во", "на", "в городе"):
            if i + 1 < len(words):
                city = words[i + 1].strip(".,!?")
                if city and len(city) > 1:
                    return city
    return None


def _parse_remind(text, tl):
    m = re.search(r'(?:через)\s+(\d+)\s*(?:минут|минуту|мин|секунд|сек|ч|час|часов)\s+(.+)', tl)
    if m:
        return (m.group(1), m.group(2).strip())
    word_map = {"полчаса": 30, "пол часа": 30, "пол-часа": 30, "час": 60, "часа": 60, "часов": 60, "пару минут": 2, "пару": 2}
    for phrase, mins in word_map.items():
        if phrase in tl:
            after = tl.split(phrase, 1)[1].strip()
            return (str(mins), after if after else "напоминание")
    return None


# ---------- template map ----------

def _pick(*variants):
    return lambda r: random.choice(variants).format(r=r)

FORMAT_TEMPLATES = {
    "screenshot": _pick("📸 {r}", "Готово! {r}", "Сделано 📸 {r}"),
    "time": _pick("⏰ {r}", "{r}", "Сейчас {r}"),
    "date": _pick("📅 {r}", "{r}", "Сегодня {r}"),
    "system": _pick("💻 Состояние системы:\n{r}", "Вот что показывает система:\n{r}", "📊 Система:\n{r}"),
    "processes": _pick("📊 {r}", "Вот топ процессов:\n{r}", "{r}"),
    "clipboard": _pick("📋 {r}", "{r}", "В буфере: {r}"),
    "web_search": _pick("🔍 Нашла:\n{r}", "Вот что удалось найти:\n{r}", "Результаты поиска:\n{r}"),
    "weather": _pick("🌤️ {r}", "{r}", "На улице {r}"),
    "calc": _pick("🧮 {r}", "{r}", "Ответ: {r}"),
    "translate": _pick("🌐 {r}", "{r}", "Перевод: {r}"),
    "add_note": _pick("📝 {r}", "Запомнила ✅ {r}", "Готово, записала 📝"),
    "delete_note": _pick("🗑️ {r}", "{r}", "Удалила ✅ {r}"),
    "list_notes": _pick("📋 {r}", "{r}", "Вот твои заметки:\n{r}"),
    "remind": _pick("🔔 {r}", "Напомню! {r}", "✅ {r}"),
    "open_app": _pick("🚀 {r}", "{r}", "Запускаю ✅"),
    "open_url": _pick("🌍 {r}", "{r}", "Открываю в браузере 💻"),
    "type": _pick("⌨️ {r}", "{r}", "Печатаю ✅"),
    "generate_image": _pick("🎨 {r}", "Вот изображение:\n{r}", "Сгенерировала 🎨\n{r}"),
    "ai_engine": _pick("🧠 {r}", "{r}", "Результат: {r}"),
    "fast_search": _pick("🔍 {r}", "{r}", "Вот что нашла:\n{r}"),
    "mood_report": _pick("🧠 {r}", "{r}", "Вот анализ:\n{r}"),
}


def fmt(name, result):
    t = FORMAT_TEMPLATES.get(name)
    return t(result) if t else result


# ---------- individual plugins ----------

class GreetPlugin(Plugin):
    name = "greet"
    keywords = ["привет", "здравствуй", "хай", "hello", "hi", "добрый", "доброе", "приветствую", "рад"]
    weight = 1.0
    description = "Приветствие"

    def execute(self, params, assistant):
        name = assistant._thinking_ctx.get("user_name")
        if name:
            return random.choice([
                f"Привет, {name}! ✨ Чем займёмся?",
                f"Здравствуй, {name}! Рада тебя видеть.",
                f"Привет, {name}! Спрашивай что угодно.",
            ])
        return random.choice([
            "✨ Привет! Я Astra, твой помощник. Чем могу помочь?",
            "Привет! Astra на связи. Рассказывай 👋",
            "Здравствуй! Я на месте, спрашивай ✨",
        ])


class HelpPlugin(Plugin):
    name = "help"
    keywords = ["помощь", "help", "команды", "что ты умеешь", "возможности", "умеешь", "функции"]
    weight = 1.0
    description = "Показать список команд"

    def execute(self, params, assistant):
        return assistant._do_help()


class ClearHistoryPlugin(Plugin):
    name = "clear_history"
    keywords = ["очисти историю", "clear history", "удали историю", "стереть историю"]
    weight = 1.0
    description = "Очистить историю"

    def execute(self, params, assistant):
        assistant.history.clear()
        assistant._save_history()
        return "История очищена"


class TimePlugin(Plugin):
    name = "time"
    keywords = ["время", "который час", "сколько времени", "часов", "час"]
    weight = 0.8
    description = "Показать текущее время"

    def execute(self, params, assistant):
        return assistant._do_time()


class DatePlugin(Plugin):
    name = "date"
    keywords = ["дата", "какое сегодня", "какое число", "день недели", "число", "год"]
    weight = 0.8
    description = "Показать текущую дату"

    def execute(self, params, assistant):
        return assistant._do_date()


class ScreenshotPlugin(Plugin):
    name = "screenshot"
    keywords = ["скриншот", "снимок экрана", "screenshot", "скрин", "фото экрана"]
    weight = 1.0
    cooldown_seconds = 3.0
    description = "Сделать скриншот"

    def execute(self, params, assistant):
        return assistant._do_screenshot()


class SystemPlugin(Plugin):
    name = "system"
    keywords = ["система", "инфо", "информация", "характеристики", "cpu", "процессор", "оператив", "память", "видеокарта", "загрузка"]
    weight = 0.7
    cooldown_seconds = 5.0
    description = "Показать состояние системы"

    def execute(self, params, assistant):
        return assistant._do_system()


class ProcessesPlugin(Plugin):
    name = "processes"
    keywords = ["процессы", "процессов", "запущен", "топ", "нагружает", "грузит", "нагрузка"]
    weight = 0.8
    cooldown_seconds = 5.0
    description = "Показать топ процессов"

    def execute(self, params, assistant):
        return assistant._do_processes()


class ClipboardPlugin(Plugin):
    name = "clipboard"
    keywords = ["буфер", "clipboard", "скопировано", "в буфере", "скопировал", "что в буфере"]
    weight = 0.9
    description = "Показать содержимое буфера"

    def execute(self, params, assistant):
        try:
            import pyperclip
            t = pyperclip.paste()
            return f"В буфере: {t[:200]}" if t else "Буфер пуст"
        except Exception:
            return "pyperclip не установлен"


class TypePlugin(Plugin):
    name = "type"
    keywords = ["напечатай", "напиши текст", "type", "введи текст", "набери", "введи"]
    weight = 1.0
    description = "Напечатать текст"

    def extract_params(self, text, tl):
        return _extract_after(text, ["напечатай", "напиши текст", "type", "введи текст", "набери", "введи"])

    def execute(self, params, assistant):
        if not params:
            return None
        try:
            import pyautogui
            pyautogui.write(params, interval=0.02)
            return f"Печатаю: {params}"
        except Exception:
            return "PyAutoGUI не установлен"


class OpenUrlPlugin(Plugin):
    name = "open_url"
    keywords = ["открой сайт", "перейди на", "open url", "открой url", "открой страницу", "открой ссылку"]
    weight = 1.0
    description = "Открыть сайт"

    def extract_params(self, text, tl):
        return _extract_after(text, ["открой сайт", "перейди на", "open url", "открой url", "открой страницу", "открой ссылку"])

    def execute(self, params, assistant):
        if not params:
            return None
        url = params.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Открываю {params}"


class OpenAppPlugin(Plugin):
    name = "open_app"
    keywords = ["открой", "запусти", "open", "launch", "открой программу", "включи"]
    weight = 0.8
    description = "Открыть приложение"

    def extract_params(self, text, tl):
        return _extract_after(text, ["открой", "запусти", "open", "launch", "открой программу", "включи"])

    def execute(self, params, assistant):
        if not params:
            return None
        app = params.strip().lower()
        from assistant import APPS
        if app in APPS:
            subprocess.Popen(APPS[app], shell=True)
            return f"Открываю {app}"
        return f"Не знаю приложение '{app}'"


class WebSearchPlugin(Plugin):
    name = "web_search"
    keywords = ["поищи", "найди", "search", "найти в интернете", "найди в интернете", "ищи", "поиск", "найди информацию", "загугли", "гугл"]
    weight = 0.9
    description = "Поиск в интернете"

    def extract_params(self, text, tl):
        return _extract_after(text, ["поищи", "найди", "search", "найти в интернете", "найди в интернете", "ищи", "поиск", "найди информацию", "загугли", "гугл"])

    def execute(self, params, assistant):
        if not params:
            return None
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(params, max_results=4))
            if not results:
                return "Ничего не найдено."
            lines = [f"• {r['title']}: {r['href']}" for r in results]
            return "\n".join(lines)
        except Exception:
            webbrowser.open(f"https://google.com/search?q={params}")
            return f"Открываю поиск в браузере: {params}"


class WeatherPlugin(Plugin):
    name = "weather"
    keywords = ["погода", "weather", "температура", "градус", "холодно", "тепло", "дождь", "ветер", "солнечно"]
    weight = 0.8
    cooldown_seconds = 10.0
    description = "Показать погоду"

    def extract_params(self, text, tl):
        return _extract_weather_city(text, tl)

    def execute(self, params, assistant):
        if not params:
            return None
        try:
            import requests as req
            r = req.get(f"https://wttr.in/{params}?format=%C+%t+%w+%h&lang=ru", timeout=10)
            if r.status_code == 200:
                return f"{params}: {r.text.strip()}"
            return "Не удалось получить погоду."
        except Exception as e:
            return f"Ошибка: {e}"


class AddNotePlugin(Plugin):
    name = "add_note"
    keywords = ["заметка", "запомни", "note", "добавь заметку", "новая заметка", "запиши", "запомнить"]
    weight = 1.0
    description = "Добавить заметку"

    def extract_params(self, text, tl):
        return _extract_after(text, ["заметка", "запомни", "note", "добавь заметку", "новая заметка", "запиши", "запомнить"])

    def execute(self, params, assistant):
        if not params:
            return None
        note = {"id": str(datetime.datetime.now().timestamp()), "text": params,
                "created": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"), "done": False}
        assistant.notes.append(note)
        assistant._save_notes()
        return f"Заметка добавлена: {params}"


class ListNotesPlugin(Plugin):
    name = "list_notes"
    keywords = ["заметки", "список заметок", "покажи заметки", "мои заметки", "все заметки", "открой заметки"]
    weight = 1.0
    description = "Показать список заметок"

    def execute(self, params, assistant):
        if not assistant.notes:
            return "Заметок нет."
        active = [n for n in assistant.notes if not n["done"]]
        done = [n for n in assistant.notes if n["done"]]
        lines = [f"📝 Заметки ({len(active)} активных, {len(done)} выполненных):"]
        for i, n in enumerate(active, 1):
            lines.append(f"  {i}. {n['text']}")
        if done:
            lines.append("  ✅ Выполненные:")
            for n in done:
                lines.append(f"    ✓ {n['text']}")
        return "\n".join(lines)


class DeleteNotePlugin(Plugin):
    name = "delete_note"
    keywords = ["удали заметку", "удалить заметку", "remove note", "удали заметку"]
    weight = 1.0
    description = "Удалить заметку"

    def extract_params(self, text, tl):
        return _extract_after(text, ["удали заметку", "удалить заметку", "remove note", "удали заметку"])

    def execute(self, params, assistant):
        if not params:
            return None
        for n in assistant.notes[:]:
            if params.lower() in n["text"].lower():
                assistant.notes.remove(n)
                assistant._save_notes()
                return f"Удалено: {n['text']}"
        return f"Заметка '{params}' не найдена"


class CalcPlugin(Plugin):
    name = "calc"
    keywords = ["калькулятор", "посчитай", "вычисли", "сколько будет", "calculate", "посчитай", "подсчитай"]
    weight = 1.0
    description = "Калькулятор"

    def extract_params(self, text, tl):
        return _extract_after(text, ["калькулятор", "посчитай", "вычисли", "сколько будет", "calculate", "посчитай", "подсчитай"])

    def execute(self, params, assistant):
        if not params:
            return None
        allowed = set("0123456789+-*/.()% ")
        if not all(c in allowed for c in params):
            return "Недопустимые символы"
        try:
            result = eval(params, {"__builtins__": {}}, {})
            return f"{params} = {result}"
        except Exception as e:
            return f"Ошибка: {e}"


class TranslatePlugin(Plugin):
    name = "translate"
    keywords = ["переведи", "translate", "перевод", "переведи текст", "перевести"]
    weight = 0.9
    description = "Перевод текста"

    def extract_params(self, text, tl):
        return _extract_after(text, ["переведи", "translate", "перевод", "переведи текст", "перевести"])

    def execute(self, params, assistant):
        if not params:
            return None
        try:
            import requests as req
            r = req.get(f"https://lingva.ml/api/v1/auto/ru/{req.utils.quote(params)}", timeout=10)
            if r.status_code == 200:
                return r.json().get("translation", params)
            return params
        except Exception:
            return params


class RemindPlugin(Plugin):
    name = "remind"
    keywords = ["напомни", "remind", "напомнить", "напоминание", "напомни мне"]
    weight = 1.0
    description = "Установить напоминание"

    def extract_params(self, text, tl):
        return _parse_remind(text, tl)

    def execute(self, params, assistant):
        if not params or not isinstance(params, (tuple, list)):
            return None
        minutes_str, text = params
        minutes = int(minutes_str)
        assistant.add_reminder(text, minutes)
        return f"✅ Напомню через {minutes} мин: {text}"


class GenerateImagePlugin(Plugin):
    name = "generate_image"
    keywords = ["нарисуй", "сгенерируй", "изображение", "картинку", "создай изображение", "сгенерируй изображение", "нарисуй картинку", "draw", "generate image"]
    weight = 0.9
    description = "Сгенерировать изображение"

    def extract_params(self, text, tl):
        return _extract_after(text, ["нарисуй", "сгенерируй", "изображение", "картинку", "создай изображение", "сгенерируй изображение", "нарисуй картинку", "draw", "generate image"])

    def execute(self, params, assistant):
        if not params:
            return None
        path, error = assistant.generate_image(params)
        if path:
            return f"🎨 Вот изображение:\n{path}"
        return f"🎨 {error}"


class SearchPlugin(Plugin):
    name = "fast_search"
    keywords = ["найди в истории", "поищи в истории", "search history", "поиск в заметках",
                 "что я говорил", "найди в данных", "поиск по всем", "fast search"]
    weight = 0.8
    description = "Быстрый поиск по всей истории, заметкам и данным"

    def extract_params(self, text, tl):
        return _extract_after(text, ["найди в истории", "поищи в истории", "search history",
                                     "поиск в заметках", "что я говорил", "найди в данных",
                                     "поиск по всем", "fast search"])

    def execute(self, params, assistant):
        if not params:
            return None
        return assistant._h_fast_search(params)


class MoodReportPlugin(Plugin):
    name = "mood_report"
    keywords = ["настроение", "mood", "как моё настроение", "эмоции", "мои эмоции",
                 "анализ настроения", "самочувствие", "как я себя чувствую"]
    weight = 0.9
    description = "Показать анализ настроения и эмоций"

    def execute(self, params, assistant):
        return assistant._h_mood_report(None)


class AiEnginePlugin(Plugin):
    name = "ai_engine"
    keywords = ["нейросеть", "ai engine", "neural", "ии", "искусственный интеллект",
                 "нейронка", "нейронная сеть", "вычисления", "inference"]
    weight = 0.7
    description = "Запуск локального AI-движка"

    def execute(self, params, assistant):
        return assistant._h_ai_engine(params)


def get_core_plugins(assistant):
    """Return a list of all built-in plugin instances."""
    return [
        GreetPlugin(),
        HelpPlugin(),
        ClearHistoryPlugin(),
        TimePlugin(),
        DatePlugin(),
        ScreenshotPlugin(),
        SystemPlugin(),
        ProcessesPlugin(),
        ClipboardPlugin(),
        TypePlugin(),
        OpenUrlPlugin(),
        OpenAppPlugin(),
        WebSearchPlugin(),
        WeatherPlugin(),
        AddNotePlugin(),
        ListNotesPlugin(),
        DeleteNotePlugin(),
        CalcPlugin(),
        TranslatePlugin(),
        RemindPlugin(),
        GenerateImagePlugin(),
        AiEnginePlugin(),
        SearchPlugin(),
        MoodReportPlugin(),
    ]
