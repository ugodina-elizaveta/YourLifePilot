import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

logger = logging.getLogger(__name__)


class LocalAI:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.model_path = "/YourLifePilot/models/lora_r2"

    def load_model(self):
        if self.is_loaded:
            return

        try:
            logger.info("🚀 Загрузка локальной модели LoRA r=2 в 4-битном формате...")

            # 4-битная конфигурация для экономии памяти
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )

            self.tokenizer = AutoTokenizer.from_pretrained(
                "microsoft/Phi-3.5-mini-instruct",
                trust_remote_code=True
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Загружаем базовую модель в 4-битном формате (на CPU)
            base_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Phi-3.5-mini-instruct",
                quantization_config=bnb_config,
                device_map="cpu",  # принудительно на CPU
                torch_dtype=torch.float16,
                trust_remote_code=True,
                use_cache=False,
            )

            # Загружаем LoRA адаптер
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            self.model.eval()

            self.is_loaded = True
            logger.info("✅ Локальная модель LoRA r=2 успешно загружена (4-bit)")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки локальной модели: {e}")
            self.is_loaded = False

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
