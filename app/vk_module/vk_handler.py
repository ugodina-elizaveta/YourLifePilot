import json
import logging
import uuid
from datetime import datetime

from app.config import (
    user_data_store,
    user_stats_store,
    AGE_OPTIONS,
    OCCUPATION_OPTIONS,
    MORNING_TIME_OPTIONS,
    EVENING_TIME_OPTIONS,
    Q1_OPTIONS,
    TIME_OPTIONS,
    WAKE_OPTIONS,
    STRESS_OPTIONS,
    Q1_TEXT,
    Q2_TEXT,
    Q3_TEXT,
    Q4_TEXT,
    Q5_TEXT,
    AGE_QUESTION,
    OCCUPATION_QUESTION,
    MORNING_TIME_QUESTION,
    EVENING_TIME_QUESTION,
    DISCLAIMER_TEXT,
    WELCOME_TEXT,
    PHYSICAL_LIMITS_QUESTION,
    PHYSICAL_LIMITS_OPTIONS,
    NOTIFICATION_FREQUENCY_QUESTION,
    NOTIFICATION_FREQUENCY_OPTIONS,
    DAILY_TIME_QUESTION,
    DAILY_TIME_OPTIONS,
    BIWEEKLY_TIME_QUESTION,
    BIWEEKLY_TIME_OPTIONS,
)
from app.ai import ai
from app.database import db

logger = logging.getLogger(__name__)


class VkHandler:
    def __init__(self, api):
        self.api = api
        # Состояния онбординга
        self.onboarding_states = {
            'AGREEMENT': self.agreement,
            'AGE': self.age,
            'OCCUPATION': self.occupation,
            'MORNING_TIME': self.morning_time,
            'EVENING_TIME': self.evening_time,
            'PHYSICAL_LIMITS': self.physical_limits,
            'PHYSICAL_DETAILS': self.physical_details,
            'NOTIFICATION_FREQ': self.notification_freq,
            'DAILY_TIME': self.daily_time,
            'BIWEEKLY_TIME': self.biweekly_time,
            'Q1': self.q1,
            'Q2': self.q2,
            'Q3': self.q3,
            'Q4': self.q4,
            'Q5': self.q5,
        }

    async def handle(self, user_id: str, text: str, cmd: str = None):
        """Главный роутер сообщений"""
        # Игнорируем пустые сообщения
        if not text and not cmd:
            return

        # Обработка callback-команд планировщика и AI-чата
        if cmd:
            await self.handle_callback(user_id, cmd)
            return

        # Специальные текстовые команды
        if text == '/start' or text.lower() == 'начать':
            await self.start(user_id)
            return
        if text == '/ai' or text.lower() == 'поговорить с ии':
            await self.start_ai_chat(user_id)
            return
        if text == '/stop_ai' or text.lower() == 'выйти из ии':
            await self.stop_ai_chat(user_id)
            return

        # Проверяем состояние онбординга
        state = user_data_store.get(user_id, {}).get('vk_state')
        if state and state in self.onboarding_states:
            await self.onboarding_states[state](user_id, text)
            return

        # Остальное — свободный текст (AI-чат или просто сообщение)
        await self.process_free_text(user_id, text)

    # ---------- Вспомогательные методы ----------
    def init_user(self, user_id):
        if user_id not in user_data_store:
            user_data_store[user_id] = {
                'username': '',
                'first_name': '',
                'last_name': '',
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
                'vk_state': None,
            }
        if user_id not in user_stats_store:
            user_stats_store[user_id] = {
                'morning_streak': 0,
                'morning_skip_streak': 0,
                'evening_streak': 0,
                'evening_skip_streak': 0,
                'day_stress_streak': 0,
                'day_stress_skip_streak': 0,
                'last_action_date': {},
            }

    async def save_and_next(self, user_id, next_state, question, options):
        """Сохраняет выбранный ответ (text) и переводит в следующее состояние"""
        # Вызовется в конкретном обработчике, поэтому здесь обобщим?
        # Не используется напрямую, оставим для ясности
        pass

    # ---------- Клавиатуры ----------
    def simple_keyboard(self, buttons_dict: dict, one_time=False):
        """Создаёт обычную клавиатуру с кнопками.
        buttons_dict: {label: cmd} (payload будет {'cmd': cmd})"""
        keyboard_buttons = []
        for label, cmd in buttons_dict.items():
            keyboard_buttons.append(
                [
                    {
                        "action": {"type": "callback", "payload": json.dumps({"cmd": cmd}), "label": label},
                        "color": "primary",
                    }
                ]
            )
        return {
            "one_time": one_time,
            "buttons": keyboard_buttons,
            "inline": True,  # используем inline-клавиатуры для callback'ов
        }

    # ---------- Онбординг ----------
    async def start(self, user_id):
        self.init_user(user_id)
        user_data_store[user_id]['vk_state'] = 'AGREEMENT'
        await self.api.send_message(int(user_id), WELCOME_TEXT)
        await self.api.send_message(
            int(user_id),
            DISCLAIMER_TEXT,
            keyboard=self.simple_keyboard({"✅ Понимаю и согласен(на)": "agree"}, one_time=True),
        )

    async def agreement(self, user_id, text):
        # Здесь text не важен, ждём callback
        pass

    async def handle_callback(self, user_id, cmd):
        """Обработка всех callback-команд (от инлайн-кнопок)"""
        state = user_data_store.get(user_id, {}).get('vk_state')
        # Команды онбординга
        if cmd == 'agree' and state == 'AGREEMENT':
            user_data_store[user_id]['vk_state'] = 'AGE'
            await self.api.send_message(int(user_id), "Отлично! Давай познакомимся поближе.")
            await self.api.send_message(
                int(user_id), AGE_QUESTION, keyboard=self.simple_keyboard(dict.fromkeys(AGE_OPTIONS, ''))
            )
            # Заменим пустые payload на соответствующие age_0..4
            # Лучше явно задать payloads
            return
        # Аналогично для каждого шага. Для лаконичности сделаем общую обработку через префиксы cmd.
        # Но проще сделать так:
        if cmd.startswith('age_'):
            idx = int(cmd.split('_')[1])
            answer = AGE_OPTIONS[idx]
            user_data_store[user_id]['age_group'] = answer
            user_data_store[user_id]['vk_state'] = 'OCCUPATION'
            await self.api.send_message(
                int(user_id), OCCUPATION_QUESTION, keyboard=self.simple_keyboard(dict.fromkeys(OCCUPATION_OPTIONS, ''))
            )
        elif cmd.startswith('occupation_'):
            idx = int(cmd.split('_')[1])
            answer = OCCUPATION_OPTIONS[idx]
            user_data_store[user_id]['occupation'] = answer
            user_data_store[user_id]['vk_state'] = 'MORNING_TIME'
            await self.api.send_message(
                int(user_id),
                MORNING_TIME_QUESTION,
                keyboard=self.simple_keyboard(dict.fromkeys(MORNING_TIME_OPTIONS, '')),
            )
        elif cmd.startswith('morning_time_'):
            idx = int(cmd.split('_')[1])
            answer = MORNING_TIME_OPTIONS[idx]
            if answer == "Не важно (09:00)":
                user_data_store[user_id]['morning_time'] = "09:00"
            else:
                user_data_store[user_id]['morning_time'] = answer
            user_data_store[user_id]['vk_state'] = 'EVENING_TIME'
            await self.api.send_message(
                int(user_id),
                EVENING_TIME_QUESTION,
                keyboard=self.simple_keyboard(dict.fromkeys(EVENING_TIME_OPTIONS, '')),
            )
        elif cmd.startswith('evening_time_'):
            idx = int(cmd.split('_')[1])
            answer = EVENING_TIME_OPTIONS[idx]
            if answer == "Не важно (21:00)":
                user_data_store[user_id]['evening_time'] = "21:00"
            else:
                user_data_store[user_id]['evening_time'] = answer
            user_data_store[user_id]['vk_state'] = 'PHYSICAL_LIMITS'
            await db.save_user(user_id, user_data_store[user_id])
            await self.api.send_message(
                int(user_id),
                PHYSICAL_LIMITS_QUESTION,
                keyboard=self.simple_keyboard(dict.fromkeys(PHYSICAL_LIMITS_OPTIONS, '')),
            )
        elif cmd.startswith('physical_'):
            idx = int(cmd.split('_')[1])
            answer = PHYSICAL_LIMITS_OPTIONS[idx]
            if answer == "Другое (укажу в следующем шаге)":
                user_data_store[user_id]['vk_state'] = 'PHYSICAL_DETAILS'
                await self.api.send_message(int(user_id), "Пожалуйста, опиши свои ограничения в одном сообщении.")
            else:
                user_data_store[user_id]['physical_limits'] = answer
                await self.api.send_message(int(user_id), "Спасибо! Я учту это.")
                await db.save_user(user_id, user_data_store[user_id])
                user_data_store[user_id]['vk_state'] = 'NOTIFICATION_FREQ'
                await self.api.send_message(
                    int(user_id),
                    NOTIFICATION_FREQUENCY_QUESTION,
                    keyboard=self.simple_keyboard(dict.fromkeys(NOTIFICATION_FREQUENCY_OPTIONS, '')),
                )
        elif cmd.startswith('freq_'):
            idx = int(cmd.split('_')[1])
            answer = NOTIFICATION_FREQUENCY_OPTIONS[idx]
            user_data_store[user_id]['notification_frequency'] = answer
            await db.save_user(user_id, user_data_store[user_id])
            if idx == 1:  # 1 сообщение в день
                user_data_store[user_id]['vk_state'] = 'DAILY_TIME'
                await self.api.send_message(
                    int(user_id),
                    DAILY_TIME_QUESTION,
                    keyboard=self.simple_keyboard(dict.fromkeys(DAILY_TIME_OPTIONS, '')),
                )
            elif idx == 2:  # Раз в пару дней
                user_data_store[user_id]['vk_state'] = 'BIWEEKLY_TIME'
                await self.api.send_message(
                    int(user_id),
                    BIWEEKLY_TIME_QUESTION,
                    keyboard=self.simple_keyboard(dict.fromkeys(BIWEEKLY_TIME_OPTIONS, '')),
                )
            else:  # 2-3 сообщения в день
                user_data_store[user_id]['vk_state'] = 'Q1'
                await self.api.send_message(int(user_id), "Теперь несколько вопросов про сон.")
                await self.api.send_message(
                    int(user_id), Q1_TEXT, keyboard=self.simple_keyboard(dict.fromkeys(Q1_OPTIONS, ''))
                )
        elif cmd.startswith('daily_time_'):
            idx = int(cmd.split('_')[1])
            answer = DAILY_TIME_OPTIONS[idx]
            user_data_store[user_id]['daily_time'] = answer
            time_map = {"Утром (08:00-10:00)": "09:00", "Днём (13:00-15:00)": "14:00", "Вечером (19:00-21:00)": "20:00"}
            user_data_store[user_id]['morning_time'] = time_map.get(answer, "09:00")
            user_data_store[user_id]['evening_time'] = None
            user_data_store[user_id]['vk_state'] = 'Q1'
            await db.save_user(user_id, user_data_store[user_id])
            await self.api.send_message(int(user_id), "Теперь несколько вопросов про сон.")
            await self.api.send_message(
                int(user_id), Q1_TEXT, keyboard=self.simple_keyboard(dict.fromkeys(Q1_OPTIONS, ''))
            )
        elif cmd.startswith('biweekly_time_'):
            idx = int(cmd.split('_')[1])
            answer = BIWEEKLY_TIME_OPTIONS[idx]
            user_data_store[user_id]['biweekly_time'] = answer
            time_map = {"Утром (08:00-10:00)": "09:00", "Днём (13:00-15:00)": "14:00", "Вечером (19:00-21:00)": "20:00"}
            user_data_store[user_id]['morning_time'] = time_map.get(answer, "09:00")
            user_data_store[user_id]['evening_time'] = None
            user_data_store[user_id]['notification_skip_days'] = 1
            user_data_store[user_id]['vk_state'] = 'Q1'
            await db.save_user(user_id, user_data_store[user_id])
            await self.api.send_message(int(user_id), "Теперь несколько вопросов про сон.")
            await self.api.send_message(
                int(user_id), Q1_TEXT, keyboard=self.simple_keyboard(dict.fromkeys(Q1_OPTIONS, ''))
            )
        elif cmd.startswith('q1_'):
            idx = int(cmd.split('_')[1])
            answer = Q1_OPTIONS[idx]
            user_data_store[user_id]['answers']['q1'] = answer
            if idx <= 1:
                if 'плохой сон' not in user_data_store[user_id]['scenario']:
                    user_data_store[user_id]['scenario'].append('плохой сон')
            user_data_store[user_id]['vk_state'] = 'Q2'
            await self.api.send_message(
                int(user_id), Q2_TEXT, keyboard=self.simple_keyboard(dict.fromkeys(TIME_OPTIONS, ''))
            )
        elif cmd.startswith('q2_'):
            idx = int(cmd.split('_')[1])
            answer = TIME_OPTIONS[idx]
            user_data_store[user_id]['answers']['q2'] = answer
            if idx >= 2:
                if 'хочу ложиться поздно' not in user_data_store[user_id]['scenario']:
                    user_data_store[user_id]['scenario'].append('хочу ложиться поздно')
            user_data_store[user_id]['vk_state'] = 'Q3'
            await self.api.send_message(
                int(user_id), Q3_TEXT, keyboard=self.simple_keyboard(dict.fromkeys(TIME_OPTIONS, ''))
            )
        elif cmd.startswith('q3_'):
            idx = int(cmd.split('_')[1])
            answer = TIME_OPTIONS[idx]
            user_data_store[user_id]['answers']['q3'] = answer
            if idx >= 2:
                if 'ложусь поздно' not in user_data_store[user_id]['scenario']:
                    user_data_store[user_id]['scenario'].append('ложусь поздно')
            user_data_store[user_id]['vk_state'] = 'Q4'
            await self.api.send_message(
                int(user_id), Q4_TEXT, keyboard=self.simple_keyboard(dict.fromkeys(WAKE_OPTIONS, ''))
            )
        elif cmd.startswith('q4_'):
            idx = int(cmd.split('_')[1])
            answer = WAKE_OPTIONS[idx]
            user_data_store[user_id]['answers']['q4'] = answer
            if idx == 2:
                if 'просыпаюсь разбитым' not in user_data_store[user_id]['scenario']:
                    user_data_store[user_id]['scenario'].append('просыпаюсь разбитым')
            user_data_store[user_id]['vk_state'] = 'Q5'
            await self.api.send_message(
                int(user_id), Q5_TEXT, keyboard=self.simple_keyboard(dict.fromkeys(STRESS_OPTIONS, ''))
            )
        elif cmd.startswith('q5_'):
            idx = int(cmd.split('_')[1])
            answer = STRESS_OPTIONS[idx]
            user_data_store[user_id]['answers']['q5'] = answer
            if idx == 1:
                if 'днём высокий стресс' not in user_data_store[user_id]['scenario']:
                    user_data_store[user_id]['scenario'].append('днём высокий стресс')
            # Завершение онбординга
            user_data_store[user_id]['onboarding_complete'] = True
            user_data_store[user_id]['scenario'] = list(set(user_data_store[user_id]['scenario']))
            user_data_store[user_id]['vk_state'] = None
            await db.save_user(user_id, user_data_store[user_id])
            await db.save_user_stats(user_id, user_stats_store[user_id])
            await db.save_action(
                user_id,
                "onboarding",
                "completed",
                {
                    "scenario": user_data_store[user_id]['scenario'],
                    "age_group": user_data_store[user_id]['age_group'],
                    "occupation": user_data_store[user_id]['occupation'],
                },
            )
            final_message = (
                "🎉 Спасибо за ответы! "
                f"Твой сценарий: {', '.join(user_data_store[user_id]['scenario']) if user_data_store[user_id]['scenario'] else 'баланс'}.\n"
                f"📅 Утренние сообщения будут приходить в {user_data_store[user_id]['morning_time']}, "
                f"вечерние — в {user_data_store[user_id]['evening_time']}.\n\n"
                "🤖 Ты всегда можешь поговорить с AI-помощником. Напиши /ai.\n"
                "Я здесь, чтобы поддержать тебя каждый день! 🌟"
            )
            await self.api.send_message(int(user_id), final_message)

        # Обработка callback от планировщика (утро, вечер, день, чувства)
        elif cmd.startswith('morning_'):
            await self.morning_action_handler(user_id, cmd)
        elif cmd.startswith('morning_micro_'):
            await self.morning_micro_handler(user_id, cmd)
        elif cmd.startswith('evening_'):
            await self.evening_action_handler(user_id, cmd)
        elif cmd.startswith('feeling_'):
            await self.feeling_handler(user_id, cmd)
        elif cmd.startswith('day_stress_'):
            await self.day_stress_handler(user_id, cmd)
        else:
            logger.warning(f"Unhandled callback: {cmd}")

    # Обработчики свободного текста
    async def process_free_text(self, user_id, text):
        # Если пользователь в режиме AI-чата
        if user_data_store.get(user_id, {}).get('ai_chat_mode'):
            await self.ai_chat(user_id, text)
        else:
            # По умолчанию отвечаем с предложением начать или AI
            await self.api.send_message(
                int(user_id), "Напишите /ai, чтобы пообщаться с ИИ-помощником, или /start для начала."
            )

    async def start_ai_chat(self, user_id):
        user_data_store[user_id]['ai_chat_mode'] = True
        user_data_store[user_id]['ai_chat_session_id'] = str(uuid.uuid4())
        await self.api.send_message(
            int(user_id),
            "🤖 Режим общения с AI активирован! Задавай вопросы или делись переживаниями.\n/stop_ai - выйти.",
        )

    async def stop_ai_chat(self, user_id):
        user_data_store[user_id]['ai_chat_mode'] = False
        await self.api.send_message(int(user_id), "Режим AI завершён.")

    async def ai_chat(self, user_id, text):
        # Сохраняем сообщение пользователя в БД
        session_id = user_data_store[user_id]['ai_chat_session_id']
        await db.save_ai_chat_message(user_id, session_id, text, "user")
        # Определяем ситуацию
        from app.handler import detect_situation_from_text  # переиспользуем

        situation = detect_situation_from_text(text)
        user_data = user_data_store.get(user_id, {})
        advice = ai.generate_advice(user_context=text, situation=situation, user_data=user_data)
        await self.api.send_message(int(user_id), advice)
        await db.save_ai_chat_message(user_id, session_id, advice, "assistant", metadata={"situation": situation})

    # Обработчики callback от рассылок
    async def morning_action_handler(self, user_id, cmd):
        if cmd == 'morning_normal':
            text = "Рад слышать! Хорошего дня."
            user_stats_store[user_id]['morning_skip_streak'] = 0
            await db.save_action(user_id, "morning", "normal")
        elif cmd == 'morning_broken':
            user_data = user_data_store.get(user_id, {})
            advice = ai.generate_advice(
                user_context="Пользователь проснулся разбитым", situation='morning', user_data=user_data
            )
            if 'просыпаюсь разбитым' in user_data.get('scenario', []):
                text = f"Жаль. {advice}\n\nПопробуй сейчас просто встать, подойти к окну и сделать 5 глубоких вдохов."
                await self.api.send_message(
                    int(user_id),
                    text,
                    keyboard=self.simple_keyboard(
                        {"✅ Сделал(а)": "morning_micro_done", "⏰ Отложить": "morning_micro_later"}
                    ),
                )
                await db.save_action(user_id, "morning", "broken_with_scenario")
                return
            else:
                text = f"Жаль. {advice}"
                await db.save_action(user_id, "morning", "broken_without_scenario")
        elif cmd == 'morning_unknown':
            text = "Хорошо, понаблюдай за собой. Если будет нужна поддержка, я рядом."
            await db.save_action(user_id, "morning", "unknown")
        else:
            return
        await self.api.send_message(int(user_id), text)

    async def morning_micro_handler(self, user_id, cmd):
        today = datetime.now().date()
        if cmd == 'morning_micro_done':
            user_stats_store[user_id]['morning_streak'] = user_stats_store[user_id].get('morning_streak', 0) + 1
            user_stats_store[user_id]['morning_skip_streak'] = 0
            user_stats_store[user_id]['last_action_date']['morning'] = today
            await db.save_action(user_id, "micro", "done")
            await self.api.send_message(int(user_id), "Отлично! Маленький шаг сделан. Так держать!")
        elif cmd == 'morning_micro_later':
            user_stats_store[user_id]['morning_skip_streak'] = (
                user_stats_store[user_id].get('morning_skip_streak', 0) + 1
            )
            user_stats_store[user_id]['morning_streak'] = 0
            user_stats_store[user_id]['last_action_date']['morning'] = today
            await db.save_action(user_id, "micro", "skipped")
            await self.api.send_message(int(user_id), "Хорошо, можешь вернуться к этому позже. Я напомню завтра.")
        await db.save_user_stats(user_id, user_stats_store[user_id])

    async def evening_action_handler(self, user_id, cmd):
        today = datetime.now().date()
        if cmd == 'evening_do':
            user_stats_store[user_id]['evening_streak'] = user_stats_store[user_id].get('evening_streak', 0) + 1
            user_stats_store[user_id]['evening_skip_streak'] = 0
            user_stats_store[user_id]['last_action_date']['evening'] = today
            await db.save_action(user_id, "evening", "do")
            text = "Отлично! Маленький шаг запланирован."
        elif cmd == 'evening_not_now':
            user_stats_store[user_id]['evening_skip_streak'] = (
                user_stats_store[user_id].get('evening_skip_streak', 0) + 1
            )
            user_stats_store[user_id]['evening_streak'] = 0
            user_stats_store[user_id]['last_action_date']['evening'] = today
            await db.save_action(user_id, "evening", "not_now")
            text = "Хорошо, в другой раз."
        await db.save_user_stats(user_id, user_stats_store[user_id])
        await self.api.send_message(int(user_id), text)
        # Следом вопрос о настроении
        await self.api.send_message(
            int(user_id),
            "И напоследок: как ты сейчас себя чувствуешь?",
            keyboard=self.simple_keyboard(
                {
                    "🙂 Спокойно": "feeling_calm",
                    "😕 Напряжён(а)": "feeling_stressed",
                    "😔 Грустно": "feeling_sad",
                    "😩 Очень плохо": "feeling_bad",
                }
            ),
        )

    async def feeling_handler(self, user_id, cmd):
        feeling_map = {
            "feeling_calm": "Спокойно",
            "feeling_stressed": "Напряжён(а)",
            "feeling_sad": "Грустно",
            "feeling_bad": "Очень плохо",
        }
        feeling = feeling_map.get(cmd, "Неизвестно")
        if 'mood_history' not in user_data_store[user_id]:
            user_data_store[user_id]['mood_history'] = []
        user_data_store[user_id]['mood_history'].append({'date': datetime.now().isoformat(), 'feeling': feeling})
        await db.save_mood(user_id, feeling)
        await db.save_action(user_id, "feeling", cmd)
        await self.api.send_message(int(user_id), f"Спасибо, что поделился. Записал: {feeling}")
        if feeling in ['Напряжён(а)', 'Грустно', 'Очень плохо']:
            advice = ai.generate_advice(
                user_context=f"Настроение: {feeling}",
                situation='stress' if feeling == 'Напряжён(а)' else 'sad',
                user_data=user_data_store.get(user_id, {}),
            )
            await self.api.send_message(int(user_id), f"💡 {advice}")
            await self.api.send_message(
                int(user_id), "Если чувствуешь напряжение, можешь рассказать мне об этом в режиме /ai."
            )

    async def day_stress_handler(self, user_id, cmd):
        today = datetime.now().date()
        if cmd == 'day_stress_done':
            user_stats_store[user_id]['day_stress_streak'] = user_stats_store[user_id].get('day_stress_streak', 0) + 1
            user_stats_store[user_id]['day_stress_skip_streak'] = 0
            user_stats_store[user_id]['last_action_date']['day_stress'] = today
            await db.save_action(user_id, "stress", "done")
            text = "Отлично! Микро-пауза помогает перезагрузиться."
        elif cmd == 'day_stress_skip':
            user_stats_store[user_id]['day_stress_skip_streak'] = (
                user_stats_store[user_id].get('day_stress_skip_streak', 0) + 1
            )
            user_stats_store[user_id]['day_stress_streak'] = 0
            user_stats_store[user_id]['last_action_date']['day_stress'] = today
            await db.save_action(user_id, "stress", "skipped")
            text = "Понимаю. Если будет возможность, просто подыши глубоко пару раз."
        await db.save_user_stats(user_id, user_stats_store[user_id])
        await self.api.send_message(int(user_id), text)
