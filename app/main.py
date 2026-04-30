import logging
import os
import sys
from datetime import datetime
from starlette.responses import PlainTextResponse
from app.vk_module.vk_bot import vk_bot
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
        "timestamp": datetime.now().isoformat(),
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
async def trigger_morning_webhook(user_id: str = None):
    """
    Тестовый запуск утренней рассылки.
    Если указан user_id - только для этого пользователя.
    Пример: /trigger-morning?user_id=962369479
    """
    try:

        class DummyContext:
            def __init__(self, bot):
                self.bot = bot

        dummy_context = DummyContext(bot_app.bot)

        if user_id:
            await send_morning_message(dummy_context, target_user_id=user_id)
            return {"ok": True, "message": f"Тестовая утренняя рассылка для пользователя {user_id} выполнена"}
        else:
            await send_morning_message(dummy_context)
            return {"ok": True, "message": "Массовая утренняя рассылка выполнена"}

    except Exception as e:
        logger.error(f"Error in trigger-morning: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/trigger-evening")
async def trigger_evening_webhook(user_id: str = None):
    """Тестовый запуск вечерней рассылки для конкретного пользователя"""
    try:

        class DummyContext:
            def __init__(self, bot):
                self.bot = bot

        dummy_context = DummyContext(bot_app.bot)

        if user_id:
            await send_evening_message(dummy_context, target_user_id=user_id)
            return {"ok": True, "message": f"Тестовая вечерняя рассылка для пользователя {user_id} выполнена"}
        else:
            await send_evening_message(dummy_context)
            return {"ok": True, "message": "Массовая вечерняя рассылка выполнена"}

    except Exception as e:
        logger.error(f"Error in trigger-evening: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/trigger-day")
async def trigger_day_webhook(user_id: str = None):
    """Тестовый запуск дневной рассылки для конкретного пользователя"""
    try:

        class DummyContext:
            def __init__(self, bot):
                self.bot = bot

        dummy_context = DummyContext(bot_app.bot)

        if user_id:
            await send_day_stress_message(dummy_context, target_user_id=user_id)
            return {"ok": True, "message": f"Тестовая дневная рассылка для пользователя {user_id} выполнена"}
        else:
            await send_day_stress_message(dummy_context)
            return {"ok": True, "message": "Массовая дневная рассылка выполнена"}

    except Exception as e:
        logger.error(f"Error in trigger-day: {e}")
        return {"ok": False, "error": str(e)}


VK_CONFIRMATION_CODE = os.getenv("VK_CONFIRMATION_CODE", "")


# ---- НОВЫЙ ЭНДПОИНТ ДЛЯ VK ----
@app.api_route("/vk-webhook", methods=["POST", "GET"])
async def vk_webhook(request: Request):
    data = await request.json()
    event_type = data.get("type")

    # Подтверждение сервера Callback API
    if event_type == "confirmation":
        logger.info(f"VK confirmation request, group_id={data.get('group_id')}")
        return PlainTextResponse(VK_CONFIRMATION_CODE)

    # Входящее сообщение
    if event_type == "message_new":
        message = data["object"]["message"]
        await vk_bot.process_message(message)
        return {"ok": True}

    # Можно обработать другие события при необходимости
    logger.warning(f"Unknown VK event: {event_type}")
    return {"ok": False, "error": "unsupported event"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.app:app", host="0.0.0.0", port=port, reload=False)
