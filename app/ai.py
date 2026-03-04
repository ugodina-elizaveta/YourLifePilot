import logging

import numpy as np
import torch
# Hugging Face Transformers
from transformers import pipeline

logger = logging.getLogger(__name__)


class HuggingFaceAI:
    """Класс для работы с AI моделями через Hugging Face"""

    def __init__(self):
        self.device = 0 if torch.cuda.is_available() else -1
        self.models = {}
        self.tokenizers = {}
        self.load_models()

    def load_models(self):
        """Загружает все необходимые модели"""
        try:
            logger.info("🤖 Загрузка AI моделей...")

            # 1. Модель для анализа тональности (русский язык)
            self.models['sentiment'] = pipeline(
                "sentiment-analysis", model="blanchefort/rubert-base-cased-sentiment", device=self.device
            )
            logger.info("✅ Модель анализа тональности загружена")

            # 2. Модель для генерации текста (русский язык)
            self.models['generation'] = pipeline(
                "text-generation",
                model="ai-forever/rugpt3small_based_on_gpt2",
                device=self.device,
                max_length=100,
                temperature=0.7,
            )
            logger.info("✅ Модель генерации текста загружена")

            # 3. Модель для классификации эмоций
            self.models['emotion'] = pipeline(
                "text-classification", model="seara/rubert-tiny2-russian-emotion-detection", device=self.device
            )
            logger.info("✅ Модель определения эмоций загружена")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки моделей: {e}")
            # Заглушки для тестирования
            self._load_fallback_models()

    def _load_fallback_models(self):
        """Заглушки для тестирования если модели не загрузились"""
        logger.warning("⚠️ Используются заглушки вместо реальных моделей")

        class MockModel:
            def __call__(self, text):
                return [{'label': 'neutral', 'score': 0.8}]

        self.models = {'sentiment': MockModel(), 'emotion': MockModel(), 'generation': MockModel()}

    # =================================================
    # АНАЛИЗ НАСТРОЕНИЯ
    # =================================================

    def analyze_sentiment(self, text: str) -> dict:
        """
        Анализирует тональность текста
        Возвращает: {'label': 'positive/negative/neutral', 'score': 0.95}
        """
        try:
            result = self.models['sentiment'](text)[0]
            return {'label': result['label'], 'score': round(result['score'], 3)}
        except Exception as e:
            logger.error(f"Ошибка анализа тональности: {e}")
            return {'label': 'neutral', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        """
        Определяет конкретную эмоцию
        Возвращает: {'label': 'joy/sadness/anger/fear', 'score': 0.9}
        """
        try:
            result = self.models['emotion'](text)[0]
            return {'label': result['label'], 'score': round(result['score'], 3)}
        except Exception as e:
            logger.error(f"Ошибка определения эмоции: {e}")
            return {'label': 'neutral', 'score': 0.5}

    # =================================================
    # ГЕНЕРАЦИЯ СОВЕТОВ
    # =================================================

    def generate_advice(self, user_context: str, situation: str) -> str:
        """
        Генерирует персонализированный совет
        """
        try:
            prompt = self._create_advice_prompt(user_context, situation)

            result = self.models['generation'](
                prompt, max_length=150, temperature=0.8, do_sample=True, top_k=50, top_p=0.95
            )[0]['generated_text']

            # Убираем промпт из результата
            advice = result.replace(prompt, '').strip()
            return advice

        except Exception as e:
            logger.error(f"Ошибка генерации совета: {e}")
            return self._get_fallback_advice(situation)

    def _create_advice_prompt(self, user_context: str, situation: str) -> str:
        """Создает промпт для генерации совета"""
        prompts = {
            'stress': f"Пользователь испытывает стресс. {user_context} Дай короткий, теплый совет как успокоиться:",
            'sleep': f"У пользователя проблемы со сном. {user_context} Посоветуй что-то простое для лучшего сна:",
            'sad': f"Пользователь грустит. {user_context} Поддержи его теплыми словами:",
            'morning': f"Утро. {user_context} Дай совет как начать день бодро:",
            'evening': f"Вечер. {user_context} Посоветуй как расслабиться перед сном:",
            'general': f"{user_context} Дай дружеский совет:",
        }
        return prompts.get(situation, prompts['general'])

    def _get_fallback_advice(self, situation: str) -> str:
        """Запасные советы если AI не работает"""
        fallback = {
            'stress': "Попробуй сделать глубокий вдох и медленный выдох. Повтори 5 раз.",
            'sleep': "Постарайся лечь спать в одно и то же время. Это помогает настроить биоритмы.",
            'sad': "Разреши себе погрустить немного. Это нормально. Завтра будет новый день.",
            'morning': "Начни утро со стакана теплой воды. Это помогает проснуться.",
            'evening': "Попробуй за час до сна убрать телефон и почитать книгу.",
            'general': "Маленькие шаги каждый день приводят к большим изменениям.",
        }
        return fallback.get(situation, fallback['general'])

    # =================================================
    # АНАЛИЗ ИСТОРИИ НАСТРОЕНИЙ
    # =================================================

    def analyze_mood_trend(self, mood_history: list[dict]) -> dict:
        """
        Анализирует тренд настроений
        """
        if not mood_history or len(mood_history) < 3:
            return {'trend': 'insufficient_data', 'message': 'Нужно больше данных'}

        # Преобразуем эмоции в числа
        mood_values = []
        for entry in mood_history[-7:]:  # последние 7 дней
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

        # Анализируем тренд
        if len(mood_values) >= 3:
            first_avg = np.mean(mood_values[:3])
            last_avg = np.mean(mood_values[-3:])

            if last_avg > first_avg + 0.5:
                trend = 'improving'
                message = "Твоё настроение улучшается! 🌟"
            elif last_avg < first_avg - 0.5:
                trend = 'worsening'
                message = "Последнее время тебе тяжело. Я рядом 🤗"
            else:
                trend = 'stable'
                message = "Настроение стабильное. Хороший знак!"

            return {
                'trend': trend,
                'message': message,
                'average': round(np.mean(mood_values), 2),
                'trend_strength': round(last_avg - first_avg, 2),
            }

        return {'trend': 'stable', 'message': 'Продолжай в том же духе!'}


# Создаем глобальный экземпляр
ai = HuggingFaceAI()
