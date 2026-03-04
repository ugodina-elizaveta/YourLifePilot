import logging
import os

# Hugging Face Transformers
from transformers import pipeline

logger = logging.getLogger(__name__)


class HuggingFaceAI:
    """Класс для работы с AI моделями через Hugging Face"""

    def __init__(self):
        self.device = -1  # Используем CPU
        self.models = {}
        self.token = os.getenv("HF_TOKEN")  # Получаем токен из .env
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
                max_new_tokens=100,  # ВАЖНО: используем max_new_tokens вместо max_length
                temperature=0.7,
            )
            logger.info("✅ Модель генерации текста загружена")

            # 3. Модель для классификации эмоций (с токеном!)
            if self.token:
                self.models['emotion'] = pipeline(
                    "text-classification",
                    model="seara/rubert-tiny2-ru-go-emotions",
                    device=self.device,
                    token=self.token,  # Передаем токен для доступа
                )
                logger.info("✅ Модель определения эмоций загружена")
            else:
                logger.warning("⚠️ HF_TOKEN не найден, модель эмоций не загружена")
                self.models['emotion'] = self._create_mock_emotion_model()

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки моделей: {e}")
            # Заглушки для тестирования
            self._load_fallback_models()

    def _create_mock_emotion_model(self):
        """Создает заглушку для модели эмоций"""

        class MockEmotionModel:
            def __call__(self, text):
                return [{'label': 'neutral', 'score': 0.8}]

        return MockEmotionModel()

    def _load_fallback_models(self):
        """Заглушки для тестирования если модели не загрузились"""
        logger.warning("⚠️ Используются заглушки вместо реальных моделей")

        class MockModel:
            def __call__(self, text, **kwargs):  # Добавляем **kwargs для совместимости
                return [{'label': 'neutral', 'score': 0.8}]

        self.models = {'sentiment': MockModel(), 'emotion': MockModel(), 'generation': MockModel()}

    # =================================================
    # АНАЛИЗ НАСТРОЕНИЯ
    # =================================================

    def analyze_sentiment(self, text: str) -> dict:
        """Анализирует тональность текста"""
        try:
            result = self.models['sentiment'](text)[0]
            return {'label': result['label'], 'score': round(result['score'], 3)}
        except Exception as e:
            logger.error(f"Ошибка анализа тональности: {e}")
            return {'label': 'neutral', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        """Определяет конкретную эмоцию"""
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
        """Генерирует персонализированный совет"""
        try:
            prompt = self._create_advice_prompt(user_context, situation)

            # ВАЖНО: используем правильные параметры
            result = self.models['generation'](
                prompt,
                max_new_tokens=100,  # вместо max_length
                temperature=0.8,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                pad_token_id=50256,  # для GPT2
            )[0]['generated_text']

            # Убираем промпт из результата
            advice = result.replace(prompt, '').strip()
            return advice if advice else self._get_fallback_advice(situation)

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
            'stress': "Попробуй сделать глубокий вдох на 4 счета, задержать дыхание на 4, выдохнуть на 6. Повтори 5 раз.",
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
        """Анализирует тренд настроений"""
        if not mood_history or len(mood_history) < 3:
            return {'trend': 'insufficient_data', 'message': 'Нужно больше данных', 'average': 2.5}

        # Преобразуем эмоции в числа
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

        # Анализируем тренд
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


# Создаем глобальный экземпляр
ai = HuggingFaceAI()
