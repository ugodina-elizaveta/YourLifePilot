import asyncio
import logging
import time
from datetime import datetime

from telegram.ext import ContextTypes

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


async def send_evening_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет только основное вечернее сообщение (без вопроса о чувствах)"""
    start_time = time.time()
    current_time = datetime.now().strftime('%H:%M:%S')
    logger.info(f"📨 [ВЕЧЕР] Начало рассылки в {current_time}")

    if not user_data_store:
        logger.warning("⚠️ [ВЕЧЕР] Нет пользователей")
        return

    sent_count = 0
    error_count = 0
    total_users = len([u for u in user_data_store.values() if u.get('onboarding_complete')])

    for user_id, data in user_data_store.items():
        if not data.get('onboarding_complete', False):
            continue

        try:
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

            # Отправляем ТОЛЬКО ОСНОВНОЕ СООБЩЕНИЕ (без вопроса о чувствах)
            main_success = await send_message_with_retry(context.bot, user_id, text, keyboard)

            if main_success:
                sent_count += 1
                logger.info(f"✅ [ВЕЧЕР] Основное сообщение отправлено {user_id}")
            else:
                error_count += 1
                logger.error(f"❌ [ВЕЧЕР] Не отправлено основное сообщение {user_id}")

            await asyncio.sleep(0.5)  # Пауза между пользователями

        except Exception as e:
            error_count += 1
            logger.error(f"❌ [ВЕЧЕР] Критическая ошибка для {user_id}: {e}")

    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("📊 [ВЕЧЕР] ИТОГИ РАССЫЛКИ:")
    logger.info(f"   👥 Всего пользователей с онбордингом: {total_users}")
    logger.info(f"   ✅ Отправлено основных сообщений: {sent_count}")
    logger.info(f"   ❌ Ошибок: {error_count}")
    logger.info(f"   ⏱️ Время выполнения: {elapsed_time:.2f}с")
    logger.info("=" * 60)


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
