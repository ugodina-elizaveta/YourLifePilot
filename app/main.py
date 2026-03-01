import asyncio
import logging
import os
import sys
from datetime import datetime

from fastapi import Request
from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler

from app.anketa import cancel, q1_handler, q2_handler, q3_handler, q4_handler, q5_handler
from app.app import FULL_WEBHOOK_URL, WEBHOOK_PATH, app, bot_app
from app.config import AGREEMENT, Q1, Q2, Q3, Q4, Q5, user_data_store
from app.handler import (
    day_stress_handler,
    evening_action_handler,
    feeling_handler,
    morning_action_handler,
    morning_micro_handler,
)
from app.sheduler import send_day_stress_message, send_evening_message, send_morning_message
from app.start import agreement_handler, start

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout
)
logger = logging.getLogger(__name__)
last_activity = datetime.now()


# --- ПЛАНИРОВЩИК ЗАДАЧ ---
async def run_scheduler():
    """Планировщик для периодических рассылок"""
    logger.info("🕐 Планировщик запущен")

    while True:
        try:
            now = datetime.now()
            current_time = now.time()

            # Утренняя рассылка в 9:00
            if current_time.hour == 9 and current_time.minute == 0 and current_time.second < 10:
                logger.info("⏰ Запуск утренней рассылки по расписанию")

                class DummyContext:
                    def __init__(self, bot):
                        self.bot = bot

                dummy_context = DummyContext(bot_app.bot)
                await send_morning_message(dummy_context)
                await asyncio.sleep(60)  # Пропускаем минуту

            # Дневная рассылка в 15:00
            elif current_time.hour == 15 and current_time.minute == 0 and current_time.second < 10:
                logger.info("⏰ Запуск дневной рассылки по расписанию")

                class DummyContext:
                    def __init__(self, bot):
                        self.bot = bot

                dummy_context = DummyContext(bot_app.bot)
                await send_day_stress_message(dummy_context)
                await asyncio.sleep(60)

            # Вечерняя рассылка в 21:00
            elif current_time.hour == 21 and current_time.minute == 0 and current_time.second < 10:
                logger.info("⏰ Запуск вечерней рассылки по расписанию")

                class DummyContext:
                    def __init__(self, bot):
                        self.bot = bot

                dummy_context = DummyContext(bot_app.bot)
                await send_evening_message(dummy_context)
                await asyncio.sleep(60)

            # Проверка каждые 30 секунд
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
            await asyncio.sleep(60)  # При ошибке ждем минуту


# --- НАСТРОЙКА ОБРАБОТЧИКОВ ---
def setup_handlers():
    """Настраивает все обработчики для бота"""
    # Обработчик диалога онбординга
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AGREEMENT: [CallbackQueryHandler(agreement_handler, pattern="^agree$")],
            Q1: [CallbackQueryHandler(q1_handler, pattern="^q1_")],
            Q2: [CallbackQueryHandler(q2_handler, pattern="^q2_")],
            Q3: [CallbackQueryHandler(q3_handler, pattern="^q3_")],
            Q4: [CallbackQueryHandler(q4_handler, pattern="^q4_")],
            Q5: [CallbackQueryHandler(q5_handler, pattern="^q5_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    bot_app.add_handler(conv_handler)

    # Обработчики колбэков
    bot_app.add_handler(CallbackQueryHandler(morning_action_handler, pattern="^morning_"))
    bot_app.add_handler(CallbackQueryHandler(morning_micro_handler, pattern="^morning_micro_"))
    bot_app.add_handler(CallbackQueryHandler(evening_action_handler, pattern="^evening_"))
    bot_app.add_handler(CallbackQueryHandler(day_stress_handler, pattern="^day_stress_"))
    bot_app.add_handler(CallbackQueryHandler(feeling_handler, pattern="^feeling_"))

    # Добавляем команду для тестовой отправки
    async def trigger_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await send_morning_message(context)
        await update.message.reply_text("Утренние сообщения отправлены!")

    async def trigger_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await send_evening_message(context)
        await update.message.reply_text("Вечерние сообщения отправлены!")

    async def trigger_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await send_day_stress_message(context)
        await update.message.reply_text("Дневные сообщения отправлены!")

    bot_app.add_handler(CommandHandler("trigger_morning", trigger_morning))
    bot_app.add_handler(CommandHandler("trigger_evening", trigger_evening))
    bot_app.add_handler(CommandHandler("trigger_day", trigger_day))

    logger.info("✅ Handlers configured")


@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    """Обработка входящих обновлений от Telegram"""
    global last_activity
    last_activity = datetime.now()

    try:
        # Получаем данные от Telegram
        update_data = await request.json()
        logger.debug(f"Received update: {update_data.get('update_id')}")

        # Создаем объект Update
        update = Update.de_json(update_data, bot_app.bot)

        # Обрабатываем обновление
        await bot_app.process_update(update)

        return {"ok": True}

    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


# Эндпоинты для проверки статуса
@app.get("/")
async def root():
    return {
        "name": "YourLifePilot Bot",
        "status": "running",
        "platform": "Self-hosted",
        "server_ip": "185.185.142.217",
        "webhook": FULL_WEBHOOK_URL,
        "users_count": len(user_data_store),
        "last_activity": last_activity.isoformat(),
    }


@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {
        "status": "healthy",
        "bot_initialized": bot_app._initialized if hasattr(bot_app, '_initialized') else False,
        "last_activity": last_activity.isoformat(),
    }


# Эндпоинты для тестовых рассылок
@app.get("/trigger-morning")
async def trigger_morning_webhook():
    """Для тестового запуска утренней рассылки"""
    try:

        class DummyContext:
            def __init__(self, bot):
                self.bot = bot

        dummy_context = DummyContext(bot_app.bot)
        await send_morning_message(dummy_context)
        return {"ok": True, "message": "Morning messages sent"}
    except Exception as e:
        logger.error(f"Error in trigger-morning: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/trigger-evening")
async def trigger_evening_webhook():
    """Для тестового запуска вечерней рассылки"""
    try:

        class DummyContext:
            def __init__(self, bot):
                self.bot = bot

        dummy_context = DummyContext(bot_app.bot)
        await send_evening_message(dummy_context)
        return {"ok": True, "message": "Evening messages sent"}
    except Exception as e:
        logger.error(f"Error in trigger-evening: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/trigger-day")
async def trigger_day_webhook():
    """Для тестового запуска дневной рассылки"""
    try:

        class DummyContext:
            def __init__(self, bot):
                self.bot = bot

        dummy_context = DummyContext(bot_app.bot)
        await send_day_stress_message(dummy_context)
        return {"ok": True, "message": "Day messages sent"}
    except Exception as e:
        logger.error(f"Error in trigger-day: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/test-newsletter")
async def test_newsletter(type: str = "morning"):
    """Тестовый запуск рассылки: /test-newsletter?type=morning/evening/day"""
    try:

        class DummyContext:
            def __init__(self, bot):
                self.bot = bot

        dummy_context = DummyContext(bot_app.bot)

        if type == "morning":
            await send_morning_message(dummy_context)
            return {"ok": True, "message": "Тестовая утренняя рассылка выполнена"}
        elif type == "evening":
            await send_evening_message(dummy_context)
            return {"ok": True, "message": "Тестовая вечерняя рассылка выполнена"}
        elif type == "day":
            await send_day_stress_message(dummy_context)
            return {"ok": True, "message": "Тестовая дневная рассылка выполнена"}
        else:
            return {"ok": False, "error": "Неверный тип. Используйте: morning/evening/day"}
    except Exception as e:
        logger.error(f"Ошибка в тестовой рассылке: {e}")
        return {"ok": False, "error": str(e)}


# Для локального запуска
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
