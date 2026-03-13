import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from app.config import (
    AGE,
    AGE_OPTIONS,
    AGE_QUESTION,
    AGREEMENT,
    DISCLAIMER_TEXT,
    EVENING_TIME,
    EVENING_TIME_OPTIONS,
    EVENING_TIME_QUESTION,
    MORNING_TIME,
    MORNING_TIME_OPTIONS,
    MORNING_TIME_QUESTION,
    OCCUPATION,
    OCCUPATION_OPTIONS,
    OCCUPATION_QUESTION,
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
            'age_group': db_user.get('age_group'),
            'occupation': db_user.get('occupation'),
            'morning_time': db_user.get('morning_time', '09:00'),
            'evening_time': db_user.get('evening_time', '21:00'),
            'mood_history': [],
        }

        # Загружаем статистику
        stats = await db.get_user_stats(user_id)
        if stats:
            user_stats_store[user_id] = stats
        else:
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
        user_data_store[user_id] = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'onboarding_complete': False,
            'scenario': [],
            'answers': {},
            'age_group': None,
            'occupation': None,
            'morning_time': '09:00',
            'evening_time': '21:00',
            'mood_history': [],
        }

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
        await db.save_user(user_id, user_data_store[user_id])
        await db.save_user_stats(user_id, user_stats_store[user_id])
        logger.info(f"✅ Новый пользователь {user_id} создан")

    await update.message.reply_text(WELCOME_TEXT)
    await update.message.reply_text(
        DISCLAIMER_TEXT,
        reply_markup=get_simple_keyboard({"✅ Понимаю и согласен(на)": "agree"}),
    )
    return AGREEMENT


async def agreement_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка согласия - переходим к возрастной группе"""
    query = update.callback_query
    await query.answer()
    # user_id = str(query.from_user.id)

    if query.data == "agree":
        await query.edit_message_text(
            "Отлично! Давай познакомимся поближе, чтобы я мог подбирать более персонализированные советы."
        )

        # Вопрос 1: Возрастная группа
        await query.message.reply_text(AGE_QUESTION, reply_markup=get_keyboard(AGE_OPTIONS, "age"))
        return AGE
    else:
        await query.edit_message_text("Что-то пошло не так. Попробуй /start")
        return ConversationHandler.END


async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ответа на возрастную группу"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    # Сохраняем ответ
    answer_index = int(data.split('_')[1])
    answer_text = AGE_OPTIONS[answer_index]
    user_data_store[user_id]['age_group'] = answer_text

    await query.edit_message_text("Спасибо! Записал.")

    # Вопрос 2: Род занятий
    await query.message.reply_text(OCCUPATION_QUESTION, reply_markup=get_keyboard(OCCUPATION_OPTIONS, "occupation"))
    return OCCUPATION


async def occupation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ответа на род занятий"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    answer_index = int(data.split('_')[1])
    answer_text = OCCUPATION_OPTIONS[answer_index]
    user_data_store[user_id]['occupation'] = answer_text

    await query.edit_message_text("Спасибо! Записал.")

    # Вопрос 3: Удобное время для утренних сообщений
    await query.message.reply_text(
        MORNING_TIME_QUESTION, reply_markup=get_keyboard(MORNING_TIME_OPTIONS, "morning_time")
    )
    return MORNING_TIME


async def morning_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора времени для утренних сообщений"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    answer_index = int(data.split('_')[1])
    answer_text = MORNING_TIME_OPTIONS[answer_index]

    # Если выбрано "Не важно", оставляем 9:00
    if answer_text == "Не важно (09:00)":
        user_data_store[user_id]['morning_time'] = "09:00"
    else:
        user_data_store[user_id]['morning_time'] = answer_text

    await query.edit_message_text("Спасибо! Записал.")

    # Вопрос 4: Удобное время для вечерних сообщений
    await query.message.reply_text(
        EVENING_TIME_QUESTION, reply_markup=get_keyboard(EVENING_TIME_OPTIONS, "evening_time")
    )
    return EVENING_TIME


async def evening_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора времени для вечерних сообщений"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    answer_index = int(data.split('_')[1])
    answer_text = EVENING_TIME_OPTIONS[answer_index]

    if answer_text == "Не важно (21:00)":
        user_data_store[user_id]['evening_time'] = "21:00"
    else:
        user_data_store[user_id]['evening_time'] = answer_text

    await query.edit_message_text("Отлично! Теперь несколько вопросов про твой сон и самочувствие.")

    # Сохраняем обновленные данные в БД
    await db.save_user(user_id, user_data_store[user_id])

    # Переходим к первому вопросу про сон
    await query.message.reply_text(Q1_TEXT, reply_markup=get_keyboard(Q1_OPTIONS, "q1"))
    return Q1
