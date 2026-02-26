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
from app.menu import get_keyboard, get_simple_keyboard

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Точка входа /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_id = str(user.id)

    # Инициализируем данные пользователя
    user_data_store[user_id] = {
        'onboarding_complete': False,
        'scenario': [],
        'answers': {},
    }
    user_stats_store[user_id] = {
        'evening_streak': 0,  # счетчик подряд сделанных вечерних действий
        'evening_skip_streak': 0,  # счетчик подряд пропущенных
        'morning_streak': 0,
        'morning_skip_streak': 0,
        'day_stress_streak': 0,
        'day_stress_skip_streak': 0,
        'last_action_date': {},  # для проверки, что действия за сегодня
    }

    await update.message.reply_text(WELCOME_TEXT)
    await update.message.reply_text(
        DISCLAIMER_TEXT,
        reply_markup=get_simple_keyboard({"✅ Понимаю и согласен(на)": "agree"}),
    )
    return AGREEMENT


# --- Обработка согласия ---
async def agreement_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    # user_id = str(query.from_user.id)

    if query.data == "agree":
        await query.edit_message_text(
            "Отлично! Давай познакомимся с твоими привычками поближе. Это займёт всего пару минут."
        )
        # Начинаем онбординг с первого вопроса
        await query.message.reply_text(Q1_TEXT, reply_markup=get_keyboard(Q1_OPTIONS, "q1"))
        return Q1
    else:
        # Если что-то пошло не так
        await query.edit_message_text("Что-то пошло не так. Попробуй /start")
        return ConversationHandler.END
