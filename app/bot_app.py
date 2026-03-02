import logging
import sys
from datetime import datetime

from telegram.ext import Application

from app.config import BOT_TOKEN, user_data_store, user_stats_store
from app.database import db

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
logger.info("✅ Bot application created")

# Для отслеживания активности
last_activity = datetime.now()


# Функция для загрузки пользователей из БД в кэш
async def load_users_to_cache():
    """Загружает пользователей из БД в кэш при старте"""
    try:
        users = await db.get_all_users()
        for user in users:
            user_id = user['user_id']
            user_data_store[user_id] = {
                'username': user['username'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'onboarding_complete': user['onboarding_complete'],
                'scenario': user['scenario'],
                'answers': user['answers'],
                'mood_history': [],  # Будет загружаться по необходимости
            }

            # Загружаем статистику
            stats = await db.get_user_stats(user_id)
            if stats:
                user_stats_store[user_id] = stats

        logger.info(f"✅ Загружено {len(user_data_store)} пользователей в кэш")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки пользователей: {e}")
