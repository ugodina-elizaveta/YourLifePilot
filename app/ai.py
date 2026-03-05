import logging
import os
import random

from transformers import pipeline, set_seed

logger = logging.getLogger(__name__)


class HuggingFaceAI:
    def __init__(self):
        self.device = -1
        self.models = {}
        self.token = os.getenv("HF_TOKEN")
        set_seed(42)
        self.load_models()

    def load_models(self):
        try:
            logger.info("🤖 Загрузка AI моделей...")

            # 1. Анализ тональности
            self.models['sentiment'] = pipeline(
                "sentiment-analysis", model="blanchefort/rubert-base-cased-sentiment", device=self.device
            )
            logger.info("✅ Модель анализа тональности загружена")

            # 2. Генерация текста (используем pipeline с return_full_text=False)
            self.models['generation'] = pipeline(
                "text-generation",
                model="tinkoff-ai/ruDialoGPT-small",
                device=self.device,
                max_new_tokens=60,
                temperature=0.8,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.2,
                pad_token_id=50256,
                return_full_text=False,  # ВАЖНО! Не возвращать промпт
            )
            logger.info("✅ Модель генерации текста загружена: tinkoff-ai/ruDialoGPT-small")

            # 3. Эмоции
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
            logger.error(f"❌ Ошибка загрузки моделей: {e}", exc_info=True)
            self._load_fallback_models()

    def _create_mock_emotion_model(self):
        class MockEmotionModel:
            def __call__(self, text):
                return [{'label': 'neutral', 'score': 0.8}]

        return MockEmotionModel()

    def _load_fallback_models(self):
        logger.warning("⚠️ Используются заглушки вместо реальных моделей")

        class MockModel:
            def __call__(self, text, **kwargs):
                return [{'label': 'neutral', 'score': 0.8}]

        self.models = {'sentiment': MockModel(), 'emotion': MockModel(), 'generation': MockModel()}

    def analyze_sentiment(self, text: str) -> dict:
        try:
            result = self.models['sentiment'](text)[0]
            return {'label': result['label'], 'score': round(result['score'], 3)}
        except Exception as e:
            logger.error(f"Ошибка анализа тональности: {e}")
            return {'label': 'NEUTRAL', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        try:
            result = self.models['emotion'](text)[0]
            return {'label': result['label'], 'score': round(result['score'], 3)}
        except Exception as e:
            logger.error(f"Ошибка определения эмоции: {e}")
            return {'label': 'neutral', 'score': 0.5}

    def generate_advice(self, user_context: str, situation: str) -> str:
        """Генерирует совет с контролем качества и fallback"""
        try:
            prompt = self._create_advice_prompt(user_context, situation)
            logger.info(f"🤖 Генерирую совет для ситуации '{situation}' с промптом: {prompt}")

            # Пытаемся получить ответ от модели
            result = self.models['generation'](prompt, max_new_tokens=60)[0]
            advice = result['generated_text'].strip()

            # Логируем сырой ответ
            logger.info(f"📝 Сырой ответ модели: {advice}")

            # Очистка от мусора
            if any(x in advice for x in ['@@', 'ПЕРВЫЙ', 'ВТОРОЙ', 'ТРЕТИЙ', 'Пользователь:', 'Помощник:']):
                logger.warning("Ответ содержит диалоговый мусор, использую fallback")
                return self._get_fallback_advice(situation)

            if len(advice) < 10:
                logger.warning("Слишком короткий ответ, использую fallback")
                return self._get_fallback_advice(situation)

            logger.info(f"✅ AI совет сгенерирован: {advice}")
            return advice

        except Exception as e:
            logger.error(f"Ошибка генерации совета: {e}", exc_info=True)
            return self._get_fallback_advice(situation)

    def _create_advice_prompt(self, user_context: str, situation: str) -> str:
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


ai = HuggingFaceAI()
