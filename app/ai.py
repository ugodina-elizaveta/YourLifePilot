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
                "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": 150},
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
            # Пробуем альтернативный URL
            return self._try_alternative_url(user_context, situation)
        except requests.Timeout:
            logger.error("❌ Таймаут при запросе к YandexGPT")
            return self.fallback_advice.get(situation, self.fallback_advice['general'])
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

    def _try_alternative_url(self, user_context: str, situation: str) -> str:
        """Пробует альтернативный URL если основной не работает"""
        try:
            alt_url = "https://llm.api.ai-studio.yandex.net/foundationModels/v1/completion"
            logger.info(f"🔄 Пробую альтернативный URL: {alt_url}")

            system_prompt = self.situation_prompts.get(situation, self.situation_prompts['general'])
            user_prompt = user_context if user_context else "Дай совет"

            payload = {
                "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
                "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": 150},
                "messages": [{"role": "system", "text": system_prompt}, {"role": "user", "text": user_prompt}],
            }

            response = requests.post(
                alt_url,
                headers={"Authorization": f"Api-Key {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                advice = result['result']['alternatives'][0]['message']['text'].strip()
                logger.info(f"✅ Альтернативный URL сработал: {advice[:100]}...")
                return advice
            else:
                logger.error(f"❌ Альтернативный URL тоже не работает: {response.status_code}")
                return self.fallback_advice.get(situation, self.fallback_advice['general'])

        except Exception as e:
            logger.error(f"❌ Альтернативный URL тоже не работает: {e}")
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

    # Заглушки для совместимости
    def analyze_sentiment(self, text: str) -> dict:
        return {'label': 'NEUTRAL', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        return {'label': 'neutral', 'score': 0.5}

    def analyze_mood_trend(self, mood_history: list[dict]) -> dict:
        # ... (код функции analyze_mood_trend) ...
        # Оставьте как было
        pass


ai = YandexGPTAI()
