import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

from telegram.ext import ContextTypes

from app.ai import ai
from app.bot_app import bot_app
from app.config import user_data_store, user_stats_store
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


async def send_morning_message(context: ContextTypes.DEFAULT_TYPE, target_user_id: Optional[str] = None):
    """
    Отправляет утреннее сообщение.
    Если target_user_id указан - только этому пользователю,
    иначе - всем пользователям, прошедшим онбординг.
    """
    start_time = time.time()
    current_time = datetime.now().strftime('%H:%M:%S')

    if target_user_id:
        logger.info(f"📨 [УТРО] Тестовая рассылка для пользователя {target_user_id} в {current_time}")
    else:
        logger.info(f"📨 [УТРО] Массовая рассылка в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [УТРО] Нет пользователей")
        return

    sent_count = 0
    error_count = 0

    # Определяем список пользователей для рассылки
    users_to_send = []
    if target_user_id:
        if target_user_id in user_data_store:
            users_to_send = [target_user_id]
            logger.info(f"👤 [УТРО] Тестовый режим: отправка пользователю {target_user_id}")
        else:
            logger.error(f"❌ [УТРО] Пользователь {target_user_id} не найден")
            return
    else:
        users_to_send = [uid for uid, data in user_data_store.items() if data.get('onboarding_complete', False)]

    total_users = len(users_to_send)
    if total_users == 0:
        logger.warning("⚠️ [УТРО] Нет пользователей для рассылки")
        return

    logger.info(f"👥 [УТРО] Будет отправлено {total_users} пользователям")

    for user_id in users_to_send:
        try:
            data = user_data_store[user_id]

            # Проверяем онбординг для массовой рассылки
            if not target_user_id and not data.get('onboarding_complete', False):
                continue

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

            await asyncio.sleep(0.3)

        except Exception as e:
            error_count += 1
            logger.error(f"❌ [УТРО] Критическая ошибка для {user_id}: {e}")

    elapsed_time = time.time() - start_time

    if target_user_id:
        logger.info(
            f"📊 [УТРО] Тестовая рассылка для {target_user_id}: отправлено {sent_count}, ошибок {error_count}, время {elapsed_time:.2f}с"
        )
    else:
        logger.info(
            f"📊 [УТРО] Массовая рассылка: отправлено {sent_count}/{total_users}, ошибок {error_count}, время {elapsed_time:.2f}с"
        )


async def send_evening_message(context: ContextTypes.DEFAULT_TYPE, target_user_id: Optional[str] = None):
    """
    Отправляет вечернее сообщение.
    Если target_user_id указан - только этому пользователю,
    иначе - всем пользователям, прошедшим онбординг.
    """
    start_time = time.time()
    current_time = datetime.now().strftime('%H:%M:%S')

    if target_user_id:
        logger.info(f"📨 [ВЕЧЕР] Тестовая рассылка для пользователя {target_user_id} в {current_time}")
    else:
        logger.info(f"📨 [ВЕЧЕР] Массовая рассылка в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [ВЕЧЕР] Нет пользователей")
        return

    sent_count = 0
    error_count = 0

    # Определяем список пользователей для рассылки
    users_to_send = []
    if target_user_id:
        if target_user_id in user_data_store:
            users_to_send = [target_user_id]
            logger.info(f"👤 [ВЕЧЕР] Тестовый режим: отправка пользователю {target_user_id}")
        else:
            logger.error(f"❌ [ВЕЧЕР] Пользователь {target_user_id} не найден")
            return
    else:
        users_to_send = [uid for uid, data in user_data_store.items() if data.get('onboarding_complete', False)]

    total_users = len(users_to_send)
    if total_users == 0:
        logger.warning("⚠️ [ВЕЧЕР] Нет пользователей для рассылки")
        return

    logger.info(f"👥 [ВЕЧЕР] Будет отправлено {total_users} пользователям")

    for user_id in users_to_send:
        try:
            data = user_data_store[user_id]

            # Проверяем онбординг для массовой рассылки
            if not target_user_id and not data.get('onboarding_complete', False):
                continue

            # Формируем только основное сообщение
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

            # Отправляем ТОЛЬКО ОСНОВНОЕ СООБЩЕНИЕ
            main_success = await send_message_with_retry(context.bot, user_id, text, keyboard)

            if main_success:
                sent_count += 1
                logger.info(f"✅ [ВЕЧЕР] Основное сообщение отправлено {user_id}")

                # Проверяем историю настроений для дополнительной поддержки
                # (только для массовой рассылки)
                if not target_user_id:
                    mood_history = data.get('mood_history', [])
                    if len(mood_history) >= 5:
                        trend = ai.analyze_mood_trend(mood_history)
                        if trend['trend'] == 'worsening':
                            asyncio.create_task(send_support_message(context, user_id))
            else:
                error_count += 1
                logger.error(f"❌ [ВЕЧЕР] Не отправлено основное сообщение {user_id}")

            await asyncio.sleep(0.5)

        except Exception as e:
            error_count += 1
            logger.error(f"❌ [ВЕЧЕР] Критическая ошибка для {user_id}: {e}")

    elapsed_time = time.time() - start_time
    logger.info("=" * 60)

    if target_user_id:
        logger.info(
            f"📊 [ВЕЧЕР] Тестовая рассылка для {target_user_id}: отправлено {sent_count}, ошибок {error_count}, время {elapsed_time:.2f}с"
        )
    else:
        logger.info(
            f"📊 [ВЕЧЕР] Массовая рассылка: отправлено {sent_count}/{total_users}, ошибок {error_count}, время {elapsed_time:.2f}с"
        )
    logger.info("=" * 60)


async def send_day_stress_message(context: ContextTypes.DEFAULT_TYPE, target_user_id: Optional[str] = None):
    """
    Отправляет дневное сообщение.
    Если target_user_id указан - только этому пользователю,
    иначе - всем пользователям со сценарием 'днём высокий стресс'.
    """
    start_time = time.time()
    current_time = datetime.now().strftime('%H:%M:%S')

    if target_user_id:
        logger.info(f"📨 [ДЕНЬ] Тестовая рассылка для пользователя {target_user_id} в {current_time}")
    else:
        logger.info(f"📨 [ДЕНЬ] Массовая рассылка в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [ДЕНЬ] Нет пользователей")
        return

    sent_count = 0
    error_count = 0
    stress_users = 0

    # Определяем список пользователей для рассылки
    users_to_send = []
    if target_user_id:
        if target_user_id in user_data_store:
            # Для теста отправляем даже если нет сценария стресса
            users_to_send = [target_user_id]
            logger.info(f"👤 [ДЕНЬ] Тестовый режим: отправка пользователю {target_user_id}")
        else:
            logger.error(f"❌ [ДЕНЬ] Пользователь {target_user_id} не найден")
            return
    else:
        # Для массовой рассылки только со стрессом
        for user_id, data in user_data_store.items():
            if data.get('onboarding_complete', False) and 'днём высокий стресс' in data.get('scenario', []):
                users_to_send.append(user_id)
                stress_users += 1

    total_users = len(users_to_send)
    if total_users == 0:
        if target_user_id:
            logger.warning(
                f"⚠️ [ДЕНЬ] Пользователь {target_user_id} найден, но не отправлено (возможно, нет онбординга)"
            )
        else:
            logger.warning("⚠️ [ДЕНЬ] Нет пользователей со стрессом")
        return

    logger.info(f"👥 [ДЕНЬ] Будет отправлено {total_users} пользователям")

    for user_id in users_to_send:
        try:
            data = user_data_store[user_id]

            # Проверяем онбординг
            if not data.get('onboarding_complete', False):
                if target_user_id:
                    logger.warning(f"⚠️ [ДЕНЬ] Пользователь {user_id} не прошёл онбординг")
                continue

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

            await asyncio.sleep(0.3)

        except Exception as e:
            error_count += 1
            logger.error(f"❌ [ДЕНЬ] Критическая ошибка для {user_id}: {e}")

    elapsed_time = time.time() - start_time

    if target_user_id:
        logger.info(
            f"📊 [ДЕНЬ] Тестовая рассылка для {target_user_id}: отправлено {sent_count}, ошибок {error_count}, время {elapsed_time:.2f}с"
        )
    else:
        logger.info(
            f"📊 [ДЕНЬ] Массовая рассылка: стресс-пользователей {stress_users}, отправлено {sent_count}, ошибок {error_count}, время {elapsed_time:.2f}с"
        )


async def send_support_message(context: ContextTypes.DEFAULT_TYPE, user_id: str):
    """Отправляет поддерживающее сообщение через минуту"""
    await asyncio.sleep(60)
    try:
        advice = ai.generate_advice(user_context="Настроение ухудшается последние дни", situation='stress')
        await context.bot.send_message(
            chat_id=user_id, text=f"🌟 Заметил, что последнее время тебе тяжело.\n\n{advice}"
        )
        logger.info(f"✅ [ВЕЧЕР] Поддерживающее сообщение отправлено {user_id}")
    except Exception as e:
        logger.error(f"❌ [ВЕЧЕР] Ошибка отправки поддержки {user_id}: {e}")


# --- ПЛАНИРОВЩИК ЗАДАЧ ---
async def run_scheduler():
    """Планировщик для периодических рассылок с учётом персонального времени"""
    logger.info("=" * 60)
    logger.info("🕐 ПЛАНИРОВЩИК ЗАПУЩЕН")
    logger.info(f"🕐 Текущее время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # Счетчик для периодических логов
    check_counter = 0

    while True:
        try:
            now = datetime.now()
            current_time = now.time()
            check_counter += 1

            # Проходим по всем пользователям и проверяем их персональное время
            for user_id, data in user_data_store.items():
                if not data.get('onboarding_complete', False):
                    continue

                # Получаем персональное время пользователя
                morning_time = data.get('morning_time', '09:00')
                evening_time = data.get('evening_time', '21:00')

                # Разбираем часы и минуты
                morning_hour, morning_min = map(int, morning_time.split(':'))
                evening_hour, evening_min = map(int, evening_time.split(':'))

                # Утренняя рассылка для конкретного пользователя
                if current_time.hour == morning_hour and current_time.minute == morning_min:
                    logger.info(f"🎯 СРАБОТАЛО: УТРЕННЯЯ РАССЫЛКА для пользователя {user_id} в {morning_time}")

                    class DummyContext:
                        def __init__(self, bot):
                            self.bot = bot

                    dummy_context = DummyContext(bot_app.bot)
                    await send_morning_message(dummy_context, target_user_id=user_id)

                    # Ждем минуту, чтобы не сработать повторно
                    await asyncio.sleep(60)

                # Дневная рассылка в 15:00 (оставляем общей)
                if current_time.hour == 15 and current_time.minute == 0:
                    # Отправляем только пользователям со стресс-сценарием
                    if 'днём высокий стресс' in data.get('scenario', []):
                        logger.info(f"🎯 СРАБОТАЛО: ДНЕВНАЯ РАССЫЛКА для пользователя {user_id}")

                        class DummyContext:
                            def __init__(self, bot):
                                self.bot = bot

                        dummy_context = DummyContext(bot_app.bot)
                        await send_day_stress_message(dummy_context, target_user_id=user_id)
                        await asyncio.sleep(60)

                # Вечерняя рассылка для конкретного пользователя
                if current_time.hour == evening_hour and current_time.minute == evening_min:
                    logger.info(f"🎯 СРАБОТАЛО: ВЕЧЕРНЯЯ РАССЫЛКА для пользователя {user_id} в {evening_time}")

                    class DummyContext:
                        def __init__(self, bot):
                            self.bot = bot

                    dummy_context = DummyContext(bot_app.bot)
                    await send_evening_message(dummy_context, target_user_id=user_id)
                    await asyncio.sleep(60)

            # Лог каждый час о том, что планировщик работает
            if check_counter % 120 == 0:
                logger.info("=" * 50)
                logger.info("⏰ ЧАСОВОЙ ОТЧЕТ ПЛАНИРОВЩИКА")
                logger.info(f"В базе данных {len(user_data_store)} пользователей")

                onboarded = sum(1 for u in user_data_store.values() if u.get('onboarding_complete', False))
                logger.info(f"Из них прошли онбординг: {onboarded}")
                logger.info("=" * 50)

            # Проверка каждые 30 секунд
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в планировщике: {e}", exc_info=True)
            await asyncio.sleep(30)
