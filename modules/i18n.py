import json
from pathlib import Path

_LOCALE_DIR = Path(__file__).parent.parent / "assets" / "locales"

TRANSLATIONS = {
    "ru": {
        "app_name": "Astra AI",
        "chat": "Чат",
        "notes": "Заметки",
        "system": "Система",
        "settings": "Настройки",
        "send": "Отправить",
        "input_placeholder": "Введите сообщение или команду...",
        "search_placeholder": "Поиск по истории... (Enter)",
        "welcome": "✨ Добро пожаловать в <b>Astra AI</b>! Спросите меня о чём угодно или введите <b>help</b> для команд.",
        "clear_chat": "Чат очищен",
        "no_results": "Ничего не найдено",
        "voice_listening": "🎤 Слушаю... говорите!",
        "voice_no_speech": "⏱ Речь не обнаружена",
        "voice_no_recognize": "🤔 Не удалось распознать",
        "voice_microphone_error": "❌ Микрофон недоступен",
        "exit_message": "До свидания! Я буду здесь, когда я вам понадоблюсь. 👋",
        "reminder": "🔔 Напоминание",
        "reminder_set": "Напомню через",
        "exit": "Выход",
        "about": "О программе",
        "version": "Версия",
        "search_results": "Результаты поиска",
        "note_added": "Заметка добавлена",
        "pomodoro_focus": "Фокус 25 мин",
        "pomodoro_break": "Перерыв 5 мин",
        "pomodoro_stop": "Остановить таймер",
        "quick_note": "Быстрая заметка",
        "help_title": "Помощь / команды",
        "settings_title": "Настройки",
        "api_key": "API ключ",
        "voice_output": "Голосовой вывод (TTS)",
        "model": "Модель",
        "auto_start": "Автозапуск при входе в Windows",
        "backup": "Создать резервную копию",
        "restore": "Восстановить из копии",
        "export": "Экспорт в JSON",
        "save": "Сохранить",
        "cancel": "Отмена",
        "commands": "Команды",
        "chat_tab": "💬  Чат",
        "notes_tab": "📝  Заметки",
        "system_tab": "🖥  Система",
        "weekdays": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"],
        "months": ["января", "февраля", "марта", "апреля", "мая", "июня",
                   "июля", "августа", "сентября", "октября", "ноября", "декабря"],
    },
    "en": {
        "app_name": "Astra AI",
        "chat": "Chat",
        "notes": "Notes",
        "system": "System",
        "settings": "Settings",
        "send": "Send",
        "input_placeholder": "Type a message or command...",
        "search_placeholder": "Search history... (Enter)",
        "welcome": "✨ Welcome to <b>Astra AI</b>! Ask me anything or type <b>help</b> for commands.",
        "clear_chat": "Chat cleared",
        "no_results": "Nothing found",
        "voice_listening": "🎤 Listening... speak!",
        "voice_no_speech": "⏱ No speech detected",
        "voice_no_recognize": "🤔 Could not recognize",
        "voice_microphone_error": "❌ Microphone unavailable",
        "exit_message": "Goodbye! I'll be here when you need me. 👋",
        "reminder": "🔔 Reminder",
        "reminder_set": "I'll remind in",
        "exit": "Exit",
        "about": "About",
        "version": "Version",
        "search_results": "Search results",
        "note_added": "Note added",
        "pomodoro_focus": "Focus 25 min",
        "pomodoro_break": "Break 5 min",
        "pomodoro_stop": "Stop timer",
        "quick_note": "Quick note",
        "help_title": "Help / commands",
        "settings_title": "Settings",
        "api_key": "API key",
        "voice_output": "Voice output (TTS)",
        "model": "Model",
        "auto_start": "Auto-start with Windows",
        "backup": "Create backup",
        "restore": "Restore from backup",
        "export": "Export to JSON",
        "save": "Save",
        "cancel": "Cancel",
        "commands": "Commands",
        "chat_tab": "💬  Chat",
        "notes_tab": "📝  Notes",
        "system_tab": "🖥  System",
        "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "months": ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"],
    },
    "de": {
        "app_name": "Astra AI",
        "chat": "Chat",
        "notes": "Notizen",
        "system": "System",
        "settings": "Einstellungen",
        "send": "Senden",
        "input_placeholder": "Nachricht oder Befehl eingeben...",
        "search_placeholder": "Verlauf durchsuchen... (Enter)",
        "welcome": "✨ Willkommen bei <b>Astra AI</b>! Fragen Sie mich alles oder geben Sie <b>help</b> ein.",
        "clear_chat": "Chat geleert",
        "no_results": "Nichts gefunden",
        "voice_listening": "🎤 Höre zu... sprechen Sie!",
        "voice_no_speech": "⏱ Keine Sprache erkannt",
        "voice_no_recognize": "🤔 Konnte nicht erkennen",
        "voice_microphone_error": "❌ Mikrofon nicht verfügbar",
        "exit_message": "Auf Wiedersehen! Ich bin da, wenn Sie mich brauchen. 👋",
        "reminder": "🔔 Erinnerung",
        "reminder_set": "Ich erinnere in",
        "exit": "Beenden",
        "about": "Über",
        "version": "Version",
        "search_results": "Suchergebnisse",
        "note_added": "Notiz hinzugefügt",
        "pomodoro_focus": "Fokus 25 min",
        "pomodoro_break": "Pause 5 min",
        "pomodoro_stop": "Timer stoppen",
        "quick_note": "Schnellnotiz",
        "help_title": "Hilfe / Befehle",
        "settings_title": "Einstellungen",
        "api_key": "API-Schlüssel",
        "voice_output": "Sprachausgabe (TTS)",
        "model": "Modell",
        "auto_start": "Autostart mit Windows",
        "backup": "Backup erstellen",
        "restore": "Wiederherstellen",
        "export": "JSON-Export",
        "save": "Speichern",
        "cancel": "Abbrechen",
        "commands": "Befehle",
        "chat_tab": "💬  Chat",
        "notes_tab": "📝  Notizen",
        "system_tab": "🖥  System",
        "weekdays": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
        "months": ["Januar", "Februar", "März", "April", "Mai", "Juni",
                   "Juli", "August", "September", "Oktober", "November", "Dezember"],
    },
    "fr": {
        "app_name": "Astra AI",
        "chat": "Chat",
        "notes": "Notes",
        "system": "Système",
        "settings": "Paramètres",
        "send": "Envoyer",
        "input_placeholder": "Message ou commande...",
        "search_placeholder": "Chercher... (Entrée)",
        "welcome": "✨ Bienvenue sur <b>Astra AI</b>! Demandez-moi n'importe quoi ou tapez <b>help</b>.",
        "clear_chat": "Chat effacé",
        "no_results": "Rien trouvé",
        "voice_listening": "🎤 J'écoute... parlez!",
        "voice_no_speech": "⏱ Aucune parole détectée",
        "voice_no_recognize": "🤔 Impossible de reconnaître",
        "voice_microphone_error": "❌ Microphone indisponible",
        "exit_message": "Au revoir! Je serai là quand vous aurez besoin de moi. 👋",
        "reminder": "🔔 Rappel",
        "reminder_set": "Je rappelle dans",
        "exit": "Quitter",
        "about": "À propos",
        "version": "Version",
        "search_results": "Résultats",
        "note_added": "Note ajoutée",
        "pomodoro_focus": "Focus 25 min",
        "pomodoro_break": "Pause 5 min",
        "pomodoro_stop": "Arrêter le timer",
        "quick_note": "Note rapide",
        "help_title": "Aide / commandes",
        "settings_title": "Paramètres",
        "api_key": "Clé API",
        "voice_output": "Sortie vocale (TTS)",
        "model": "Modèle",
        "auto_start": "Démarrage auto avec Windows",
        "backup": "Créer une sauvegarde",
        "restore": "Restaurer",
        "export": "Export JSON",
        "save": "Enregistrer",
        "cancel": "Annuler",
        "commands": "Commandes",
        "chat_tab": "💬  Chat",
        "notes_tab": "📝  Notes",
        "system_tab": "🖥  Système",
        "weekdays": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
        "months": ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                   "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"],
    },
}


class I18n:
    def __init__(self, lang="ru"):
        self._lang = lang if lang in TRANSLATIONS else "ru"
        self._strings = TRANSLATIONS[self._lang]

    @property
    def lang(self):
        return self._lang

    def set_lang(self, lang):
        if lang in TRANSLATIONS:
            self._lang = lang
            self._strings = TRANSLATIONS[lang]

    def t(self, key, *args, **kwargs):
        val = self._strings.get(key, key)
        if args:
            val = val.format(*args)
        elif kwargs:
            val = val.format(**kwargs)
        return val

    def weekday(self, n):
        days = self._strings.get("weekdays", TRANSLATIONS["ru"]["weekdays"])
        return days[n] if 0 <= n < len(days) else ""

    def month(self, n):
        months = self._strings.get("months", TRANSLATIONS["ru"]["months"])
        return months[n - 1] if 1 <= n <= len(months) else ""


_global_i18n = I18n()


def t(key, *args, **kwargs):
    return _global_i18n.t(key, *args, **kwargs)


def set_lang(lang):
    _global_i18n.set_lang(lang)


def get_i18n():
    return _global_i18n
