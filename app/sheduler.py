import asyncio
from datetime import datetime
import logging
import sys

from telegram.ext import ContextTypes

from app.bot_app import bot_app
from app.config import user_data_store, user_stats_store
from app.menu import get_simple_keyboard

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout
)
logger = logging.getLogger(__name__)


# --- Функции для планировщика ---
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


# --- ПЛАНИРОВЩИК ЗАДАЧ ---
async def run_scheduler():
    """Планировщик для периодических рассылок"""
    logger.info("🕐 Планировщик запущен")

    while True:
        try:
            now = datetime.now()
            current_time = now.time()

            # Утренняя рассылка в 9:00
            if current_time.hour == 9 and current_time.minute == 0 and current_time.second < 10:
                logger.info("⏰ Запуск утренней рассылки по расписанию")

                class DummyContext:
                    def __init__(self, bot):
                        self.bot = bot

                dummy_context = DummyContext(bot_app.bot)
                await send_morning_message(dummy_context)
                await asyncio.sleep(60)  # Пропускаем минуту

            # Дневная рассылка в 15:00
            elif current_time.hour == 15 and current_time.minute == 0 and current_time.second < 10:
                logger.info("⏰ Запуск дневной рассылки по расписанию")

                class DummyContext:
                    def __init__(self, bot):
                        self.bot = bot

                dummy_context = DummyContext(bot_app.bot)
                await send_day_stress_message(dummy_context)
                await asyncio.sleep(60)

            # Вечерняя рассылка в 21:00
            elif current_time.hour == 21 and current_time.minute == 0 and current_time.second < 10:
                logger.info("⏰ Запуск вечерней рассылки по расписанию")

                class DummyContext:
                    def __init__(self, bot):
                        self.bot = bot

                dummy_context = DummyContext(bot_app.bot)
                await send_evening_message(dummy_context)
                await asyncio.sleep(60)

            # Проверка каждые 30 секунд
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
            await asyncio.sleep(60)  # При ошибке ждем минуту
