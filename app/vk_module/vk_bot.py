import logging
from app.vk_module.vk_api import VkApi
from app.vk_module.vk_handler import VkHandler
import json

logger = logging.getLogger(__name__)


class VkBot:
    def __init__(self):
        self.api = VkApi()
        self.handler = VkHandler(self.api)

    async def process_message(self, msg: dict):
        """Обрабатывает входящее сообщение от VK"""
        user_id = str(msg['from_id'])
        text = msg.get('text', '').strip()
        payload = msg.get('payload', '')

        # Если есть payload (от callback-кнопки), извлекаем команду
        cmd = None
        if payload:
            try:
                payload_data = json.loads(payload) if isinstance(payload, str) else payload
                cmd = payload_data.get('cmd')
            except Exception:
                pass

        await self.handler.handle(user_id, text, cmd)


# Глобальный экземпляр
vk_bot = VkBot()
