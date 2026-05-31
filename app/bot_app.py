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

            # Преобразуем JSONB-поля
            scenario = user['scenario']
            if isinstance(scenario, str):
                import json

                try:
                    scenario = json.loads(scenario)
                except:
                    scenario = []

            answers = user['answers']
            if isinstance(answers, str):
                import json

                try:
                    answers = json.loads(answers)
                except:
                    answers = {}

            user_data_store[user_id] = {
                'username': user['username'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'onboarding_complete': user['onboarding_complete'],
                'scenario': scenario if isinstance(scenario, list) else [],
                'answers': answers if isinstance(answers, dict) else {},
                'age_group': user.get('age_group'),
                'occupation': user.get('occupation'),
                'morning_time': user.get('morning_time', '09:00'),
                'evening_time': user.get('evening_time', '21:00'),
                'physical_limits': user.get('physical_limits'),
                'notification_frequency': user.get('notification_frequency'),
                'daily_time': user.get('daily_time'),
                'biweekly_time': user.get('biweekly_time'),
                'notification_skip_days': user.get('notification_skip_days', 0),
                'last_sent_date': user.get('last_sent_date'),
                'mood_history': [],
            }

            stats = await db.get_user_stats(user_id)
            if stats:
                user_stats_store[user_id] = stats

        logger.info(f"✅ Загружено {len(user_data_store)} пользователей в кэш")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки пользователей: {e}")
