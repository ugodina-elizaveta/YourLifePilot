import logging
import os
import re


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

            # 1. Анализ тональности (лёгкая модель)
            self.models['sentiment'] = pipeline(
                "sentiment-analysis", model="blanchefort/rubert-base-cased-sentiment", device=self.device
            )
            logger.info("✅ Модель анализа тональности загружена")

            # 2. Эмоции
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

            # 3. Генерация текста (попробуем другую модель)
            try:
                model_name = "ai-forever/rugpt3medium_based_on_gpt2"
                self.models['generation'] = pipeline(
                    "text-generation",
                    model=model_name,
                    device=self.device,
                    max_new_tokens=100,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.2,
                    pad_token_id=50256,
                    return_full_text=False,
                )
                logger.info(f"✅ Модель генерации загружена: {model_name}")
            except Exception as e:
                logger.error(f"❌ Не удалось загрузить модель: {e}")
                self.models['generation'] = None

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
        """Генерирует совет с улучшенным промптом"""
        try:
            # Если модель не загрузилась, сразу fallback
            if not self.models.get('generation'):
                logger.warning("Модель генерации не загружена, использую fallback")
                return self._get_fallback_advice(situation)

            prompt = self._create_detailed_prompt(user_context, situation)
            logger.info(f"🤖 Генерирую совет для '{situation}'")

            result = self.models['generation'](prompt, max_new_tokens=100)[0]
            raw_advice = result['generated_text'].strip()
            logger.info(f"📝 Сырой ответ: {raw_advice[:100]}...")

            # Постобработка
            cleaned = self._clean_advice(raw_advice)

            if cleaned and len(cleaned) > 20:
                logger.info(f"✅ Совет: {cleaned}")
                return cleaned
            else:
                logger.warning("Ответ слишком короткий, fallback")
                return self._get_fallback_advice(situation)

        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            return self._get_fallback_advice(situation)

    def _create_detailed_prompt(self, user_context: str, situation: str) -> str:
        """Создаёт подробный промпт для модели"""
        prompts = {
            'stress': """
                Человек испытывает стресс. Дай ему короткий, добрый и практический совет,
                как успокоиться прямо сейчас. Напиши 2-3 предложения.
                
                Совет:""",
            'sleep': """
                Человек хочет улучшить свой сон. Посоветуй простые и эффективные способы,
                как быстрее засыпать и лучше высыпаться. Напиши 2-3 предложения.
                
                Совет:""",
            'sad': """
                Человеку грустно. Поддержи его тёплыми словами, дай простой совет,
                как поднять настроение. Напиши 2-3 предложения.
                
                Совет:""",
            'morning': """
                Человек только проснулся и хочет начать день бодро и позитивно.
                Посоветуй простые утренние ритуалы для хорошего дня. Напиши 2-3 предложения.
                
                Совет:""",
            'evening': """
                Вечер, человек готовится ко сну. Посоветуй, как расслабиться после трудного дня
                и подготовиться к здоровому сну. Напиши 2-3 предложения.
                
                Совет:""",
            'general': """
                Дай дружеский совет человеку, который обратился за поддержкой.
                Ответ должен быть тёплым, коротким и полезным. Напиши 2-3 предложения.
                
                Совет:""",
        }
        return prompts.get(situation, prompts['general'])

    def _clean_advice(self, text: str) -> str:
        """Очищает и форматирует ответ"""
        # Убираем диалоговые метки
        text = re.sub(r'@@|ПЕРВЫЙ|ВТОРОЙ|ТРЕТИЙ|Пользователь:|Помощник:', '', text)

        # Убираем странные символы
        text = re.sub(r'[^\w\s.,!?;:()\-]', ' ', text)

        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()

        # Берём первые 2-3 предложения
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if sentences:
            text = ' '.join(sentences[:3])

        # Обрезаем длину
        if len(text) > 200:
            text = text[:200] + '...'

        return text

    def _get_fallback_advice(self, situation: str) -> str:
        """Запасные советы (уже хорошие)"""
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


# Создаём экземпляр
ai = HuggingFaceAI()
