import logging
import os
import sys
from datetime import datetime

from fastapi import Request
from telegram import Update

from app.app import app, bot_app
from app.config import FULL_WEBHOOK_URL, WEBHOOK_PATH, user_data_store
from app.sheduler import send_day_stress_message, send_evening_message, send_morning_message

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout
)
logger = logging.getLogger(__name__)
last_activity = datetime.now()


@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    """Обработка входящих обновлений от Telegram"""
    global last_activity
    last_activity = datetime.now()

    try:
        # Получаем данные от Telegram
        update_data = await request.json()
        logger.info(f"📨 Получено обновление: {update_data.get('update_id')}")

        # Создаем объект Update
        update = Update.de_json(update_data, bot_app.bot)

        # Логируем тип обновления
        if update.message:
            logger.info(f"💬 Сообщение от {update.message.from_user.id}: {update.message.text}")
        elif update.callback_query:
            logger.info(f"🖱️ Callback от {update.callback_query.from_user.id}: {update.callback_query.data}")

        # Обрабатываем обновление
        await bot_app.process_update(update)

        return {"ok": True}

    except Exception as e:
        logger.error(f"❌ Ошибка обработки: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@app.get(WEBHOOK_PATH)
async def webhook_get():
    """Telegram иногда отправляет GET для проверки webhook"""
    logger.info("📞 GET request to webhook (health check)")
    return {
        "ok": True, 
        "message": "Webhook is active and listening",
        "method": "GET",
        "webhook_url": FULL_WEBHOOK_URL,
        "timestamp": datetime.now().isoformat()
    }


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
        "users_count": len(user_data_store),
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
    uvicorn.run("app.app:app", host="0.0.0.0", port=port, reload=True)
