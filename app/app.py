import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application

from app.config import BOT_TOKEN, MANUAL_URL, SERVER_IP
from app.main import setup_handlers, run_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Проверка токена
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not configured!")
    sys.exit(1)

# Создаем экземпляр бота
bot_app = Application.builder().token(BOT_TOKEN).build()
scheduler_tasks = []
logger.info("✅ Bot application created")

# Для отслеживания активности
last_activity = datetime.now()

# Вызываем настройку обработчиков
setup_handlers()

if MANUAL_URL:
    BASE_URL = MANUAL_URL
    logger.info(f"✅ Using manual WEBHOOK_URL: {BASE_URL}")
else:
    # Используем HTTPS через nginx
    BASE_URL = f"https://{SERVER_IP}"
    logger.info(f"✅ Using server IP with HTTPS: {BASE_URL}")

WEBHOOK_PATH = "/webhook"
FULL_WEBHOOK_URL = f"{BASE_URL.rstrip('/')}{WEBHOOK_PATH}"


# --- LIFESPAN ДЛЯ FASTAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global last_activity
    last_activity = datetime.now()

    logger.info("🚀 Запуск приложения...")

    try:
        # 1. Инициализируем бота
        await bot_app.initialize()
        logger.info("✅ Бот инициализирован")

        # 2. Устанавливаем вебхук
        if FULL_WEBHOOK_URL:
            webhook_info = await bot_app.bot.get_webhook_info()
            logger.info(f"Текущий webhook: {webhook_info.url}")

            result = await bot_app.bot.set_webhook(
                url=FULL_WEBHOOK_URL, allowed_updates=Update.ALL_TYPES, drop_pending_updates=True
            )

            if result:
                logger.info(f"✅ Webhook установлен: {FULL_WEBHOOK_URL}")
            else:
                logger.error("❌ Не удалось установить webhook")

        # 3. Запускаем планировщик
        scheduler_task = asyncio.create_task(run_scheduler())
        scheduler_tasks.append(scheduler_task)
        logger.info("✅ Планировщик запущен")

        yield  # Приложение работает

    finally:
        # Остановка
        logger.info("🛑 Остановка приложения...")

        # Отменяем задачи планировщика
        for task in scheduler_tasks:
            task.cancel()

        # Удаляем вебхук
        await bot_app.bot.delete_webhook()
        logger.info("✅ Webhook удален")

        # Останавливаем бота
        await bot_app.shutdown()
        logger.info("✅ Бот остановлен")


app = FastAPI(lifespan=lifespan)
