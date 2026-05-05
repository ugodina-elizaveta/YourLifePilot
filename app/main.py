import logging
import os
import sys
from datetime import datetime, timedelta

from starlette.responses import PlainTextResponse
from fastapi import Request

from app.app import app
from app.config import user_data_store, FULL_WEBHOOK_URL, WEBHOOK_PATH
from app.sheduler import send_morning_message, send_evening_message, send_day_stress_message
from app.vk_module.vk_bot import vk_bot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout
)
logger = logging.getLogger(__name__)
last_activity = datetime.now()

# Код подтверждения VK
VK_CONFIRMATION_CODE = os.getenv("VK_CONFIRMATION_CODE", "")

# Словарь для отслеживания уже обработанных сообщений (защита от дубликатов)
processed_messages: dict = {}


# ============================================================
# ЭНДПОИНТЫ ДЛЯ ПРОВЕРКИ СТАТУСА
# ============================================================


@app.get("/")
async def root():
    return {
        "name": "YourLifePilot Bot (VK)",
        "status": "running",
        "platform": "Self-hosted",
        "server_ip": "185.185.142.217",
        "users_count": len(user_data_store),
        "last_activity": last_activity.isoformat(),
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "last_activity": last_activity.isoformat(),
        "users_count": len(user_data_store),
    }


# ============================================================
# ЭНДПОИНТЫ ДЛЯ ТЕСТОВЫХ РАССЫЛОК
# ============================================================


@app.get("/trigger-morning")
async def trigger_morning_webhook(user_id: str = None):
    try:
        await send_morning_message(target_user_id=user_id)
        return {"ok": True, "message": f"Утренняя рассылка выполнена для {user_id or 'всех'}"}
    except Exception as e:
        logger.error(f"Error in trigger-morning: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/trigger-evening")
async def trigger_evening_webhook(user_id: str = None):
    try:
        await send_evening_message(target_user_id=user_id)
        return {"ok": True, "message": f"Вечерняя рассылка выполнена для {user_id or 'всех'}"}
    except Exception as e:
        logger.error(f"Error in trigger-evening: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/trigger-day")
async def trigger_day_webhook(user_id: str = None):
    try:
        await send_day_stress_message(target_user_id=user_id)
        return {"ok": True, "message": f"Дневная рассылка выполнена для {user_id or 'всех'}"}
    except Exception as e:
        logger.error(f"Error in trigger-day: {e}")
        return {"ok": False, "error": str(e)}


# ============================================================
# VK CALLBACK API
# ============================================================
@app.api_route("/vk-webhook", methods=["POST", "GET"])
async def vk_webhook(request: Request):
    global processed_messages, last_activity

    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        return PlainTextResponse("error")

    event_type = data.get("type")

    # Подтверждение сервера
    if event_type == "confirmation":
        logger.info(f"VK confirmation request, group_id={data.get('group_id')}")
        return PlainTextResponse(VK_CONFIRMATION_CODE)

    # Входящее сообщение
    if event_type == "message_new":
        last_activity = datetime.now()
        message = data["object"]["message"]
        message_id = str(message.get("conversation_message_id", message.get("id")))
        from_id = str(message.get("from_id"))

        msg_key = f"msg_{from_id}_{message_id}"
        if msg_key in processed_messages:
            return PlainTextResponse("ok")

        processed_messages[msg_key] = datetime.now()
        logger.info(f"New message from VK user {from_id}: {message.get('text', '')[:50]}")
        await vk_bot.process_message(message)
        return PlainTextResponse("ok")

    # Нажатие на callback-кнопку
    if event_type == "message_event":
        last_activity = datetime.now()
        event_data = data["object"]
        user_id = str(event_data.get("user_id"))
        event_id = str(event_data.get("event_id", ""))
        payload = event_data.get("payload", {})

        cb_key = f"cb_{user_id}_{event_id}"
        if cb_key in processed_messages:
            return PlainTextResponse("ok")

        processed_messages[cb_key] = datetime.now()

        if isinstance(payload, str):
            import json

            payload = json.loads(payload)

        cmd = payload.get("cmd", "")
        logger.info(f"VK callback from {user_id}: {cmd}")
        await vk_bot.handler.handle(user_id, "", cmd)
        return PlainTextResponse("ok")

    # Очистка старых записей при накоплении
    if len(processed_messages) > 500:
        cutoff = datetime.now() - timedelta(minutes=5)
        processed_messages = {k: v for k, v in processed_messages.items() if v > cutoff}

    return PlainTextResponse("ok")


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.app:app", host="0.0.0.0", port=port, reload=False)
