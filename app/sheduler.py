import asyncio
import logging
import sys
from datetime import datetime

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
    current_time = datetime.now().strftime('%H:%M:%S')
    logger.info(f"📨 [УТРО] Начало рассылки в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [УТРО] Нет пользователей в базе данных")
        return

    sent_count = 0
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
                sent_count += 1
                logger.info(f"✅ [УТРО] Сообщение отправлено пользователю {user_id}")

            except Exception as e:
                logger.error(f"❌ [УТРО] Ошибка для пользователя {user_id}: {e}")

    logger.info(f"📊 [УТРО] Рассылка завершена. Отправлено: {sent_count} из {len(user_data_store)}")


async def send_evening_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет вечернее сообщение."""
    current_time = datetime.now().strftime('%H:%M:%S')
    logger.info(f"📨 [ВЕЧЕР] Начало рассылки в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [ВЕЧЕР] Нет пользователей в базе данных")
        return

    sent_count = 0
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

                # Отправляем вопрос о самочувствии
                await context.bot.send_message(
                    chat_id=user_id,
                    text="И напоследок: как ты сейчас себя чувствуешь?",
                    reply_markup=get_simple_keyboard(
                        {
                            "🙂 Спокойно": "feeling_calm",
                            "😕 Напряжён(а)": "feeling_stressed",
                            "😔 Грустно": "feeling_sad",
                            "😩 Очень плохо": "feeling_bad",
                        }
                    ),
                )

                sent_count += 1
                logger.info(f"✅ [ВЕЧЕР] Сообщение отправлено пользователю {user_id}")

            except Exception as e:
                logger.error(f"❌ [ВЕЧЕР] Ошибка для пользователя {user_id}: {e}")

    logger.info(f"📊 [ВЕЧЕР] Рассылка завершена. Отправлено: {sent_count} из {len(user_data_store)}")


async def send_day_stress_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет дневное сообщение только тем, у кого сценарий 'днём высокий стресс'."""
    current_time = datetime.now().strftime('%H:%M:%S')
    logger.info(f"📨 [ДЕНЬ] Начало рассылки в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [ДЕНЬ] Нет пользователей в базе данных")
        return

    sent_count = 0
    stress_users = 0

    for user_id, data in user_data_store.items():
        if data.get('onboarding_complete', False):
            has_stress = 'днём высокий стресс' in data.get('scenario', [])
            if has_stress:
                stress_users += 1
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
                    sent_count += 1
                    logger.info(f"✅ [ДЕНЬ] Сообщение отправлено пользователю {user_id} (стресс-сценарий)")

                except Exception as e:
                    logger.error(f"❌ [ДЕНЬ] Ошибка для пользователя {user_id}: {e}")

    logger.info(f"📊 [ДЕНЬ] Рассылка завершена. Пользователей со стрессом: {stress_users}, отправлено: {sent_count}")


# --- ПЛАНИРОВЩИК ЗАДАЧ ---
async def run_scheduler():
    """Планировщик для периодических рассылок"""
    logger.info("=" * 60)
    logger.info("🕐 ПЛАНИРОВЩИК ЗАПУЩЕН")
    logger.info(f"🕐 Текущее время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🕐 Часовой пояс сервера: {datetime.now().astimezone().tzinfo}")
    logger.info("=" * 60)

    # Счетчик для периодических логов
    check_counter = 0

    while True:
        try:
            now = datetime.now()
            current_time = now.time()
            check_counter += 1

            # Утренняя рассылка в 9:00
            if current_time.hour == 9 and current_time.minute == 0:
                logger.info("🎯" + "=" * 50)
                logger.info("🎯 СРАБОТАЛО: УТРЕННЯЯ РАССЫЛКА в 9:00")
                logger.info(
                    f"🎯 Точное время срабатывания: {current_time.hour:02d}:{current_time.minute:02d}:{current_time.second:02d}"
                )
                logger.info("🎯" + "=" * 50)

                class DummyContext:
                    def __init__(self, bot):
                        self.bot = bot

                dummy_context = DummyContext(bot_app.bot)
                await send_morning_message(dummy_context)

                logger.info("✅ Утренняя рассылка полностью завершена")
                await asyncio.sleep(60)

            # Дневная рассылка в 15:00
            elif current_time.hour == 15 and current_time.minute == 0:
                logger.info("🎯" + "=" * 50)
                logger.info("🎯 СРАБОТАЛО: ДНЕВНАЯ РАССЫЛКА в 15:00")
                logger.info(
                    f"🎯 Точное время срабатывания: {current_time.hour:02d}:{current_time.minute:02d}:{current_time.second:02d}"
                )
                logger.info("🎯" + "=" * 50)

                class DummyContext:
                    def __init__(self, bot):
                        self.bot = bot

                dummy_context = DummyContext(bot_app.bot)
                await send_day_stress_message(dummy_context)

                logger.info("✅ Дневная рассылка полностью завершена")
                await asyncio.sleep(60)

            # Вечерняя рассылка в 21:00
            elif current_time.hour == 21 and current_time.minute == 0:
                logger.info("🎯" + "=" * 50)
                logger.info("🎯 СРАБОТАЛО: ВЕЧЕРНЯЯ РАССЫЛКА в 21:00")
                logger.info(
                    f"🎯 Точное время срабатывания: {current_time.hour:02d}:{current_time.minute:02d}:{current_time.second:02d}"
                )
                logger.info("🎯" + "=" * 50)

                class DummyContext:
                    def __init__(self, bot):
                        self.bot = bot

                dummy_context = DummyContext(bot_app.bot)
                await send_evening_message(dummy_context)

                logger.info("✅ Вечерняя рассылка полностью завершена")
                await asyncio.sleep(60)

            # Лог каждый час о том, что планировщик работает
            if check_counter % 120 == 0:  # 120 * 30 сек = 3600 сек = 1 час
                logger.info("=" * 50)
                logger.info("⏰ ЧАСОВОЙ ОТЧЕТ ПЛАНИРОВЩИКА")
                logger.info(f"В базе данных {len(user_data_store)} пользователей")

                # Подсчет пользователей с онбордингом
                onboarded = sum(1 for u in user_data_store.values() if u.get('onboarding_complete', False))
                logger.info(f"Из них прошли онбординг: {onboarded}")

                logger.info("=" * 50)
            # Проверка каждые 60 секунд
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в планировщике: {e}", exc_info=True)
            await asyncio.sleep(30)
