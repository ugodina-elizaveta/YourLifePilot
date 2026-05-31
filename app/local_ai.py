import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import gc
import os

logger = logging.getLogger(__name__)


class LocalAI:
    """Локальная модель LoRA r=2 (CPU, float16)"""

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

            torch.set_num_threads(4)
            os.environ["OMP_NUM_THREADS"] = "4"

            gc.collect()

            logger.info("📥 Токенизатор...")
            self.tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3.5-mini-instruct", trust_remote_code=True)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            logger.info("📥 Базовая модель (CPU, float16)...")
            base_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Phi-3.5-mini-instruct",
                device_map="cpu",
                torch_dtype=torch.float16,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

            logger.info("📥 LoRA адаптер...")
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            self.model.eval()

            for param in self.model.parameters():
                param.requires_grad = False

            self.is_loaded = True
            logger.info("✅ Модель готова")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки: {e}")
            self.is_loaded = False

    def is_available(self) -> bool:
        return self.is_loaded

    def generate_advice(self, user_context: str, situation: str, user_data: dict = None) -> str:
        if not self.is_loaded:
            return "Извини, модель ещё загружается. Попробуй через минуту."

        # Проверка запрещённых тем
        from app.config import FORBIDDEN_TOPICS

        if any(word in user_context.lower() for word in FORBIDDEN_TOPICS):
            return (
                "Мне очень жаль, что ты проходишь через это. "
                "Пожалуйста, обратись за профессиональной помощью:\n"
                "📞 Круглосуточный телефон доверия: 8-800-2000-122\n"
                "Я здесь, чтобы поддержать, но в этой ситуации "
                "важно поговорить со специалистом."
            )

        try:
            # Ситуационные подсказки
            situation_hints = {
                'stress': "Дай практический совет как справиться со стрессом.",
                'sleep': "Посоветуй что-то простое для улучшения сна.",
                'sad': "Поддержи тёплыми словами, подними настроение.",
                'morning': "Посоветуй как начать день бодро.",
                'evening': "Посоветуй как расслабиться перед сном.",
                'general': "Дай полезный совет.",
            }
            hint = situation_hints.get(situation, situation_hints['general'])

            prompt = (
                "<|system|>\nТы — эмпатичный психологический помощник. "
                "Отвечай на русском языке. "
                "Будь поддерживающим и доброжелательным. "
                "Пиши 3-5 предложений, заканчивай мысль полностью. "
                f"{hint}<|end|>\n"
                f"<|user|>\n{user_context}<|end|>\n<|assistant|>\n"
            )

            inputs = self.tokenizer(prompt, return_tensors="pt")
            input_len = inputs.input_ids.shape[1]

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=120,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )

            response = self.tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()

            # Мягкая очистка: обрезаем только явный мусор
            for bad in ['<|end|>', '<|user|>', '<|system|>', '<|assistant|>']:
                if bad in response:
                    response = response.split(bad)[0].strip()

            # Убираем незаконченные предложения в конце
            if response and response[-1] not in '.!?':
                # Находим последний знак препинания
                for i in range(len(response) - 1, 0, -1):
                    if response[i] in '.!?':
                        response = response[: i + 1]
                        break

            if not response or len(response) < 10:
                response = "Понимаю тебя. Расскажи подробнее, что тебя беспокоит."

            logger.info(f"✅ Ответ ({len(response)} символов): {response[:100]}...")
            return response

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
