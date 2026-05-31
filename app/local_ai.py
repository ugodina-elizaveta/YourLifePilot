import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
import gc
import os

logger = logging.getLogger(__name__)


class LocalAI:
    """Локальная модель LoRA r=2 (оптимизировано для CPU)"""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.model_path = "/YourLifePilot/models/lora_r2"

    def load_model(self):
        if self.is_loaded:
            return

        try:
            logger.info("🚀 Загрузка локальной модели LoRA r=2...")

            # Ограничиваем потоки
            torch.set_num_threads(4)
            os.environ["OMP_NUM_THREADS"] = "4"
            os.environ["MKL_NUM_THREADS"] = "4"

            gc.collect()

            logger.info("📥 Загрузка токенизатора...")
            self.tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3.5-mini-instruct", trust_remote_code=True)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            logger.info("📥 Загрузка базовой модели (4-bit)...")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            )

            base_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Phi-3.5-mini-instruct",
                quantization_config=bnb_config,
                device_map="cpu",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

            logger.info("📥 Загрузка LoRA адаптера...")
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            self.model.eval()

            for param in self.model.parameters():
                param.requires_grad = False

            self.is_loaded = True
            logger.info("✅ Локальная модель LoRA r=2 успешно загружена")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки: {e}")
            self.is_loaded = False

    def is_available(self) -> bool:
        return self.is_loaded

    def generate_advice(self, user_context: str, situation: str, user_data: dict = None) -> str:
        if not self.is_loaded:
            return "Извини, модель ещё загружается. Попробуй через минуту."

        try:
            # Более короткий промпт для ускорения
            prompt = (
                "<|system|>\nТы — эмпатичный помощник. Отвечай кратко, поддерживающе, на русском.<|end|>\n"
                f"<|user|>\n{user_context}<|end|>\n<|assistant|>\n"
            )

            inputs = self.tokenizer(prompt, return_tensors="pt")
            input_len = inputs.input_ids.shape[1]

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=80,  # больше токенов для осмысленного ответа
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.2,  # чтобы не зацикливалась
                )

            response = self.tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()

            logger.info(f"✅ Сгенерирован ответ: {response[:100]}...")
            return response if response else "Понимаю тебя. Расскажи подробнее, что тебя беспокоит."

        except Exception as e:
            logger.error(f"❌ Ошибка генерации: {e}")
            return "Извини, сейчас я немного загружен. Попробуй ещё раз."

    def analyze_sentiment(self, text: str) -> dict:
        return {'label': 'NEUTRAL', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        return {'label': 'neutral', 'score': 0.5}

    def analyze_mood_trend(self, mood_history: list) -> dict:
        return {'trend': 'stable', 'message': 'Продолжай в том же духе!', 'average': 2.5}


local_ai = LocalAI()
