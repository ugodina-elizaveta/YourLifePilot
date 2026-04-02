# /YourLifePilot/app/start.py

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from app.config import (
    AGE,
    AGE_OPTIONS,
    AGE_QUESTION,
    AGREEMENT,
    BIWEEKLY_TIME,
    BIWEEKLY_TIME_OPTIONS,
    BIWEEKLY_TIME_QUESTION,
    DAILY_TIME,
    DAILY_TIME_OPTIONS,
    DAILY_TIME_QUESTION,
    DISCLAIMER_TEXT,
    EVENING_TIME,
    EVENING_TIME_OPTIONS,
    EVENING_TIME_QUESTION,
    MORNING_TIME,
    MORNING_TIME_OPTIONS,
    MORNING_TIME_QUESTION,
    NOTIFICATION_FREQ,
    NOTIFICATION_FREQUENCY_OPTIONS,
    NOTIFICATION_FREQUENCY_QUESTION,
    OCCUPATION,
    OCCUPATION_OPTIONS,
    OCCUPATION_QUESTION,
    PHYSICAL_LIMITS,
    PHYSICAL_LIMITS_OPTIONS,
    PHYSICAL_LIMITS_QUESTION,
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

    db_user = await db.get_user(user_id)

    if db_user:
        # Загружаем существующего пользователя
        scenario_data = db_user['scenario']
        answers_data = db_user['answers']

        if isinstance(scenario_data, str):
            import json

            try:
                scenario_data = json.loads(scenario_data)
            except:
                scenario_data = []

        if isinstance(answers_data, str):
            import json

            try:
                answers_data = json.loads(answers_data)
            except:
                answers_data = {}

        user_data_store[user_id] = {
            'username': db_user['username'],
            'first_name': db_user['first_name'],
            'last_name': db_user['last_name'],
            'onboarding_complete': db_user['onboarding_complete'],
            'scenario': scenario_data if isinstance(scenario_data, list) else [],
            'answers': answers_data if isinstance(answers_data, dict) else {},
            'age_group': db_user.get('age_group'),
            'occupation': db_user.get('occupation'),
            'morning_time': db_user.get('morning_time', '09:00'),
            'evening_time': db_user.get('evening_time', '21:00'),
            'physical_limits': db_user.get('physical_limits'),
            'notification_frequency': db_user.get('notification_frequency'),
            'daily_time': db_user.get('daily_time'),
            'biweekly_time': db_user.get('biweekly_time'),
            'mood_history': [],
        }

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
        # Создаём нового пользователя
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
            'physical_limits': None,
            'notification_frequency': None,
            'daily_time': None,
            'biweekly_time': None,
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

        await db.save_user(user_id, user_data_store[user_id])
        await db.save_user_stats(user_id, user_stats_store[user_id])
        logger.info(f"✅ Новый пользователь {user_id} создан")

    await update.message.reply_text(WELCOME_TEXT)
    await update.message.reply_text(
        DISCLAIMER_TEXT, reply_markup=get_simple_keyboard({"✅ Понимаю и согласен(на)": "agree"})
    )
    return AGREEMENT


async def agreement_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка согласия - переходим к возрастной группе"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

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
    answer_index = int(query.data.split('_')[1])
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
    answer_index = int(query.data.split('_')[1])
    answer_text = OCCUPATION_OPTIONS[answer_index]
    user_data_store[user_id]['occupation'] = answer_text

    await query.edit_message_text("Спасибо! Записал.")
    await query.message.reply_text(
        MORNING_TIME_QUESTION, reply_markup=get_keyboard(MORNING_TIME_OPTIONS, "morning_time")
    )
    return MORNING_TIME


async def morning_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора времени для утренних сообщений"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    parts = query.data.split('_')
    answer_index = int(parts[2])
    answer_text = MORNING_TIME_OPTIONS[answer_index]

    if answer_text == "Не важно (09:00)":
        user_data_store[user_id]['morning_time'] = "09:00"
    else:
        user_data_store[user_id]['morning_time'] = answer_text

    await query.edit_message_text("Спасибо! Записал.")
    await query.message.reply_text(
        EVENING_TIME_QUESTION, reply_markup=get_keyboard(EVENING_TIME_OPTIONS, "evening_time")
    )
    return EVENING_TIME


async def evening_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора времени для вечерних сообщений"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    parts = query.data.split('_')
    answer_index = int(parts[2])
    answer_text = EVENING_TIME_OPTIONS[answer_index]

    if answer_text == "Не важно (21:00)":
        user_data_store[user_id]['evening_time'] = "21:00"
    else:
        user_data_store[user_id]['evening_time'] = answer_text

    await query.edit_message_text("Спасибо! Записал.")

    # Сохраняем базовую информацию в БД
    await db.save_user(user_id, user_data_store[user_id])

    # Переходим к вопросу о физических ограничениях
    await query.message.reply_text(
        PHYSICAL_LIMITS_QUESTION, reply_markup=get_keyboard(PHYSICAL_LIMITS_OPTIONS, "physical")
    )
    return PHYSICAL_LIMITS


async def physical_limits_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ответа о физических ограничениях"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    parts = query.data.split('_')
    answer_index = int(parts[1])
    answer_text = PHYSICAL_LIMITS_OPTIONS[answer_index]

    if answer_text == "Другое (укажу в следующем шаге)":
        await query.edit_message_text(
            "Пожалуйста, опиши свои ограничения в одном сообщении.\n\n"
            "Например: «У меня астма, нельзя интенсивных нагрузок» или «Беременность, 2 триместр»."
        )
        context.user_data['awaiting_physical_details'] = True
        return PHYSICAL_LIMITS
    else:
        user_data_store[user_id]['physical_limits'] = answer_text
        await query.edit_message_text("Спасибо! Я учту это при подборе рекомендаций.")
        await query.message.reply_text(
            NOTIFICATION_FREQUENCY_QUESTION, reply_markup=get_keyboard(NOTIFICATION_FREQUENCY_OPTIONS, "freq")
        )
        return NOTIFICATION_FREQ


async def physical_limits_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка свободного ввода ограничений"""
    user_id = str(update.effective_user.id)
    user_data_store[user_id]['physical_limits'] = update.message.text

    await update.message.reply_text("Спасибо! Я учту это при подборе рекомендаций.")
    await update.message.reply_text(
        NOTIFICATION_FREQUENCY_QUESTION, reply_markup=get_keyboard(NOTIFICATION_FREQUENCY_OPTIONS, "freq")
    )
    context.user_data['awaiting_physical_details'] = False
    return NOTIFICATION_FREQ


async def notification_frequency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора частоты уведомлений"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    parts = query.data.split('_')
    answer_index = int(parts[1])
    answer_text = NOTIFICATION_FREQUENCY_OPTIONS[answer_index]

    user_data_store[user_id]['notification_frequency'] = answer_text

    await query.edit_message_text(f"Записал: {answer_text}")

    # Определяем следующий шаг в зависимости от выбора
    if answer_index == 1:  # "1 сообщение в день"
        await query.message.reply_text(DAILY_TIME_QUESTION, reply_markup=get_keyboard(DAILY_TIME_OPTIONS, "daily_time"))
        return DAILY_TIME
    elif answer_index == 2:  # "Раз в пару дней"
        await query.message.reply_text(
            BIWEEKLY_TIME_QUESTION, reply_markup=get_keyboard(BIWEEKLY_TIME_OPTIONS, "biweekly_time")
        )
        return BIWEEKLY_TIME
    else:  # "2-3 сообщения в день" (стандартный режим)
        # Сохраняем настройки в БД
        await db.save_user(user_id, user_data_store[user_id])
        # Переходим к вопросам про сон
        await query.message.reply_text("Отлично! Теперь несколько вопросов про твой сон и самочувствие.")
        await query.message.reply_text(Q1_TEXT, reply_markup=get_keyboard(Q1_OPTIONS, "q1"))
        return Q1


async def daily_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора времени для режима 1 сообщение в день"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    parts = query.data.split('_')
    answer_index = int(parts[2])
    answer_text = DAILY_TIME_OPTIONS[answer_index]

    user_data_store[user_id]['daily_time'] = answer_text

    # Определяем конкретное время для рассылки
    time_map = {"Утром (08:00-10:00)": "09:00", "Днём (13:00-15:00)": "14:00", "Вечером (19:00-21:00)": "20:00"}
    user_data_store[user_id]['morning_time'] = time_map.get(answer_text, "09:00")

    await query.edit_message_text(f"Записал: {answer_text}. Буду присылать одно сообщение в день.")

    # Сохраняем настройки в БД
    await db.save_user(user_id, user_data_store[user_id])

    # Переходим к вопросам про сон
    await query.message.reply_text("Теперь несколько вопросов про твой сон и самочувствие.")
    await query.message.reply_text(Q1_TEXT, reply_markup=get_keyboard(Q1_OPTIONS, "q1"))
    return Q1


async def biweekly_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора времени для режима раз в пару дней"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    parts = query.data.split('_')
    answer_index = int(parts[2])
    answer_text = BIWEEKLY_TIME_OPTIONS[answer_index]

    user_data_store[user_id]['biweekly_time'] = answer_text

    # Определяем конкретное время для рассылки
    time_map = {"Утром (08:00-10:00)": "09:00", "Днём (13:00-15:00)": "14:00", "Вечером (19:00-21:00)": "20:00"}
    user_data_store[user_id]['morning_time'] = time_map.get(answer_text, "09:00")
    user_data_store[user_id]['notification_skip_days'] = 1  # флаг для пропуска дней

    await query.edit_message_text(f"Записал: {answer_text}. Буду присылать сообщения раз в 2 дня.")

    # Сохраняем настройки в БД
    await db.save_user(user_id, user_data_store[user_id])

    # Переходим к вопросам про сон
    await query.message.reply_text("Теперь несколько вопросов про твой сон и самочувствие.")
    await query.message.reply_text(Q1_TEXT, reply_markup=get_keyboard(Q1_OPTIONS, "q1"))
    return Q1


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена онбординга"""
    await update.message.reply_text("Онбординг отменён. Если захочешь начать заново, напиши /start.")
    return ConversationHandler.END
