import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Optional

from telegram.ext import ContextTypes

# from app.ai import ai
from app.bot_app import bot_app
from app.config import user_data_store, user_stats_store
from app.menu import get_simple_keyboard
from app.vk_module.vk_bot import vk_bot

logger = logging.getLogger(__name__)


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========


def vk_simple_keyboard(buttons_dict: dict, one_time=False):
    """Создаёт inline-клавиатуру для VK.
    buttons_dict: {label: cmd}"""
    keyboard_buttons = []
    for label, cmd in buttons_dict.items():
        keyboard_buttons.append(
            [{"action": {"type": "callback", "payload": json.dumps({"cmd": cmd}), "label": label}, "color": "primary"}]
        )
    return {"one_time": one_time, "buttons": keyboard_buttons, "inline": True}


async def send_message_with_retry(
    bot, chat_id: str, text: str, keyboard: dict, max_retries: int = 2, timeout: float = 10.0
) -> bool:
    """Отправляет сообщение через Telegram с повторными попытками"""
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


async def vk_send_message_with_retry(user_id: str, text: str, keyboard: dict = None, max_retries: int = 2) -> bool:
    """Отправляет сообщение через VK с повторными попытками"""
    for attempt in range(max_retries):
        try:
            result = await vk_bot.api.send_message(int(user_id), text, keyboard)
            if result:
                return True
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки VK: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    return False


def is_vk_user(user_id: str) -> bool:
    """Определяет платформу пользователя по ID.
    Telegram ID обычно > 100000000, VK ID короче.
    Также можно добавить поле platform в user_data_store."""
    try:
        uid = int(user_id)
        # VK ID обычно меньше 1 миллиарда, Telegram ID больше
        if uid < 1000000000:
            return True
        return False
    except Exception:
        return False


# ========== УТРЕННЯЯ РАССЫЛКА ==========


async def send_morning_message(context: ContextTypes.DEFAULT_TYPE, target_user_id: Optional[str] = None):
    """Отправляет утреннее сообщение (Telegram и VK)"""
    start_time = time.time()

    if not user_data_store:
        logger.warning("⚠️ [УТРО] Нет пользователей")
        return

    sent_count = 0
    error_count = 0

    users_to_send = []
    if target_user_id:
        if target_user_id in user_data_store:
            users_to_send = [target_user_id]
        else:
            logger.error(f"❌ [УТРО] Пользователь {target_user_id} не найден")
            return
    else:
        users_to_send = [uid for uid, data in user_data_store.items() if data.get('onboarding_complete', False)]

    for user_id in users_to_send:
        try:
            data = user_data_store[user_id]
            if not data.get('onboarding_complete', False):
                continue

            base_text = "Доброе утро! Как ты проснулся(лась) сегодня?\nДавай заодно сделаем маленький шаг для более ясного утра."
            stats = user_stats_store.get(user_id, {})
            morning_streak = stats.get('morning_streak', 0)
            morning_skip_streak = stats.get('morning_skip_streak', 0)

            if morning_streak >= 3:
                text = base_text + (
                    f"\n\nВижу, ты уже {morning_streak} утра подряд делаешь этот маленький шаг — это круто 👏\n"
                    "Если чувствуешь силы, давай сегодня чуть усилим ритуал:\n"
                    "попробуй не только вдохи, но и 3 минуты почитать что‑то спокойное или сделать растяжку."
                )
            elif morning_skip_streak >= 3:
                text = base_text + (
                    "\n\nПохоже, сейчас у тебя слишком плотные утра, и это нормально.\n"
                    "Давай сделаем совсем простой вариант:\n"
                    "сегодня достаточно просто встать с кровати и улыбнуться своему отражению."
                )
            else:
                text = base_text

            if is_vk_user(user_id):
                keyboard = vk_simple_keyboard(
                    {
                        "😊 Нормально": "morning_normal",
                        "🥱 Разбит(а)": "morning_broken",
                        "😐 Пока непонятно": "morning_unknown",
                    }
                )
                success = await vk_send_message_with_retry(user_id, text, keyboard)
            else:
                keyboard = {
                    "😊 Нормально": "morning_normal",
                    "🥱 Разбит(а)": "morning_broken",
                    "😐 Пока непонятно": "morning_unknown",
                }
                success = await send_message_with_retry(context.bot, user_id, text, keyboard)

            if success:
                sent_count += 1
            else:
                error_count += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            error_count += 1
            logger.error(f"❌ [УТРО] Ошибка для {user_id}: {e}")

    elapsed = time.time() - start_time
    logger.info(f"📊 [УТРО] Отправлено {sent_count}, ошибок {error_count}, время {elapsed:.2f}с")


# ========== ВЕЧЕРНЯЯ РАССЫЛКА ==========


async def send_evening_message(context: ContextTypes.DEFAULT_TYPE, target_user_id: Optional[str] = None):
    """Отправляет вечернее сообщение (Telegram и VK)"""
    start_time = time.time()

    if not user_data_store:
        logger.warning("⚠️ [ВЕЧЕР] Нет пользователей")
        return

    sent_count = 0
    error_count = 0

    users_to_send = []
    if target_user_id:
        if target_user_id in user_data_store:
            users_to_send = [target_user_id]
        else:
            logger.error(f"❌ [ВЕЧЕР] Пользователь {target_user_id} не найден")
            return
    else:
        users_to_send = [uid for uid, data in user_data_store.items() if data.get('onboarding_complete', False)]

    for user_id in users_to_send:
        try:
            data = user_data_store[user_id]
            if not data.get('onboarding_complete', False):
                continue

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
                buttons = {"Ок, попробую": "evening_do", "Пока рано, оставим как было": "evening_not_now"}
            elif evening_skip_streak >= 3:
                text = (
                    "Похоже, сейчас у тебя слишком плотные вечера, и это нормально.\n"
                    "Давай сделаем совсем простой вариант:\n"
                    "сегодня достаточно просто поставить себе будильник на желаемое время отхода ко сну"
                    " и хотя бы на 30 минут приблизиться к нему."
                )
                buttons = {"Ок, так проще": "evening_do", "Не хочу сейчас этим заниматься": "evening_not_now"}
            else:
                text = base_text
                buttons = {"Сделаю сегодня": "evening_do", "Не сейчас": "evening_not_now"}

            if is_vk_user(user_id):
                keyboard = vk_simple_keyboard(buttons)
                success = await vk_send_message_with_retry(user_id, text, keyboard)
            else:
                keyboard = buttons
                success = await send_message_with_retry(context.bot, user_id, text, keyboard)

            if success:
                sent_count += 1
            else:
                error_count += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            error_count += 1
            logger.error(f"❌ [ВЕЧЕР] Ошибка для {user_id}: {e}")

    elapsed = time.time() - start_time
    logger.info(f"📊 [ВЕЧЕР] Отправлено {sent_count}, ошибок {error_count}, время {elapsed:.2f}с")


# ========== ДНЕВНАЯ РАССЫЛКА ==========


async def send_day_stress_message(context: ContextTypes.DEFAULT_TYPE, target_user_id: Optional[str] = None):
    """Отправляет дневное сообщение (Telegram и VK)"""
    if not user_data_store:
        return

    sent_count = 0
    error_count = 0

    users_to_send = []
    if target_user_id:
        if target_user_id in user_data_store:
            users_to_send = [target_user_id]
        else:
            return
    else:
        users_to_send = [
            uid
            for uid, data in user_data_store.items()
            if data.get('onboarding_complete', False) and 'днём высокий стресс' in data.get('scenario', [])
        ]

    for user_id in users_to_send:
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

            buttons = {"✅ Сделал(а)": "day_stress_done", "Не до этого": "day_stress_skip"}

            if is_vk_user(user_id):
                keyboard = vk_simple_keyboard(buttons)
                success = await vk_send_message_with_retry(user_id, text, keyboard)
            else:
                keyboard = buttons
                success = await send_message_with_retry(context.bot, user_id, text, keyboard)

            if success:
                sent_count += 1
            else:
                error_count += 1
            await asyncio.sleep(0.3)
        except Exception:
            error_count += 1

    logger.info(f"📊 [ДЕНЬ] Отправлено {sent_count}, ошибок {error_count}")


# ========== ПЛАНИРОВЩИК ==========


async def run_scheduler():
    """Планировщик для периодических рассылок с учётом персонального времени"""
    logger.info("=" * 60)
    logger.info("🕐 ПЛАНИРОВЩИК ЗАПУЩЕН")
    logger.info(f"🕐 Текущее время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    check_counter = 0

    while True:
        try:
            now = datetime.now()
            current_time = now.time()
            check_counter += 1

            for user_id, data in user_data_store.items():
                if not data.get('onboarding_complete', False):
                    continue

                morning_time = data.get('morning_time', '09:00')
                evening_time = data.get('evening_time', '21:00')

                if morning_time is None:
                    morning_time = '09:00'

                # Утренняя рассылка
                try:
                    morning_hour, morning_min = map(int, morning_time.split(':'))
                    if current_time.hour == morning_hour and current_time.minute == morning_min:
                        if should_send_message(user_id, 'morning'):
                            logger.info(f"🎯 [УТРО] Рассылка {user_id} в {morning_time}")

                            class DummyContext:
                                def __init__(self, bot):
                                    self.bot = bot

                            dummy_context = DummyContext(bot_app.bot)
                            await send_morning_message(dummy_context, target_user_id=user_id)
                            await asyncio.sleep(60)
                except (ValueError, TypeError):
                    pass

                # Вечерняя рассылка
                if evening_time is not None:
                    try:
                        evening_hour, evening_min = map(int, evening_time.split(':'))
                        if current_time.hour == evening_hour and current_time.minute == evening_min:
                            if should_send_message(user_id, 'evening'):
                                logger.info(f"🎯 [ВЕЧЕР] Рассылка {user_id} в {evening_time}")

                                class DummyContext:
                                    def __init__(self, bot):
                                        self.bot = bot

                                dummy_context = DummyContext(bot_app.bot)
                                await send_evening_message(dummy_context, target_user_id=user_id)
                                await asyncio.sleep(60)
                    except (ValueError, TypeError):
                        pass

                # Дневная рассылка в 15:00
                if current_time.hour == 15 and current_time.minute == 0:
                    if should_send_message(user_id, 'day'):
                        if 'днём высокий стресс' in data.get('scenario', []):
                            logger.info(f"🎯 [ДЕНЬ] Рассылка {user_id}")

                            class DummyContext:
                                def __init__(self, bot):
                                    self.bot = bot

                            dummy_context = DummyContext(bot_app.bot)
                            await send_day_stress_message(dummy_context, target_user_id=user_id)
                            await asyncio.sleep(60)

            if check_counter % 120 == 0:
                logger.info("=" * 50)
                logger.info("⏰ ЧАСОВОЙ ОТЧЕТ ПЛАНИРОВЩИКА")
                logger.info(f"В базе данных {len(user_data_store)} пользователей")
                onboarded = sum(1 for u in user_data_store.values() if u.get('onboarding_complete', False))
                logger.info(f"Из них прошли онбординг: {onboarded}")
                logger.info("=" * 50)

            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в планировщике: {e}", exc_info=True)
            await asyncio.sleep(30)


def should_send_message(user_id: str, message_type: str) -> bool:
    """Определяет, нужно ли отправлять сообщение с учётом настроек частоты"""
    user_data = user_data_store.get(user_id, {})
    frequency = user_data.get('notification_frequency', '')

    if not frequency or frequency.startswith("2-3"):
        return True

    if frequency.startswith("1 сообщение"):
        daily_time = user_data.get('daily_time', '')
        if daily_time.startswith("Утром") and message_type == 'morning':
            return True
        elif daily_time.startswith("Днём") and message_type == 'day':
            return True
        elif daily_time.startswith("Вечером") and message_type == 'evening':
            return True
        return message_type == 'morning'

    if frequency.startswith("Раз в пару дней"):
        biweekly_time = user_data.get('biweekly_time', '')
        if biweekly_time.startswith("Утром") and message_type == 'morning':
            return True
        elif biweekly_time.startswith("Днём") and message_type == 'day':
            return True
        elif biweekly_time.startswith("Вечером") and message_type == 'evening':
            return True
        return message_type == 'morning'

    return True
