# /YourLifePilot/app/app.py

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from telegram import Update

from app.bot_app import bot_app, load_users_to_cache
from app.config import FULL_WEBHOOK_URL
from app.database import db
from app.handler import setup_handlers
from app.sheduler import run_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

scheduler_tasks = []
last_activity = datetime.now()

# Вызываем настройку обработчиков
setup_handlers()


# --- LIFESPAN ДЛЯ FASTAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global last_activity
    last_activity = datetime.now()

    logger.info("🚀 Запуск приложения...")

    try:
        # 1. Подключаемся к базе данных
        await db.connect()
        logger.info("✅ База данных подключена")

        # 2. Загружаем пользователей в кэш
        await load_users_to_cache()
        logger.info("✅ Кэш пользователей загружен")

        # 3. Инициализируем бота
        await bot_app.initialize()
        logger.info("✅ Бот инициализирован")

        # 4. Устанавливаем вебхук
        if FULL_WEBHOOK_URL:
            webhook_info = await bot_app.bot.get_webhook_info()
            logger.info(f"Текущий webhook: {webhook_info.url}")

            with open('/etc/nginx/ssl/yourlifepilot.crt', 'rb') as f:
                certificate = f.read()

            result = await bot_app.bot.set_webhook(
                url=FULL_WEBHOOK_URL,
                certificate=certificate,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                max_connections=40,
            )

            if result:
                logger.info(f"✅ Webhook установлен: {FULL_WEBHOOK_URL}")
            else:
                logger.error("❌ Не удалось установить webhook")

        # # 5. Загружаем локальную AI-модель (LoRA r=2) при старте
        # try:
        #     from app.local_ai import local_ai
        #     logger.info("🤖 Предварительная загрузка локальной модели LoRA r=2...")
        #     local_ai.load_model()
        #     if local_ai.is_loaded:
        #         logger.info("✅ Локальная модель успешно загружена")
        #     else:
        #         logger.warning("⚠️ Локальная модель не загрузилась, будет использоваться YandexGPT")
        # except Exception as e:
        #     logger.error(f"❌ Ошибка при загрузке локальной модели: {e}")

        # 6. Запускаем планировщик
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

        # Закрываем соединение с БД
        await db.close()
        logger.info("✅ Соединение с БД закрыто")


app = FastAPI(lifespan=lifespan)
