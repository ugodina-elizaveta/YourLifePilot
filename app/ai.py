import logging
import os
import requests  # меняем aiohttp на requests (синхронный)
from datetime import datetime

logger = logging.getLogger(__name__)


class YandexGPTAI:
    """Класс для работы с YandexGPT API (синхронная версия)"""

    def __init__(self):
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.url = "https://api.ai-studio.yandex.net/v1/chat/completions"

        self.requests_today = 0
        self.last_reset = datetime.now().date()

        self.situation_prompts = {
            'stress': "Ты - дружелюбный помощник по психологическому здоровью. Дай короткий, тёплый совет человеку, который испытывает стресс. Ответ должен быть 2-3 предложения, на русском языке.",
            'sleep': "Ты - дружелюбный помощник по сну. Посоветуй простые способы, как улучшить сон. Ответ должен быть 2-3 предложения, на русском языке.",
            'sad': "Ты - поддерживающий друг. Поддержи человека, которому грустно, тёплыми словами. Ответ должен быть 2-3 предложения, на русском языке.",
            'morning': "Ты - эксперт по утренним ритуалам. Дай совет, как начать день бодро и позитивно. Ответ должен быть 2-3 предложения, на русском языке.",
            'evening': "Ты - эксперт по релаксации. Посоветуй, как расслабиться вечером перед сном. Ответ должен быть 2-3 предложения, на русском языке.",
            'general': "Ты - дружелюбный помощник. Дай короткий, полезный совет человеку, который обратился за поддержкой. Ответ должен быть 2-3 предложения, на русском языке.",
        }

        self.fallback_advice = {
            'stress': "Попробуй сделать глубокий вдох на 4 счета, задержать дыхание на 4, выдохнуть на 6. Повтори 5 раз. Это помогает успокоиться.",
            'sleep': "Постарайся ложиться спать в одно и то же время. За час до сна убери телефон и почитай книгу.",
            'sad': "Разреши себе погрустить немного. Это нормально. Помни, что плохие дни всегда проходят.",
            'morning': "Начни утро со стакана тёплой воды. Сделай лёгкую зарядку и улыбнись новому дню.",
            'evening': "Попробуй за час до сна убрать телефон и почитать книгу. Тёплый душ тоже помогает расслабиться.",
            'general': "Будь к себе добрее. Маленькие шаги каждый день приводят к большим изменениям.",
        }

        logger.info("✅ YandexGPT AI (синхронный) инициализирован")

    def _check_limit(self) -> bool:
        today = datetime.now().date()
        if today != self.last_reset:
            self.requests_today = 0
            self.last_reset = today
        if self.requests_today >= 1000:
            logger.warning("⚠️ Дневной лимит YandexGPT исчерпан (1000 запросов)")
            return False
        return True

    def generate_advice(self, user_context: str, situation: str) -> str:
        """Синхронная версия генерации совета"""
        if not self._check_limit():
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

        if not self.api_key:
            logger.error("❌ YANDEX_API_KEY не настроен")
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

        try:
            system_prompt = self.situation_prompts.get(situation, self.situation_prompts['general'])
            user_prompt = user_context if user_context else "Дай совет"

            payload = {
                "model": "yandexgpt/latest",
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "temperature": 0.6,
                "max_tokens": 150,
            }

            logger.info(f"🤖 Запрос к YandexGPT для ситуации '{situation}'")

            response = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )

            self.requests_today += 1
            logger.info(f"📊 Запросов сегодня: {self.requests_today}/1000")

            if response.status_code == 200:
                result = response.json()
                advice = result['choices'][0]['message']['content'].strip()
                logger.info(f"✅ YandexGPT ответил: {advice[:100]}...")
                return advice
            else:
                logger.error(f"❌ Ошибка YandexGPT API: {response.status_code} - {response.text}")
                return self.fallback_advice.get(situation, self.fallback_advice['general'])

        except requests.Timeout:
            logger.error("❌ Таймаут при запросе к YandexGPT")
            return self.fallback_advice.get(situation, self.fallback_advice['general'])
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

    def analyze_sentiment(self, text: str) -> dict:
        return {'label': 'NEUTRAL', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        return {'label': 'neutral', 'score': 0.5}

    def analyze_mood_trend(self, mood_history: list[dict]) -> dict:
        # Оставляем как было
        if not mood_history or len(mood_history) < 3:
            return {'trend': 'insufficient_data', 'message': 'Нужно больше данных для анализа', 'average': 2.5}

        mood_values = []
        for entry in mood_history[-7:]:
            feeling = entry.get('feeling', '')
            if feeling == 'Спокойно':
                mood_values.append(4)
            elif feeling == 'Напряжён(а)':
                mood_values.append(3)
            elif feeling == 'Грустно':
                mood_values.append(2)
            elif feeling == 'Очень плохо':
                mood_values.append(1)
            else:
                mood_values.append(2.5)

        if len(mood_values) >= 3:
            first_avg = sum(mood_values[:3]) / 3
            last_avg = sum(mood_values[-3:]) / 3

            if last_avg > first_avg + 0.5:
                trend = 'improving'
                message = "Твоё настроение улучшается! Так держать! 🌟"
            elif last_avg < first_avg - 0.5:
                trend = 'worsening'
                message = "Последнее время тебе тяжело. Помни, что я рядом и всегда готов поддержать 🤗"
            else:
                trend = 'stable'
                message = "Настроение стабильное. Это хороший знак!"

            return {
                'trend': trend,
                'message': message,
                'average': round(sum(mood_values) / len(mood_values), 2),
                'trend_strength': round(last_avg - first_avg, 2),
            }

        return {'trend': 'stable', 'message': 'Продолжай в том же духе!', 'average': 2.5}


ai = YandexGPTAI()
