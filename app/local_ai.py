# Локальная модель LoRA r=2 вместо YandexGPT

import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from app.config import FORBIDDEN_TOPICS

logger = logging.getLogger(__name__)


class LocalAI:
    """Локальная модель LoRA r=2 для генерации эмпатичных ответов"""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self.is_loaded = False
        self.model_path = "/YourLifePilot/models/lora_r2"

    def load_model(self):
        """Загружает модель LoRA r=2 в память"""
        if self.is_loaded:
            logger.info("Модель уже загружена")
            return

        try:
            logger.info("🚀 Загрузка локальной модели LoRA r=2...")

            # Определяем устройство
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Используется устройство: {self.device}")

            # Загружаем токенизатор
            self.tokenizer = AutoTokenizer.from_pretrained(
                "microsoft/Phi-3.5-mini-instruct",
                trust_remote_code=True
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Загружаем базовую модель
            base_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Phi-3.5-mini-instruct",
                device_map="auto" if torch.cuda.is_available() else None,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                trust_remote_code=True,
                use_cache=False,
            )

            # Загружаем LoRA адаптер
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            self.model.eval()

            self.is_loaded = True
            logger.info("✅ Локальная модель LoRA r=2 успешно загружена")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки локальной модели: {e}")
            self.is_loaded = False
            raise

    def generate_advice(self, user_context: str, situation: str, user_data: dict = None) -> str:
        """
        Генерирует персонализированный совет с помощью локальной модели
        """
        # Проверяем на запрещённые темы
        context_lower = user_context.lower()
        for forbidden in FORBIDDEN_TOPICS:
            if forbidden in context_lower:
                return ("Мне очень жаль, что ты проходишь через это. "
                        "Пожалуйста, обратись за профессиональной помощью: "
                        "круглосуточный телефон доверия 8-800-2000-122. "
                        "Я здесь, чтобы поддержать, но в этой ситуации важно поговорить со специалистом.")

        if not self.is_loaded:
            self.load_model()

        try:
            # Формируем промпт
            system_message = (
                "Ты — эмпатичный помощник, оказывающий психологическую поддержку. "
                "Отвечай доброжелательно, поддерживающе и по существу. Будь кратким (2-3 предложения)."
            )

            prompt = f"<|system|>\n{system_message}<|end|>\n<|user|>\n{user_context}<|end|>\n<|assistant|>\n"

            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=150,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Извлекаем только ответ ассистента
            if "<|assistant|>" in response:
                response = response.split("<|assistant|>")[-1].strip()

            logger.info(f"✅ Локальная модель ответила: {response[:100]}...")
            return response

        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа локальной моделью: {e}")
            return "Извини, сейчас я немного занят. Попробуй ещё раз чуть позже."

    def analyze_sentiment(self, text: str) -> dict:
        """Заглушка для совместимости с существующим кодом"""
        return {'label': 'NEUTRAL', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        """Заглушка для совместимости с существующим кодом"""
        return {'label': 'neutral', 'score': 0.5}

    def analyze_mood_trend(self, mood_history: list) -> dict:
        """Заглушка для совместимости с существующим кодом"""
        return {'trend': 'stable', 'message': 'Продолжай в том же духе!', 'average': 2.5}


# Создаём глобальный экземпляр
local_ai = LocalAI()
