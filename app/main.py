import logging

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler

from app.anketa import cancel, q1_handler, q2_handler, q3_handler, q4_handler, q5_handler
from app.config import AGREEMENT, BOT_TOKEN, Q1, Q2, Q3, Q4, Q5, WEBHOOK_URL, user_data_store, user_stats_store
from app.handler import (
    day_stress_handler,
    evening_action_handler,
    feeling_handler,
    morning_action_handler,
    morning_micro_handler,
)
from app.menu import get_simple_keyboard
from app.start import agreement_handler, start

# Создаем FastAPI приложение
app = FastAPI()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем экземпляр бота
bot_app = Application.builder().token(BOT_TOKEN).build()


# --- Функции для планировщика ---
# На Render.com эти функции НЕ БУДУТ вызываться автоматически!
# Мы их оставляем, но они будут срабатывать только когда бот получит команду /trigger
async def send_morning_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет утреннее сообщение всем пользователям, прошедшим онбординг."""
    for user_id, data in user_data_store.items():
        if data.get('onboarding_complete', False):
            try:
                base_text = "Доброе утро! Как ты проснулся(лась) сегодня?\nДавай заодно сделаем маленький шаг для более ясного утра."
                stats = user_stats_store.get(user_id, {})
                morning_streak = stats.get('morning_streak', 0)
                morning_skip_streak = stats.get('morning_skip_streak', 0)

                if morning_streak >= 3:
                    praise_text = (
                        f"\n\nВижу, ты уже {morning_streak} утра подряд делаешь этот маленький шаг — это круто 👏\n"
                        "Если чувствуешь силы, давай сегодня чуть усилим ритуал:\n"
                        "попробуй не только вдохи, но и 3 минуты почитать что‑то спокойное или сделать растяжку."
                    )
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=base_text + praise_text,
                        reply_markup=get_simple_keyboard(
                            {
                                "😊 Нормально": "morning_normal",
                                "🥱 Разбит(а)": "morning_broken",
                                "😐 Пока непонятно": "morning_unknown",
                            }
                        ),
                    )
                elif morning_skip_streak >= 3:
                    soft_text = (
                        "\n\nПохоже, сейчас у тебя слишком плотные утра, и это нормально.\n"
                        "Давай сделаем совсем простой вариант:\n"
                        "сегодня достаточно просто встать с кровати и улыбнуться своему отражению."
                    )
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=base_text + soft_text,
                        reply_markup=get_simple_keyboard(
                            {
                                "😊 Нормально": "morning_normal",
                                "🥱 Разбит(а)": "morning_broken",
                                "😐 Пока непонятно": "morning_unknown",
                            }
                        ),
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=base_text,
                        reply_markup=get_simple_keyboard(
                            {
                                "😊 Нормально": "morning_normal",
                                "🥱 Разбит(а)": "morning_broken",
                                "😐 Пока непонятно": "morning_unknown",
                            }
                        ),
                    )
            except Exception as e:
                logger.error(f"Не удалось отправить утреннее сообщение пользователю {user_id}: {e}")


async def send_evening_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет вечернее сообщение."""
    for user_id, data in user_data_store.items():
        if data.get('onboarding_complete', False):
            try:
                base_text = (
                    "Как проходит вечер? Давай поможем себе лечь пораньше.\n"
                    "Предлагаю маленький шаг:\n"
                    "за 15–20 минут до сна убрать яркий экран и сделать 1–2 минуты спокойного дыхания."
                )
                stats = user_stats_store.get(user_id, {})
                evening_streak = stats.get('evening_streak', 0)
                evening_skip_streak = stats.get('evening_skip_streak', 0)

                if evening_streak >= 3:
                    text = (
                        f"Вижу, ты уже {evening_streak} вечеров подряд делаешь этот маленький шаг — это круто 👏\n"
                        "Если чувствуешь силы, давай чуть усилим ритуал:\n"
                        "сегодня попробуй не только убрать экран, но и 3 минуты почитать что‑то спокойное или сделать растяжку."
                    )
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=get_simple_keyboard(
                            {
                                "Ок, попробую": "evening_do",
                                "Пока рано, оставим как было": "evening_not_now",
                            }
                        ),
                    )
                elif evening_skip_streak >= 3:
                    text = (
                        "Похоже, сейчас у тебя слишком плотные вечера, и это нормально.\n"
                        "Давай сделаем совсем простой вариант:\n"
                        "сегодня достаточно просто поставить себе будильник на желаемое время отхода ко сну"
                        " и хотя бы на 30 минут приблизиться к нему."
                    )
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=get_simple_keyboard(
                            {
                                "Ок, так проще": "evening_do",
                                "Не хочу сейчас этим заниматься": "evening_not_now",
                            }
                        ),
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=base_text,
                        reply_markup=get_simple_keyboard(
                            {
                                "Сделаю сегодня": "evening_do",
                                "Не сейчас": "evening_not_now",
                            }
                        ),
                    )
            except Exception as e:
                logger.error(f"Не удалось отправить вечернее сообщение пользователю {user_id}: {e}")


async def send_day_stress_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет дневное сообщение только тем, у кого сценарий 'днём высокий стресс'."""
    for user_id, data in user_data_store.items():
        if data.get('onboarding_complete', False) and 'днём высокий стресс' in data.get('scenario', []):
            try:
                text = (
                    "Как день? Если чувствуешь, что голова закипает, давай сделаем 30‑секундную паузу:\n"
                    "посмотри в окно или на дальнюю точку, сделай 5 медленных вдохов и потяни плечи."
                )
                stats = user_stats_store.get(user_id, {})
                day_streak = stats.get('day_stress_streak', 0)
                day_skip_streak = stats.get('day_stress_skip_streak', 0)

                if day_streak >= 3:
                    text = "Супер! Ты уже несколько дней делаешь паузу. Если есть силы, добавь к паузе стакан воды."
                elif day_skip_streak >= 3:
                    text = "Вижу, сейчас сложно. Попробуй хотя бы просто выключить звук на телефоне на 1 минуту."

                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=get_simple_keyboard(
                        {
                            "✅ Сделал(а)": "day_stress_done",
                            "Не до этого": "day_stress_skip",
                        }
                    ),
                )
            except Exception as e:
                logger.error(f"Не удалось отправить дневное сообщение пользователю {user_id}: {e}")


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


# Вызываем настройку обработчиков
setup_handlers()


# --- НАСТРОЙКА FASTAPI ДЛЯ WEBHOOK ---
@app.on_event("startup")
async def on_startup():
    """Устанавливаем вебхук при запуске"""
    webhook_info = await bot_app.bot.get_webhook_info()
    logger.info(f"Current webhook: {webhook_info.url}")

    await bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook", allowed_updates=Update.ALL_TYPES)
    logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")


@app.post("/webhook")
async def webhook(request: Request):
    """Принимаем обновления от Telegram"""
    update_data = await request.json()
    update = Update.de_json(update_data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}


@app.on_event("shutdown")
async def on_shutdown():
    """Удаляем вебхук при остановке"""
    await bot_app.bot.delete_webhook()
    logger.info("Webhook deleted")


@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {"status": "ok"}


@app.get("/trigger-morning")
async def trigger_morning_webhook():
    """Вызывается внешним cron-сервисом"""
    async with bot_app:
        await send_morning_message(None)
    return {"ok": True}


@app.get("/trigger-evening")
async def trigger_evening_webhook():
    async with bot_app:
        await send_evening_message(None)
    return {"ok": True}


@app.get("/trigger-day")
async def trigger_day_webhook():
    async with bot_app:
        await send_day_stress_message(None)
    return {"ok": True}


# Для локального тестирования (не будет вызываться на Render)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
