# Astra AI

Когнитивный голосовой ассистент с адаптивным мышлением, эмоциональным интеллектом и графом знаний. Работает полностью локально — без интернета, без облаков, без слежки.

- **Сайт**: https://psodhdh776.github.io/AstraAI/
- **Релизы**: https://github.com/psodhdh776/AstraAI/releases
- **CI**: https://github.com/psodhdh776/AstraAI/actions

## Возможности

- 🧠 Фрактальное мышление — когнитивная архитектура с 7-этапным конвейером
- 🗣️ Голосовое управление с wake-word «Астра» (TTS/STT, полностью офлайн)
- 💾 5 типов памяти: краткосрочная, эпизодическая, семантическая, процедурная, долговременная
- 🔌 Система плагинов с маркетплейсом (Telegram, горячие клавиши, клипборд и др.)
- 🌐 Встроенный REST API + Web UI (порт 8741)
- 🏠 Интеграция с Home Assistant
- 📱 Портированный движок для Android
- 🤖 6 локальных движков: чат, диалог, эмоции, семантика, фракталы, мышление

## Быстрый старт

```bash
pip install -r requirements.txt
python app.py
```

Откройте браузер:
- **Управление**: http://127.0.0.1:8741/
- **Лендинг**: http://127.0.0.1:8741/landing

## REST API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/status` | Статус ассистента |
| GET | `/history` | История диалога |
| POST | `/chat` | Отправить сообщение |
| POST | `/voice` | Включить/выключить голос |
| GET | `/github/status` | Статус Git-интеграции |
| POST | `/github/push` | Push на GitHub |
| POST | `/github/release` | Создать релиз |
| GET | `/github/check-update` | Проверить обновление |
| POST | `/github/update` | Скачать обновление |
| GET | `/theme` | Текущая тема |
| POST | `/theme` | Сменить тему |
| GET | `/memory` | Статистика памяти |
| GET | `/plugins/*` | Управление плагинами |
| GET | `/backups` | Список бэкапов |

## GitHub CI/CD

### Push на GitHub
```powershell
.\push_to_github.ps1 -CommitMessage "my message"
```
Автоматически: `init` → `add -A` → `commit` → `push`. Токен читает из `data/github_config.json`.

### Создание релиза
```bash
python create_release.py --tag v2.2.0 --title "v2.2.0 — Название" --list
python create_release.py --list
```

### Непрерывная интеграция
GitHub Actions автоматически запускает тесты (Python 3.12/3.13/3.14) на каждый push в `main`. При публикации релиза собирается `.exe` через PyInstaller.

## Архитектура

```
🧠 Фрактальное ядро — когнитивная обработка
🗣️ Голосовые движки — TTS / STT
💬 Чат / Диалог — марковские цепи + TF-IDF
📦 Память — эпизодическая + семантическая + процедурная
🔌 Плагины — маркетплейс, Telegram, горячие клавиши
🌐 REST API + Web UI — удалённое управление
📱 Android — портативный движок
```

## Тестирование

```bash
pip install pytest sounddevice psutil numpy
python -m pytest tests/ -v --tb=short --ignore=tests/test_desktop_widgets.py --ignore=tests/test_chat_widget_md.py --ignore=tests/test_gui.py
```

**644 теста, 0 падений** — 44 тестовых файла, покрытие всех 52 модулей.

## Требования

- **Python**: 3.12–3.14
- **ОС**: Windows 10/11 (основная), Android (портированный движок)
- **Дополнительно**: PySide6 (только для GUI-режима)

## Лицензия

MIT
