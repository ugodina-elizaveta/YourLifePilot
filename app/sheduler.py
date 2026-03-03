import asyncio
import logging
import time
from datetime import datetime

from telegram.ext import ContextTypes

from app.config import user_data_store, user_stats_store
from app.database import db
from app.menu import get_simple_keyboard

logger = logging.getLogger(__name__)


async def send_message_with_retry(
    bot, chat_id: str, text: str, keyboard: dict, max_retries: int = 2, timeout: float = 10.0
) -> bool:
    """Отправляет сообщение с повторными попытками и таймаутом"""
    for attempt in range(max_retries):
        try:
            await asyncio.wait_for(
                bot.send_message(chat_id=chat_id, text=text, reply_markup=get_simple_keyboard(keyboard)),
                timeout=timeout,
            )
            return True
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                logger.warning(f"⏰ Таймаут (попытка {attempt + 1}), пробуем снова...")
                await asyncio.sleep(1)
            else:
                logger.error(f"❌ Таймаут после {max_retries} попыток")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")
            break
    return False


async def send_morning_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет утреннее сообщение с контролем времени"""
    start_time = time.time()
    current_time = datetime.now().strftime('%H:%M:%S')
    logger.info(f"📨 [УТРО] Начало рассылки в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [УТРО] Нет пользователей")
        return

    sent_count = 0
    error_count = 0
    total_users = len(user_data_store)

    for user_id, data in user_data_store.items():
        if not data.get('onboarding_complete', False):
            continue

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
                text = base_text + praise_text
            elif morning_skip_streak >= 3:
                soft_text = (
                    "\n\nПохоже, сейчас у тебя слишком плотные утра, и это нормально.\n"
                    "Давай сделаем совсем простой вариант:\n"
                    "сегодня достаточно просто встать с кровати и улыбнуться своему отражению."
                )
                text = base_text + soft_text
            else:
                text = base_text

            keyboard = {
                "😊 Нормально": "morning_normal",
                "🥱 Разбит(а)": "morning_broken",
                "😐 Пока непонятно": "morning_unknown",
            }

            success = await send_message_with_retry(context.bot, user_id, text, keyboard)

            if success:
                sent_count += 1
                logger.info(f"✅ [УТРО] Отправлено {user_id}")
            else:
                error_count += 1
                logger.error(f"❌ [УТРО] Не удалось отправить {user_id}")

            await asyncio.sleep(0.3)  # Пауза между сообщениями

        except Exception as e:
            error_count += 1
            logger.error(f"❌ [УТРО] Критическая ошибка для {user_id}: {e}")

    elapsed_time = time.time() - start_time
    logger.info(
        f"📊 [УТРО] Итог: отправлено {sent_count}/{total_users}, ошибок {error_count}, время {elapsed_time:.2f}с"
    )

    # Сохраняем в БД
    await db.save_newsletter_log("morning", sent_count, error_count, total_users)


async def send_evening_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет вечернее сообщение с контролем времени"""
    start_time = time.time()
    current_time = datetime.now().strftime('%H:%M:%S')
    logger.info(f"📨 [ВЕЧЕР] Начало рассылки в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [ВЕЧЕР] Нет пользователей")
        return

    sent_count = 0
    error_count = 0
    total_users = len(user_data_store)

    for user_id, data in user_data_store.items():
        if not data.get('onboarding_complete', False):
            continue

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
                keyboard = {
                    "Ок, попробую": "evening_do",
                    "Пока рано, оставим как было": "evening_not_now",
                }
            elif evening_skip_streak >= 3:
                text = (
                    "Похоже, сейчас у тебя слишком плотные вечера, и это нормально.\n"
                    "Давай сделаем совсем простой вариант:\n"
                    "сегодня достаточно просто поставить себе будильник на желаемое время отхода ко сну"
                    " и хотя бы на 30 минут приблизиться к нему."
                )
                keyboard = {
                    "Ок, так проще": "evening_do",
                    "Не хочу сейчас этим заниматься": "evening_not_now",
                }
            else:
                text = base_text
                keyboard = {
                    "Сделаю сегодня": "evening_do",
                    "Не сейчас": "evening_not_now",
                }

            success = await send_message_with_retry(context.bot, user_id, text, keyboard)

            if success:
                # Отправляем вопрос о самочувствии
                mood_success = await send_message_with_retry(
                    context.bot,
                    user_id,
                    "И напоследок: как ты сейчас себя чувствуешь?",
                    {
                        "🙂 Спокойно": "feeling_calm",
                        "😕 Напряжён(а)": "feeling_stressed",
                        "😔 Грустно": "feeling_sad",
                        "😩 Очень плохо": "feeling_bad",
                    },
                )

                if mood_success:
                    sent_count += 1
                    logger.info(f"✅ [ВЕЧЕР] Отправлено {user_id}")
                else:
                    error_count += 1
                    logger.error(f"❌ [ВЕЧЕР] Не отправлен вопрос настроения {user_id}")
            else:
                error_count += 1
                logger.error(f"❌ [ВЕЧЕР] Не отправлено основное сообщение {user_id}")

            await asyncio.sleep(0.5)  # Пауза между пользователями

        except Exception as e:
            error_count += 1
            logger.error(f"❌ [ВЕЧЕР] Критическая ошибка для {user_id}: {e}")

    elapsed_time = time.time() - start_time
    logger.info(
        f"📊 [ВЕЧЕР] Итог: отправлено {sent_count}/{total_users}, ошибок {error_count}, время {elapsed_time:.2f}с"
    )

    await db.save_newsletter_log("evening", sent_count, error_count, total_users)


async def send_day_stress_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет дневное сообщение с контролем времени"""
    start_time = time.time()
    current_time = datetime.now().strftime('%H:%M:%S')
    logger.info(f"📨 [ДЕНЬ] Начало рассылки в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [ДЕНЬ] Нет пользователей")
        return

    sent_count = 0
    error_count = 0
    stress_users = 0

    for user_id, data in user_data_store.items():
        if not data.get('onboarding_complete', False):
            continue

        has_stress = 'днём высокий стресс' in data.get('scenario', [])
        if not has_stress:
            continue

        stress_users += 1

        try:
            stats = user_stats_store.get(user_id, {})
            day_streak = stats.get('day_stress_streak', 0)
            day_skip_streak = stats.get('day_stress_skip_streak', 0)

            if day_streak >= 3:
                text = "Супер! Ты уже несколько дней делаешь паузу. Если есть силы, добавь к паузе стакан воды."
            elif day_skip_streak >= 3:
                text = "Вижу, сейчас сложно. Попробуй хотя бы просто выключить звук на телефоне на 1 минуту."
            else:
                text = (
                    "Как день? Если чувствуешь, что голова закипает, давай сделаем 30‑секундную паузу:\n"
                    "👀 посмотри в окно или на дальнюю точку\n"
                    "🌬️ сделай 5 медленных вдохов\n"
                    "💪 потяни плечи"
                )

            keyboard = {
                "✅ Сделал(а)": "day_stress_done",
                "Не до этого": "day_stress_skip",
            }

            success = await send_message_with_retry(context.bot, user_id, text, keyboard)

            if success:
                sent_count += 1
                logger.info(f"✅ [ДЕНЬ] Отправлено {user_id}")
            else:
                error_count += 1
                logger.error(f"❌ [ДЕНЬ] Не отправлено {user_id}")

            await asyncio.sleep(0.3)  # Пауза между сообщениями

        except Exception as e:
            error_count += 1
            logger.error(f"❌ [ДЕНЬ] Критическая ошибка для {user_id}: {e}")

    elapsed_time = time.time() - start_time
    logger.info(
        f"📊 [ДЕНЬ] Итог: стресс-пользователей {stress_users}, отправлено {sent_count}, ошибок {error_count}, время {elapsed_time:.2f}с"
    )

    await db.save_newsletter_log("day_stress", sent_count, error_count, stress_users, {"stress_users": stress_users})
