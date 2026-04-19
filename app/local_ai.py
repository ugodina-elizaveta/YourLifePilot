# /YourLifePilot/app/local_ai.py

import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from app.config import FORBIDDEN_TOPICS
import gc
import psutil
import os

logger = logging.getLogger(__name__)


class LocalAI:
    """Локальная модель LoRA r=2 (оптимизировано для 16GB RAM)"""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.model_path = "/YourLifePilot/models/lora_r2"

    def load_model(self):
        """Загружает модель с оптимизацией под 16GB RAM"""
        if self.is_loaded:
            logger.info("Модель уже загружена")
            return

        try:
            logger.info("🚀 Загрузка локальной модели LoRA r=2...")
            
            # Проверяем доступную память
            available_ram_gb = psutil.virtual_memory().available / (1024**3)
            logger.info(f"📊 Доступно RAM: {available_ram_gb:.1f} GB")

            # Ограничиваем потоки CPU (у вас 4 ядра, оставляем 2 для модели)
            torch.set_num_threads(2)
            os.environ["OMP_NUM_THREADS"] = "2"
            os.environ["MKL_NUM_THREADS"] = "2"
            
            # Очищаем память
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("📥 Загрузка токенизатора...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                "microsoft/Phi-3.5-mini-instruct",
                trust_remote_code=True
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            logger.info("📥 Загрузка базовой модели...")
            # Оптимизированные настройки для 16GB RAM
            base_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Phi-3.5-mini-instruct",
                device_map="cpu",
                torch_dtype=torch.float16,
                trust_remote_code=True,
                use_cache=False,
                low_cpu_mem_usage=True,
                attn_implementation="eager",  # Без flash attention
            )
            
            # Логируем память после загрузки базы
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            logger.info(f"📊 RAM после базы: {memory_mb:.0f} MB")

            logger.info("📥 Загрузка LoRA адаптера...")
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            self.model.eval()

            # Замораживаем все параметры
            for param in self.model.parameters():
                param.requires_grad = False

            self.is_loaded = True
            logger.info("✅ Локальная модель LoRA r=2 успешно загружена")

            # Финальный лог памяти
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            memory_percent = psutil.virtual_memory().percent
            logger.info(f"📊 Итоговое использование RAM: {memory_mb:.0f} MB ({memory_percent:.1f}%)")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки локальной модели: {e}")
            self.is_loaded = False

    def is_available(self) -> bool:
        return self.is_loaded

    def generate_advice(self, user_context: str, situation: str, user_data: dict = None) -> str:
        # Проверка на запрещённые темы
        context_lower = user_context.lower()
        for forbidden in FORBIDDEN_TOPICS:
            if forbidden in context_lower:
                return ("Мне очень жаль, что ты проходишь через это. "
                        "Пожалуйста, обратись за профессиональной помощью: "
                        "круглосуточный телефон доверия 8-800-2000-122. "
                        "Я здесь, чтобы поддержать, но в этой ситуации важно поговорить со специалистом.")

        # Ленивая загрузка при первом вызове
        if not self.is_loaded:
            self.load_model()
            if not self.is_loaded:
                return "Извини, сейчас я загружаюсь. Попробуй ещё раз через минуту."

        try:
            system_message = (
                "Ты — эмпатичный помощник, оказывающий психологическую поддержку. "
                "Отвечай доброжелательно, поддерживающе и по существу. Будь кратким (2-3 предложения)."
            )

            prompt = f"<|system|>\n{system_message}<|end|>\n<|user|>\n{user_context}<|end|>\n<|assistant|>\n"

            inputs = self.tokenizer(prompt, return_tensors="pt")

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=100,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                    use_cache=False,
                )

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            if "<|assistant|>" in response:
                response = response.split("<|assistant|>")[-1].strip()

            logger.info(f"✅ Локальная модель ответила: {response[:100]}...")
            return response

        except Exception as e:
            logger.error(f"❌ Ошибка генерации: {e}")
            return ("Извини, сейчас я немного загружен. Попробуй ещё раз чуть позже. "
                    "А пока могу предложить сделать несколько глубоких вдохов — это помогает.")

    def analyze_sentiment(self, text: str) -> dict:
        return {'label': 'NEUTRAL', 'score': 0.5}

    def analyze_emotion(self, text: str) -> dict:
        return {'label': 'neutral', 'score': 0.5}

    def analyze_mood_trend(self, mood_history: list) -> dict:
        return {'trend': 'stable', 'message': 'Продолжай в том же духе!', 'average': 2.5}

    def unload_model(self):
        """Выгружает модель для освобождения памяти (опционально)"""
        if self.is_loaded:
            del self.model
            del self.tokenizer
            gc.collect()
            self.is_loaded = False
            logger.info("🔄 Модель выгружена из памяти")


local_ai = LocalAI()