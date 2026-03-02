import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from app.config import (
    AGREEMENT,
    DISCLAIMER_TEXT,
    Q1,
    Q1_OPTIONS,
    Q1_TEXT,
    WELCOME_TEXT,
    user_data_store,
    user_stats_store,
)
from app.database import db
from app.menu import get_keyboard, get_simple_keyboard

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Точка входа /start"""
    user = update.effective_user
    user_id = str(user.id)

    # Проверяем, есть ли пользователь в БД
    db_user = await db.get_user(user_id)

    if db_user:
        # Загружаем из БД в кэш
        user_data_store[user_id] = {
            'username': db_user['username'],
            'first_name': db_user['first_name'],
            'last_name': db_user['last_name'],
            'onboarding_complete': db_user['onboarding_complete'],
            'scenario': db_user['scenario'],
            'answers': db_user['answers'],
            'mood_history': [],
        }

        # Загружаем статистику
        stats = await db.get_user_stats(user_id)
        if stats:
            user_stats_store[user_id] = stats
        else:
            # Создаем новую статистику
            user_stats_store[user_id] = {
                'morning_streak': 0,
                'morning_skip_streak': 0,
                'evening_streak': 0,
                'evening_skip_streak': 0,
                'day_stress_streak': 0,
                'day_stress_skip_streak': 0,
                'last_action_date': {},
            }

        logger.info(f"✅ Пользователь {user_id} загружен из БД")
    else:
        # Создаем нового пользователя
        user_data = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'onboarding_complete': False,
            'scenario': [],
            'answers': {},
            'mood_history': [],
        }

        user_data_store[user_id] = user_data

        user_stats_store[user_id] = {
            'morning_streak': 0,
            'morning_skip_streak': 0,
            'evening_streak': 0,
            'evening_skip_streak': 0,
            'day_stress_streak': 0,
            'day_stress_skip_streak': 0,
            'last_action_date': {},
        }

        # Сохраняем в БД
        await db.save_user(user_id, user_data)
        await db.save_user_stats(user_id, user_stats_store[user_id])
        logger.info(f"✅ Новый пользователь {user_id} создан")

    await update.message.reply_text(WELCOME_TEXT)
    await update.message.reply_text(
        DISCLAIMER_TEXT,
        reply_markup=get_simple_keyboard({"✅ Понимаю и согласен(на)": "agree"}),
    )
    return AGREEMENT


async def agreement_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка согласия"""
    query = update.callback_query
    await query.answer()
    # user_id = str(query.from_user.id)

    if query.data == "agree":
        await query.edit_message_text(
            "Отлично! Давай познакомимся с твоими привычками поближе. Это займёт всего пару минут."
        )
        await query.message.reply_text(Q1_TEXT, reply_markup=get_keyboard(Q1_OPTIONS, "q1"))
        return Q1
    else:
        await query.edit_message_text("Что-то пошло не так. Попробуй /start")
        return ConversationHandler.END
