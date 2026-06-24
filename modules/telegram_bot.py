"""
Telegram bot — manage Astra AI via Telegram.
Requires: python-telegram-bot (pip install python-telegram-bot)
"""

import logging
import threading
from pathlib import Path

logger = logging.getLogger("Astra.Telegram")

BOT_TOKEN_FILE = Path(__file__).parent.parent / "data" / "telegram_token.txt"

_bot_instance = None
_bot_thread = None


def get_token():
    if BOT_TOKEN_FILE.exists():
        return BOT_TOKEN_FILE.read_text("utf-8").strip()
    return ""


def set_token(token):
    BOT_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    BOT_TOKEN_FILE.write_text(token.strip(), encoding="utf-8")
    return True


def start_bot(assistant, token=None):
    global _bot_instance, _bot_thread

    if _bot_instance:
        logger.info("Telegram bot already running")
        return True

    token = token or get_token()
    if not token:
        logger.warning("No Telegram token set")
        return False

    try:
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

        app = ApplicationBuilder().token(token).build()

        async def start(update, context):
            await update.message.reply_text(
                "🤖 Astra AI Bot\n\n"
                "Команды:\n"
                "/chat <текст> — отправить сообщение\n"
                "/status — статус ассистента\n"
                "/theme — текущая тема\n"
                "/ping — проверка связи"
            )

        async def chat(update, context):
            text = " ".join(context.args)
            if not text:
                await update.message.reply_text("Использование: /chat <текст>")
                return
            try:
                result = assistant.process(text)
                await update.message.reply_text(result or "❌ Нет ответа")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {e}")

        async def status(update, context):
            h = len(getattr(assistant, "history", []))
            n = len(getattr(assistant, "notes", []))
            await update.message.reply_text(
                f"📊 Astra AI\n"
                f"💬 Сообщений: {h}\n"
                f"📝 Заметок: {n}\n"
                f"🔊 TTS: {'✅' if assistant.voice_enabled else '❌'}"
            )

        async def theme(update, context):
            from modules.theme import C
            await update.message.reply_text(f"🎨 Тема: {C.current}")

        async def ping(update, context):
            await update.message.reply_text("🏓 Pong!")

        async def handle_text(update, context):
            text = update.message.text
            result = assistant.process(text)
            await update.message.reply_text(result or "❌ Нет ответа")

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("chat", chat))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CommandHandler("theme", theme))
        app.add_handler(CommandHandler("ping", ping))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        def run():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            app.run_polling()

        _bot_thread = threading.Thread(target=run, daemon=True)
        _bot_thread.start()
        _bot_instance = app
        logger.info("Telegram bot started")
        return True

    except ImportError:
        logger.warning("python-telegram-bot not installed. Install: pip install python-telegram-bot")
        return False
    except Exception as e:
        logger.error("Telegram bot failed: %s", e)
        return False


def stop_bot():
    global _bot_instance
    if _bot_instance:
        try:
            _bot_instance.stop()
        except Exception:
            pass
        _bot_instance = None
        logger.info("Telegram bot stopped")
