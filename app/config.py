import os
from typing import Any

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Настройки БД
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "yourlifepilot")
DB_USER = os.getenv("DB_USER", "yourlifepilot_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Состояния для ConversationHandler
AGREEMENT, AGE, OCCUPATION, MORNING_TIME, EVENING_TIME, Q1, Q2, Q3, Q4, Q5 = range(10)

# Кэш для данных пользователей
user_data_store: dict[str, Any] = {}
user_stats_store: dict[str, Any] = {}

# --- НОВЫЕ ВОПРОСЫ ДЛЯ ОНБОРДИНГА ---
AGE_QUESTION = "👤 Выбери, пожалуйста, свою возрастную группу. Чтобы лучше подбирать советы."
AGE_OPTIONS = ["До 18", "18–24", "25–34", "35–44", "45+"]

OCCUPATION_QUESTION = "💼 Чем ты сейчас в основном занимаешься?"
OCCUPATION_OPTIONS = ["Учусь", "Работаю", "Работаю и учусь", "Не учусь и не работаю"]

MORNING_TIME_QUESTION = "⏰ Во сколько тебе удобнее получать **утренние** сообщения?"
MORNING_TIME_OPTIONS = ["07:00", "08:00", "09:00", "Не важно (09:00)"]

EVENING_TIME_QUESTION = "🌙 Во сколько тебе удобнее получать **вечерние** сообщения?"
EVENING_TIME_OPTIONS = ["21:00", "22:00", "23:00", "Не важно (21:00)"]

WELCOME_TEXT = (
    "Привет! Я YourLifePilot — цифровой помощник, который помогает наладить сон и чуть аккуратнее относиться к себе.\n\n"
    "Я не врач и не ставлю диагнозы, моя роль — напоминать о маленьких шагах, поддерживать и задавать простые вопросы, "
    "чтобы тебе было легче держать курс."
)

DISCLAIMER_TEXT = (
    "Важно: я не оказываю медицинскую помощь и не заменяю консультацию врача или психолога. "
    "Если у тебя есть серьёзные проблемы со здоровьем или самочувствием, лучше обратиться к специалисту.\n\n"
    "Если ты согласен(на) с этим и готов(а) продолжить, нажми кнопку ниже."
)

# Вопросы онбординга
Q1_TEXT = "Насколько ты в целом доволен(на) своим сном за последние две недели?"
Q2_TEXT = "Во сколько ты обычно хочешь ложиться спать?"
Q3_TEXT = "А во сколько ты на самом деле чаще всего засыпаешь?"
Q4_TEXT = "Как ты чаще всего просыпаешься?"
Q5_TEXT = "Когда чаще всего чувствуешь сильный стресс?"

# Варианты ответов
Q1_OPTIONS = ["1 – совсем недоволен(на)", "2", "3", "4", "5 – в целом доволен(на)"]
TIME_OPTIONS = ["До 22:00", "22:00–23:00", "23:00–00:00", "После полуночи"]
WAKE_OPTIONS = ["Бодрым(ой)", "Так себе, средне", "Разбитым(ой)"]
STRESS_OPTIONS = ["Утром", "Днём", "Вечером", "Скорее равномерно в течение дня"]

# Настройки webhook
SERVER_IP = "185.185.142.217"
SERVER_PORT = os.getenv("PORT", "8000")
WEBHOOK_PATH = "/webhook"
FULL_WEBHOOK_URL = f"https://{SERVER_IP}{WEBHOOK_PATH}"
