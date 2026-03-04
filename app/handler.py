import asyncio
import logging
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
from app.config import AGREEMENT, Q1, Q2, Q3, Q4, Q5, user_data_store, user_stats_store
from app.database import db
from app.menu import get_simple_keyboard
from app.sheduler import send_day_stress_message, send_evening_message, send_morning_message
from app.start import agreement_handler, start

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
        # AI генерирует утренний совет
        advice = ai.generate_advice(user_context="Пользователь проснулся разбитым", situation='morning')

        if 'просыпаюсь разбитым' in user_data_store.get(user_id, {}).get('scenario', []):
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
    """Сохраняем ответ о самочувствии и даем AI-совет"""
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

    mood_entry = {'date': datetime.now().isoformat(), 'feeling': feeling}
    user_data_store[user_id]['mood_history'].append(mood_entry)

    # Сохраняем в БД
    await db.save_mood(user_id, feeling)
    await db.save_action(user_id, "feeling", data)

    # Анализируем через AI
    sentiment = ai.analyze_sentiment(feeling)
    emotion = ai.analyze_emotion(feeling)
    logger.info(f"🤖 AI Анализ: {sentiment}, {emotion}")

    # Получаем историю настроений
    mood_history = user_data_store[user_id].get('mood_history', [])

    # Если это уже 3-й ответ, анализируем тренд
    if len(mood_history) >= 3:
        trend = ai.analyze_mood_trend(mood_history)

        # Отправляем анализ тренда (не чаще раза в день)
        last_trend_date = context.user_data.get('last_trend_date')
        today = datetime.now().date()

        if last_trend_date != today:
            await asyncio.sleep(1)  # Небольшая пауза перед доп. сообщением
            await query.message.reply_text(f"📊 {trend['message']}\n" f"Средний уровень: {trend.get('average', '?')}/4")
            context.user_data['last_trend_date'] = today

    # Если настроение плохое, даем поддерживающий совет
    if feeling in ['Напряжён(а)', 'Грустно', 'Очень плохо']:
        advice = ai.generate_advice(
            user_context=f"У пользователя настроение: {feeling}",
            situation='stress' if feeling == 'Напряжён(а)' else 'sad',
        )

        # Отправляем совет с небольшой задержкой
        await asyncio.sleep(1.5)
        await query.message.reply_text(f"💡 {advice}")

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
    """Обычный чат с AI"""
    user_message = update.message.text

    # Проверяем, активирован ли режим чата
    if not context.user_data.get('ai_chat_mode'):
        return

    # Показываем, что бот печатает
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action="typing")

    # Получаем историю настроений пользователя
    user_id = str(update.effective_user.id)
    mood_history = user_data_store.get(user_id, {}).get('mood_history', [])

    # Формируем контекст
    mood_summary = ""
    if mood_history:
        last_mood = mood_history[-1]['feeling']
        mood_summary = f"Пользователь недавно чувствовал {last_mood}. "

    # Анализируем сообщение пользователя через AI
    sentiment = ai.analyze_sentiment(user_message)
    emotion = ai.analyze_emotion(user_message)
    logger.info(f"🤖 AI Чат: сообщение '{user_message[:30]}...' - {sentiment}, {emotion}")

    # Генерируем ответ
    response = ai.generate_advice(user_context=mood_summary, situation='general')

    await update.message.reply_text(response)


async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в режим AI-чата"""
    context.user_data['ai_chat_mode'] = True
    await update.message.reply_text(
        "🤖 **Режим общения с AI активирован!**\n\n"
        "Задавай любые вопросы, делись переживаниями или просто болтай.\n"
        "Я постараюсь поддержать и помочь.\n\n"
        "Напиши **/stop_ai** чтобы выйти из режима."
    )


async def stop_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из режима AI-чата"""
    context.user_data['ai_chat_mode'] = False
    await update.message.reply_text("👋 Режим AI чата завершен.\n" "Возвращайся ещё, когда захочешь поговорить!")


# --- НАСТРОЙКА ОБРАБОТЧИКОВ ---
def setup_handlers():
    """Настраивает все обработчики для бота"""
    # Обработчик диалога онбординга
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AGREEMENT: [CallbackQueryHandler(agreement_handler, pattern="^agree$")],
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

    # Добавляем AI-команды
    bot_app.add_handler(CommandHandler("ai", start_ai_chat))
    bot_app.add_handler(CommandHandler("stop_ai", stop_ai_chat))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_handler))

    logger.info("✅ Handlers configured (including AI)")
# Добавьте после других обработчиков, перед logger.info


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список доступных команд"""
    help_text = """
🤖 **YourLifePilot - Доступные команды**

**Основные:**
/start - Начать работу с ботом
/cancel - Отменить текущий диалог

**AI-помощник:**
/ai - Войти в режим общения с AI
/stop_ai - Выйти из режима AI

**Статистика:**
/stats - Моя статистика
/mood_history - История настроения

**Тестовые команды:**
/trigger_morning - Тест утренней рассылки
/trigger_evening - Тест вечерней рассылки
/trigger_day - Тест дневной рассылки

/help - Показать это сообщение
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

bot_app.add_handler(CommandHandler("help", help_command))
