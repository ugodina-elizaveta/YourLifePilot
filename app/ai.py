import logging
import os
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class YandexGPTAI:
    """Класс для работы с YandexGPT API (проверенный URL)"""

    def __init__(self):
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID")

        # ПРОВЕРЕННЫЙ URL Yandex Cloud (не AI Studio)
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        self.requests_today = 0
        self.last_reset = datetime.now().date()

        self.situation_prompts = {
            'stress': "Ты - дружелюбный помощник по психологическому здоровью. Человек испытывает стресс. Дай ему короткий, практический совет, как успокоиться прямо сейчас. Ответ должен быть 2-3 предложения, начинай с конкретного действия.",
            'sleep': "Ты - эксперт по сну. Человек спрашивает про сон. Дай конкретный, полезный совет, как улучшить качество сна или быстрее заснуть. Ответ должен быть 2-3 предложения.",
            'sad': "Ты - поддерживающий друг. Человеку грустно. Поддержи его тёплыми, ободряющими словами, дай простой совет, как поднять настроение. Ответ должен быть 2-3 предложения.",
            'morning': "Ты - эксперт по утренним ритуалам. Человек интересуется утром. Посоветуй, как начать день бодро и энергично. Ответ должен быть 2-3 предложения.",
            'evening': "Ты - эксперт по релаксации. Человек спрашивает про вечер или сон. Посоветуй, как расслабиться вечером и подготовиться ко сну. Ответ должен быть 2-3 предложения.",
            'general': "Ты - дружелюбный помощник. Дай короткий, полезный и разнообразный совет человеку. Ответ должен быть 2-3 предложения. Старайся не повторять одни и те же фразы в разных ответах.",
        }

        self.fallback_advice = {
            'stress': "Попробуй сделать глубокий вдох на 4 счета, задержать дыхание на 4, выдохнуть на 6. Повтори 5 раз. Это помогает успокоиться.",
            'sleep': "Постарайся ложиться спать в одно и то же время. За час до сна убери телефон и почитай книгу.",
            'sad': "Разреши себе погрустить немного. Это нормально. Помни, что плохие дни всегда проходят.",
            'morning': "Начни утро со стакана тёплой воды. Сделай лёгкую зарядку и улыбнись новому дню.",
            'evening': "Попробуй за час до сна убрать телефон и почитать книгу. Тёплый душ тоже помогает расслабиться.",
            'general': "Будь к себе добрее. Маленькие шаги каждый день приводят к большим изменениям.",
        }

        logger.info("✅ YandexGPT AI инициализирован")

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
        """Генерирует совет через YandexGPT API"""
        if not self._check_limit():
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

        if not self.api_key or not self.folder_id:
            logger.error("❌ YANDEX_API_KEY или YANDEX_FOLDER_ID не настроены")
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

        try:
            system_prompt = self.situation_prompts.get(situation, self.situation_prompts['general'])
            user_prompt = user_context if user_context else "Дай совет"

            # Формируем запрос для Yandex Cloud API
            payload = {
                "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
                "completionOptions": {"stream": False, "temperature": 0.8, "maxTokens": 150},
                "messages": [{"role": "system", "text": system_prompt}, {"role": "user", "text": user_prompt}],
            }

            logger.info(f"🤖 Запрос к YandexGPT для ситуации '{situation}'")

            response = requests.post(
                self.url,
                headers={"Authorization": f"Api-Key {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )

            self.requests_today += 1
            logger.info(f"📊 Запросов сегодня: {self.requests_today}/1000")

            if response.status_code == 200:
                result = response.json()
                advice = result['result']['alternatives'][0]['message']['text'].strip()
                logger.info(f"✅ YandexGPT ответил: {advice[:100]}...")
                return advice
            else:
                logger.error(f"❌ Ошибка YandexGPT API: {response.status_code} - {response.text}")
                return self.fallback_advice.get(situation, self.fallback_advice['general'])

        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Ошибка подключения: {e}")
        except requests.Timeout:
            logger.error("❌ Таймаут при запросе к YandexGPT")
            return self.fallback_advice.get(situation, self.fallback_advice['general'])
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

    # Заглушки для совместимости
    def analyze_sentiment(self, text: str) -> dict:
        return {'label': 'NEUTRAL', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        return {'label': 'neutral', 'score': 0.5}

    def analyze_mood_trend(self, mood_history: list[dict]) -> dict:
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


# Создаём экземпляр
ai = YandexGPTAI()
