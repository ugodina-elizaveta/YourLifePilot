import asyncio
import logging
import uuid
from datetime import datetime

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.ai import ai
from app.anketa import cancel, q1_handler, q2_handler, q3_handler, q4_handler, q5_handler
from app.bot_app import bot_app
from app.config import (
    AGE,
    AGREEMENT,
    BIWEEKLY_TIME,
    DAILY_TIME,
    EVENING_TIME,
    MORNING_TIME,
    NOTIFICATION_FREQ,
    OCCUPATION,
    PHYSICAL_LIMITS,
    Q1,
    Q2,
    Q3,
    Q4,
    Q5,
    user_data_store,
    user_stats_store,
)
from app.database import db
from app.menu import get_simple_keyboard
from app.sheduler import send_day_stress_message, send_evening_message, send_morning_message
from app.start import (
    age_handler,
    agreement_handler,
    biweekly_time_handler,
    daily_time_handler,
    evening_time_handler,
    morning_time_handler,
    notification_frequency_handler,
    occupation_handler,
    physical_limits_details_handler,
    physical_limits_handler,
    start,
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def morning_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов на утреннее сообщение с AI-советами"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    text = None

    if data == "morning_normal":
        text = "Рад слышать! Хорошего дня."
        user_stats_store[user_id]['morning_skip_streak'] = 0
        await db.save_action(user_id, "morning", "normal")

    elif data == "morning_broken":
        # Получаем данные пользователя для персонализации
        user_data = user_data_store.get(user_id, {})

        # AI генерирует утренний совет
        advice = ai.generate_advice(
            user_context="Пользователь проснулся разбитым",
            situation='morning',
            user_data=user_data,  # ✅ Передаём возраст и занятия
        )

        if 'просыпаюсь разбитым' in user_data.get('scenario', []):
            await query.edit_message_text(
                f"Жаль. {advice}\n\n" "Попробуй сейчас просто встать, подойти к окну и сделать 5 глубоких вдохов.",
                reply_markup=get_simple_keyboard(
                    {
                        "✅ Сделал(а)": "morning_micro_done",
                        "⏰ Отложить": "morning_micro_later",
                    }
                ),
            )
            await db.save_action(user_id, "morning", "broken_with_scenario")
            return
        else:
            text = f"Жаль. {advice}"
            await db.save_action(user_id, "morning", "broken_without_scenario")

    elif data == "morning_unknown":
        text = "Хорошо, понаблюдай за собой. Если будет нужна поддержка, я рядом."
        await db.save_action(user_id, "morning", "unknown")

    if text is not None:
        await query.edit_message_text(text)
    else:
        logger.error(f"Необработанный callback data: {data} для пользователя {user_id}")
        await query.edit_message_text("Что-то пошло не так. Попробуй еще раз.")


async def morning_micro_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка микро-задачи утром."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    today = datetime.now().date()

    if data == "morning_micro_done":
        await query.edit_message_text("Отлично! Маленький шаг сделан. Так держать!")
        user_stats_store[user_id]['morning_streak'] = user_stats_store[user_id].get('morning_streak', 0) + 1
        user_stats_store[user_id]['morning_skip_streak'] = 0
        user_stats_store[user_id]['last_action_date']['morning'] = today
        await db.save_action(user_id, "micro", "done")
        await db.save_user_stats(user_id, user_stats_store[user_id])

    elif data == "morning_micro_later":
        await query.edit_message_text("Хорошо, можешь вернуться к этому позже. Я напомню завтра.")
        user_stats_store[user_id]['morning_skip_streak'] = user_stats_store[user_id].get('morning_skip_streak', 0) + 1
        user_stats_store[user_id]['morning_streak'] = 0
        user_stats_store[user_id]['last_action_date']['morning'] = today
        await db.save_action(user_id, "micro", "skipped")
        await db.save_user_stats(user_id, user_stats_store[user_id])


async def evening_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов на вечернее сообщение."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    today = datetime.now().date()

    text = None

    if data == "evening_do":
        text = "Отлично! Маленький шаг запланирован."
        user_stats_store[user_id]['evening_streak'] = user_stats_store[user_id].get('evening_streak', 0) + 1
        user_stats_store[user_id]['evening_skip_streak'] = 0
        user_stats_store[user_id]['last_action_date']['evening'] = today
        await db.save_action(user_id, "evening", "do")
        await db.save_user_stats(user_id, user_stats_store[user_id])

    elif data == "evening_not_now":
        text = "Хорошо, в другой раз. Главное — быть в контакте с собой."
        user_stats_store[user_id]['evening_skip_streak'] = user_stats_store[user_id].get('evening_skip_streak', 0) + 1
        user_stats_store[user_id]['evening_streak'] = 0
        user_stats_store[user_id]['last_action_date']['evening'] = today
        await db.save_action(user_id, "evening", "not_now")
        await db.save_user_stats(user_id, user_stats_store[user_id])

    if text is not None:
        # Сначала отвечаем на callback
        await query.edit_message_text(text)

        # Затем отправляем вопрос о самочувствии
        await query.message.reply_text(
            "И напоследок: как ты сейчас себя чувствуешь?",
            reply_markup=get_simple_keyboard(
                {
                    "🙂 Спокойно": "feeling_calm",
                    "😕 Напряжён(а)": "feeling_stressed",
                    "😔 Грустно": "feeling_sad",
                    "😩 Очень плохо": "feeling_bad",
                }
            ),
        )
        logger.info(f"✅ [ВЕЧЕР] Вопрос о настроении отправлен {user_id} после ответа")

    else:
        logger.error(f"Необработанный callback data: {data} для пользователя {user_id}")
        await query.edit_message_text("Что-то пошло не так. Попробуй еще раз.")


async def feeling_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем ответ о самочувствии и даем персонализированный AI-совет"""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    feeling_map = {
        "feeling_calm": "Спокойно",
        "feeling_stressed": "Напряжён(а)",
        "feeling_sad": "Грустно",
        "feeling_bad": "Очень плохо",
    }

    feeling = feeling_map.get(data, "Неизвестно")

    if user_id not in user_data_store:
        user_data_store[user_id] = {'mood_history': []}

    if 'mood_history' not in user_data_store[user_id]:
        user_data_store[user_id]['mood_history'] = []

    user_data_store[user_id]['mood_history'].append({'date': datetime.now().isoformat(), 'feeling': feeling})

    # Сохраняем в БД
    await db.save_mood(user_id, feeling)
    await db.save_action(user_id, "feeling", data)

    # Анализируем через AI
    sentiment = ai.analyze_sentiment(feeling)
    emotion = ai.analyze_emotion(feeling)
    logger.info(f"🤖 AI Анализ: {sentiment}, {emotion}")

    # Получаем историю настроений
    mood_history = user_data_store[user_id].get('mood_history', [])

    # Получаем данные пользователя для персонализации
    user_data = user_data_store.get(user_id, {})

    # Если это уже 3-й ответ, анализируем тренд
    if len(mood_history) >= 3:
        trend = ai.analyze_mood_trend(mood_history)

        if trend and isinstance(trend, dict) and 'message' in trend:
            last_trend_date = context.user_data.get('last_trend_date')
            today = datetime.now().date()

            if last_trend_date != today:
                await asyncio.sleep(1)
                await query.message.reply_text(
                    f"📊 {trend['message']}\n" f"Средний уровень: {trend.get('average', '?')}/4"
                )
                context.user_data['last_trend_date'] = today
        else:
            logger.warning(f"⚠️ Некорректные данные тренда: {trend}")

    # Если настроение плохое, даем поддерживающий совет с персонализацией
    if feeling in ['Напряжён(а)', 'Грустно', 'Очень плохо']:
        advice = ai.generate_advice(
            user_context=f"У пользователя настроение: {feeling}",
            situation='stress' if feeling == 'Напряжён(а)' else 'sad',
            user_data=user_data,  # ✅ Передаём возраст и занятия
        )

        await asyncio.sleep(1.5)
        await query.message.reply_text(f"💡 {advice}")

        # ✅ НОВОЕ: предлагаем рассказать о проблеме
        await asyncio.sleep(2)
        await query.message.reply_text(
            "🗣️ *Если чувствуешь напряжение, усталость или стресс, можешь рассказать мне об этом.*\n\n"
            "Например: *«Я устал(а) / переживаю / напряжён(а), сейчас я чувствую…»*\n\n"
            "Просто напиши мне сообщение в режиме /ai — я выслушаю и постараюсь помочь. 🤗",
            parse_mode='Markdown',
        )

    await query.edit_message_text(f"Спасибо, что поделился(лась). Записал: {feeling}")


async def day_stress_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка дневного сообщения про стресс."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    today = datetime.now().date()

    text = None

    if data == "day_stress_done":
        text = "Отлично! Микро-пауза помогает перезагрузиться."
        user_stats_store[user_id]['day_stress_streak'] = user_stats_store[user_id].get('day_stress_streak', 0) + 1
        user_stats_store[user_id]['day_stress_skip_streak'] = 0
        user_stats_store[user_id]['last_action_date']['day_stress'] = today
        await db.save_action(user_id, "stress", "done")
        await db.save_user_stats(user_id, user_stats_store[user_id])

    elif data == "day_stress_skip":
        text = "Понимаю. Если будет возможность, просто подыши глубоко пару раз."
        user_stats_store[user_id]['day_stress_skip_streak'] = (
            user_stats_store[user_id].get('day_stress_skip_streak', 0) + 1
        )
        user_stats_store[user_id]['day_stress_streak'] = 0
        user_stats_store[user_id]['last_action_date']['day_stress'] = today
        await db.save_action(user_id, "stress", "skipped")
        await db.save_user_stats(user_id, user_stats_store[user_id])

    if text is not None:
        await query.edit_message_text(text)
    else:
        logger.error(f"Необработанный callback data: {data} для пользователя {user_id}")
        await query.edit_message_text("Что-то пошло не так. Попробуй еще раз.")


async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обычный чат с AI - определяет тему сообщения и даёт релевантный ответ"""
    user_id = str(update.effective_user.id)
    user_message = update.message.text

    # Проверяем, активирован ли режим чата
    if not context.user_data.get('ai_chat_mode'):
        return

    # Получаем или создаём ID сессии
    session_id = context.user_data.get('ai_chat_session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        context.user_data['ai_chat_session_id'] = session_id

    # Сохраняем сообщение пользователя
    await db.save_ai_chat_message(
        user_id=user_id, session_id=session_id, message=user_message, role="user", metadata={"type": "user_query"}
    )

    # Показываем, что бот печатает
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action="typing")

    # Получаем данные пользователя для персонализации
    user_data = user_data_store.get(user_id, {})
    mood_history = user_data.get('mood_history', [])

    # Определяем ситуацию по тексту сообщения
    situation = detect_situation_from_text(user_message)

    # Формируем контекст с учётом истории настроений
    mood_context = ""
    if mood_history:
        last_mood = mood_history[-1]['feeling']
        mood_context = f" (последнее настроение: {last_mood})"

    logger.info(f"🤖 AI Чат: определена ситуация '{situation}' для сообщения")

    # Генерируем ответ с персонализацией
    response = ai.generate_advice(
        user_context=user_message + mood_context,
        situation=situation,
        user_data=user_data,
    )

    # Сохраняем ответ бота
    await db.save_ai_chat_message(
        user_id=user_id,
        session_id=session_id,
        message=response,
        role="assistant",
        metadata={"situation": situation, "sentiment": ai.analyze_sentiment(user_message)},
    )

    await update.message.reply_text(response)


def detect_situation_from_text(text: str) -> str:
    """Определяет ситуацию по тексту сообщения"""
    text_lower = text.lower()

    stress_keywords = ['стресс', 'напряж', 'пережив', 'тревог', 'волну', 'нерв', 'паник']
    sleep_keywords = ['сон', 'спать', 'уснуть', 'просып', 'бессонниц', 'кровать', 'ночь', 'выспаться']
    sad_keywords = ['груст', 'печал', 'тоск', 'плохое настроение', 'депресс', 'унын', 'тоска']
    morning_keywords = ['утро', 'проснул', 'начать день', 'бодр', 'зарядк']
    evening_keywords = ['вечер', 'расслабит', 'перед сном', 'успокоят', 'отдых']

    if any(word in text_lower for word in stress_keywords):
        return 'stress'
    elif any(word in text_lower for word in sleep_keywords):
        return 'sleep'
    elif any(word in text_lower for word in sad_keywords):
        return 'sad'
    elif any(word in text_lower for word in morning_keywords):
        return 'morning'
    elif any(word in text_lower for word in evening_keywords):
        return 'evening'
    else:
        return 'general'


async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в режим AI-чата"""
    user_id = str(update.effective_user.id)
    # Генерируем новый ID сессии
    context.user_data['ai_chat_session_id'] = str(uuid.uuid4())
    context.user_data['ai_chat_mode'] = True

    # Сохраняем начало сессии
    await db.save_ai_chat_message(
        user_id=user_id,
        session_id=context.user_data['ai_chat_session_id'],
        message="[Начало сессии]",
        role="system",
        metadata={"event": "session_start"},
    )

    await update.message.reply_text(
        "🤖 **Режим общения с AI активирован!**\n\n"
        "Задавай любые вопросы, делись переживаниями или просто болтай.\n"
        "Я постараюсь поддержать и помочь.\n\n"
        "Напиши **/stop_ai** чтобы выйти из режима."
    )


async def stop_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из режима AI-чата"""
    user_id = str(update.effective_user.id)
    session_id = context.user_data.get('ai_chat_session_id')

    if session_id:
        await db.save_ai_chat_message(
            user_id=user_id,
            session_id=session_id,
            message="[Конец сессии]",
            role="system",
            metadata={"event": "session_end"},
        )

    context.user_data['ai_chat_mode'] = False
    context.user_data['ai_chat_session_id'] = None

    await update.message.reply_text("👋 Режим AI чата завершен.\n" "Возвращайся ещё, когда захочешь поговорить!")


# --- НАСТРОЙКА ОБРАБОТЧИКОВ ---
def setup_handlers():
    """Настраивает все обработчики для бота"""

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AGREEMENT: [CallbackQueryHandler(agreement_handler, pattern="^agree$")],
            AGE: [CallbackQueryHandler(age_handler, pattern="^age_")],
            OCCUPATION: [CallbackQueryHandler(occupation_handler, pattern="^occupation_")],
            MORNING_TIME: [CallbackQueryHandler(morning_time_handler, pattern="^morning_time_")],
            EVENING_TIME: [CallbackQueryHandler(evening_time_handler, pattern="^evening_time_")],
            PHYSICAL_LIMITS: [
                CallbackQueryHandler(physical_limits_handler, pattern="^physical_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, physical_limits_details_handler),
            ],
            NOTIFICATION_FREQ: [CallbackQueryHandler(notification_frequency_handler, pattern="^freq_")],
            DAILY_TIME: [CallbackQueryHandler(daily_time_handler, pattern="^daily_time_")],
            BIWEEKLY_TIME: [CallbackQueryHandler(biweekly_time_handler, pattern="^biweekly_time_")],
            Q1: [CallbackQueryHandler(q1_handler, pattern="^q1_")],
            Q2: [CallbackQueryHandler(q2_handler, pattern="^q2_")],
            Q3: [CallbackQueryHandler(q3_handler, pattern="^q3_")],
            Q4: [CallbackQueryHandler(q4_handler, pattern="^q4_")],
            Q5: [CallbackQueryHandler(q5_handler, pattern="^q5_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    bot_app.add_handler(conv_handler)

    # Обработчики колбэков
    bot_app.add_handler(CallbackQueryHandler(morning_action_handler, pattern="^morning_"))
    bot_app.add_handler(CallbackQueryHandler(morning_micro_handler, pattern="^morning_micro_"))
    bot_app.add_handler(CallbackQueryHandler(evening_action_handler, pattern="^evening_"))
    bot_app.add_handler(CallbackQueryHandler(day_stress_handler, pattern="^day_stress_"))
    bot_app.add_handler(CallbackQueryHandler(feeling_handler, pattern="^feeling_"))

    # Добавляем команду для тестовой отправки
    async def trigger_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await send_morning_message(context)
        await update.message.reply_text("Утренние сообщения отправлены!")

    async def trigger_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await send_evening_message(context)
        await update.message.reply_text("Вечерние сообщения отправлены!")

    async def trigger_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await send_day_stress_message(context)
        await update.message.reply_text("Дневные сообщения отправлены!")

    bot_app.add_handler(CommandHandler("trigger_morning", trigger_morning))
    bot_app.add_handler(CommandHandler("trigger_evening", trigger_evening))
    bot_app.add_handler(CommandHandler("trigger_day", trigger_day))

    # AI-команды
    bot_app.add_handler(CommandHandler("ai", start_ai_chat))
    bot_app.add_handler(CommandHandler("stop_ai", stop_ai_chat))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_handler))

    logger.info("✅ Handlers configured (including personalization)")
