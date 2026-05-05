import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI

from app.database import db
from app.handler import setup_handlers
from app.sheduler import run_scheduler

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout
)
logger = logging.getLogger(__name__)

scheduler_tasks = []
last_activity = datetime.now()

setup_handlers()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global last_activity
    last_activity = datetime.now()

    logger.info("🚀 Запуск приложения (VK Only)...")

    try:
        # 1. База данных
        await db.connect()
        logger.info("✅ База данных подключена")

        # 2. Кэш пользователей из БД
        from app.bot_app import load_users_to_cache

        await load_users_to_cache()
        logger.info("✅ Кэш пользователей загружен")

        # # Загружаем локальную AI-модель (LoRA r=2) при старте
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

        # 3. Планировщик
        scheduler_task = asyncio.create_task(run_scheduler())
        scheduler_tasks.append(scheduler_task)
        logger.info("✅ Планировщик запущен")

        yield

    finally:
        logger.info("🛑 Остановка приложения...")
        for task in scheduler_tasks:
            task.cancel()
        await db.close()
        logger.info("✅ Соединение с БД закрыто")


app = FastAPI(lifespan=lifespan)
