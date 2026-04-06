import logging
import os
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class YandexGPTAI:
    """Класс для работы с YandexGPT API с поддержкой персонализации"""

    def __init__(self):
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID")
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        self.requests_today = 0
        self.last_reset = datetime.now().date()

        # Категории для разных ситуаций
        self.situation_prompts = {
            'stress': "Дай короткий, добрый, практический совет как справиться со стрессом. Учти возраст и образ жизни.",
            'sleep': "Посоветуй что-то простое для улучшения сна. Учти возраст и образ жизни.",
            'sad': "Поддержи тёплыми словами, дай простой совет поднять настроение. Учти возраст.",
            'morning': "Дай совет как начать день бодро и позитивно. Учти возраст и чем человек занимается.",
            'evening': "Посоветуй как расслабиться вечером перед сном. Учти возраст и занятия.",
            'general': "Дай короткий, полезный, добрый совет. Учти возраст и образ жизни.",
        }

        # Fallback советы на случай ошибок
        self.fallback_advice = {
            'stress': "Попробуй сделать глубокий вдох на 4 счета, задержать дыхание на 4, выдохнуть на 6. Повтори 5 раз. Это помогает успокоиться.",
            'sleep': "Постарайся ложиться спать в одно и то же время. За час до сна убери телефон и почитай книгу.",
            'sad': "Разреши себе погрустить немного. Это нормально. Помни, что плохие дни всегда проходят.",
            'morning': "Начни утро со стакана тёплой воды. Сделай лёгкую зарядку и улыбнись новому дню.",
            'evening': "Попробуй за час до сна убрать телефон и почитать книгу. Тёплый душ тоже помогает расслабиться.",
            'general': "Будь к себе добрее. Маленькие шаги каждый день приводят к большим изменениям.",
        }

        logger.info("✅ YandexGPT AI инициализирован (с поддержкой персонализации)")

    def _check_limit(self) -> bool:
        """Проверяет, не превышен ли дневной лимит"""
        today = datetime.now().date()
        if today != self.last_reset:
            self.requests_today = 0
            self.last_reset = today
        if self.requests_today >= 1000:
            logger.warning("⚠️ Дневной лимит YandexGPT исчерпан (1000 запросов)")
            return False
        return True

    def _get_personal_info(self, user_data: dict = None) -> str:
        """
        Формирует строку с информацией о пользователе для персонализации советов
        """
        if not user_data:
            return ""

        age = user_data.get('age_group', '')
        occupation = user_data.get('occupation', '')
        scenario = user_data.get('scenario', [])

        parts = []

        # Возраст
        age_map = {
            "До 18": "подросток",
            "18–24": "молодой человек",
            "25–34": "человек в активном возрасте",
            "35–44": "человек среднего возраста",
            "45+": "человек старшего возраста",
        }

        if age in age_map:
            parts.append(age_map[age])
        elif age:
            parts.append(f"возраст {age}")

        # Занятие
        occ_map = {
            "Учусь": "студент",
            "Работаю": "работающий",
            "Работаю и учусь": "работающий студент",
            "Не учусь и не работаю": "в поиске себя",
        }

        if occupation in occ_map:
            parts.append(occ_map[occupation])
        elif occupation:
            parts.append(occupation.lower())

        # Сценарии (кратко)
        if "ложусь поздно" in scenario:
            parts.append("склонен(на) ложиться поздно")
        if "просыпаюсь разбитым" in scenario:
            parts.append("часто просыпается разбитым")
        if "днём высокий стресс" in scenario:
            parts.append("испытывает стресс днём")

        if not parts:
            return ""

        return "Ты " + ", ".join(parts) + ". "

    def _get_physical_info(self, user_data: dict = None) -> str:
        """Формирует строку с информацией о физических ограничениях"""
        if not user_data:
            return ""

        physical_limits = user_data.get('physical_limits', '')
        if not physical_limits or physical_limits == "Без ограничений":
            return ""

        return (
            f"ВАЖНО: У пользователя есть ограничения: {physical_limits}. "
            "НЕ рекомендуй физические упражнения, бег, интенсивные нагрузки. "
            "Предлагай только безопасные практики: глубокое медленное дыхание, лёгкая растяжка сидя."
        )

    def generate_advice(self, user_context: str, situation: str, user_data: dict = None) -> str:
        """
        Генерирует персонализированный совет с учётом возраста и занятий
        """
        if not self._check_limit():
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

        if not self.api_key or not self.folder_id:
            logger.error("❌ YANDEX_API_KEY или YANDEX_FOLDER_ID не настроены")
            return self.fallback_advice.get(situation, self.fallback_advice['general'])

        try:
            # Получаем информацию о пользователе
            personal_info = self._get_personal_info(user_data)
            physical_info = self._get_physical_info(user_data)

            # Формируем полный промпт
            context_parts = []
            if personal_info:
                context_parts.append(personal_info)
            if physical_info:
                context_parts.append(physical_info)

            context_str = " ".join(context_parts)
            full_prompt = f"{context_str}{self.situation_prompts.get(situation)}"

            logger.info(f"🤖 Запрос к YandexGPT для ситуации '{situation}'")
            logger.debug(f"Промпт: {full_prompt[:200]}...")

            # Формируем запрос
            payload = {
                "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
                "completionOptions": {"stream": False, "temperature": 0.7, "maxTokens": 150},
                "messages": [
                    {"role": "system", "text": full_prompt},
                    {"role": "user", "text": user_context if user_context else "Дай совет"},
                ],
            }

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
            return self.fallback_advice.get(situation, self.fallback_advice['general'])
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
        """Анализирует тренд настроений"""
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
