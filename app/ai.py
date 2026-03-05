import logging
import os
import random

# Hugging Face Transformers
from transformers import pipeline, set_seed

logger = logging.getLogger(__name__)


class HuggingFaceAI:
    """Класс для работы с AI моделями через Hugging Face"""

    def __init__(self):
        self.device = -1  # Используем CPU
        self.models = {}
        self.token = os.getenv("HF_TOKEN")
        set_seed(42)  # Для воспроизводимости
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

            # 2. Модель для генерации текста - ВОЗВРАЩАЕМСЯ К ДИАЛОГОВОЙ, НО С ПРАВИЛЬНЫМ ФОРМАТОМ
            model_name = "tinkoff-ai/ruDialoGPT-small"

            # Загружаем модель отдельно, чтобы контролировать параметры
            from transformers import AutoTokenizer, AutoModelForCausalLM

            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(model_name)

            self.models['generation'] = {'model': model, 'tokenizer': tokenizer}
            logger.info(f"✅ Модель генерации текста загружена: {model_name}")

            # 3. Модель для классификации эмоций
            if self.token:
                self.models['emotion'] = pipeline(
                    "text-classification",
                    model="seara/rubert-tiny2-ru-go-emotions",
                    device=self.device,
                    token=self.token,
                )
                logger.info("✅ Модель определения эмоций загружена")
            else:
                logger.warning("⚠️ HF_TOKEN не найден, модель эмоций не загружена")
                self.models['emotion'] = self._create_mock_emotion_model()

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки моделей: {e}")
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
            def __call__(self, text, **kwargs):
                return [{'label': 'neutral', 'score': 0.8}]

        self.models = {'sentiment': MockModel(), 'emotion': MockModel(), 'generation': MockModel()}

    def analyze_sentiment(self, text: str) -> dict:
        """Анализирует тональность текста"""
        try:
            result = self.models['sentiment'](text)[0]
            return {'label': result['label'], 'score': round(result['score'], 3)}
        except Exception as e:
            logger.error(f"Ошибка анализа тональности: {e}")
            return {'label': 'NEUTRAL', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        """Определяет конкретную эмоцию"""
        try:
            result = self.models['emotion'](text)[0]
            return {'label': result['label'], 'score': round(result['score'], 3)}
        except Exception as e:
            logger.error(f"Ошибка определения эмоции: {e}")
            return {'label': 'neutral', 'score': 0.5}

    def generate_advice(self, user_context: str, situation: str) -> str:
        """Генерирует персонализированный совет"""
        try:
            prompt = self._create_advice_prompt(user_context, situation)

            # Получаем модель и токенизатор
            model_data = self.models['generation']
            if isinstance(model_data, dict) and 'model' in model_data and 'tokenizer' in model_data:
                model = model_data['model']
                tokenizer = model_data['tokenizer']

                # Токенизируем вход
                inputs = tokenizer(prompt, return_tensors="pt")

                # Генерируем
                outputs = model.generate(
                    inputs.input_ids,
                    max_new_tokens=50,
                    temperature=0.8,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                )

                # Декодируем
                advice = tokenizer.decode(outputs[0], skip_special_tokens=True)

                # Убираем промпт
                advice = advice.replace(prompt, '').strip()
            else:
                # Если модель в формате pipeline
                result = model_data(prompt, max_new_tokens=50, temperature=0.8, do_sample=True)[0]
                advice = result['generated_text'].replace(prompt, '').strip()

            # Проверяем качество
            if not advice or len(advice) < 10:
                return self._get_fallback_advice(situation)

            # Очищаем от мусора
            if any(x in advice for x in ['@@', 'ПЕРВЫЙ', 'ВТОРОЙ', 'ТРЕТИЙ']):
                return self._get_fallback_advice(situation)

            logger.info(f"✅ AI сгенерировал совет для ситуации '{situation}': {advice[:50]}...")
            return advice

        except Exception as e:
            logger.error(f"Ошибка генерации совета: {e}")
            return self._get_fallback_advice(situation)

    def _create_advice_prompt(self, user_context: str, situation: str) -> str:
        """Создает промпт для генерации совета"""
        prompts = {
            'stress': "Дай короткий, добрый совет человеку, который испытывает стресс:",
            'sleep': "Посоветуй что-то простое для лучшего сна:",
            'sad': "Поддержи человека, который грустит, тёплыми словами:",
            'morning': "Дай совет как начать день бодро и позитивно:",
            'evening': "Посоветуй как расслабиться перед сном:",
            'general': "Дай дружеский совет:",
        }
        return prompts.get(situation, prompts['general'])

    def _get_fallback_advice(self, situation: str) -> str:
        """Запасные советы если AI не работает"""
        fallback = {
            'stress': "Попробуй сделать глубокий вдох на 4 счета, задержать дыхание на 4, выдохнуть на 6. Повтори 5 раз. Это помогает успокоиться.",
            'sleep': "Постарайся лечь спать в одно и то же время. За час до сна убери телефон и почитай книгу.",
            'sad': "Разреши себе погрустить немного. Это нормально. Помни, что плохие дни всегда проходят.",
            'morning': "Начни утро со стакана тёплой воды. Сделай лёгкую зарядку и улыбнись новому дню.",
            'evening': "Попробуй за час до сна убрать телефон и почитать книгу. Тёплый душ тоже помогает расслабиться.",
            'general': "Будь к себе добрее. Маленькие шаги каждый день приводят к большим изменениям.",
        }
        return fallback.get(situation, fallback['general'])

    def analyze_mood_trend(self, mood_history: list[dict]) -> dict:
        """Анализирует тренд настроений"""
        if not mood_history or len(mood_history) < 3:
            return {'trend': 'insufficient_data', 'message': 'Нужно больше данных для анализа', 'average': 2.5}

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
